"""Analytic P0 ball-halfspace used only for numeric tangent-slope diagnostics."""
from __future__ import annotations

import math
import numpy as np
import pytest

from .tangent_neighborhood import audit_tangent_neighborhood, NeighborhoodRejected
B=np.diag([1.]*7+[2.]*3)  # Frozen native-entry to monomial map

BASE=np.array([-.2,0.,0.,1.,0.,0.,0.,0.,0.,0.]);BASE/=np.linalg.norm(BASE)
SOURCE_ID='a'*64


def _raw_spherical_cap_unit(radius,cut):
    R,h=radius,cut
    m=math.pi*(2*R**3/3-R*R*h+h**3/3)
    z=math.pi*(R*R-h*h)**2/4
    qz=math.pi*(R*R*(R**3-h**3)/3-(R**5-h**5)/5)
    qx=math.pi/4*(R**4*(R-h)-2*R*R*(R**3-h**3)/3+(R**5-h**5)/5)
    return np.array([m,0.,0.,z,qx,qx,qz,0.,0.,0.])


def _cap(c):
    # Rotate a ball cap so its positive linear half-space is a+b·x>=0.
    b=c[1:4];length=np.linalg.norm(b)
    h=-c[0]/length
    assert -1<h<1
    axis=b/length
    ref=np.array([0.,1.,0.])
    x=np.cross(ref,axis);x/=np.linalg.norm(x)
    y=np.cross(axis,x)
    R=np.column_stack((x,y,axis))
    r=_raw_spherical_cap_unit(1.,h)
    l=R@r[1:4]
    Q0=np.diag(r[4:7])
    Q=R@Q0@R.T
    return np.array([r[0],*l,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]])


def _jacobian(c):
    # Independent disk monomial integral Gram formula (NOT actual Cherchi J).
    h=-c[0]/c[3];rad=math.sqrt(1-h*h)
    powers=((0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),
            (0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))
    J=np.zeros((10,10))
    for i,p in enumerate(powers):
        for j,q in enumerate(powers):
            a,b,z=(p[k]+q[k] for k in range(3))
            if a%2 or b%2:continue
            disk=math.gamma((a+1)/2)*math.gamma((b+1)/2)/math.gamma((a+b)/2+2)*rad**(a+b+2)
            J[i,j]=h**z*disk/c[3]
    return J@B


def _data():
    raw=np.eye(10)[:,[0,1,2]]
    basis=[]
    for x in raw.T:
        v=x-BASE*(BASE@x)
        for earlier in basis:v-=earlier*(earlier@v)
        v/=np.linalg.norm(v)
        basis.append(v)
    basis=np.column_stack(basis)
    J=_jacobian(BASE)
    h=.02
    probes=[]
    for v in basis.T:
        entry={}
        for name,a in [('plus_h',h),('minus_h',-h),('plus_half',h/2),('minus_half',-h/2)]:
            c=math.cos(a)*BASE+math.sin(a)*v
            entry[name]={'c_native':c.tolist(),'r_design':_cap(c).tolist(),
                         'feature_branch_sha256':SOURCE_ID}
        probes.append(entry)
    kwargs=dict(native_c=BASE,Jc=J,tangent_basis=basis,probes=probes,
                step_radians=h,base_feature_branch_sha256=SOURCE_ID,length_ref=1.,density_ref=1.,
                max_normalized_jacobian_error=2e-7)
    return kwargs


def test_analytic_sphere_cap_tangent_three_directions():
    r=audit_tangent_neighborhood(**_data())
    assert r['status']=='NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED'
    assert not r['smooth_neighborhood_certified']
    assert not r['training_admissible']
    assert len(r['directions'])==3
    assert max(x['native_Jc_directional_max_normalized_error'] for x in r['directions'])<2e-7


def test_branch_change_veto_even_if_numeric_matches():
    kw=_data();kw['probes'][0]['plus_h']['feature_branch_sha256']='b'*64
    r=audit_tangent_neighborhood(**kw)
    assert r['status']=='OBSERVED_BRANCH_CHANGE_DERIVATIVE_EXCLUDED'
    assert not r['training_admissible']


def test_all_four_samples_on_other_branch_are_still_vetoed():
    kw=_data()
    for value in kw['probes'][0].values():
        value['feature_branch_sha256']='b'*64
    assert audit_tangent_neighborhood(**kw)['status']=='OBSERVED_BRANCH_CHANGE_DERIVATIVE_EXCLUDED'


def test_wrong_j_veto():
    kw=_data();kw['Jc'][0,1]+=.1
    r=audit_tangent_neighborhood(**kw)
    assert r['status']=='NUMERICAL_JACOBIAN_DISAGREEMENT_DERIVATIVE_EXCLUDED'


def test_explicit_per_case_error_budget_no_universal_percentage():
    kw=_data();kw['max_normalized_jacobian_error']=1e-20
    assert audit_tangent_neighborhood(**kw)['status']=='NUMERICAL_JACOBIAN_DISAGREEMENT_DERIVATIVE_EXCLUDED'


@pytest.mark.parametrize('change',[
    lambda kw:kw['probes'][0].pop('minus_half'),
    lambda kw:kw['probes'][0]['plus_h'].__setitem__('c_native',[0.]*10),
    lambda kw:kw['probes'][0]['plus_h'].__setitem__('r_design',[float('nan')]*10),
    lambda kw:kw['probes'][0]['plus_h'].__setitem__('feature_branch_sha256','BAD'),
    lambda kw:kw['tangent_basis'].__setitem__((0,0),.9),
    lambda kw:kw.update(step_radians=0),
    lambda kw:kw.update(step_radians=.4),
    lambda kw:kw.update(density_ref=float('inf')),
    lambda kw:kw.update(length_ref=-1.),
    lambda kw:kw.update(base_feature_branch_sha256="BAD"),
    lambda kw:kw.update(probes=kw['probes'][:-1]),
    lambda kw:kw.update(native_c=np.zeros(10)),
    lambda kw:kw['probes'][0]['plus_h'].__setitem__('c_native',[True]+[0.]*9),
])
def test_malformed_tangent_pack_fails_closed(change):
    kw=_data();change(kw)
    with pytest.raises(NeighborhoodRejected):audit_tangent_neighborhood(**kw)
