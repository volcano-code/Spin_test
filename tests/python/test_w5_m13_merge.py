"""Prevent scientific provenance inflation in merged M13 matched framework runs."""
import copy
import json
from pathlib import Path
import pytest

from research.NeuralMoments.models.deeponet.m13_merge import merge

REPO=Path(__file__).resolve().parents[2]
BASE=REPO/'research/NeuralMoments/models/deeponet'
FILES=[BASE/f'm13_train_seed{x}.json' for x in (67,71,73)]


def test_three_actual_seed_files_aggregate_without_loss():
    result=merge(FILES)
    assert result['seeds']==[67,71,73]
    assert result['independent_seed_count']==3
    assert len(result['full_seed_results'])==3
    assert result['W2_native_teacher_samples']==0
    assert result['native_Cherchi_evaluations']==0
    assert result['capacity_minmax']<=1.05
    for model,metrics in result['aggregate'].items():
        assert metrics['heldout.r_mae']['mean']>=0
        assert metrics['heldout.J_mae']['mean']>=0
        assert len(metrics['heldout.r_mae']['per_seed'])==3


def write_json(path,data):
    path.write_text(json.dumps(data,allow_nan=False),encoding='utf-8')


def test_duplicate_seed_rejected():
    with pytest.raises(ValueError,match='DUPLICATED_RANDOM_SEED'):
        merge([FILES[0],FILES[0]])


@pytest.mark.parametrize('mutator,msg',[ 
 (lambda j:j.update({'steps_max':999}),'UNMATCHED_TRAINING_PROTOCOL'),
 (lambda j:j.update({'native_Cherchi_evaluations':1}),'NATIVE_LABEL_TRAINING'),
 (lambda j:j.update({'W2_admissible_J_labels':1}),'NATIVE_LABEL_TRAINING'),
 (lambda j:j['all_seed_results'][0].update({'train_SHA256':''}),'MISSING_DATASET_FINGERPRINT'),
 (lambda j:j['all_seed_results'][0]['results'].pop('w6_realizable_m7_centered'),'INCOMPLETE_MODEL'),
])
def test_corrupt_report_rejected(tmp_path,mutator,msg):
    j=copy.deepcopy(json.loads(FILES[1].read_text()))
    mutator(j)
    broken=tmp_path/'broken.json';write_json(broken,j)
    with pytest.raises(ValueError,match=msg):
        merge([FILES[0],broken])


def test_source_sha_tamper_rejected(tmp_path):
    data=json.loads(FILES[1].read_text())
    data['W6_m7_git_blob_pins']['m7_realizable.py']='0'*40
    file=tmp_path/'forged.json';write_json(file,data)
    with pytest.raises(ValueError,match='W6_EXTERNAL_BLOB_DRIFT'):
        merge([FILES[0],file])
