"""Replay the frozen M21 Heart label's numeric evidence; never release a label.

Run from the W2 teacher directory:
  PYTHONINTMAXSTRDIGITS=100000 python m22_audit_heart_label.py \
      --spec FROZEN_SPEC.json --label M21_PILOT_LABEL.json --result M21_PILOT_RESULT.json
Optionally add --material SAME_CALL_MATERIAL.json to re-integrate its boundary.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path

from independent_reference import compare_predeclared_budget, integrate_exact_boundary
from m16_native_acceptance import file_hash, strict_json
from native_cherchi_teacher import digest, verify

RECEIPT = Path(__file__).with_name("M21_HEART_NATIVE_DIAGNOSTIC_RESULT.json")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def audit(spec_path, label_path, result_path, receipt, material_path=None):
    require(file_hash(spec_path) == receipt["spec_sha256"], "FROZEN_SPEC_HASH_MISMATCH")
    spec = strict_json(spec_path.read_bytes())
    result = strict_json(result_path.read_bytes())
    require(result["label_sha256"] == file_hash(label_path), "RAW_LABEL_HASH_MISMATCH")
    require(result["status"] == receipt["pilot_status"], "PILOT_STATUS_MISMATCH")
    label = strict_json(label_path.read_bytes())
    payload = verify(label, expected_q=spec["native_c"],
                     expected_model_sha256=spec["expected_model_sha256"],
                     expected_native_module_sha256=spec["expected_native_module_sha256"])
    require(payload["split"] == "excluded" and payload["J_D"] is None and
            payload["derivative_contract"] is None and payload["derivative_status"] == "UNKNOWN"
            and payload["topology_status"] == "OBSERVED_DISCRETE_MAP"
            and payload["failure_reason"] == receipt["native_child_exit_reason"],
            "EXPECTED_EXCLUDED_DIAGNOSTIC")
    for field in ("r_D", "r_F"):
        require(digest(payload[field]) == digest(receipt[field]), "TRANSCRIBED_MOMENT_MISMATCH:" + field)
    require(payload["frame"] == spec["frame"] and payload["density"] == spec["request"]["material_density"],
            "FROZEN_FRAME_OR_DENSITY_MISMATCH")
    proof = payload["exact_proof"]
    require(proof["native_cherchi"] is True and proof["kind"] == "cherchi_same_call_discrete_map",
            "EXPECTED_NATIVE_EVALUATION")
    binding = proof["same_call_attachment"]
    require(binding["schema"] == "w2-same-call-material-binding-v1" and
            binding["native_c_sha256"] == digest(spec["native_c"]), "MATERIAL_BINDING_MISMATCH")
    reference = proof["independent_ten_moment_audit"]
    require(reference["schema"] == "w2-independent-tetra-integral-v1", "REFERENCE_SCHEMA_MISMATCH")
    exact = [Fraction(s) for s in reference["reference_raw_moments_exact"]]
    budgets = spec["reference_absolute_tolerances"]
    compare = compare_predeclared_budget(payload["r_D"], exact, budgets)
    require(compare["within_tolerance"] and compare == reference["comparison"],
            "STORED_COMPARISON_MISMATCH")
    require(all(compare[k] == v for k, v in receipt["independent_comparison"].items()),
            "TRANSCRIBED_COMPARISON_MISMATCH")
    if material_path is not None:
        material = strict_json(material_path.read_bytes())
        require(digest(material) == binding["serialized_material_sha256"], "MATERIAL_HASH_MISMATCH")
        recomputed, info = integrate_exact_boundary(material["variable_rational_vertices"],
                                                     material["variable_faces"], payload["density"])
        require(info["exact_boundary_sha256"] == reference["exact_boundary_sha256"]
                and recomputed == exact, "INDEPENDENT_BOUNDARY_REPLAY_MISMATCH")
    return {"scope": "frozen_heart_label_numeric_replay", "spec_sha256": receipt["spec_sha256"],
            "label_sha256": result["label_sha256"], "result_sha256": file_hash(result_path),
            "reference_components": len(exact), "maximum_absolute_error": compare["maximum_absolute_error"],
            "material_reintegrated": material_path is not None, "split": "excluded", "J_D": None,
            "training_admitted": False, "production_postflight_reaudited": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("spec", "label", "result"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--material", type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.spec, args.label, args.result,
                       strict_json(RECEIPT.read_bytes()), args.material)
    except (OSError, KeyError, ValueError, TypeError, ZeroDivisionError, OverflowError) as err:
        parser.exit(2, "M22 numeric replay blocked: " + str(err) + "\n")
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
