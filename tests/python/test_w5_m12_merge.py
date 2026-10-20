"""M12 evidence merger enforces source identity and no post-hoc seed manipulation."""
import copy
import json
from pathlib import Path
import pytest
from research.NeuralMoments.models.deeponet.m12_merge import combine

HOME=Path(__file__).resolve().parents[2]/'research/NeuralMoments/models/deeponet'


def test_real_executed_three_seeds_merge():
    f=[HOME/f'm12_seed{s}.json' for s in (53,59,61)]
    out=combine(f)
    assert out['seed_list']==[53,59,61]
    assert out['strict_saturation_total_queries']==240
    assert out['strict_saturation_total_independent_geometries']==60
    assert out['strict_saturation_total_full_oracle_analytic_calls']==60
    assert out['protected_full_r_mae']==out['protected_empty_r_mae']==out['protected_max_J_abs']==0
    assert out['real_Cherchi_native_calls']==out['W2_certified_smooth_J_training_labels']==0
    assert out['aggregate']['w5_deeponet_voxel']['interior_r_mae']['mean']<0.05
    assert out['aggregate']['w5_cone_integrable_025']['unprotected_full_r_mae']['mean']>0.001


def test_duplicate_seed_fails():
    with pytest.raises(ValueError,match='DUPLICATED'):combine([HOME/'m12_seed53.json']*2)


def test_bad_provenance_fails(tmp_path):
    good=json.loads((HOME/'m12_seed53.json').read_text())
    for key,value in [('real_w2_training_labels',1),('native_cherchi_calls',1),('teacher_kind','FAKE_CHERCHI')]:
        bad=copy.deepcopy(good);bad[key]=value
        f=tmp_path/'tampered.json';f.write_text(json.dumps(bad))
        with pytest.raises(ValueError,match='PROTOCOL'):combine([f,HOME/'m12_seed59.json'])


def test_forged_saturation_fails(tmp_path):
    good=json.loads((HOME/'m12_seed53.json').read_text())
    good['results']['w5_cone_integrable_025']['M12_strict_saturation_with_independent_analytic_full_moment']['empty_raw_r_mae']=0.1
    f=tmp_path/'f.json';f.write_text(json.dumps(good))
    with pytest.raises(ValueError,match='SATURATION'):combine([f,HOME/'m12_seed59.json'])
