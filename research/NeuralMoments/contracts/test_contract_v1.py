"""Run: python -m pytest -q research/NeuralMoments/contracts/test_contract_v1.py"""
import math
import numpy as np
import pytest
from .moment_coordinates import (
    B,RAW_R_ORDER,NATIVE_C_ORDER,normalize_new_c,evaluate_native,
    native_to_monomial_coefficients,monomial_to_native_coefficients,
    raw_to_tensors,tensors_to_raw,pushforward_raw,jacobian_native_to_monomial,
    continuum_hessian_diagnostic,normalized_component_error,merge_cached_fixed)
from .physical_transforms import pullback_native,physical_from_normalized
from .analytic_references import box,ellipsoid,sphere_cap,sphere_cap_ambient_jacobian


def test_orders_factor_two_nonzero_xy_xz_yz():
    assert RAW_R_ORDER==("M","LX","LY","LZ","QXX","QYY","QZZ","QYZ","QXZ","QXY")
    assert tuple(np.diag(B))==(1.,)*7+(2.,)*3
    c=np.array((.3,.2,-.8,.1,1.,2.,3.,4.,5.,6.))
    x,y,z=.4,-.6,.7
    cpp_value=(c[0]+c[1]*x+c[2]*y+c[3]*z+c[4]*x*x+c[5]*y*y+c[6]*z*z
               +2*c[7]*y*z+2*c[8]*x*z+2*c[9]*x*y)
    assert evaluate_native(c,(x,y,z))==pytest.approx(cpp_value,abs=1e-14)
    np.testing.assert_allclose(monomial_to_native_coefficients(native_to_monomial_coefficients(c)),c)


def test_projective_positive_ray_and_negative_sign():
    c=normalize_new_c((-.2,0.,0.,1.,0.,0.,0.,0.,0.,0.))
    np.testing.assert_allclose(normalize_new_c(5*c),c,atol=1e-15)
    assert evaluate_native(-c,(0.,0.,.9))==-evaluate_native(c,(0.,0.,.9))
    with pytest.raises(ValueError):normalize_new_c([0.]*10)


def test_box_transformed_against_independent_gauss_integral():
    c=np.array((.2,-.3,.5));h=np.array((.7,.8,1.1))
    theta=.47
    R=np.array(((math.cos(theta),-math.sin(theta),0.),(math.sin(theta),math.cos(theta),0.),(0.,0.,1.)))
    A=R@np.diag((1.8,.6,1.3));t=np.array((.4,-.2,.5))
    actual=pushforward_raw(box(c,h,1.3),A,t,density_ratio=2.4)
    roots,weights=np.polynomial.legendre.leggauss(3)
    expected=np.zeros(10)
    for i in range(3):
        for j in range(3):
            for k in range(3):
                p=A@(c+h*np.array((roots[i],roots[j],roots[k])))+t
                x,y,z=p
                m=np.array((1.,x,y,z,x*x,y*y,z*z,y*z,x*z,x*y))
                expected+=1.3*2.4*abs(np.linalg.det(A))*np.prod(h)*weights[i]*weights[j]*weights[k]*m
    np.testing.assert_allclose(actual,expected,rtol=5e-14,atol=1e-13)
    assert abs(actual[7])>1e-3 and abs(actual[9])>1e-3


def test_sphere_rotated_ellipsoid_density():
    theta=.61
    R=np.array(((1.,0.,0.),(0.,math.cos(theta),-math.sin(theta)),(0.,math.sin(theta),math.cos(theta))))
    axes=np.array((1.2,1.7,.9))
    t=(.2,-.7,.4)
    actual=pushforward_raw(ellipsoid((0,0,0),(1,1,1)),R@np.diag(axes),t,density_ratio=3.)
    np.testing.assert_allclose(actual,ellipsoid(t,axes,R,3.),rtol=3e-14,atol=3e-14)


def test_normalization_with_translation_density_and_scale():
    base=box((0,0,0),(.5,.5,.5))
    L,R=2.3,4.2;t=np.array((.7,-.2,.4))
    result=physical_from_normalized(base,original_origin=t,length_units=L,density_units=R)
    M,first,Q=raw_to_tensors(result)
    assert M==pytest.approx(base[0]*L**3*R)
    np.testing.assert_allclose(first,M*t,atol=1e-14)
    assert Q[0,0]==pytest.approx(base[4]*L**5*R+M*t[0]**2)


def test_quadric_pullback_sign_and_coordinate_frame():
    c=normalize_new_c((1.,.2,-.7,1.2,-.8,.4,.9,.3,-.2,.6))
    a=.31;A=1.6*np.array(((math.cos(a),-math.sin(a),0.),(math.sin(a),math.cos(a),0.),(0.,0.,1.)))
    t=np.array((.1,-.4,.7));p=pullback_native(c,A,t)
    factors=[]
    for y in ((.3,-.1,.5),(-.7,.4,.2),(.6,.2,-.3)):
        v=evaluate_native(c,A@np.array(y)+t)
        factors.append(evaluate_native(p,y)/v)
    assert min(factors)>0 and max(factors)-min(factors)<1e-13


def test_sphere_cap_P0_independent_quadrature():
    R,h,rho=1.4,.2,2.1
    r=sphere_cap(R,h,rho)
    roots,w=np.polynomial.legendre.leggauss(48)
    z=(R-h)/2*roots+(R+h)/2
    v=rho*(R-h)/2*float(w@(math.pi*(R*R-z*z)))
    assert abs(v-r[0])<2e-13


def test_P0_J_native_not_symmetric_but_J_B_inverse_symmetric():
    c=normalize_new_c((-.2,0,0,1,0,0,0,0,0,0))
    J=sphere_cap_ambient_jacobian(1.,.2,vertical_coefficient=c[3])
    assert np.max(np.abs(J-J.T))>.1
    H=jacobian_native_to_monomial(J)
    np.testing.assert_allclose(H,H.T,rtol=1e-13,atol=1e-13)
    assert continuum_hessian_diagnostic(J,ambient=True,smooth_continuum=True)["maximum_absolute_asymmetry"]<1e-13
    with pytest.raises(ValueError):continuum_hessian_diagnostic(J,ambient=False,smooth_continuum=True)


def test_P0_analytic_vertical_derivative_finite_difference():
    c=normalize_new_c((-.2,0,0,1,0,0,0,0,0,0))
    J=sphere_cap_ambient_jacobian(1.,.2,vertical_coefficient=c[3])
    eps=1e-6
    for i in (0,3):
        hi,lo=c.copy(),c.copy();hi[i]+=eps;lo[i]-=eps
        fd=(sphere_cap(1.,-hi[0]/hi[3])-sphere_cap(1.,-lo[0]/lo[3]))/(2*eps)
        np.testing.assert_allclose(fd,J[:,i],rtol=2e-8,atol=2e-9)
    np.testing.assert_allclose(J@c,np.zeros(10),atol=2e-14)


def test_cached_F_and_error_scale_no_universal_gate():
    F=box((.1,.2,.3),(.1,.1,.1),2.)
    D=box((.4,.2,-.2),(.1,.2,.4))
    np.testing.assert_allclose(merge_cached_fixed(F,D),F+D)
    e=normalized_component_error([8.,16.,16.,16.,32.,32.,32.,32.,32.,32.],[0.]*10,length_ref=2.,density_ref=1.)
    np.testing.assert_allclose(e,np.ones(10))
    with pytest.raises(ValueError):pushforward_raw(F,np.zeros((3,3)))
