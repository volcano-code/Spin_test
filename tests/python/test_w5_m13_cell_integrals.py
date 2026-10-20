"""M13 independently checks exact volume cell integrals and W0-native Jacobians."""
import numpy as np
import pytest
import torch

from research.NeuralMoments.models.deeponet.m8_analytic_data import Shape,analytic_truth
from research.NeuralMoments.models.deeponet.m13_cell_integrals import (
    CellwiseMomentReference, B, vertical_native_c)


def uniform(n=8,rho=1.4):
    d=np.zeros((4,n,n,n),dtype=np.float64)
    d[0]=rho;d[1]=1
    return d


@pytest.mark.parametrize('n',[8,12,20])
@pytest.mark.parametrize('h',[-.51,-.17,.11,.39])
def test_exact_uniform_box_integral_and_full_ambient_J(n,h):
    D=uniform(n)
    cut=CellwiseMomentReference.bind(D).evaluate(vertical_native_c(h))
    native,truth,J=analytic_truth(Shape('box',(0.,)*3,(1.,)*3,density=1.4),h)
    assert cut['derivative_status']=='PIECEWISE_CONSTANT_SMOOTH_CELL_INTERIOR'
    np.testing.assert_allclose(cut['r'],truth,atol=2e-12,rtol=2e-12)
    np.testing.assert_allclose(cut['Jc'],J,atol=2e-11,rtol=2e-11)
    np.testing.assert_allclose(cut['Jc'] @ native,np.zeros(10),atol=3e-12)
    H=cut['Jc']/B[None,:]
    np.testing.assert_allclose(H,H.T,atol=3e-12)
    assert np.linalg.eigvalsh((H+H.T)/2).min()>-1e-11


def test_nonsymmetric_density_and_undoubled_moments():
    n=9;d=uniform(n)
    x=np.linspace(-1+1/n,1-1/n,n)
    xx,yy,zz=np.meshgrid(x,x,x,indexing='ij')
    d[0]=1.25 + .18*xx + .23*yy - .12*zz + .1*xx*yy
    cache=CellwiseMomentReference.bind(d)
    h=.16
    c=vertical_native_c(h)
    a=cache.evaluate(c)
    assert abs(a['r'][9])>1e-5
    assert abs(a['Jc'][0,7])>0
    np.testing.assert_allclose(a['Jc']/B[None,:],(a['Jc']/B[None,:]).T,atol=3e-12)
    eps=1e-5
    cp=vertical_native_c(h+eps);cm=vertical_native_c(h-eps)
    dcdh=(cp-cm)/(2*eps)
    fd=(cache.evaluate(cp)['r']-cache.evaluate(cm)['r'])/(2*eps)
    np.testing.assert_allclose(fd,a['Jc'] @ dcdh,atol=2e-7,rtol=2e-7)


def test_full_empty_strict_zero_derivative_and_contact_exclusions():
    cache=CellwiseMomentReference.bind(uniform())
    zero=cache.evaluate(vertical_native_c(1.25))
    full=cache.evaluate(vertical_native_c(-1.25))
    assert zero['derivative_status']=='STRICT_SIGN_CONSTANT_P0'
    np.testing.assert_array_equal(zero['r'],np.zeros(10))
    np.testing.assert_array_equal(zero['Jc'],np.zeros((10,10)))
    np.testing.assert_array_equal(full['Jc'],np.zeros((10,10)))
    assert full['r'][0]==pytest.approx(8*1.4)
    for h in (-1,1,-.5,0.,.5):
        # all 8^3 cell planes are conservative discontinuity exclusions
        out=cache.evaluate(vertical_native_c(h))
        assert out['Jc'] is None
        assert 'UNAVAILABLE' in out['derivative_status']


def test_nonvertical_native_and_nonunit_never_promoted():
    cache=CellwiseMomentReference.bind(uniform())
    c=vertical_native_c(.23)
    c[7]=.01
    with pytest.raises(ValueError,match='ONLY_NATIVE_POSITIVE_VERTICAL'):
        cache.evaluate(c)
    with pytest.raises(ValueError,match='NONUNIT'):
        cache.evaluate(vertical_native_c(.23)*1.1)
    with pytest.raises(ValueError,match='ONLY_NATIVE_POSITIVE_VERTICAL'):
        cache.evaluate(-vertical_native_c(.23))


@pytest.mark.parametrize('case', ['nan','negative_rho','bad_occ','bad_shape','nonfloat','needs_grad'])
def test_bad_volume_fails_closed(case):
    d=uniform()
    if case=='nan':d[0,1,1,1]=np.nan
    if case=='negative_rho':d[0,1,1,1]=-1
    if case=='bad_occ':d[1,1,1,1]=1.2
    if case=='bad_shape':d=d[:3]
    if case=='nonfloat':d=d.astype(np.int64)
    if case=='needs_grad':d=torch.from_numpy(d).requires_grad_()
    with pytest.raises(ValueError):CellwiseMomentReference.bind(d)


def test_replay_is_deterministic_and_does_not_modify_input():
    rng=np.random.default_rng(918)
    d=np.zeros((4,8,8,8),dtype=np.float32)
    d[0]=rng.uniform(.01,2.,(8,8,8));d[1]=rng.integers(0,2,(8,8,8));original=d.copy()
    a=CellwiseMomentReference.bind(d);b=CellwiseMomentReference.bind(d)
    assert a.source_sha256==b.source_sha256
    for h in (-.27,.12):
        np.testing.assert_array_equal(a.evaluate(vertical_native_c(h))['r'],b.evaluate(vertical_native_c(h))['r'])
    np.testing.assert_array_equal(d,original)
    assert not a.weights.flags.writeable


def test_density_linear_scaling_and_fixed_F_not_double_counted():
    D=uniform(8,1.0);R=CellwiseMomentReference.bind(D)
    h=.12;c=vertical_native_c(h)
    d2=D.copy();d2[0]*=2
    r1=R.evaluate(c);r2=CellwiseMomentReference.bind(d2).evaluate(c)
    np.testing.assert_allclose(r2['r'],2*r1['r'],atol=2e-12)
    np.testing.assert_allclose(r2['Jc'],2*r1['Jc'],atol=2e-12)
    assert 'r_fixed' not in r1 and 'r_total' not in r1


def test_c_cross_coefficient_order_matches_W0_double_mapping():
    cache=CellwiseMomentReference.bind(uniform(8))
    c=vertical_native_c(.123)
    result=cache.evaluate(c)
    H=result['Jc']/B[None,:]
    np.testing.assert_allclose(result['Jc'][:,7],2*H[:,7],atol=1e-13)
    np.testing.assert_allclose(result['Jc'][:,8],2*H[:,8],atol=1e-13)
    np.testing.assert_allclose(result['Jc'][:,9],2*H[:,9],atol=1e-13)


def test_numeric_cache_sha_rejects_mutated_precomputation():
    D=uniform(8)
    r=CellwiseMomentReference.bind(D)
    r.assert_same_voxel_source(D)
    D2=D.copy();D2[0,0,0,0]+=0.01
    with pytest.raises(ValueError,match='SOURCE_IDENTITY_MISMATCH'):
        r.assert_same_voxel_source(D2)
    # A caller may forcibly mark a numpy array writable. The cached data
    # digest must still detect such unauthorized changes before any result.
    r.xy_power_sums.setflags(write=True)
    r.xy_power_sums[0,0,0]+=0.1
    with pytest.raises(ValueError,match='NUMERIC_CONTENT_TAMPERED'):
        r.evaluate(vertical_native_c(.13))
