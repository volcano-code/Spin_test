"""Check independent M11 seed aggregation against committed raw experiment files."""
import copy
import json
from pathlib import Path
import tempfile
import pytest
from research.NeuralMoments.models.deeponet.m11_merge import merge_seed_files

ROOT=Path(__file__).resolve().parents[2]/'research/NeuralMoments/models/deeponet'
FILES=[ROOT/f'm11_seed{s}.json' for s in (41,43,47)]

def test_real_seed_source_aggregate():
    if not all(p.is_file() for p in FILES):
        pytest.skip('Raw actually executed seed JSON unavailable')
    x=merge_seed_files(FILES)
    assert x['seeds']==[41,43,47]
    assert x['real_native_calls']==0 and x['native_J_training_labels']==0
    assert x['aggregate']['w5_cone_integrable_025']['necessary_support_pass']['mean']==1.
    assert x['aggregate']['w5_cone_integrable_075']['necessary_support_pass']['mean']==1.
    assert x['aggregate']['w5_cone_integrable_025']['Jq_asymmetry_max']['mean']<1e-5
    assert x['aggregate']['w5_cone_integrable_075']['Jq_min_eigenvalue']['mean']>-1e-5


def test_merger_rejects_native_promotion():
    if not FILES[0].is_file():pytest.skip('need real seed file')
    x=json.loads(FILES[0].read_text())
    y=copy.deepcopy(x);y['seed']=42;y['seeds']=[42];y['dataset_train_sha256']='1'*64;y['dataset_heldout_sha256']='2'*64
    y['W2_admissible_training_labels']=1
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/'bad.json';p.write_text(json.dumps(y))
        with pytest.raises(ValueError,match='incompatible|Native|untrusted|Untrusted'):
            merge_seed_files([FILES[0],p])


def test_merger_rejects_duplicate_and_dataset_leaks():
    if not all(p.is_file() for p in FILES[:2]):pytest.skip('need real seed files')
    with pytest.raises(ValueError,match='Duplicate'):
        merge_seed_files([FILES[0],FILES[0]])
    x=json.loads(FILES[1].read_text())
    x['dataset_heldout_sha256']=json.loads(FILES[0].read_text())['dataset_heldout_sha256']
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/'duped.json';p.write_text(json.dumps(x))
        with pytest.raises(ValueError,match='Repeated'):
            merge_seed_files([FILES[0],p])


def test_merger_rejects_missing_holdout_provenance():
    if not all(p.is_file() for p in FILES[:2]):pytest.skip('need real seed files')
    x=json.loads(FILES[1].read_text());x['geometry_split']={}
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/'leak.json';p.write_text(json.dumps(x))
        with pytest.raises(ValueError,match='split provenance'):
            merge_seed_files([FILES[0],p])
