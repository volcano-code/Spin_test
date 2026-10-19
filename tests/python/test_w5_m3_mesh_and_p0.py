"""M3 strict closed-mesh input + independent W0-aligned analytic P0 decision smoke."""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

import numpy as np
import pytest
import torch

from research.NeuralMoments.models.deeponet.mesh_features import (
    MESH_FEATURE_DIM, cached_mesh_geometry, mesh_features, read_obj_features,
)
from research.NeuralMoments.models.deeponet.native_p0 import (
    B, cap_moments, cap_jacobian_native, native_vertical_c, dh_native_c,
    gauss_newton_decision,
)
from research.NeuralMoments.models.deeponet.model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment
from research.NeuralMoments.models.deeponet.contract_gate import raw_pushforward


def cube(center=(0.,0.,0.), half=(1.,1.,1.)):
    c, h = np.asarray(center), np.asarray(half)
    signs=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],
                    [-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]],dtype=float)
    v = c + signs*h
    f=np.array([(0,2,1),(0,3,2),(4,5,6),(4,6,7),
                (0,1,5),(0,5,4),(1,2,6),(1,6,5),
                (2,3,7),(2,7,6),(3,0,4),(3,4,7)], dtype=np.int64)
    return v,f


def analytic_box(center, half, density):
    M=8*np.prod(half)*density
    L=M*np.asarray(center)
    Q=M*(np.outer(center,center)+np.diag(np.asarray(half)**2/3))
    return np.array([M,*L,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]])


def test_box_exact_ten_moments_and_24_features():
    c,h=(.3,-.4,.5),(1.2,.8,1.5)
    d=mesh_features(*cube(c,h),density=2.3)
    np.testing.assert_allclose(d.original_moments,analytic_box(c,h,2.3),rtol=3e-14,atol=3e-14)
    assert len(d.geometry)==MESH_FEATURE_DIM
    assert d.geometry[0]==pytest.approx(d.original_moments[0])
    assert d.geometry[10:13]==pytest.approx(c)
    assert d.vertices==8 and d.faces==12 and not d.material_certified


def test_affine_frame_reflection_reoriented_and_w0_pushforward():
    v,f=cube((.1,-.2,.3),(.5,.7,.9))
    A=np.array([[-1.8,.3,0.],[.1,1.5,.2],[.0,.4,1.2]])
    t=np.array([.4,-.5,.6])
    mapped=v@A.T+t
    transformed=mesh_features(mapped,f[:,[0,2,1]],density=1.7)
    before=mesh_features(v,f,density=1.7)
    expected=raw_pushforward(before.original_moments,A,t)
    np.testing.assert_allclose(transformed.original_moments,expected,rtol=3e-13,atol=3e-13)
    framed=mesh_features(mapped,f[:,[0,2,1]],density=1.7,
             length_original_per_normalized=2.3,density_original_per_normalized=3.1,
             origin_original=(.2,-.1,.7))
    restored=raw_pushforward(framed.normalized_moments,np.eye(3)*2.3,[.2,-.1,.7],density_ratio=3.1)
    np.testing.assert_allclose(restored,framed.original_moments,rtol=4e-13,atol=4e-13)


@pytest.mark.parametrize('mutation', ['hole','flip','duplicate','inward','bad_vertex','dangling'])
def test_bad_or_unproven_mesh_rejected(mutation):
    v,f=cube()
    if mutation=='hole': f=f[:-1]
    if mutation=='flip': f[0]=f[0,[0,2,1]]
    if mutation=='duplicate': f[-1]=f[0]
    if mutation=='inward': f=f[:,[0,2,1]]
    if mutation=='bad_vertex': v[0,0]=np.nan
    if mutation=='dangling': v=np.vstack([v,[7.,7.,7.]])
    with pytest.raises(ValueError):mesh_features(v,f)


def test_obj_sha_byte_identity_and_nontriangle_rejection():
    v,f=cube()
    def payload():
        return ''.join('v '+' '.join(map(str,row))+'\n' for row in v)+''.join('f '+' '.join(str(i+1) for i in tri)+'\n' for tri in f)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'closed.obj'
        path.write_text(payload(),encoding='utf8')
        a=read_obj_features(path)
        assert a.source_sha256==hashlib.sha256(path.read_bytes()).hexdigest()
        path.write_text('# provenance changed\n'+payload(),encoding='utf8')
        b=read_obj_features(path)
        assert a.source_sha256 != b.source_sha256
        np.testing.assert_allclose(a.geometry,b.geometry)
        path.write_text(payload()+'f 1 2 3 4\n',encoding='utf8')
        with pytest.raises(ValueError,match='nontriangular'):read_obj_features(path)


@pytest.mark.parametrize('cls', [DeepONetMoment,GeometryMLPMoment])
def test_mesh_features_feed_cached_models_and_jacrev(cls):
    torch.manual_seed(101)
    model=cls(geometry_dim=24).double()
    desc=mesh_features(*cube())
    z=cached_mesh_geometry(model,desc,dtype=torch.float64)
    controls=torch.stack([torch.randn(10,dtype=torch.float64) for _ in range(5)])
    assert model.moment(z,controls).shape == (5,10)
    assert model.jacobian(z,controls).shape == (5,10,10)
    with pytest.raises(ValueError):cached_mesh_geometry(cls().double(),desc,dtype=torch.float64)


def test_native_cross_terms_and_psd_are_in_w0_q_basis():
    c=native_vertical_c(.23)
    assert np.linalg.norm(c)==pytest.approx(1.)
    J=cap_jacobian_native(1.3,.23,density=2.0)
    assert J.shape==(10,10)
    assert not np.allclose(J,J.T,atol=1e-4)
    H=J/B[None,:]
    np.testing.assert_allclose(H,H.T,atol=1e-12)
    assert np.linalg.eigvalsh(H).min()>-1e-10
    np.testing.assert_allclose(J@c,np.zeros(10),atol=1e-12)
    for h in (-.31,.15,.32):
        eps=1e-6
        finite=(cap_moments(1.3,h+eps)-cap_moments(1.3,h-eps))/(2*eps)
        np.testing.assert_allclose(finite,cap_jacobian_native(1.3,h)@dh_native_c(h),rtol=2e-8,atol=2e-9)


def test_native_p0_decision_exact_and_bad_predictor():
    exact=gauss_newton_decision(1.2,.25,-.12)
    assert exact['step_absolute_error'] == 0
    assert exact['signed_oracle_loss_gap']==0
    assert exact['loss_oracle_after'] < exact['loss_before']
    false=gauss_newton_decision(1.2,.25,-.12,
       predicted_r=cap_moments(1.2,.25)+.1,
       predicted_jc=np.zeros((10,10)))
    assert false['step_absolute_error']>0
    assert false['loss_candidate_after']>=exact['loss_oracle_after']
    assert false['truth_kind']=='ANALYTIC_P0_ONLY'


@pytest.mark.parametrize('height',[-1.,1.])
def test_p0_boundary_singularity_fails_closed(height):
    with pytest.raises(ValueError): cap_moments(1.,height)
    with pytest.raises(ValueError): cap_jacobian_native(1.,height)


def test_m3_audit_never_promotes_noncomparable_geometry_to_teacher():
    from research.NeuralMoments.models.deeponet.m3_audit import run
    report=run(seed=11,repeats=2)
    assert report['train_steps']==0
    assert report['no_real_teacher_or_accuracy_or_speedup_claim']
    assert report['non_comparable_inputs']
    assert report['mesh_feature_dimension']==24
    assert set(report['models_untrained_interface_probes'])=={'deeponet','geometry_mlp'}
