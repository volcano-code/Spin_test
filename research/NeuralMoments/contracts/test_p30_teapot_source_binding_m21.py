from __future__ import annotations

import copy
import hashlib
import json
from fractions import Fraction

import pytest

from .p30_teapot_source_binding_m21 import (
    SourceBindingRejected, verify_snapshot, strict_json, verify_core_source_tree)


def b(n,d=1): return {"numerator":str(n),"denominator":str(d)}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
    path.write_bytes(raw)
    return raw

def fixture(tmp_path):
    root=tmp_path
    paths={"M":"P19_material_case/material/M_native.obj",
           "F":"P19_material_case/material/F_native.obj",
           "D":"P19_material_case/material/D_native.obj",
           "S":"P19_material_case/source/shaft-reference.obj"}
    obj={name:(f"OBJ-{name}-frozen\n".encode()) for name in paths}
    objsha={}
    for name,rel in paths.items():
        (root/rel).parent.mkdir(parents=True,exist_ok=True)
        (root/rel).write_bytes(obj[name]);objsha[name]=sha(obj[name])
    manifest={
        "material_files":{"M":"material/M_native.obj","F":"material/F_native.obj",
                          "D":"material/D_native.obj","S":"source/shaft-reference.obj"},
        "files_sha256":{paths[k].removeprefix("P19_material_case/"):v for k,v in objsha.items()},
        "scientific_flags":{"W0_physical_tip_or_FD_approved":False,
          "W2_Teapot_teacher_admitted":False,"printability_certified":False},
        "construction":{"shaft_envelope":{"radial_scale_exact":"9/8",
           "rotation_degrees_display":7},"original_shaft_file_unchanged":True}}
    manifest_raw=dump(root/"P19_material_case/manifest.json",manifest)
    report={
        "status":"P19_EXACT_SAVED_SOLID_AND_COMPLETE_ORIGINAL_SHAFT_PASS_NOT_ADMITTED",
        "physical_proposal":{"status":"P13_UNIFIED_PHYSICAL_CASE_PROPOSAL_NOT_W0_APPROVED",
          "case_config":{"scale_m_per_unit":.025,"density_kg_m3":1200,
            "density_model":"ASSUMED_UNIFORM_SOLID_NOT_PRINTED_MATERIAL_CERTIFICATE"},
          "materials":{"M":{"bounds_m":[[0.,0.,0.],[1.,1.,1.]]}}},
        "geometry":{"complete_original_shaft_in_fixed":True,
          "design_shaft_separation_certified":True},
        "scientific_flags":{"printability_certified":False,"training_admitted":False}}
    report_raw=dump(root/"P19_CANONICAL_SOURCE_COMPLETE_REPORT.json",report)
    request={
        "source_w0_commit":"5bab2eb2616df306906a6887a273f68acfa49320",
        "source_w4_commit":"58fd12c1306c1c01679a19172e276eef0cb30542",
        "manifest":{"path":"P19_material_case/manifest.json","sha256":sha(manifest_raw)},
        "canonical_report":{"path":"P19_CANONICAL_SOURCE_COMPLETE_REPORT.json","sha256":sha(report_raw)},
        "material_inputs":{k:{"path":v,"sha256":objsha[k]} for k,v in paths.items()},
        "units":{"fixed_density":1,"design_density":1,"length_m_per_reference_binary64":.025,
          "length_m_per_reference_exact":"3602879701896397/144115188075855872",
          "physical_density_kg_m3":1200,"physical_parameters_approved":False},
        "target":{"mode":"SPINNING_TOP","axis":[0,0,1],"origin":[0,0,0],"support_points":[]},
        "admission":{"W0_owner_admitted":False,"original_author_CAD":False},
        "geometry_policy":{"shaft_material":"S_ALREADY_INCLUDED_IN_F_NEVER_ADDED_AGAIN"}}
    request_raw=dump(root/"P20_native_request.json",request)
    masses={"M":.03,"F":.029,"D":.001,"S":.0002}
    com={k:[0.,0.,.01] for k in masses}
    inertia={k:[[1e-5,0.,0.],[0.,1e-5,0.],[0.,0.,1e-5]] for k in masses}
    tip=[b(-1,10**18),b(0),b(1,10**18)]
    frame={
      "actual_core_sources":{"commit":request["source_w4_commit"],
        "native_core_executed":False,"whole_commit_tree_verified":False},
      "actual_frame":{"coefficient_frame":"INPUT_NORMALIZED_TARGET_V1",
        "actual_target_axes_exact":[[b(1),b(0),b(0)],[b(0),b(1),b(0)],[b(0),b(0),b(1)]],
        "length_original_per_normalized_exact":b(723841050109123,281474976710656),
        "density_original_per_normalized_exact":b(1),
        "native_length_scale_is_bbox_L_not_SI_0025":True,
        "represented_tip_reference_exact":tip,"represented_tip_is_exact_requested_tip":False,
        "represented_tip_minus_requested_exact":tip,"frame_identity_sha256":"a"*64},
      "physical_replay":{"density_reference":1.0,
        "shaft_already_in_F_not_added_to_mass":True,
        "source_report_sha256":sha(report_raw),"source_manifest_sha256":sha(manifest_raw),
        "source_material_sha256":objsha,"source_meshes_reintegrated":False,
        "P19_geometric_proofs_reexecuted":False,
        "materials":{k:{"mass_kg":masses[k],"center_of_mass_m":com[k],
          "full_inertia_com_kg_m2":inertia[k]} for k in masses}},
      "scientific_flags":{"physical_material_validated":False,
        "native_M6_material_partition_certified":False,"optimization_admitted":False,
        "training_admitted":False,"native_implicit_identity_certified":False}}
    frame_raw=dump(root/"P20_EXACT_FRAME_AND_PHYSICS_REPORT.json",frame)
    review={
      "w0_baseline":request["source_w0_commit"],
      "p20_request_sha256":sha(request_raw),"p19_manifest_sha256":sha(manifest_raw),
      "obj_sha256":objsha,"scale_m_per_reference":.025,"density_kg_m3":1200,
      "density_model":report["physical_proposal"]["case_config"]["density_model"],
      "bounds_m":report["physical_proposal"]["materials"]["M"]["bounds_m"],
      "length_original_per_normalized":float(Fraction(723841050109123,281474976710656)),
      "frame_length_is_bbox_L":True,"mass_kg":masses,"center_of_mass_m":com,
      "full_inertia_com_kg_m2":inertia,"shaft_included_in_fixed":True,
      "shaft_added_separately_to_total":False,"radial_envelope_scale":"9/8",
      "xy_rotation_degrees":7,"original_shaft_bytes_preserved":True,
      "original_author_cad":False,"physical_parameters_approved":False,
      "support_points":[],"target_tip_reference":[0,0,0],
      "represented_tip_exactly_equals_requested":False,
      "represented_tip_minus_requested_exact":tip,
      "p19_complete_shaft_in_fixed":True,"p19_design_shaft_separation":True,
      "global_printability_or_strength_proved":False,
      "native_implicit_region_equality_proved":False}
    factory_raw=b"p20 factory source\\n"
    physical_raw=b"p20 physical contract source\\n"
    (root/"p20_native_factory.py").write_bytes(factory_raw)
    (root/"p20_physical_contract.py").write_bytes(physical_raw)
    expected={
      "P20_native_request.json":sha(request_raw),
      "P19_material_case/manifest.json":sha(manifest_raw),
      "P19_CANONICAL_SOURCE_COMPLETE_REPORT.json":sha(report_raw),
      "P20_EXACT_FRAME_AND_PHYSICS_REPORT.json":sha(frame_raw),
      "p20_native_factory.py":sha(factory_raw),
      "p20_physical_contract.py":sha(physical_raw),
      **{paths[k]:objsha[k] for k in paths}}
    return root,review,expected


def test_real_source_binding_fixture_passes(tmp_path):
    root,review,expected=fixture(tmp_path)
    result=verify_snapshot(root,"a"*40,review,expected_head="a"*40,expected_files=expected)
    assert result["status"]=="SOURCE_BYTES_AND_CROSS_REPORT_BINDINGS_VERIFIED_NOT_PHYSICAL_APPROVAL"
    assert len(result["source_sha256"])==8
    assert result["admission"]["P30B_diagnostic_authorized"] is False


def test_tampered_obj_bytes_fail_before_report_acceptance(tmp_path):
    root,review,expected=fixture(tmp_path)
    (root/"P19_material_case/material/M_native.obj").write_bytes(b"tampered")
    with pytest.raises(SourceBindingRejected,match="W4_SOURCE_SHA256_MISMATCH"):
        verify_snapshot(root,"a"*40,review,expected_head="a"*40,expected_files=expected)


def test_static_review_cannot_drift_from_source_reports(tmp_path):
    root,review,expected=fixture(tmp_path);review["scale_m_per_reference"]=.15
    with pytest.raises(SourceBindingRejected,match="W0_review_evidence.scale_m_per_reference"):
        verify_snapshot(root,"a"*40,review,expected_head="a"*40,expected_files=expected)


def test_unreviewed_w4_head_rejected(tmp_path):
    root,review,expected=fixture(tmp_path)
    with pytest.raises(SourceBindingRejected,match="UNREVIEWED_W4_HEAD"):
        verify_snapshot(root,"b"*40,review,expected_head="a"*40,expected_files=expected)


def test_manifest_material_path_mismatch_rejected(tmp_path):
    root,review,expected=fixture(tmp_path)
    path=root/"P19_material_case/manifest.json"
    data=json.loads(path.read_text());data["material_files"]["M"]="material/other.obj"
    dump(path,data)
    manifest_sha=sha(path.read_bytes())
    expected["P19_material_case/manifest.json"]=manifest_sha
    req_path=root/"P20_native_request.json"
    req=json.loads(req_path.read_text());req["manifest"]["sha256"]=manifest_sha
    dump(req_path,req)
    expected["P20_native_request.json"]=sha(req_path.read_bytes())
    frame_path=root/"P20_EXACT_FRAME_AND_PHYSICS_REPORT.json"
    frame=json.loads(frame_path.read_text())
    frame["physical_replay"]["source_manifest_sha256"]=manifest_sha
    dump(frame_path,frame)
    expected["P20_EXACT_FRAME_AND_PHYSICS_REPORT.json"]=sha(frame_path.read_bytes())
    with pytest.raises(SourceBindingRejected,match="manifest.material_files.M"):
        verify_snapshot(root,"a"*40,review,expected_head="a"*40,expected_files=expected)


def test_frame_scale_change_rejected_even_if_file_hash_updated(tmp_path):
    root,review,expected=fixture(tmp_path)
    path=root/"P20_EXACT_FRAME_AND_PHYSICS_REPORT.json"
    data=json.loads(path.read_text());data["actual_frame"]["length_original_per_normalized_exact"]=b(3)
    dump(path,data);expected["P20_EXACT_FRAME_AND_PHYSICS_REPORT.json"]=sha(path.read_bytes())
    with pytest.raises(SourceBindingRejected,match="P20_NORMALIZATION_L_CHANGED"):
        verify_snapshot(root,"a"*40,review,expected_head="a"*40,expected_files=expected)


def test_symlink_source_rejected(tmp_path):
    root,review,expected=fixture(tmp_path)
    path=root/"P19_material_case/material/D_native.obj"
    target=root/"outside.obj";target.write_bytes(path.read_bytes())
    path.unlink();path.symlink_to(target)
    with pytest.raises(SourceBindingRejected,match="SYMLINK_REJECTED"):
        verify_snapshot(root,"a"*40,review,expected_head="a"*40,expected_files=expected)


def test_duplicate_json_keys_rejected():
    with pytest.raises(SourceBindingRejected,match="DUPLICATE_JSON_KEY"):
        strict_json(b'{"a":1,"a":2}',"test")


def test_pinned_core_source_tree_hashes_are_recomputed(tmp_path):
    expected={}
    for i in range(10):
        rel=f"src/module_{i}.py"
        target=tmp_path/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(f"core-source-{i}\\n".encode())
        expected[rel]=sha(target.read_bytes())
    observed=verify_core_source_tree(tmp_path,"5"*40,expected)
    assert observed==expected
    (tmp_path/"src/module_3.py").write_bytes(b"tampered")
    with pytest.raises(SourceBindingRejected,match="P20_CORE_SOURCE_SHA256_MISMATCH"):
        verify_core_source_tree(tmp_path,"5"*40,expected)
