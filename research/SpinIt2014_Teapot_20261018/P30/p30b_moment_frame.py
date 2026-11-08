"""W4 M22: source-pinned W0 M21 moment-frame integration.

P20 Cherchi outputs are captured natively in INPUT_NORMALIZED_TARGET_V1.
The exact W0 M21 implementation is vendored under w0_m21_reference/ and
verified by Git commit + Git blob identities. No runtime import from W0's
branch is performed.

Native mode preserves r/J and requires L=1, R=1. Conditional SI mode applies
the same affine raw10 pushforward to every r sample and every output column of
Jc. The coefficient vector c and tangent directions are never transformed.
This module does not approve the physical case, pilot, smoothness, Newton or
training.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from w0_m21_reference.teapot_moment_frame_m21 import (
    NATIVE_FRAME, SI_FRAME,
    MomentFrameRejected,
    build_p20_moment_frame_contract,
    normalization_for_frame,
    validate_normalization,
    transform_raw10_native_to_si,
    transform_jacobian_native_to_si,
    audit_tangent_neighborhood_in_frame,
)
from w0_m21_reference.moment_coordinates import checked


W0_M21_SOURCE_COMMIT = "cd72c04631a672408aaf576ab1b98747625f9468"
W0_M21_TESTED_COMMIT = "e1b765c46bfce0ece47e0f691d8131f1b50c9b1d"
W0_M21_SOURCE_BLOBS = {
    "teapot_moment_frame_m21.py": "f38b135b9d61a214e2c8b4240654dcfd8a57fb47",
    "moment_coordinates.py": "7f844fadc02b8f02c8560b5180e29bac78332ab4",
    "tangent_neighborhood.py": "4fbfd52a787f3cbbc4228b1c1bbdab01638ed57f",
}
P20_REQUEST_SHA256 = "a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9"
P20_FRAME_REPORT_SHA256 = "eaba6b60753fcb2141be425081897a8e891821349c166f5daff143d3ce9ea5fc"
VIEW_SCHEMA = "W4_P30B_MOMENT_FRAME_VIEW_V1"
BUDGET_SCHEMA = "W0_TEAPOT_P30_DIAGNOSTIC_AUTHORIZATION_V1"
RELEASE_CLOSED = {
    "W0_owner_admitted": False,
    "W2_teacher_training_allowed": False,
    "P30B_real_native_authorized": False,
    "continuous_smooth_neighborhood_certified": False,
    "Newton_accepted": False,
    "training_admissible": False,
}


class MomentFrameIntegrationRejected(ValueError):
    pass


def _need(condition, reason):
    if not condition:
        raise MomentFrameIntegrationRejected(reason)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\\0" + raw).hexdigest()


def strict_json(raw, label):
    def pairs(rows):
        result = {}
        for key, value in rows:
            _need(key not in result, "DUPLICATE_JSON_KEY:" + label + ":" + key)
            result[key] = value
        return result

    def bad_constant(token):
        raise MomentFrameIntegrationRejected("NONFINITE_JSON:" + label + ":" + token)

    result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                        parse_constant=bad_constant)
    _need(type(result) is dict, "JSON_OBJECT_REQUIRED:" + label)
    return result


def source_provenance():
    root = Path(__file__).resolve().parent / "w0_m21_reference"
    observed = {}
    for name, expected_blob in W0_M21_SOURCE_BLOBS.items():
        path = root / name
        _need(path.is_file() and not path.is_symlink(),
              "W0_M21_VENDORED_SOURCE_MISSING:" + name)
        raw = path.read_bytes()
        actual_blob = git_blob_sha1(raw)
        _need(actual_blob == expected_blob,
              "W0_M21_VENDORED_GIT_BLOB_MISMATCH:" + name)
        observed[name] = {
            "git_blob_sha1": actual_blob,
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
        }
    return {
        "w0_branch": "research/neuralmoments-w0-contract-20261019",
        "w0_m21_source_commit": W0_M21_SOURCE_COMMIT,
        "w0_m21_tested_commit": W0_M21_TESTED_COMMIT,
        "source_files": observed,
        "source_bundle_sha256": sha256_bytes(canonical_bytes(observed)),
        "runtime_import_from_w0_branch": False,
    }


def load_contract(request_path, frame_report_path):
    request_path = Path(request_path)
    frame_report_path = Path(frame_report_path)
    request_raw = request_path.read_bytes()
    frame_raw = frame_report_path.read_bytes()
    request_sha = sha256_bytes(request_raw)
    frame_sha = sha256_bytes(frame_raw)
    _need(request_sha == P20_REQUEST_SHA256, "P20_REQUEST_SHA256_MISMATCH")
    _need(frame_sha == P20_FRAME_REPORT_SHA256, "P20_FRAME_REPORT_SHA256_MISMATCH")
    request = strict_json(request_raw, "P20 request")
    frame_report = strict_json(frame_raw, "P20 frame report")
    contract = build_p20_moment_frame_contract(request, frame_report)
    contract_report = contract.report()
    contract_sha = sha256_bytes(canonical_bytes(contract_report))
    affine_identity = {
        "schema": "W4_P30B_AFFINE_MOMENT_TRANSFORM_IDENTITY_V1",
        "source_frame": contract.native_frame,
        "target_frame": contract.si_frame,
        "linear": contract_report["target_to_si_linear"],
        "translation": contract_report["target_to_si_translation"],
        "native_to_si_density_ratio": contract.native_to_si_density_ratio,
        "frame_identity_sha256": contract.frame_identity_sha256,
        "p20_request_sha256": request_sha,
        "p20_frame_report_sha256": frame_sha,
    }
    affine_sha = sha256_bytes(canonical_bytes(affine_identity))
    provenance = source_provenance()
    provenance.update({
        "p20_request_sha256": request_sha,
        "p20_frame_report_sha256": frame_sha,
        "frame_contract_sha256": contract_sha,
        "affine_transform_identity_sha256": affine_sha,
    })
    return contract, provenance


def _affine_identity_payload(contract, provenance):
    report = contract.report()
    return {
        "schema": "W4_P30B_AFFINE_MOMENT_TRANSFORM_IDENTITY_V1",
        "source_frame": contract.native_frame,
        "target_frame": contract.si_frame,
        "linear": report["target_to_si_linear"],
        "translation": report["target_to_si_translation"],
        "native_to_si_density_ratio": contract.native_to_si_density_ratio,
        "frame_identity_sha256": contract.frame_identity_sha256,
        "p20_request_sha256": provenance["p20_request_sha256"],
        "p20_frame_report_sha256": provenance["p20_frame_report_sha256"],
    }


def frame_metadata(contract, provenance, moment_coordinate_frame):
    _need(moment_coordinate_frame in (NATIVE_FRAME, SI_FRAME),
          "UNKNOWN_MOMENT_COORDINATE_FRAME")
    length_ref, density_ref = normalization_for_frame(contract, moment_coordinate_frame)
    validate_normalization(contract, moment_coordinate_frame, length_ref, density_ref)
    _need(sha256_bytes(canonical_bytes(contract.report())) ==
          provenance["frame_contract_sha256"], "FRAME_CONTRACT_OBJECT_CHANGED")
    _need(sha256_bytes(canonical_bytes(_affine_identity_payload(contract, provenance))) ==
          provenance["affine_transform_identity_sha256"],
          "AFFINE_TRANSFORM_IDENTITY_CHANGED")
    return {
        "moment_coordinate_frame": moment_coordinate_frame,
        "normalization_L": float(length_ref),
        "normalization_R": float(density_ref),
        "native_material_density": float(contract.native_material_density),
        "coordinate_transform_applied": moment_coordinate_frame == SI_FRAME,
        "affine_transform_identity_sha256": provenance["affine_transform_identity_sha256"],
        "frame_contract_sha256": provenance["frame_contract_sha256"],
        "frame_contract_source": {
            "w0_m21_source_commit": provenance["w0_m21_source_commit"],
            "w0_m21_tested_commit": provenance["w0_m21_tested_commit"],
            "w0_m21_source_files": provenance["source_files"],
            "w0_m21_source_bundle_sha256": provenance["source_bundle_sha256"],
            "p20_request_sha256": provenance["p20_request_sha256"],
            "p20_frame_report_sha256": provenance["p20_frame_report_sha256"],
            "runtime_import_from_w0_branch": False,
        },
    }


def make_moment_view(native_r, native_j, contract, provenance, moment_coordinate_frame):
    native_r = checked(native_r, (10,), "native r")
    native_j = checked(native_j, (10, 10), "native Jc")
    meta = frame_metadata(contract, provenance, moment_coordinate_frame)
    if moment_coordinate_frame == NATIVE_FRAME:
        r_view = native_r.copy()
        j_view = native_j.copy()
    elif moment_coordinate_frame == SI_FRAME:
        r_view = transform_raw10_native_to_si(native_r, contract)
        j_view = transform_jacobian_native_to_si(native_j, contract)
    else:
        raise MomentFrameIntegrationRejected("UNKNOWN_MOMENT_COORDINATE_FRAME")
    _need(r_view.shape == (10,) and j_view.shape == (10, 10),
          "TRANSFORMED_R_OR_J_SHAPE_INVALID")
    _need(np.isfinite(r_view).all() and np.isfinite(j_view).all(),
          "TRANSFORMED_R_OR_J_NONFINITE")
    return {
        "schema": VIEW_SCHEMA,
        **meta,
        "coefficient_coordinate_frame": "P20_NATIVE_COEFFICIENT_COORDINATES_UNCHANGED",
        "c_and_tangent_basis_transformed": False,
        "native_capture": {
            "moment_coordinate_frame": NATIVE_FRAME,
            "r_sha256": sha256_bytes(canonical_bytes(native_r.tolist())),
            "Jc_sha256": sha256_bytes(canonical_bytes(native_j.tolist())),
        },
        "r_design_in_frame": r_view.tolist(),
        "Jc_in_frame": j_view.tolist(),
    }


def validate_moment_view(view, native_r, native_j, contract, provenance,
                         expected_mode):
    _need(type(view) is dict and view.get("schema") == VIEW_SCHEMA,
          "MOMENT_FRAME_VIEW_SCHEMA_MISMATCH")
    expected = make_moment_view(native_r, native_j, contract, provenance, expected_mode)
    _need(canonical_bytes(view) == canonical_bytes(expected),
          "MOMENT_FRAME_VIEW_DOES_NOT_MATCH_NATIVE_CAPTURE_OR_PINNED_TRANSFORM")
    _need(view.get("normalization_L") > 0 and view.get("normalization_R") > 0,
          "MOMENT_FRAME_NORMALIZATION_INVALID")
    return expected


def _validate_approval_frame(doc, contract, provenance, label):
    _need(type(doc) is dict and doc.get("schema") in (
        "W0_TEAPOT_P30_DIAGNOSTIC_AUTHORIZATION_V1",
        "W2_TEAPOT_P30_FEATURE_PILOT_AUTHORIZATION_V1",
    ), "MISSING_" + label + "_FRAME_APPROVAL_SCHEMA")
    mode = doc.get("moment_coordinate_frame")
    _need(mode in (NATIVE_FRAME, SI_FRAME), label + "_FRAME_MODE_MISSING")
    meta = frame_metadata(contract, provenance, mode)
    for key in (
        "moment_coordinate_frame", "normalization_L", "normalization_R",
        "native_material_density", "affine_transform_identity_sha256",
        "frame_contract_sha256",
    ):
        _need(doc.get(key) == meta[key], label + "_FRAME_BINDING_MISMATCH:" + key)
    _need(doc.get("w0_m21_source_commit") == W0_M21_SOURCE_COMMIT,
          label + "_W0_M21_SOURCE_COMMIT_MISMATCH")
    _need(doc.get("w0_m21_source_bundle_sha256") == provenance["source_bundle_sha256"],
          label + "_W0_M21_SOURCE_BUNDLE_MISMATCH")
    _need(doc.get("w0_m21_source_files") == provenance["source_files"],
          label + "_W0_M21_SOURCE_FILES_MISMATCH")
    _need(doc.get("length_ref") == meta["normalization_L"] and
          doc.get("density_ref") == meta["normalization_R"],
          label + "_LEGACY_NORMALIZATION_FIELDS_MISMATCH")
    return meta


def validate_owner_teacher_frame(w0_doc, w2_doc, contract, provenance):
    w0 = _validate_approval_frame(w0_doc, contract, provenance, "W0")
    w2 = _validate_approval_frame(w2_doc, contract, provenance, "W2")
    _need(w0 == w2, "W0_W2_MOMENT_FRAME_APPROVALS_DISAGREE")
    return {
        **w0,
        "W0_owner_frame_approval_present": True,
        "W2_teacher_frame_approval_present": True,
    }


def audit_tangent_packets(*, budget_receipt, contract, provenance,
                          native_c, native_Jc, tangent_basis, probes,
                          base_feature_branch_sha256, step_radians):
    """Run W0's finite-difference diagnostic only with an explicit W0 budget.

    A numeric PASS is never a continuous smoothness, Newton or training proof.
    """
    mode = budget_receipt.get("moment_coordinate_frame") if type(budget_receipt) is dict else None
    meta = _validate_approval_frame(budget_receipt, contract, provenance, "W0_BUDGET")
    _need(budget_receipt.get("decision") == "APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
          "W0_DIAGNOSTIC_BUDGET_NOT_APPROVED")
    _need(budget_receipt.get("approved_physical_case") is True and
          budget_receipt.get("approve_real_native_pilot") is True,
          "W0_PHYSICAL_CASE_OR_PILOT_NOT_APPROVED")
    budget = budget_receipt.get("max_normalized_jacobian_error")
    _need(type(budget) in (int, float) and math.isfinite(budget) and budget > 0,
          "W0_CASE_SPECIFIC_JACOBIAN_ERROR_BUDGET_MISSING")
    result = audit_tangent_neighborhood_in_frame(
        contract=contract,
        moment_coordinate_frame=mode,
        normalization_L=meta["normalization_L"],
        normalization_R=meta["normalization_R"],
        native_c=native_c,
        Jc=native_Jc,
        tangent_basis=tangent_basis,
        probes=probes,
        base_feature_branch_sha256=base_feature_branch_sha256,
        step_radians=step_radians,
        max_normalized_jacobian_error=float(budget),
    )
    return {
        "schema": "W4_P30B_FRAME_BOUND_TANGENT_DIAGNOSTIC_V1",
        **meta,
        "W0_budget_receipt_sha256": sha256_bytes(canonical_bytes(budget_receipt)),
        "numeric_diagnostic": result,
        "smooth_neighborhood_certified": False,
        "continuous_smooth_neighborhood_certified": False,
        "Newton_accepted": False,
        "training_admissible": False,
    }
