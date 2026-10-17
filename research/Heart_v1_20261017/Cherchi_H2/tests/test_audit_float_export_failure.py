import importlib.util
import json
from pathlib import Path
import pytest

MODULE = Path(__file__).resolve().parents[1] / 'source' / 'audit_float_export_failure.py'
spec = importlib.util.spec_from_file_location('audit_float_export_failure', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import os
ROOT = Path(os.environ.get('HEART_H1_ROOT', str(Path(__file__).resolve().parents[2] / 'Cherchi_H1')))


def sources():
    return ROOT/'output_proxy_v1/cherchi-authoritative-exact.json', ROOT/'evidence/proxy-cherchi-full-audit.json', ROOT/'evidence/rational-output-audit.json'


def test_existing_h1_failure_classified():
    out = m.audit(*sources())
    assert out['float_intersecting_pairs'] == 78
    assert out['involved_face_count'] == 71
    assert out['input_face_count'] == 1570
    assert not out['qualified_binary64_obj']
    assert not out['exact_retriangulation_authorized']


def test_tampered_pair_count_rejected(tmp_path):
    mat,bina,rat = sources()
    blob=json.loads(bina.read_text()); blob['intersecting_pair_count']=77
    new=tmp_path/'binary.json'; new.write_text(json.dumps(blob))
    with pytest.raises(ValueError, match='NATIVE_PAIR_COUNT_MISMATCH'):
        m.audit(mat,new,rat)


def test_unverified_rational_rejected(tmp_path):
    mat,bina,rat=sources()
    blob=json.loads(rat.read_text());blob['boundary_valid']=False
    new=tmp_path/'rational.json';new.write_text(json.dumps(blob))
    with pytest.raises(ValueError, match='RATIONAL_INPUT_NOT_ADMITTED'):
        m.audit(mat,bina,new)


def test_no_rounded_failure_rejected(tmp_path):
    mat,bina,rat=sources()
    blob=json.loads(bina.read_text());blob['boundary_valid']=True
    new=tmp_path/'binary.json';new.write_text(json.dumps(blob))
    with pytest.raises(ValueError, match='NO_BINARY64_FAILURE_TO_CLASSIFY'):
        m.audit(mat,new,rat)
