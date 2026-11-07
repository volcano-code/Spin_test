"""Pure read-only fail-closed P29 W0/W2 admission-gate regressions."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import unittest

import p29_scientific_admission_gate as gate


def seed():
    p20 = {
        "schema": "W4_P20_TEAPOT_NATIVE_REQUEST_V1",
        "purpose": "PREREGISTERED_NONOPTIMIZED_ONE_POINT_MATERIAL_PARTITION_PROBE",
        "source_w0_commit": gate.W0_SHA,
        "units": {
            "physical_parameters_approved": False,
            "physical_density_kg_m3": 1200,
            "length_m_per_reference_binary64": 0.025,
        },
        "target": {
            "mode": "SPINNING_TOP", "axis": [0, 0, 1],
            "origin": [0, 0, 0], "support_points": [],
        },
        "geometry_policy": {"shaft_material": "S_ALREADY_INCLUDED_IN_F_NEVER_ADDED_AGAIN"},
        "admission": {
            "W0_owner_admitted": False, "W2_teacher_training_allowed": False,
            "Faster_optimization_executed": False,
            "MuJoCo_optimized_before_after_executed": False,
            "original_author_CAD": False,
            "physical_validation_passed": False,
        },
    }
    p28 = {
        "status": "ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT",
        "formal_status": "REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE",
        "formal_exit_code": 0,
        "formal_w0_commit": gate.W0_SHA,
        "formal_run_id": gate.P27_RUN,
        "registered_lock_sha256": gate.P27_LOCK_SHA,
        "formal_manifest_sha256": gate.P27_MANIFEST_SHA,
        "manifest_files_hash_verified": 37,
        "manifest_files_hash_failed": 0,
        "exact_D_minus_R_minus_C_zero": True,
        "exact_M_minus_F_minus_R_minus_C_zero": True,
        "same_call_100_jacobian_bytes_match": True,
        "independent_negative_controls": {"total": 2, "correctly_rejected": 2},
        "official_p21_replay_verify_executed": False,
        "independent_native_set_predicates_reexecuted": False,
        "independent_runtime_attestation": False,
        "scientific_admission": False,
        "W0_owner_admitted": False,
        "W2_teacher_training_allowed": False,
        "smooth_neighborhood_certified": False,
        "newton_terminal_certified": False,
        "Faster_optimization_executed": False,
    }
    w2 = {
        "schema": "w2-cherchi-teacher-v2-pre-w0",
        "status": "M23_DIAGNOSTIC_ONLY",
        "training_samples": 0,
        "native_teacher_runs": 1,
        "data_splits": {"train": [], "val": [], "test": [],
                        "excluded": [{"count": 81}]},
        "latest_native_diagnostic": {
            "J_D": None, "split": "excluded", "training_admitted": False,
        },
    }
    return p20, p28, w2


class P29Gate(unittest.TestCase):
    def setUp(self):
        self.p20, self.p28, self.w2 = seed()

    def check(self):
        return gate.inspect(self.p20, self.p28, self.w2,
                            observed_w0=gate.W0_SHA, observed_w2=gate.W2_SHA)

    def must_reject(self, message):
        with self.assertRaisesRegex(gate.AdmissionRejected, message):
            self.check()

    def test_known_good_formal_m6_never_promotes_training(self):
        out = self.check()
        self.assertEqual(out["status"], gate.STATUS)
        self.assertTrue(out["gates"]["P27_formal_native_M6_geometry_receipt"])
        self.assertFalse(out["gates"]["W0_owner_adoption_for_Teapot"])
        self.assertFalse(out["gates"]["W2_independent_Teapot_teacher_proof"])
        self.assertFalse(out["scientific_admission"])
        self.assertFalse(out["Newton_accepted"])
        self.assertFalse(out["training_admissible"])
        self.assertEqual(out["new_native_calls"], 0)

    def test_reject_unreviewed_W0_commit(self):
        with self.assertRaisesRegex(gate.AdmissionRejected, "UPSTREAM_COMMIT_NOT_PINNED"):
            gate.inspect(self.p20, self.p28, self.w2,
                         observed_w0="a" * 40, observed_w2=gate.W2_SHA)

    def test_reject_unreviewed_W2_commit(self):
        with self.assertRaisesRegex(gate.AdmissionRejected, "UPSTREAM_COMMIT_NOT_PINNED"):
            gate.inspect(self.p20, self.p28, self.w2,
                         observed_w0=gate.W0_SHA, observed_w2="b" * 40)

    def test_reject_forged_physical_owner_approval(self):
        self.p20["units"]["physical_parameters_approved"] = True
        self.must_reject("W0_PHYSICAL_APPROVAL_CHANGE")

    def test_reject_forged_w4_owner_or_training(self):
        for key in ("W0_owner_admitted", "W2_teacher_training_allowed",
                    "Faster_optimization_executed",
                    "MuJoCo_optimized_before_after_executed"):
            p20, p28, w2 = seed()
            self.p20, self.p28, self.w2 = p20, p28, w2
            self.p20["admission"][key] = True
            self.must_reject("FORGED_W4_SCIENTIFIC_ADMISSION")

    def test_reject_forged_author_CAD_and_physical(self):
        for key in ("original_author_CAD", "physical_validation_passed"):
            self.p20, self.p28, self.w2 = seed()
            self.p20["admission"][key] = True
            self.must_reject("FORGED_ORIGINAL_CAD_OR_PHYSICAL_PROOF")

    def test_reject_wrong_registered_case_and_physical_scaling(self):
        self.p20["purpose"] = "OPTIMIZED_THREE_OBJECTIVE_OUTPUT"
        self.must_reject("W4_REGISTERED_TEAPOT_CASE_CHANGED")
        self.p20, self.p28, self.w2 = seed()
        self.p20["units"]["length_m_per_reference_binary64"] = 0.047619047619
        self.must_reject("TEAPOT_PHYSICAL_PROPOSAL_IDENTITY_CHANGED")

    def test_reject_fake_tip_and_shaft(self):
        self.p20["target"]["support_points"] = [[0, 0, 0]]
        self.must_reject("TEAPOT_TARGET_OR_SUPPORT_CHANGED")
        self.p20, self.p28, self.w2 = seed()
        self.p20["geometry_policy"]["shaft_material"] = "S_COUNTED_AGAIN"
        self.must_reject("FIXED_SHAFT_MATERIAL_CONTRACT_CHANGED")

    def test_reject_drifted_formal_identity(self):
        for key, changed in (
            ("formal_exit_code", 1),
            ("formal_run_id", "unrelated-run"),
            ("registered_lock_sha256", "a" * 64),
            ("formal_manifest_sha256", "b" * 64),
            ("formal_w0_commit", "c" * 40),
            ("formal_status", "TEST_ONLY"),
        ):
            self.p20, self.p28, self.w2 = seed()
            self.p28[key] = changed
            self.must_reject("P27_P28_FORMAL_EVIDENCE_IDENTITY_CHANGED")

    def test_reject_jacobian_hash_or_arithmetic_drift(self):
        for key, changed in (
            ("manifest_files_hash_verified", 36),
            ("manifest_files_hash_failed", 1),
            ("exact_D_minus_R_minus_C_zero", False),
            ("exact_M_minus_F_minus_R_minus_C_zero", False),
            ("same_call_100_jacobian_bytes_match", False),
            ("independent_negative_controls", {"total": 2, "correctly_rejected": 1}),
        ):
            self.p20, self.p28, self.w2 = seed()
            self.p28[key] = changed
            self.must_reject("P28_ARITHMETIC_OR_BYTE_EVIDENCE_MISSING")

    def test_reject_self_promoted_p28_scientific_release(self):
        for key in (
            "official_p21_replay_verify_executed",
            "independent_native_set_predicates_reexecuted",
            "independent_runtime_attestation",
            "scientific_admission",
            "W0_owner_admitted", "W2_teacher_training_allowed",
            "smooth_neighborhood_certified",
            "newton_terminal_certified", "Faster_optimization_executed",
        ):
            self.p20, self.p28, self.w2 = seed()
            self.p28[key] = True
            self.must_reject("P28_REVIEW_SCOPE_OR_RELEASE_FLAGS_CHANGED")

    def test_reject_w2_training_export(self):
        self.w2["training_samples"] = 1
        self.must_reject("W2_TEACHER_MANIFEST_CHANGED")
        self.p20, self.p28, self.w2 = seed()
        self.w2["data_splits"]["train"] = [{"Teapot": True}]
        self.must_reject("W2_TRAINING_SPLIT_PROMOTION")

    def test_reject_heart_J_being_reused_as_teapot_J(self):
        self.w2["latest_native_diagnostic"]["J_D"] = [[0] * 10] * 10
        self.must_reject("W2_EXCLUDED_HEART_DIAGNOSTIC_CHANGED")
        self.p20, self.p28, self.w2 = seed()
        self.w2["latest_native_diagnostic"]["split"] = "train"
        self.must_reject("W2_EXCLUDED_HEART_DIAGNOSTIC_CHANGED")

    def test_reject_duplicate_json_keys(self):
        with self.assertRaisesRegex(gate.AdmissionRejected, "DUPLICATE_JSON_KEY"):
            gate.strict_json(b'{"status":"safe","status":"unsafe"}')

    def test_current_pinned_cross_window_snapshot(self):
        # Real check runs in CI against three independently fetched Git refs.
        roots = {part: os.environ.get("P29_" + part.upper() + "_ROOT")
                 for part in ("w4", "w0", "w2")}
        if not all(roots.values()):
            self.skipTest("requires pinned real W4/W0/W2 checkouts")
        report = gate.run(*(Path(roots[part]) for part in ("w4", "w0", "w2")))
        self.assertEqual(report["status"], gate.STATUS)
        self.assertEqual(report["w2_manifest"]["training_samples"], 0)
        self.assertEqual(report["reviewed_upstreams"]["w0_commit"], gate.W0_SHA)
        self.assertEqual(report["reviewed_upstreams"]["w2_commit"], gate.W2_SHA)
        self.assertFalse(report["scientific_admission"])
        self.assertFalse(report["gates"]["W0_physical_parameters_and_true_tip_approved"])


if __name__ == "__main__":
    unittest.main()
