"""W0 M21: directly hash-bind the public W4 P19/P20 physical evidence.

This verifier reads an immutable W4 checkout exported by CI. It does not trust
hash strings copied into the W0 review JSON: it hashes the actual bytes,
cross-checks the P20 request against P19 manifest/material files, binds the P19
and P20 physical reports, and compares all review facts to their source.
A passing result is source-integrity only, never physical approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

W4_REVIEWED_COMMIT = "aca53abf0d31329264fe1f028b2aff2175165ba3"
P20_REQUEST = "P20_native_request.json"
P19_MANIFEST = "P19_material_case/manifest.json"
P19_REPORT = "P19_CANONICAL_SOURCE_COMPLETE_REPORT.json"
P20_FRAME_REPORT = "P20_EXACT_FRAME_AND_PHYSICS_REPORT.json"
EXPECTED_FILES = {
    P20_REQUEST: "a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9",
    P19_MANIFEST: "c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6",
    P19_REPORT: "f30fabc8ce348b9b8f42ff20649e683557349582ef31baf6c05d35e17b448601",
    P20_FRAME_REPORT: "eaba6b60753fcb2141be425081897a8e891821349c166f5daff143d3ce9ea5fc",
    "P19_material_case/material/M_native.obj": "0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704",
    "P19_material_case/material/F_native.obj": "5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8",
    "P19_material_case/material/D_native.obj": "d64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073",
    "P19_material_case/source/shaft-reference.obj": "65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0",
}
MATERIAL_KEYS = ("M", "F", "D", "S")
SHA = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")


class SourceBindingRejected(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise SourceBindingRejected(code)


def strict_json(raw: bytes, label: str):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, "DUPLICATE_JSON_KEY:" + label + ":" + key)
            result[key] = value
        return result
    def constant(token):
        raise SourceBindingRejected("NONFINITE_JSON:" + label + ":" + token)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                       parse_constant=constant)
    need(type(value) is dict, "JSON_OBJECT_REQUIRED:" + label)
    return value


def _safe_bytes(root: Path, relative: str) -> bytes:
    rel = PurePosixPath(relative)
    need(not rel.is_absolute() and ".." not in rel.parts and rel.as_posix() == relative,
         "UNSAFE_RELATIVE_PATH:" + relative)
    path = root.joinpath(*rel.parts)
    for item in (path, *path.parents):
        need(not item.is_symlink(), "SYMLINK_REJECTED:" + relative)
        if item == root:
            break
    need(path.is_file() and path.resolve().is_relative_to(root.resolve()),
         "SOURCE_FILE_MISSING_OR_ESCAPES_ROOT:" + relative)
    return path.read_bytes()


def _float_fraction(payload, label):
    need(type(payload) is dict and set(payload) == {"numerator", "denominator"},
         "INVALID_EXACT_FRACTION:" + label)
    n, d = payload["numerator"], payload["denominator"]
    need(type(n) is str and type(d) is str and n.lstrip("-").isdigit()
         and d.isdigit() and int(d) > 0, "INVALID_EXACT_FRACTION_TOKENS:" + label)
    return int(n) / int(d)


def _same(actual, expected, label):
    need(actual == expected, "REVIEW_EVIDENCE_DOES_NOT_MATCH_SOURCE:" + label)


def verify_snapshot(root, w4_head, review_evidence, *,
                    expected_head=W4_REVIEWED_COMMIT,
                    expected_files=EXPECTED_FILES):
    root = Path(root).resolve(strict=True)
    need(type(w4_head) is str and HEX40.fullmatch(w4_head), "INVALID_W4_HEAD")
    need(w4_head == expected_head, "UNREVIEWED_W4_HEAD:" + w4_head)

    raw = {}
    hashes = {}
    for relative, expected in expected_files.items():
        need(type(expected) is str and SHA.fullmatch(expected), "BAD_EXPECTED_SHA:" + relative)
        data = _safe_bytes(root, relative)
        actual = hashlib.sha256(data).hexdigest()
        need(actual == expected, "W4_SOURCE_SHA256_MISMATCH:" + relative)
        raw[relative] = data
        hashes[relative] = actual

    request = strict_json(raw[P20_REQUEST], P20_REQUEST)
    manifest = strict_json(raw[P19_MANIFEST], P19_MANIFEST)
    p19 = strict_json(raw[P19_REPORT], P19_REPORT)
    p20 = strict_json(raw[P20_FRAME_REPORT], P20_FRAME_REPORT)

    _same(request["source_w0_commit"], "5bab2eb2616df306906a6887a273f68acfa49320",
          "P20_request.source_w0_commit")
    _same(p20["actual_core_sources"]["commit"], request["source_w4_commit"],
          "P20_request_and_frame_report_core_commit")
    need(p20["actual_core_sources"]["native_core_executed"] is False
         and p20["actual_core_sources"]["whole_commit_tree_verified"] is False,
         "P20_FRAME_REPORT_SCOPE_CHANGED")

    # P20 request must identify the exact P19 files that were actually hashed.
    _same(request["manifest"]["path"], P19_MANIFEST, "request.manifest.path")
    _same(request["manifest"]["sha256"], hashes[P19_MANIFEST], "request.manifest.sha256")
    _same(request["canonical_report"]["path"], P19_REPORT, "request.canonical_report.path")
    _same(request["canonical_report"]["sha256"], hashes[P19_REPORT], "request.canonical_report.sha256")
    _same(set(request["material_inputs"]), set(MATERIAL_KEYS), "request.material_inputs.keys")

    material_paths = {}
    for name in MATERIAL_KEYS:
        ref = request["material_inputs"][name]
        path = ref["path"]
        material_paths[name] = path
        _need_prefix = "P19_material_case/"
        need(path.startswith(_need_prefix), "REQUEST_MATERIAL_PATH_OUTSIDE_P19_CASE:" + name)
        manifest_path = path[len(_need_prefix):]
        _same(manifest_path, manifest["material_files"][name],
              "manifest.material_files." + name)
        _same(ref["sha256"], hashes[path],
              "request.material_inputs." + name + ".sha256")
        _same(manifest["files_sha256"][manifest_path], hashes[path],
              "manifest.files_sha256." + manifest_path)
        _same(manifest["files_sha256"][manifest_path], ref["sha256"],
              "P20_and_P19_material_sha_disagree:" + name)

    need(manifest["scientific_flags"]["W0_physical_tip_or_FD_approved"] is False
         and manifest["scientific_flags"]["W2_Teapot_teacher_admitted"] is False
         and manifest["scientific_flags"]["printability_certified"] is False,
         "P19_MANIFEST_PREMATURE_ADMISSION")
    need(p19["status"] == "P19_EXACT_SAVED_SOLID_AND_COMPLETE_ORIGINAL_SHAFT_PASS_NOT_ADMITTED",
         "P19_REPORT_STATUS_CHANGED")
    need(p19["geometry"]["complete_original_shaft_in_fixed"] is True
         and p19["geometry"]["design_shaft_separation_certified"] is True,
         "P19_SAVED_SHAFT_GEOMETRY_RECEIPT_MISSING")
    need(p19["scientific_flags"]["printability_certified"] is False
         and p19["scientific_flags"]["training_admitted"] is False,
         "P19_REPORT_PREMATURE_ADMISSION")
    need(p19["physical_proposal"]["status"] == "P13_UNIFIED_PHYSICAL_CASE_PROPOSAL_NOT_W0_APPROVED",
         "P19_PHYSICAL_PROPOSAL_STATUS_CHANGED")

    units = request["units"]
    case = p19["physical_proposal"]["case_config"]
    need(units["fixed_density"] == 1 and units["design_density"] == 1,
         "P20_NATIVE_DENSITY_NOT_ONE")
    need(units["physical_parameters_approved"] is False,
         "P20_PHYSICAL_PARAMETERS_CLAIMED_APPROVED")
    need(request["admission"]["W0_owner_admitted"] is False
         and request["admission"]["original_author_CAD"] is False,
         "P20_REQUEST_ADMISSION_FLAGS_CHANGED")
    _same(case["scale_m_per_unit"], units["length_m_per_reference_binary64"],
          "P19_P20_scale")
    _same(case["density_kg_m3"], units["physical_density_kg_m3"], "P19_P20_density")
    _same(case["density_model"], "ASSUMED_UNIFORM_SOLID_NOT_PRINTED_MATERIAL_CERTIFICATE",
          "P19_density_model")
    need(request["target"]["mode"] == "SPINNING_TOP"
         and request["target"]["axis"] == [0, 0, 1]
         and request["target"]["origin"] == [0, 0, 0]
         and request["target"]["support_points"] == [],
         "P20_TARGET_OR_SUPPORT_CONTRACT_CHANGED")
    need(request["geometry_policy"]["shaft_material"] ==
         "S_ALREADY_INCLUDED_IN_F_NEVER_ADDED_AGAIN",
         "P20_SHAFT_ACCOUNTING_POLICY_CHANGED")

    frame = p20["actual_frame"]
    need(frame["coefficient_frame"] == "INPUT_NORMALIZED_TARGET_V1",
         "P20_NATIVE_COEFFICIENT_FRAME_CHANGED")
    need(frame["native_length_scale_is_bbox_L_not_SI_0025"] is True,
         "P20_FRAME_SCALE_SEMANTICS_CHANGED")
    need(frame["actual_target_axes_exact"] == [
        [{"numerator":"1","denominator":"1"},{"numerator":"0","denominator":"1"},{"numerator":"0","denominator":"1"}],
        [{"numerator":"0","denominator":"1"},{"numerator":"1","denominator":"1"},{"numerator":"0","denominator":"1"}],
        [{"numerator":"0","denominator":"1"},{"numerator":"0","denominator":"1"},{"numerator":"1","denominator":"1"}]],
         "P20_TARGET_AXES_NOT_IDENTITY")
    length_native = _float_fraction(frame["length_original_per_normalized_exact"],
                                    "length_original_per_normalized_exact")
    density_original_per_native = _float_fraction(
        frame["density_original_per_normalized_exact"],
        "density_original_per_normalized_exact")
    need(abs(length_native - 2.5716) <= 1e-15, "P20_NORMALIZATION_L_CHANGED")
    need(density_original_per_native == 1.0, "P20_DENSITY_FRAME_SCALE_CHANGED")
    need(p20["physical_replay"]["density_reference"] == 1.0,
         "P20_REPLAY_DENSITY_REFERENCE_CHANGED")
    need(p20["physical_replay"]["shaft_already_in_F_not_added_to_mass"] is True,
         "P20_SHAFT_DOUBLE_COUNT_POLICY_CHANGED")
    need(p20["physical_replay"]["source_report_sha256"] == hashes[P19_REPORT],
         "P20_REPLAY_NOT_BOUND_TO_P19_REPORT")
    need(p20["physical_replay"]["source_meshes_reintegrated"] is False
         and p20["physical_replay"]["P19_geometric_proofs_reexecuted"] is False,
         "P20_PHYSICAL_REPLAY_SCOPE_OVERSTATED")
    need(p20["physical_replay"]["source_manifest_sha256"] == hashes[P19_MANIFEST],
         "P20_REPLAY_NOT_BOUND_TO_P19_MANIFEST")
    need(p20["physical_replay"]["source_material_sha256"] ==
         {name: hashes[material_paths[name]] for name in MATERIAL_KEYS},
         "P20_REPLAY_MATERIAL_SHA_BINDING_CHANGED")
    need(p20["scientific_flags"]["physical_material_validated"] is False
         and p20["scientific_flags"]["native_M6_material_partition_certified"] is False
         and p20["scientific_flags"]["optimization_admitted"] is False
         and p20["scientific_flags"]["training_admitted"] is False,
         "P20_REPORT_PREMATURE_ADMISSION")

    # Derive all saved-mesh physical facts from the source reports, not W0 literals.
    materials = p20["physical_replay"]["materials"]
    p19_m = p19["physical_proposal"]["materials"]["M"]
    construction = manifest["construction"]
    derived = {
        "p20_request_sha256": hashes[P20_REQUEST],
        "p19_manifest_sha256": hashes[P19_MANIFEST],
        "obj_sha256": {name: hashes[material_paths[name]]
                       for name in MATERIAL_KEYS},
        "scale_m_per_reference": units["length_m_per_reference_binary64"],
        "density_kg_m3": units["physical_density_kg_m3"],
        "density_model": case["density_model"],
        "bounds_m": p19_m["bounds_m"],
        "length_original_per_normalized": length_native,
        "frame_length_is_bbox_L": frame["native_length_scale_is_bbox_L_not_SI_0025"],
        "mass_kg": {name: materials[name]["mass_kg"] for name in MATERIAL_KEYS},
        "center_of_mass_m": {name: materials[name]["center_of_mass_m"] for name in MATERIAL_KEYS},
        "full_inertia_com_kg_m2": {
            name: materials[name]["full_inertia_com_kg_m2"] for name in MATERIAL_KEYS},
        "shaft_included_in_fixed": p20["physical_replay"]["shaft_already_in_F_not_added_to_mass"],
        "shaft_added_separately_to_total": False,
        "radial_envelope_scale": construction["shaft_envelope"]["radial_scale_exact"],
        "xy_rotation_degrees": construction["shaft_envelope"]["rotation_degrees_display"],
        "original_shaft_bytes_preserved": construction["original_shaft_file_unchanged"],
        "original_author_cad": request["admission"]["original_author_CAD"],
        "physical_parameters_approved": units["physical_parameters_approved"],
        "support_points": request["target"]["support_points"],
        "target_tip_reference": request["target"]["origin"],
        "represented_tip_exactly_equals_requested": frame["represented_tip_is_exact_requested_tip"],
        "represented_tip_minus_requested_exact": frame["represented_tip_minus_requested_exact"],
        "p19_complete_shaft_in_fixed": p19["geometry"]["complete_original_shaft_in_fixed"],
        "p19_design_shaft_separation": p19["geometry"]["design_shaft_separation_certified"],
        "global_printability_or_strength_proved": p19["scientific_flags"]["printability_certified"],
        "native_implicit_region_equality_proved":
            p20["scientific_flags"]["native_implicit_identity_certified"],
    }
    _same(review_evidence.get("w0_baseline"), request["source_w0_commit"],
          "W0_review_evidence.w0_baseline")
    for key, value in derived.items():
        _same(review_evidence.get(key), value, "W0_review_evidence." + key)

    return {
        "schema": "W0_P30_TEAPOT_SOURCE_BINDING_M21_V1",
        "status": "SOURCE_BYTES_AND_CROSS_REPORT_BINDINGS_VERIFIED_NOT_PHYSICAL_APPROVAL",
        "w4_head": w4_head,
        "source_sha256": hashes,
        "derived_review_facts": derived,
        "native_coordinate_frame": {
            "frame": frame["coefficient_frame"],
            "native_material_density": units["design_density"],
            "native_length_ref": 1.0,
            "native_density_ref": units["design_density"],
            "original_per_native_length": length_native,
            "original_per_native_density": density_original_per_native,
            "SI_transform_requires_separate_r_and_J_pushforward": True,
        },
        "admission": {
            "W0_physical_case_approved": False,
            "P30B_diagnostic_authorized": False,
            "W2_teacher_training_allowed": False,
            "continuous_smooth_neighborhood_certified": False,
            "Newton_accepted": False,
            "training_admissible": False,
        },
        "scope": "HASH_AND_CROSS_REPORT_INTEGRITY_ONLY_NO_NATIVE_GEOMETRY_OR_PHYSICAL_CERTIFICATION",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w4-root", type=Path, required=True,
                        help="P1 directory from the W4 branch archive")
    parser.add_argument("--w4-head", required=True)
    parser.add_argument("--review-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        evidence = strict_json(args.review_evidence.read_bytes(), "W0 review evidence")
        result = verify_snapshot(args.w4_root, args.w4_head, evidence)
        if args.output.exists() or args.output.is_symlink():
            raise SourceBindingRejected("REFUSE_OVERWRITE")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True,
                                          allow_nan=False) + "\\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "w4_head": result["w4_head"],
                          "hashed_files": len(result["source_sha256"]),
                          "physical_case_approved": False,
                          "P30B_authorized": False}, sort_keys=True))
        return 0
    except (SourceBindingRejected, OSError, KeyError, TypeError, ValueError,
            json.JSONDecodeError) as exc:
        print(json.dumps({"status": "W0_M21_SOURCE_BINDING_REJECTED",
                          "reason": str(exc), "P30B_authorized": False},
                         sort_keys=True), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
