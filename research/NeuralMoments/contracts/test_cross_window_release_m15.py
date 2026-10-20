"""W0 M15 no-native release-gate tests."""
import copy
import json
import pytest
from pathlib import Path
from .cross_window_release_m15 import audit, strict_json, GateError, main

OBS = json.loads((Path(__file__).parent / "m15_observation.json").read_text())

def test_actual_status_does_not_release():
    r = audit(OBS)
    assert r["status"] == "BLOCKED_INDEPENDENT_RELEASE_SEAL_MISSING"
    assert not r["W5_real_teacher_admitted"] and not r["W6_real_teacher_admitted"]
    assert not r["newton_admitted"] and not r["training_admitted"]
    assert "W3_FOUR_REAL_SIDES_MISSING" in r["blockers"]

def test_all_windows_are_observed_not_certified():
    assert len(audit(OBS)["branch_shas"]) == 7
    assert audit(OBS)["observations_not_CI_or_native_proof"]

@pytest.mark.parametrize("path,value", [
    (("branch_observations","W0","sha"),"not-a-sha"),
    (("branch_observations","W4","branch"),"main"),
    (("w2","unit_native_c"),81),
    (("w2","nonunit_native_c"),0),
    (("w2","archive_sha256"),"0"*64),
    (("w2","new_native_teacher_samples"),-1),
    (("w2","released_J_D"),-1),
    (("w3","new_side_materials"),-1),
    (("w3","required_side_materials"),0),
    (("consumer_policy","analytic_p0_is_real_teacher"),True),
    (("consumer_policy","w5_requires_formal_teacher"),False),
    (("consumer_policy","w6_requires_formal_teacher"),False),
])
def test_modified_source_or_bypass_denied(path,value):
    d=copy.deepcopy(OBS)
    node=d
    for key in path[:-1]: node=node[key]
    node[path[-1]]=value
    with pytest.raises(GateError):audit(d)

def test_fake_upstream_success_not_enough():
    d=copy.deepcopy(OBS)
    d["w2"].update(new_native_teacher_samples=10,released_J_D=10,
      train_splits_present=True,continuous_neighborhood_certified=True,formal_teacher_release=True)
    d["w3"].update(new_side_materials=4,accepted_newton_steps=1,
      continuous_neighborhood_certified=True,final_heart_obj=True)
    r=audit(d)
    assert "UNVERIFIED_UPSTREAM_RELEASE_CLAIM" in r["blockers"]
    assert not r["training_admitted"]

def test_duplicated_keys_and_nonfinite_denied():
    with pytest.raises(GateError): strict_json('{"x":1,"x":2}')
    with pytest.raises(GateError): strict_json('{"x":NaN}')

def test_cannot_overwrite(tmp_path):
    report=tmp_path/"saved.json"
    report.write_text("original")
    with pytest.raises(FileExistsError):main([
       "--snapshot",str(Path(__file__).parent/"m15_observation.json"),
       "--output",str(report)])
    assert report.read_text()=="original"

def test_no_mutation():
    copy_observation=copy.deepcopy(OBS)
    audit(copy_observation)
    assert copy_observation==OBS
