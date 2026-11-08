"""W0 independent physical-case review for Teapot P30-B.

This module is a fail-closed evidence reviewer. It deliberately does not create
P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json. A geometry/arithmetic receipt is not
an owner-issued physical case or support/contact specification.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any

W0_BASELINE = "5bab2eb2616df306906a6887a273f68acfa49320"
P20_REQUEST_SHA256 = "a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9"
P27_MANIFEST_SHA256 = "3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773"
P27_LOCK_SHA256 = "451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4"
P30_PRIVATE_PLAN_SHA256 = "fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc"
P30_BASE_C_SHA256 = "57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca"
P30_SAME_CALL_JACOBIAN_SHA256 = "26cf3b5dd53d45a4b80f14319b39d28fa9ef7b8d8be3a915189e90ba077a08a5"
P19_MANIFEST_SHA256 = "c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6"
OBJ_SHA256 = {
    "M": "0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704",
    "F": "5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8",
    "D": "d64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073",
    "S": "65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0",
}

class ReviewRejected(ValueError):
    pass


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise ReviewRejected(code)


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    _need(p.is_file() and not p.is_symlink(), "INPUT_NOT_REGULAR_FILE")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_frozen_file(path: str | Path, expected_sha256: str) -> bool:
    return sha256_file(path) == expected_sha256


def audit_case(e: dict[str, Any]) -> dict[str, Any]:
    """Audit facts extracted from the exact pinned P19/P20/P27/P28/P30 records.

    P27 manifest/lock and P30 private-plan hashes are reported as corroborated
    by the P28/P27/P30 public receipts; the private archive/plan bytes are not
    publicly present on the W4 branch and therefore are NOT claimed rehashed.
    """
    _need(type(e) is dict, "EVIDENCE_OBJECT_REQUIRED")
    _need(e.get("w0_baseline") == W0_BASELINE, "W0_BASELINE_MISMATCH")
    _need(e.get("p20_request_sha256") == P20_REQUEST_SHA256, "P20_REQUEST_IDENTITY_MISMATCH")
    _need(e.get("p19_manifest_sha256") == P19_MANIFEST_SHA256, "P19_MANIFEST_IDENTITY_MISMATCH")
    _need(e.get("obj_sha256") == OBJ_SHA256, "P19_OBJ_IDENTITY_MISMATCH")
    _need(e.get("p27_manifest_sha256") == P27_MANIFEST_SHA256, "P27_MANIFEST_IDENTITY_MISMATCH")
    _need(e.get("p27_lock_sha256") == P27_LOCK_SHA256, "P27_LOCK_IDENTITY_MISMATCH")
    _need(e.get("p30_private_plan_sha256") == P30_PRIVATE_PLAN_SHA256, "P30_PLAN_IDENTITY_MISMATCH")
    _need(e.get("base_native_c_sha256") == P30_BASE_C_SHA256, "P30_BASE_C_IDENTITY_MISMATCH")
    _need(e.get("same_call_jacobian_sha256") == P30_SAME_CALL_JACOBIAN_SHA256, "P30_JACOBIAN_IDENTITY_MISMATCH")

    # Physical model facts: these are saved-mesh diagnostics under assumptions.
    _need(e.get("scale_m_per_reference") == 0.025, "PROPOSED_SCALE_CHANGED")
    _need(e.get("density_kg_m3") == 1200, "PROPOSED_DENSITY_CHANGED")
    _need(e.get("density_model") == "ASSUMED_UNIFORM_SOLID_NOT_PRINTED_MATERIAL_CERTIFICATE", "DENSITY_MODEL_NOT_EXPLICIT")
    _need(e.get("bounds_m") == [[-0.029950000000000004,-0.020000000000000004,0.0],[0.03434,0.020000000000000004,0.04275]], "MESH_BOUNDS_CHANGED")
    _need(e.get("length_original_per_normalized") == 2.5716 and e.get("frame_length_is_bbox_L") is True, "NORMALIZED_FRAME_SCALE_CHANGED")
    _need(abs(e["length_original_per_normalized"] * e["scale_m_per_reference"] - 0.06429) < 1e-15, "CONDITIONAL_SI_LENGTH_TRANSFORM_MISMATCH")
    masses=e.get("mass_kg")
    _need(type(masses) is dict and set(masses)=={"M","F","D","S"}, "MATERIAL_MASS_TABLE_INVALID")
    for v in masses.values():
        _need(type(v) in (float,int) and math.isfinite(v) and v > 0, "INVALID_MATERIAL_MASS")
    _need(abs(masses["M"] - masses["F"] - masses["D"]) <= 2e-17, "M_NOT_EQUAL_F_PLUS_D")
    _need(e.get("shaft_included_in_fixed") is True, "SHAFT_NOT_DECLARED_IN_FIXED")
    _need(e.get("shaft_added_separately_to_total") is False, "SHA_DOUBLE_COUNT_RISK")
    _need(masses["S"] < masses["F"], "SHAFT_MASS_EXCEEDS_FIXED_MASS")
    inertia=e.get("full_inertia_com_kg_m2")
    _need(type(inertia) is dict and set(inertia)=={"M","F","D","S"}, "INERTIA_TABLE_INVALID")
    for name,mat in inertia.items():
        _need(type(mat) is list and len(mat)==3 and all(type(row) is list and len(row)==3 for row in mat), "INERTIA_SHAPE_INVALID:"+name)
        _need(all(type(v) in (int,float) and math.isfinite(v) for row in mat for v in row), "INERTIA_NONFINITE:"+name)
        _need(all(abs(mat[i][j]-mat[j][i]) <= max(1e-30,abs(mat[i][j])*1e-12) for i in range(3) for j in range(3)), "INERTIA_NOT_SYMMETRIC:"+name)
        minor2=mat[0][0]*mat[1][1]-mat[0][1]*mat[1][0]
        det=(mat[0][0]*(mat[1][1]*mat[2][2]-mat[1][2]*mat[2][1])-
             mat[0][1]*(mat[1][0]*mat[2][2]-mat[1][2]*mat[2][0])+
             mat[0][2]*(mat[1][0]*mat[2][1]-mat[1][1]*mat[2][0]))
        _need(mat[0][0]>0 and minor2>0 and det>0, "INERTIA_NOT_POSITIVE_DEFINITE:"+name)

    # Saved-mesh construction is mathematically auditable but not an author CAD.
    _need(e.get("radial_envelope_scale") == "9/8", "SHAFT_ENVELOPE_SCALE_CHANGED")
    _need(e.get("xy_rotation_degrees") == 7, "SHAFT_ENVELOPE_ROTATION_CHANGED")
    _need(e.get("original_shaft_bytes_preserved") is True, "ORIGINAL_SHAFT_BYTES_NOT_PRESERVED")
    _need(e.get("original_author_cad") is False, "AUTHOR_CAD_STATUS_CHANGED")
    _need(e.get("physical_parameters_approved") is False, "PHYSICAL_PARAMETERS_CLAIMED_APPROVED")
    _need(e.get("support_points") == [], "SUPPORT_POINT_RECORD_CHANGED")
    _need(e.get("target_tip_reference") == [0,0,0], "REQUESTED_TIP_CHANGED")
    _need(e.get("represented_tip_exactly_equals_requested") is False, "TIP_FRAME_FACT_CHANGED")
    _need(e.get("p19_complete_shaft_in_fixed") is True, "P19_SHAFT_CONTAINMENT_NOT_PROVED")
    _need(e.get("p19_design_shaft_separation") is True, "P19_DESIGN_SHAFT_SEPARATION_NOT_PROVED")
    _need(e.get("global_printability_or_strength_proved") is False, "UNSUPPORTED_STRENGTH_CLAIM")
    _need(e.get("native_implicit_region_equality_proved") is False, "UNSUPPORTED_NATIVE_REGION_CLAIM")

    blockers = [
        "NO_AUTHORITATIVE_ORIGINAL_TEAPOT_CAD_OR_DIMENSIONED_DRAWING",
        "0.025_M_PER_REFERENCE_UNIT_IS_PROPOSED_NOT_OWNER_APPROVED",
        "1200_KG_M3_UNIFORM_SOLID_DENSITY_IS_ASSUMED_NOT_MATERIAL_CERTIFIED",
        "NO_AUTHENTIC_TIP_CONTACT_GEOMETRY_OR_CONTACT_PATCH",
        "SUPPORT_POINTS_EMPTY_AND_NO_SUPPORT_OR_REACTION_CONSTRAINTS",
        "NO_OWNER_APPROVED_SPIN_AXIS_BEARING_OR_LOAD_PATH_SPECIFICATION",
        "9_OVER_8_RADIAL_SHAFT_ENVELOPE_AND_7_DEG_ROTATION_ARE_RECONSTRUCTION_RULES_NOT_AUTHOR_CAD",
        "D_IS_GEOMETRICALLY_PARTITIONED_BUT_NO_GLOBAL_MINIMUM_WALL_OR_STRUCTURAL_STRENGTH_CERTIFICATE",
        "P30_PRIVATE_PLAN_AND_P27_LOCK_ARCHIVE_BYTES_NOT_PRESENT_IN_PUBLIC_W4_BRANCH_FOR_DIRECT_REHASH",
        "P20_FRAME_HAS_NONZERO_EXACT_TIP_RESIDUAL_AND_NO_PHYSICAL_TOLERANCE_AUTHORITY",
    ]
    return {
        "schema": "W0_TEAPOT_P30_PHYSICAL_REVIEW_V1",
        "decision": "BLOCKED_PHYSICAL_CASE_NOT_OWNER_APPROVED",
        "verified_public_pins": {
            "w0_baseline": W0_BASELINE,
            "p20_request_sha256": P20_REQUEST_SHA256,
            "p19_manifest_sha256": P19_MANIFEST_SHA256,
            "p27_manifest_sha256_from_p28_receipt": P27_MANIFEST_SHA256,
            "p27_lock_sha256_from_p27_review_and_p28_receipt": P27_LOCK_SHA256,
            "p30_private_plan_sha256_from_public_receipt_only": P30_PRIVATE_PLAN_SHA256,
            "base_native_c_sha256_from_public_receipt_only": P30_BASE_C_SHA256,
            "same_call_jacobian_sha256_from_p28_receipt": P30_SAME_CALL_JACOBIAN_SHA256,
            "p19_obj_sha256": OBJ_SHA256,
        },
        "p27_p28_scope": "FORMAL_M6_GEOMETRY_AND_SAME_CALL_ARITHMETIC_RECEIPT_ONLY_NOT_OWNER_PHYSICAL_ADMISSION",
        "physical_case": {
            "proposed_scale_m_per_reference": 0.025,
            "proposed_density_kg_m3": 1200,
            "proposed_uniform_solid_mass_kg": masses["M"],
            "fixed_mass_kg": masses["F"], "design_mass_kg": masses["D"],
            "shaft_mass_kg_diagnostic_only_already_in_fixed": masses["S"],
            "center_of_mass_m": e["center_of_mass_m"],
            "full_inertia_com_kg_m2": inertia,
            "bbox_m": e["bounds_m"],
            "bbox_mm": [64.29,40.0,42.75],
            "conditional_normalized_frame_length_m": 0.06429,
            "conditional_length_ref_candidate_m": 0.06429,
            "conditional_density_ref_candidate_kg_m3": 1200,
            "conditional_units_are_not_approved": True,
            "shaft_envelope_radial_scale": "9/8",
            "shaft_envelope_xy_rotation_degrees": 7,
            "target_axis": [0,0,1], "nominal_tip": [0,0,0],
            "support_points": [],
            "M_equals_F_plus_D": True,
            "S_already_in_F": True,
            "D_saved_surface_topology_pass": True,
            "global_strength_printability": False,
        },
        "p30b": {
            "diagnostic_pilot_authorized": False,
            "pilot_directions": [0,1,2],
            "maximum_real_native_points": 12,
            "proposed_h_radians": 0.002,
            "h_semantics": "GEODESIC_STEP_ON_10D_UNIT_NATIVE_COEFFICIENT_SPHERE_NOT_A_RIGID_BODY_ROTATION",
            "h_approved": False,
            "length_ref": None,
            "density_ref": None,
            "max_normalized_jacobian_error": None,
            "tolerance_reason": "PHYSICAL_SCALE_AND_DENSITY_UNAPPROVED; FEATURE_BRANCH_UNAVAILABLE; NO_MEASURED_CASE_SPECIFIC_NOISE_OR_ERROR_BUDGET",
        },
        "blockers": blockers,
        "newton_authorized": False,
        "training_authorized": False,
        "continuous_smooth_neighborhood_certified": False,
        "physical_validation_authorized": False,
        "real_native_pilot_authorized": False,
    }


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args(argv)
    raw=a.evidence.read_text(encoding="utf-8")
    doc=json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ReviewRejected("NONFINITE_JSON")))
    result=audit_case(doc)
    if a.output.exists() or a.output.is_symlink(): raise FileExistsError("REFUSE_OVERWRITE")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
    print(result["decision"])
    return 3

if __name__ == "__main__":
    raise SystemExit(main())
