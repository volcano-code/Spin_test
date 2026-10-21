"""W0 review of a byte-pinned *W5 migration proposal*; W5 branch is untouched."""
from __future__ import annotations
import copy
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
import pytest
from .validate_contract_v1 import validate_record, ContractError

ROOT=Path(__file__).resolve().parent
MIGRATION=ROOT/"migration_proposals"/"w5_contract_gate_v2_m18.py"
LEGACY=ROOT/"frozen_external_m16"/"w5_contract_gate.py"
SAMPLE=ROOT/"sample_contract_v1.json"

def module_at(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

@lru_cache(maxsize=1)
def versions():
    return module_at(LEGACY,"legacy_w5_m18"),module_at(MIGRATION,"candidate_w5_m18")

def fixture():
    old,_=versions()
    c=[1.000004]+[0.]*6+[3e-6,-4e-6,5e-6]
    geom={"original_sha256":"1"*64,"fixed_F_sha256":"2"*64,
          "design_D_sha256":"3"*64,"family":"H8-reconstructed"}
    pins={"model":"a"*64,"module":"b"*64,"geometry":old.digest(geom)}
    p={
       "schema":"w2-cherchi-teacher-v2-pre-w0",
       "order":["m","x","y","z","xx","yy","zz","yz","xz","xy"],
       "coefficient_convention":"NATIVE_MATRIX_ENTRIES_C10_POLYNOMIAL_Q_EQUALS_BC_V1",
       "native_c_order":"CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY".split(","),
       "native_c":c[:],"q":c[:],
       "polynomial_q":[v*(2 if i>=7 else 1) for i,v in enumerate(c)],
       "model_sha256":pins["model"],"native_module_sha256":pins["module"],
       "geometry":geom,"density":1.,"frame":{"kind":"INPUT_NORMALIZED_TARGET_V1",
       "length_original_per_normalized":1.,"density_original_per_normalized":1.,
       "origin_original":[0.,0.,0.]},
       "r_D":[0.]*10,"r_F":[0.]*10,"J_D":None,
       "topology_status":"OBSERVED_DISCRETE_MAP","derivative_status":"UNKNOWN",
       "derivative_contract":None,"stage_seconds":{"native":0.0},
       "peak_rss_bytes":0,"exact_proof":{},"split":"excluded",
       "failure_reason":"finite-point-not-certified",
       "total_policy":"r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D",
    }
    doc={"payload":p,"payload_sha256":old.digest(p),
         "identity":{"q_sha256":old.digest(c),"geometry_sha256":pins["geometry"],
         "model_sha256":pins["model"],"native_module_sha256":pins["module"]}}
    return doc,pins,c

def test_exact_historical_w5_has_known_bug_and_migration_fixes_it():
    original,candidate=versions()
    record=json.loads(SAMPLE.read_text())
    record["coefficients"]["c"]=[1+4e-10]+[0.]*9
    assert original.check_w0_contract(record)["j_type"]=="UNAVAILABLE"
    with pytest.raises(ContractError):validate_record(record)
    with pytest.raises(candidate.AdmissionError,match="native unit-normalized"):
        candidate.check_w0_contract(record)
    assert candidate.W2_SCHEMA=="w2-cherchi-teacher-v1-pre-w0"
    assert candidate.W2_V2_SCHEMA=="w2-cherchi-teacher-v2-pre-w0"

def test_w0_valid_record_still_accepted():
    _,candidate=versions()
    record=json.loads(SAMPLE.read_text())
    assert validate_record(record)["structural_valid"]
    assert candidate.check_w0_contract(record)["j_type"]=="UNAVAILABLE"

def review(tmp_path,doc,pins,raw):
    _,candidate=versions()
    path=tmp_path/"candidate.json"
    path.write_text(candidate.canonical(doc))
    return candidate.inspect_w2_v2_excluded_record(path,
      expected_native_c=raw,expected_model_sha256=pins["model"],
      expected_native_module_sha256=pins["module"],
      expected_geometry_sha256=pins["geometry"])

def test_valid_v2_diagnostic_with_nonunit_original_never_trains(tmp_path):
    doc,pins,raw=fixture()
    before=copy.deepcopy(doc)
    result=review(tmp_path,doc,pins,raw)
    assert result["status"]=="READ_ONLY_V2_EXCLUDED_NO_NATIVE_RELEASE"
    assert result["native_c_w0_unit_compatible"] is False
    assert result["derivative_J_D"] is None
    assert not result["training_admitted"] and not result["native_material_certified"]
    assert doc==before

@pytest.mark.parametrize("field",[
 "train","J_D","derivative","q_alias","monomial","c","model","geometry",
 "wrong_norm_copy","failed_moments","density","timing","rss","duplicate"
])
def test_v2_self_resealed_attacks_fail_closed(tmp_path,field):
    doc,pins,raw=fixture()
    p=doc["payload"]
    if field=="train":p["split"]="train"
    elif field=="J_D":p["J_D"]=[[0.]*10 for _ in range(10)]
    elif field=="derivative":p["derivative_status"]="VALID"
    elif field=="q_alias":p["q"][0]+=0.5
    elif field=="monomial":p["polynomial_q"][7]=p["native_c"][7]
    elif field=="c":p["native_c"][0]+=0.5
    elif field=="model":p["model_sha256"]="c"*64
    elif field=="geometry":p["geometry"]["original_sha256"]="d"*64
    elif field=="wrong_norm_copy":p["native_c"]=[x/1.000004 for x in p["native_c"]]
    elif field=="failed_moments":p.update(topology_status="FAILED",derivative_status="INVALID")
    elif field=="density":p["density"]=-1
    elif field=="timing":p["stage_seconds"]["native"]=-1
    elif field=="rss":p["peak_rss_bytes"]=-1
    elif field=="duplicate":
        _,candidate=versions()
        path=tmp_path/"duplicate.json"
        path.write_text('{"payload":{}, "payload":{}, "identity":{}, "payload_sha256":"x"}')
        with pytest.raises(candidate.AdmissionError):candidate.inspect_w2_v2_excluded_record(
          path,expected_native_c=raw,expected_model_sha256=pins["model"],
          expected_native_module_sha256=pins["module"],
          expected_geometry_sha256=pins["geometry"])
        return
    _,candidate=versions()
    doc["payload_sha256"]=candidate.digest(p)
    with pytest.raises(candidate.AdmissionError):
        review(tmp_path,doc,pins,raw)

def test_v2_at_old_training_entry_is_never_approved(tmp_path):
    doc,pins,raw=fixture()
    _,candidate=versions()
    path=tmp_path/"candidate.json"
    path.write_text(candidate.canonical(doc))
    with pytest.raises(candidate.AdmissionError,match="W2_V2_FORMAL_NATIVE_RELEASE"):
        candidate.admit_w2_record(path,expected_c_native=raw,
             model_path=path,native_module_path=path,
             approved_file_sha256=[],expected_design_sha256="1"*64,
             expected_w0_original_sha256="2"*64,expected_w0_fixed_sha256="3"*64)

def test_external_pins_must_be_independent(tmp_path):
    doc,pins,raw=fixture()
    pins["geometry"]="0"*64
    _,candidate=versions()
    with pytest.raises(candidate.AdmissionError,match="V2_INDEPENDENT_EXPECTED_SHA"):
        review(tmp_path,doc,pins,raw)

def test_immutable_snapshot_of_original_w5_is_expected():
    import hashlib
    raw=LEGACY.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    assert blob=="14b2ab225a032188fe16570414ef321af9a81e00"

def test_v2_parser_does_not_export_moments_or_jacobians(tmp_path):
    doc,pins,raw=fixture()
    result=review(tmp_path,doc,pins,raw)
    assert "r_D" not in result and "J_native" not in result
    assert "candidate_native_c" not in result



def test_test_fixture_imports_have_stable_exception_identity():
    first=versions()[1]
    second=versions()[1]
    assert first is second
    assert first.AdmissionError is second.AdmissionError
