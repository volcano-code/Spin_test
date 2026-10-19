"""W5 M4: physical native-P0 labels and architecture training smoke.

No native/Cherchi teacher data, CAD Boolean, real W2 material proof or GPU run.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile

import numpy as np
import pytest
import torch

from research.NeuralMoments.models.deeponet.native_p0 import (
    native_vertical_c,cap_moments,cap_jacobian_native,dh_native_c)
from research.NeuralMoments.models.deeponet.native_p0_families import (
    NativeP0Primitive,oracle,validate_exact_reference,decision)
from research.NeuralMoments.models.deeponet.m4_native_p0_train import (
    make_dataset,train,evaluate,adaptation,run)
from research.NeuralMoments.models.deeponet.m2_audit import check_w2_readiness
from research.NeuralMoments.models.deeponet.model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment


@pytest.fixture(scope='module')
def shapes():
    return [
        NativeP0Primitive('box', (.12,-.17,.19),(.75,.64,.82),1.16),
        NativeP0Primitive('sphere',(0.,0.,0.),(1.2,1.2,1.2),1.),
        NativeP0Primitive('ellipsoid',(-.14,.08,.21),(.66,1.17,.88),1.07),
    ]


def test_oracle_matches_independent_existing_sphere_cap():
    p=NativeP0Primitive('sphere',(0,0,0),(1.2,1.2,1.2),1.0)
    for h in (-.8,-.1,0.,.2,.7):
        r,j,c=oracle(p,h)
        np.testing.assert_allclose(r,cap_moments(1.2,h),rtol=0,atol=3e-15)
        np.testing.assert_allclose(j,cap_jacobian_native(1.2,h),rtol=0,atol=5e-15)
        np.testing.assert_allclose(c,native_vertical_c(h),rtol=0,atol=0)


def test_ellipsoid_cap_independent_affine_sphere_reference():
    from research.NeuralMoments.models.deeponet.contract_gate import raw_pushforward
    p=NativeP0Primitive('ellipsoid',(.15,-.24,.11),(.65,1.2,.77),1.2)
    h=.21
    u=(h-p.center[2])/p.axes[2]
    expected=raw_pushforward(cap_moments(1.,u),np.diag(p.axes),np.array(p.center),density_ratio=p.density)
    r,j,_=oracle(p,h)
    np.testing.assert_allclose(r,expected,rtol=2e-13,atol=2e-13)
    assert j.shape==(10,10)


def test_box_cap_has_exact_volume_first_and_second_moments():
    p=NativeP0Primitive('box',(0.,0.,0.),(1.,2.,3.),2.)
    r,j,_=oracle(p,1.)
    # x in [-1,1], y in [-2,2], z in [1,3], rho=2
    assert r[0]==pytest.approx(32.)
    assert r[1]==pytest.approx(0.)
    assert r[2]==pytest.approx(0.)
    assert r[3]==pytest.approx(64.)
    assert r[4]==pytest.approx(32./3.)
    assert r[5]==pytest.approx(128./3.)
    assert r[6]==pytest.approx(32.*13./3.)
    # d mass / d cut height = -density*area = -16
    np.testing.assert_allclose(j@dh_native_c(1.), np.array([-16.,0.,0.,-16.,-16./3.,-64./3.,-16.,0.,0.,0.]), atol=1e-12)


@pytest.mark.parametrize('family_index',[0,1,2])
def test_full_ambient_jc_w0_B_rule_and_height_finite_difference(shapes,family_index):
    p=shapes[family_index]
    h=p.center[2]+.13*p.axes[2]
    evidence=validate_exact_reference(p,h,eps=2e-5)
    assert evidence['max_directional_fd_abs_error']<3e-8
    assert evidence['max_B_corrected_asymmetry']<1e-12
    assert evidence['max_scale_null_error']<1e-12
    r,J,c=oracle(p,h)
    assert r.shape==(10,) and J.shape==(10,10) and c.shape==(10,)
    assert np.linalg.norm(c)==pytest.approx(1.,abs=1e-14)
    # W0 q=Bc cross-terms doubled; Jc itself need not be symmetric.
    assert not np.allclose(J,J.T,atol=1e-9)
    np.testing.assert_allclose(J/np.array([1.]*7+[2.]*3)[None,:],
                               (J/np.array([1.]*7+[2.]*3)[None,:]).T,atol=1e-12)


def test_interior_sign_density_family_gate():
    with pytest.raises(ValueError): NativeP0Primitive('sphere',(0,0,0),(.9,.9,.91))
    with pytest.raises(ValueError): NativeP0Primitive('ellipsoid',(0,0,0),(1.,1.,1.))
    with pytest.raises(ValueError): NativeP0Primitive('box',(0,0,0),(-1,1,1))
    with pytest.raises(ValueError): NativeP0Primitive('box',(0,0,0),(1,1,1),-1.)
    with pytest.raises(ValueError): NativeP0Primitive('nope',(0,0,0),(1,1,1))
    p=NativeP0Primitive('box',(0,0,0),(1,1,1))
    for h in (-1.,1.,math.inf,math.nan):
        with pytest.raises(ValueError):oracle(p,h)
    with pytest.raises(ValueError):decision(p,0.,0.,predicted_jc=np.zeros((10,9)))
    with pytest.raises(ValueError):validate_exact_reference(p,.999999,eps=1e-4)


@pytest.mark.parametrize('family_index',[0,1,2])
def test_oracle_decision_has_zero_error_on_exact_labels(shapes,family_index):
    p=shapes[family_index]
    h=p.center[2]
    target=h+.12*p.axes[2]
    true_r,true_j,_=oracle(p,h)
    audit=decision(p,h,target,predicted_r=true_r,predicted_jc=true_j)
    assert audit['step_absolute_error']==pytest.approx(0.,abs=1e-14)
    assert audit['signed_oracle_loss_gap']==pytest.approx(0.,abs=1e-14)
    assert audit['loss_oracle_after']<=audit['loss_before']


def test_dataset_is_deterministic_and_holdout_disjoint():
    a=make_dataset(seed=7,per_family=5)
    b=make_dataset(seed=7,per_family=5)
    c=make_dataset(seed=8,per_family=5)
    assert a['sha256']==b['sha256']!=c['sha256']
    assert a['geometry_holdout_verified']
    assert len(a['train']['shapes'])==30 and len(a['test']['shapes'])==15
    assert set(a['train']['geometry_sha256']).isdisjoint(a['test']['geometry_sha256'])
    assert {p.family for p in a['train']['shapes']}=={'box','sphere'}
    assert {p.family for p in a['test']['shapes']}=={'ellipsoid'}
    assert a['train']['j'].shape==(30,10,10)
    assert a['test']['d'].shape==(15,10)
    for c in a['train']['c']:
        assert torch.linalg.vector_norm(c).item()==pytest.approx(1.,abs=1e-6)


@pytest.mark.parametrize('cls',[DeepONetMoment,GeometryMLPMoment])
def test_physical_p0_training_and_few_shot(cls):
    torch.set_num_threads(1)
    data=make_dataset(seed=3,per_family=3)
    torch.manual_seed(3)
    model=cls(geometry_dim=10)
    train_report=train(model,data,steps=3,seed=3,derivative_enhanced=True,batch_size=4)
    assert train_report['steps']==3 and train_report['derivative_weight']==.5
    heldout=evaluate(model,data)
    assert heldout['unique_heldout_geometries']==3
    assert heldout['evaluated_queries']==9
    for key in ('r_mae','Jc_mae','height_directional_mae','step_absolute_error','signed_true_objective_gap','candidate_step_worsened_start_fraction'):
        assert np.isfinite(heldout[key])
    adap=adaptation(model,data['test']['shapes'][0])
    assert list(adap)==['0','1','2','4','8']
    for k in (0,1,2,4,8):
        assert adap[str(k)]['oracle_query_count']==k
        assert adap[str(k)]['heldout_query_count']==7
        assert np.isfinite(adap[str(k)]['r_mae'])


def test_w2_manifest_fail_closed_even_if_self_declares_samples(tmp_path):
    manifest={'schema':'w2-cherchi-teacher-v1-pre-w0','status':'ADAPTER_SMOKE_ONLY',
              'native_teacher_runs':0,'training_samples':0}
    path=tmp_path/'w2.json'
    path.write_text(json.dumps(manifest))
    assert check_w2_readiness(path)['ready'] is False
    manifest['status']='NATIVE_VERIFIED'
    manifest['native_teacher_runs']=99999
    manifest['training_samples']=99999
    path.write_text(json.dumps(manifest))
    result=check_w2_readiness(path)
    assert result['native_teacher_runs_declared']==99999
    assert result['ready'] is False
    with pytest.raises(ValueError):
        path.write_text(json.dumps({**manifest,'training_samples':True}))
        check_w2_readiness(path)
    with pytest.raises(ValueError):
        path.write_text(json.dumps({**manifest,'schema':'other'}))
        check_w2_readiness(path)


def test_small_multiseed_run_has_no_native_claim():
    report=run(seeds=(7,19),steps=2,per_family=2,repeats=2)
    assert report['status']=='INDEPENDENT_ANALYTIC_P0_ONLY_REAL_W2_TRAINING_BLOCKED'
    assert not report['teacher_gate']['ready']
    assert report['gpu_seconds']==0
    assert report['native_training_samples']==0
    assert report['train_families']==['box','sphere']
    assert report['test_families']==['ellipsoid']
    assert sorted(report['runs'])==['19','7']
    for model in ('deeponet','geometry_mlp'):
        for arm in ('residual_only','derivative_enhanced'):
            data=report['runs']['7']['models'][model][arm]
            assert data['training']['steps']==2
            assert np.isfinite(data['heldout']['r_mae'])
            assert data['complexity_and_cpu_timing']['estimated_complexity']['parameters']>0
            assert data['oracle_adaptation']['8']['oracle_query_count']==8
