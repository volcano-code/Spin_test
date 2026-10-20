"""M13 source-pinned W6 M7 crosswalk and independent analytic cell-volume protocol."""
from pathlib import Path
import shutil
import tempfile
import numpy as np
import pytest
import torch

from research.NeuralMoments.models.deeponet.m8_analytic_data import Shape,analytic_truth
from research.NeuralMoments.models.deeponet.m13_cell_integrals import CellwiseMomentReference,vertical_native_c
from research.NeuralMoments.models.deeponet.m13_resolution_benchmark import (
    center_cell_voxel,w6_gauss_maximum_atomic_moments,run as resolution_run)
from research.NeuralMoments.models.deeponet.m13_m7_model_comparison import (
    MODEL_NAMES, centered_dataset, build_model,run as model_run)
from research.NeuralMoments.models.deeponet.m13_w6_m7_probe import (
    load_w6_m7,untrained_m7_api_probe,W6_M7_FILES)
from research.NeuralMoments.models.deeponet.m9_readonly_w6 import load_m9_w6
from research.NeuralMoments.models.deeponet.m7_cross_framework import UntrustedW6Source

REPO=Path(__file__).resolve().parents[2]


def test_source_pinned_w6_m7_operator_runs_and_has_derivative():
    D=torch.zeros(1,4,8,8,8)
    D[:,0]=1.;D[:,1]=1.
    c=torch.tensor(vertical_native_c(.17),dtype=torch.float32)[None]
    record=untrained_m7_api_probe(REPO,D,c,seed=67)
    assert record['not_trained'] is True
    assert record['params']==13448
    assert len(record['r'])==10 and np.asarray(record['Jc']).shape==(10,10)
    assert record['no_native_teacher_J'] is True
    assert record['source_blob_pins']==W6_M7_FILES
    assert record['r'][0]>=0


def test_W6_original_source_tampering_rejected_before_import():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'research/NeuralMoments/models/pcraft_ufno'
        p.mkdir(parents=True)
        for name in ('m4_lite_model.py','m5_potential.py','m6_gauss_potential.py',
                     'm6_moment_guard.py','m6_safe_inference.py','m7_realizable.py'):
            shutil.copy2(REPO/'research/NeuralMoments/models/pcraft_ufno'/name,p/name)
        (p/'m7_realizable.py').write_text((p/'m7_realizable.py').read_text()+'\n# INJECTED\n')
        with pytest.raises(UntrustedW6Source,match='M7_BLOB'):
            load_w6_m7(td)


def test_center_cell_voxel_preserves_known_uniform_full_box():
    shape=Shape('box',(0.,0.,0.),(1.,1.,1.))
    d=center_cell_voxel(shape,8)
    assert np.all(d[0]==1) and np.all(d[1]==1)
    ref=CellwiseMomentReference.bind(d)
    c,r,j=analytic_truth(shape,.137)
    np.testing.assert_allclose(ref.evaluate(c)['r'],r,atol=1e-12)
    np.testing.assert_allclose(ref.evaluate(c)['Jc'],j,atol=1e-12)
    capped=w6_gauss_maximum_atomic_moments(d,c)
    assert capped.shape==(10,) and np.isfinite(capped).all()


@pytest.mark.parametrize('family',['box','sphere','ellipsoid'])
def test_positive_gauss_capacity_never_negative_mass(family):
    shape=Shape(family,(0.,0.,0.),(.67,.67,.67) if family=='sphere' else (.59,.64,.53))
    for n in (8,16):
        vox=center_cell_voxel(shape,n)
        r=w6_gauss_maximum_atomic_moments(vox,vertical_native_c(.2))
        assert r[0]>=0
        assert np.isfinite(r).all()


def test_different_cell_sampling_conventions_not_relabelled_identically():
    shape=Shape('ellipsoid',(.07,-.02,.05),(.51,.63,.47))
    centered=center_cell_voxel(shape,8)
    from research.NeuralMoments.models.deeponet.m8_analytic_data import make_voxel
    legacy=make_voxel(shape,8).numpy()
    assert not np.array_equal(centered,legacy)
    assert CellwiseMomentReference.bind(centered).source_sha256 != CellwiseMomentReference.bind(legacy).source_sha256


def test_benchmark_reports_non_native_gauss_J_as_unavailable():
    report=resolution_run(seeds=(67,),per_family=2,resolutions=(8,16),queries=1)
    assert report['count']==(3*2*2)+(3*2)
    assert report['distinct_geometry_ids']==6
    assert report['formal_W2_J_training_labels']==0
    assert report['oracle_native_cherchi_queries']==0
    assert all(row['gauss_m7_max_capacity_J_available'] is False for row in report['rows'])
    assert 'CELL_CENTER_n16' in report['aggregate']
    assert report['aggregate']['CELL_CENTER_n8']['J_mae']['count']==6


def test_centered_dataset_retains_shared_controls_and_distinct_family_ids():
    data=centered_dataset(('box','sphere'),per_family=6,seed=67)
    held=centered_dataset(('ellipsoid',),per_family=6,seed=68)
    train_ids={x['geometry_id'] for x in data[4]}
    held_ids={x['geometry_id'] for x in held[4]}
    assert not train_ids & held_ids
    assert len(train_ids)==12 and len(held_ids)==6
    assert data[0].shape==(24,4,8,8,8)
    for i in range(0,len(data[4]),2):
        assert data[4][i]['geometry_id']==data[4][i+1]['geometry_id']
        assert torch.equal(data[0][i],data[0][i+1])


def test_three_model_parameter_parity_and_actual_gradient():
    m4,m5,m6,guard=load_m9_w6(REPO)
    m7=load_w6_m7(REPO)
    libs=m4,m5,m6,guard,m7
    models={name:build_model(name,67,libs) for name in MODEL_NAMES}
    counts={key:sum(p.numel()*(2 if p.is_complex() else 1) for p in model.parameters() if p.requires_grad)
            for key,model in models.items()}
    assert max(counts.values())/min(counts.values()) <=1.05
    data=centered_dataset(('box',),per_family=6,seed=67)
    for model in models.values():
        z=model.encode_geometry(data[0][:2]);c=data[1][:2]
        r=model.moment(z,c);J=model.jacobian(z,c)
        assert r.shape==(2,10) and J.shape==(2,10,10)
        loss=(r-data[2][:2]).square().mean()+.1*(J-data[3][:2]).square().mean()
        model.zero_grad(set_to_none=True);loss.backward()
        assert any(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters())


def test_small_new_seed_comparison_runs_true_training_not_just_history():
    output=model_run(w6_root=REPO,seeds=(67,),per_family=6,steps=3,repeats=1)
    assert output['capacity_max_min_ratio']<1.05
    assert output['W2_admissible_J_labels']==0
    assert output['native_Cherchi_evaluations']==0
    for model in MODEL_NAMES:
        z=output['all_seed_results'][0]['results'][model]
        assert z['training']['steps_executed']==3
        assert z['training']['loss']=='MSE(r)+0.5*MSE(Jc)'
        assert np.isfinite(z['heldout']['J_mae'])
