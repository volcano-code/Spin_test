"""M12 strict analytic saturation and no-native-admission regressions."""
import math
import numpy as np
import pytest
import torch
from research.NeuralMoments.models.deeponet.m8_analytic_data import Shape, make_voxel, analytic_truth
from research.NeuralMoments.models.deeponet.m11_cone_integrable import ConeIntegrableMoment
from research.NeuralMoments.models.deeponet.m12_saturation import (
    analytic_full_moments,analytic_aabb,strict_native_sign,SaturationGuard)
from test_w5_m11_cone_integrable import FrozenQuadrature


def unit(c):
    x=torch.tensor(c,dtype=torch.float64)
    return x/x.norm()


def shape(family='ellipsoid'):
    a=(.52,.71,.43) if family!='sphere' else (.52,)*3
    return Shape(family,(.11,-.12,.07),a,1.1)

@pytest.mark.parametrize('family',['box','sphere','ellipsoid'])
def test_full_matches_independent_cap_limit(family):
    s=shape(family)
    expected=analytic_full_moments(s)
    near=analytic_truth(s,-1+1e-9)[1]
    np.testing.assert_allclose(expected,near,rtol=1e-8,atol=3e-8)
    assert expected[0]>0 and expected[7]!=0


def test_exact_sign_conservative_cross_coefficients():
    s=shape()
    full=unit([1.,.04,-.02,.05,.02,-.03,.01,.06,-.05,.03])
    assert strict_native_sign(full,s)=='ANALYTIC_CERTIFIED_FULL'
    assert strict_native_sign(-full,s)=='ANALYTIC_CERTIFIED_EMPTY'
    # A zero native coefficient is neither a valid cutting function nor a normalizable one.
    with pytest.raises(ValueError,match='UNIT_LENGTH'):strict_native_sign(torch.zeros(10,dtype=full.dtype),s)
    with pytest.raises(ValueError,match='UNIT_LENGTH'):strict_native_sign(full*3,s)

@pytest.mark.parametrize('family',['box','sphere','ellipsoid'])
def test_boundary_full_empty_replaces_biased_surrogate(family):
    s=shape(family)
    from research.NeuralMoments.models.deeponet.m9_readonly_w6 import load_m9_w6
    import os
    root=os.environ.get('W5_M12_READONLY_W6_ROOT')
    if not root:pytest.skip('source-pinned W6 root not configured')
    _,_,w6,_=load_m9_w6(root)
    model=ConeIntegrableMoment(w6.GaussPotentialMoment(points_per_axis=6,hidden=32),mix=.75)
    guard=SaturationGuard(model)
    D=make_voxel(s)[None].float()
    cache=guard.bind_analytic_geometry(D,s)
    first=unit([1.,.05,.01,-.02,0,0,0,.03,.01,.02]).float()[None]
    second=-first
    full=guard.predict(cache,first)
    empty=guard.predict(cache,second)
    assert full['region']=='ANALYTIC_CERTIFIED_FULL'
    assert empty['region']=='ANALYTIC_CERTIFIED_EMPTY'
    assert torch.allclose(full['r'][0],torch.from_numpy(analytic_full_moments(s)).float(),atol=0,rtol=0)
    assert torch.count_nonzero(full['Jc'])==0
    assert torch.count_nonzero(empty['r'])==0 and torch.count_nonzero(empty['Jc'])==0
    assert guard.encoding_calls==1 and guard.analytic_full_reference_calls==1 and guard.native_teacher_calls==0
    assert full['native_training_admissible'] is False


def test_undecided_cut_and_contact_expected():
    s=shape('box')
    c=unit([0,0,0,1,0,0,0,0,0,0])
    assert strict_native_sign(c,s)=='UNDECIDED'
    with pytest.raises(ValueError):strict_native_sign(c,object())


def test_shape_outside_world_cube_fails_closed():
    s=Shape('box',(.9,0,0),(.4,.3,.4))
    with pytest.raises(ValueError,match='OUTSIDE_FROZEN_WORLD_CUBE'):analytic_aabb(s)


def test_nonfinite_and_bool_coefficients_fail():
    with pytest.raises(ValueError):strict_native_sign(torch.tensor([float('nan')]+[0.]*9),shape())
    with pytest.raises(ValueError):strict_native_sign(torch.zeros(1,10),shape())


def test_full_has_discrete_surrogate_bias_and_nonzero_j():
    model=ConeIntegrableMoment(FrozenQuadrature(),mix=.75)
    z=model.encode_geometry(torch.zeros(1,1,dtype=torch.float64))
    c=unit([1,.1,0,0,0,0,0,0,0,0])[None]
    assert float((model.moment(z,c)-z@model.encoder.monomials).abs().max().detach())>1e-5
    assert float(model.jacobian(z,c).abs().max().detach())>1e-8
    assert model.derivative_contract()['native_cherchi_derivative_admitted'] is False


def test_invalid_model_bound():
    with pytest.raises(ValueError):SaturationGuard(object())


def test_native_reject_immutable_semantics():
    m=ConeIntegrableMoment(FrozenQuadrature(),mix=.25)
    assert m.derivative_contract()['global_C2_or_smooth_native_ambient_guaranteed'] is False


def test_analytic_shape_voxel_binding_rejects_tamper():
    from research.NeuralMoments.models.deeponet.m9_readonly_w6 import load_m9_w6
    import os
    from dataclasses import replace
    root=os.environ.get('W5_M12_READONLY_W6_ROOT')
    if not root:pytest.skip('pinned W6 mirror required')
    _,_,w6,_=load_m9_w6(root)
    s=shape('ellipsoid')
    model=ConeIntegrableMoment(w6.GaussPotentialMoment(points_per_axis=6,hidden=32),mix=.25)
    guard=SaturationGuard(model)
    D=make_voxel(s)[None].float()
    fake=D.clone();fake[0,0,0,0,0]+=0.1
    with pytest.raises(ValueError,match='VOXEL_BYTES_DO_NOT_MATCH'):
        guard.bind_analytic_geometry(fake,s)
    cache=guard.bind_analytic_geometry(D,s)
    with pytest.raises(ValueError,match='INVALID_ANALYTIC_CACHE'):
        guard.predict(replace(cache,full_moments=cache.full_moments.clone().add(1)),
                      torch.tensor([[1.]+[0.]*9]))
    with pytest.raises(ValueError,match='INVALID_ANALYTIC_CACHE'):
        guard.predict(replace(cache,z=cache.z.clone().add(.01)),
                      torch.tensor([[1.]+[0.]*9]))
    wrong=shape('box')
    with pytest.raises(ValueError,match='VOXEL_BYTES_DO_NOT_MATCH'):
        guard.bind_analytic_geometry(D,wrong)


def test_nodal_activation_boundary_withholds_ambient_surrogate_J():
    s=shape('box')
    model=ConeIntegrableMoment(FrozenQuadrature(),mix=.25,boundary_rtol=1e-8)
    guard=SaturationGuard(model)
    cache=guard.bind_analytic_geometry(make_voxel(s)[None].float(),s)
    # Node x=.2 makes beta=-.2+x=0, a true fixed-node activation event.
    c=unit([-.2,1.]+[0.]*8)[None]
    output=guard.predict(cache,c)
    assert output['region']=='UNDECIDED'
    assert output['Jc'] is None
    assert output['interpretation']=='SURROGATE_NODE_BOUNDARY_J_WITHHELD'
    assert output['native_training_admissible'] is False


def test_fraction_native_cross_double_and_no_incorrect_certificate():
    s=shape('box')
    # c7 is native Ayz: polynomial contributes 2*c7*y*z, not c7*y*z.
    ambiguous=unit([0.0,0,0,0,0,0,0,1.,0,0])
    assert strict_native_sign(ambiguous,s)=='UNDECIDED'
    # A large positive constant outweighs ALL quadratic cross terms.
    guaranteed=unit([10.,0,0,0,0,0,0,1.,1.,1.])
    assert strict_native_sign(guaranteed,s)=='ANALYTIC_CERTIFIED_FULL'
    assert strict_native_sign(-guaranteed,s)=='ANALYTIC_CERTIFIED_EMPTY'


def test_zero_and_full_newton_derivatives_correct_for_analytic_shape():
    from research.NeuralMoments.models.deeponet.m9_readonly_w6 import load_m9_w6
    import os
    root=os.environ.get('W5_M12_READONLY_W6_ROOT')
    if not root:pytest.skip('pinned W6 mirror required')
    _,_,w6,_=load_m9_w6(root)
    s=shape('sphere')
    model=ConeIntegrableMoment(w6.GaussPotentialMoment(points_per_axis=6,hidden=32),mix=.25)
    guard=SaturationGuard(model)
    cache=guard.bind_analytic_geometry(make_voxel(s)[None].float(),s)
    c=unit([1.,.1,0,0,0,0,0,0,0,0]).float()[None]
    for control in (c,-c):
        first=guard.predict(cache,control)
        perturb=control.clone();perturb[0,4]=1e-4
        perturb/=perturb.norm(dim=-1,keepdim=True)
        second=guard.predict(cache,perturb)
        assert torch.equal(first['r'],second['r'])
        assert torch.count_nonzero(first['Jc'])==0
        assert second['region']==first['region']
