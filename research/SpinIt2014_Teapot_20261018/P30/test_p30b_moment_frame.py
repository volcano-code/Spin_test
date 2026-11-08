from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import p30b_moment_frame as frame


P30 = Path(__file__).resolve().parent
P1 = P30.parent / "P1"
FEATURE = "a" * 64


@pytest.fixture(scope="module")
def contract_and_provenance():
    return frame.load_contract(
        P1 / "P20_native_request.json",
        P1 / "P20_EXACT_FRAME_AND_PHYSICS_REPORT.json",
    )


def make_budget(contract, provenance, mode):
    meta = frame.frame_metadata(contract, provenance, mode)
    return {
        "schema": frame.BUDGET_SCHEMA,
        "decision": "APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
        "approved_physical_case": True,
        "approve_real_native_pilot": True,
        **meta,
        "w0_m21_source_commit": provenance["w0_m21_source_commit"],
        "w0_m21_source_bundle_sha256": provenance["source_bundle_sha256"],
        "w0_m21_source_files": provenance["source_files"],
        "length_ref": meta["normalization_L"],
        "density_ref": meta["normalization_R"],
        "max_normalized_jacobian_error": 1e-8,
    }


def make_packets(step=0.002, branch=FEATURE):
    c = np.zeros(10); c[0] = 1.0
    v = np.zeros(10); v[1] = 1.0
    J = np.eye(10)
    packet = {}
    for name, angle in (
        ("plus_h", step), ("minus_h", -step),
        ("plus_half", step / 2), ("minus_half", -step / 2),
    ):
        cp = np.cos(angle) * c + np.sin(angle) * v
        packet[name] = {
            "c_native": cp.tolist(),
            "r_design": (J @ cp).tolist(),
            "feature_branch_sha256": branch,
        }
    return c, J, v.reshape(10, 1), [packet]


def test_01_vendored_w0_m21_sources_match_commit_and_git_blob_pins():
    provenance = frame.source_provenance()
    assert provenance["w0_m21_source_commit"] == "cd72c04631a672408aaf576ab1b98747625f9468"
    assert provenance["runtime_import_from_w0_branch"] is False
    assert set(provenance["source_files"]) == {
        "teapot_moment_frame_m21.py", "moment_coordinates.py", "tangent_neighborhood.py"
    }
    assert all(len(row["sha256"]) == 64 for row in provenance["source_files"].values())
    assert all(len(row["git_blob_sha1"]) == 40 for row in provenance["source_files"].values())


def test_02_p20_frame_contract_is_loaded_from_actual_pinned_files(contract_and_provenance):
    contract, provenance = contract_and_provenance
    assert provenance["p20_request_sha256"] == frame.P20_REQUEST_SHA256
    assert provenance["p20_frame_report_sha256"] == frame.P20_FRAME_REPORT_SHA256
    assert contract.native_frame == frame.NATIVE_FRAME
    assert contract.native_length_ref == 1.0
    assert contract.native_density_ref == 1.0
    assert contract.si_length_ref == pytest.approx(0.06429, abs=1e-16)
    assert contract.si_density_ref == 1200.0
    assert contract.physical_parameters_approved is False


def test_03_native_mode_preserves_r_and_j_with_L1_R1(contract_and_provenance):
    contract, provenance = contract_and_provenance
    r = np.arange(10, dtype=float) / 7
    J = np.arange(100, dtype=float).reshape(10, 10) / 13
    view = frame.make_moment_view(r, J, contract, provenance, frame.NATIVE_FRAME)
    assert view["moment_coordinate_frame"] == frame.NATIVE_FRAME
    assert view["normalization_L"] == 1.0
    assert view["normalization_R"] == 1.0
    assert view["native_material_density"] == 1.0
    assert view["coordinate_transform_applied"] is False
    np.testing.assert_array_equal(view["r_design_in_frame"], r)
    np.testing.assert_array_equal(view["Jc_in_frame"], J)
    assert view["coefficient_coordinate_frame"] == "P20_NATIVE_COEFFICIENT_COORDINATES_UNCHANGED"
    assert view["c_and_tangent_basis_transformed"] is False


def test_04_si_mode_uses_conditional_SI_normalization(contract_and_provenance):
    contract, provenance = contract_and_provenance
    view = frame.make_moment_view(np.ones(10), np.eye(10), contract, provenance, frame.SI_FRAME)
    assert view["moment_coordinate_frame"] == frame.SI_FRAME
    assert view["normalization_L"] == pytest.approx(0.06429, abs=1e-16)
    assert view["normalization_R"] == 1200.0
    assert view["native_material_density"] == 1.0
    assert view["coordinate_transform_applied"] is True
    assert view["affine_transform_identity_sha256"] == provenance["affine_transform_identity_sha256"]


def test_05_si_view_pushes_all_ten_raw_moments_and_all_J_columns(contract_and_provenance):
    contract, provenance = contract_and_provenance
    r = np.arange(10, dtype=float) / 5
    J = np.arange(100, dtype=float).reshape(10, 10) / 11
    view = frame.make_moment_view(r, J, contract, provenance, frame.SI_FRAME)
    expected_r = frame.transform_raw10_native_to_si(r, contract)
    expected_J = frame.transform_jacobian_native_to_si(J, contract)
    np.testing.assert_array_equal(view["r_design_in_frame"], expected_r)
    np.testing.assert_array_equal(view["Jc_in_frame"], expected_J)
    assert not np.array_equal(view["Jc_in_frame"], J)


def test_06_native_rj_cannot_be_labelled_as_si(contract_and_provenance):
    contract, provenance = contract_and_provenance
    r, J = np.arange(10, dtype=float), np.eye(10)
    native = frame.make_moment_view(r, J, contract, provenance, frame.NATIVE_FRAME)
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="MOMENT_FRAME_VIEW_DOES_NOT_MATCH"):
        frame.validate_moment_view(native, r, J, contract, provenance, frame.SI_FRAME)


def test_07_si_rj_cannot_be_labelled_as_native(contract_and_provenance):
    contract, provenance = contract_and_provenance
    r, J = np.arange(10, dtype=float), np.eye(10)
    si = frame.make_moment_view(r, J, contract, provenance, frame.SI_FRAME)
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="MOMENT_FRAME_VIEW_DOES_NOT_MATCH"):
        frame.validate_moment_view(si, r, J, contract, provenance, frame.NATIVE_FRAME)


def test_08_missing_affine_provenance_is_rejected(contract_and_provenance):
    contract, provenance = contract_and_provenance
    view = frame.make_moment_view(np.ones(10), np.eye(10), contract, provenance, frame.SI_FRAME)
    del view["affine_transform_identity_sha256"]
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="MOMENT_FRAME_VIEW_DOES_NOT_MATCH"):
        frame.validate_moment_view(view, np.ones(10), np.eye(10),
                                   contract, provenance, frame.SI_FRAME)


def test_09_wrong_affine_translation_cannot_reuse_old_identity(contract_and_provenance):
    contract, provenance = contract_and_provenance
    bad = replace(contract, target_to_si_translation=(0.0, 0.0, 0.0))
    bad_provenance = dict(provenance)
    bad_provenance["frame_contract_sha256"] = frame.sha256_bytes(
        frame.canonical_bytes(bad.report()))
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="AFFINE_TRANSFORM_IDENTITY_CHANGED"):
        frame.frame_metadata(bad, bad_provenance, frame.SI_FRAME)


def test_10_wrong_density_ratio_cannot_reuse_old_identity(contract_and_provenance):
    contract, provenance = contract_and_provenance
    bad = replace(contract, native_to_si_density_ratio=1199.0)
    bad_provenance = dict(provenance)
    bad_provenance["frame_contract_sha256"] = frame.sha256_bytes(
        frame.canonical_bytes(bad.report()))
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="AFFINE_TRANSFORM_IDENTITY_CHANGED"):
        frame.frame_metadata(bad, bad_provenance, frame.SI_FRAME)


def test_11_jacobian_with_only_rows_transformed_is_rejected(contract_and_provenance):
    contract, provenance = contract_and_provenance
    r, J = np.arange(10, dtype=float), np.eye(10)
    view = frame.make_moment_view(r, J, contract, provenance, frame.SI_FRAME)
    view["Jc_in_frame"] = (np.asarray(view["Jc_in_frame"]) * 2.0).tolist()
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="MOMENT_FRAME_VIEW_DOES_NOT_MATCH"):
        frame.validate_moment_view(view, r, J, contract, provenance, frame.SI_FRAME)


def test_12_jacobian_with_only_columns_transformed_is_rejected(contract_and_provenance):
    contract, provenance = contract_and_provenance
    r, J = np.arange(10, dtype=float), np.eye(10)
    view = frame.make_moment_view(r, J, contract, provenance, frame.SI_FRAME)
    matrix = np.asarray(view["Jc_in_frame"])
    matrix[:, 0] *= 2.0
    view["Jc_in_frame"] = matrix.tolist()
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="MOMENT_FRAME_VIEW_DOES_NOT_MATCH"):
        frame.validate_moment_view(view, r, J, contract, provenance, frame.SI_FRAME)


def test_13_w0_and_w2_must_approve_identical_frame_binding(contract_and_provenance):
    contract, provenance = contract_and_provenance
    w0 = make_budget(contract, provenance, frame.NATIVE_FRAME)
    w2 = dict(w0)
    w2["schema"] = "W2_TEAPOT_P30_FEATURE_PILOT_AUTHORIZATION_V1"
    assert frame.validate_owner_teacher_frame(w0, w2, contract, provenance)["moment_coordinate_frame"] == frame.NATIVE_FRAME
    w2["moment_coordinate_frame"] = frame.SI_FRAME
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="W2_FRAME_BINDING_MISMATCH"):
        frame.validate_owner_teacher_frame(w0, w2, contract, provenance)


def test_14_native_and_si_richardson_audits_use_consistent_frames(contract_and_provenance):
    contract, provenance = contract_and_provenance
    c, J, basis, probes = make_packets()
    native = frame.audit_tangent_packets(
        budget_receipt=make_budget(contract, provenance, frame.NATIVE_FRAME),
        contract=contract, provenance=provenance, native_c=c, native_Jc=J,
        tangent_basis=basis, probes=probes, base_feature_branch_sha256=FEATURE,
        step_radians=0.002)
    si = frame.audit_tangent_packets(
        budget_receipt=make_budget(contract, provenance, frame.SI_FRAME),
        contract=contract, provenance=provenance, native_c=c, native_Jc=J,
        tangent_basis=basis, probes=probes, base_feature_branch_sha256=FEATURE,
        step_radians=0.002)
    assert native["numeric_diagnostic"]["status"] == "NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED"
    assert si["numeric_diagnostic"]["status"] == "NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED"
    assert native["coordinate_transform_applied"] is False
    assert si["coordinate_transform_applied"] is True
    assert native["smooth_neighborhood_certified"] is False
    assert si["Newton_accepted"] is False
    assert si["training_admissible"] is False


def test_15_si_audit_preserves_feature_branch_change_veto(contract_and_provenance):
    contract, provenance = contract_and_provenance
    c, J, basis, probes = make_packets(branch="b" * 64)
    budget = make_budget(contract, provenance, frame.SI_FRAME)
    result = frame.audit_tangent_packets(
        budget_receipt=budget, contract=contract, provenance=provenance,
        native_c=c, native_Jc=J, tangent_basis=basis, probes=probes,
        base_feature_branch_sha256=FEATURE, step_radians=0.002)
    assert result["numeric_diagnostic"]["status"] == "OBSERVED_BRANCH_CHANGE_DERIVATIVE_EXCLUDED"
    assert result["smooth_neighborhood_certified"] is False


def test_16_missing_or_wrong_frame_budget_is_rejected(contract_and_provenance):
    contract, provenance = contract_and_provenance
    c, J, basis, probes = make_packets()
    budget = make_budget(contract, provenance, frame.NATIVE_FRAME)
    budget["normalization_R"] = 1200.0
    with pytest.raises(frame.MomentFrameIntegrationRejected,
                       match="W0_BUDGET_FRAME_BINDING_MISMATCH:normalization_R"):
        frame.audit_tangent_packets(
            budget_receipt=budget, contract=contract, provenance=provenance,
            native_c=c, native_Jc=J, tangent_basis=basis, probes=probes,
            base_feature_branch_sha256=FEATURE, step_radians=0.002)


def test_17_audit_budget_cannot_promote_newton_or_training(contract_and_provenance):
    contract, provenance = contract_and_provenance
    c, J, basis, probes = make_packets()
    result = frame.audit_tangent_packets(
        budget_receipt=make_budget(contract, provenance, frame.NATIVE_FRAME),
        contract=contract, provenance=provenance, native_c=c, native_Jc=J,
        tangent_basis=basis, probes=probes, base_feature_branch_sha256=FEATURE,
        step_radians=0.002)
    assert result["numeric_diagnostic"]["status"] == "NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED"
    assert result["smooth_neighborhood_certified"] is False
    assert result["continuous_smooth_neighborhood_certified"] is False
    assert result["Newton_accepted"] is False
    assert result["training_admissible"] is False
