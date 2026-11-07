"""P30-B diagnostic-only authority, isolation and append-only journal tests.

All tests here are pure Python/synthetic and MUST NEVER start Cherchi.
Actual W0/W2 permission is separately checked in the GitHub CI checkouts.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import p30_neighborhood_preflight as p30
import p30b_authority as authority
import p30b_native_sampler as native

NATIVE_C=[0.03640053031737869,-1.4100319353783204e-18,0.0,
          -0.2886365552481779,0.552377871982299,0.552377871982299,
          0.552377871982299,0.0,0.0,0.0]
FEATURE="b"*64
W0_DIGEST="a"*64

def plan():
    return p30.plan({
        "c":NATIVE_C,
        "Jc":[[float(i==j) for j in range(10)] for i in range(10)],
        "pins":{"context_sha256":"c"*64},
        "saved_geometry_hash":"d"*64,
        "saved_topology_hash":FEATURE,
    })

def owner(plan):
    return {
        "schema":"W0_TEAPOT_P30_DIAGNOSTIC_AUTHORIZATION_V1",
        "decision":"APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
        "source_w0_baseline":authority.EXPECTED_W0_FROZEN,
        "p20_request_sha256":authority.EXPECTED_REQUEST_SHA,
        "p27_manifest_sha256":p30.MANIFEST_SHA,
        "p30_plan_sha256":authority.P30_PRIVATE_PLAN_SHA,
        "native_c_sha256":p30.C_SHA,
        "approved_physical_case":True,
        "real_support_tip_and_shaft_reviewed":True,
        "approve_real_native_pilot":True,
        "pilot_directions":[0,1,2],
        "maximum_real_native_points":12,
        "step_radians":plan["step_radians"],
        "length_ref":1.0,
        "density_ref":1.0,
        "max_normalized_jacobian_error":1e-8,
        "newton_authorized":False,
        "training_authorized":False,
    }

def teacher(plan):
    return {
        "schema":"W2_TEAPOT_P30_FEATURE_PILOT_AUTHORIZATION_V1",
        "decision":"APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
        "p27_manifest_sha256":p30.MANIFEST_SHA,
        "p30_plan_sha256":authority.P30_PRIVATE_PLAN_SHA,
        "native_c_sha256":p30.C_SHA,
        "native_Jc_sha256":p30.J_SHA,
        "w0_approval_sha256":W0_DIGEST,
        "feature_branch_policy":"SOURCE_FEATURE_BRANCH_V2",
        "base_feature_branch_sha256":FEATURE,
        "independent_feature_branch_reviewed":True,
        "approve_real_native_pilot":True,
        "native_Jc_numerically_certified":False,
        "smooth_neighborhood_certified":False,
        "training_authorized":False,
        "Newton_authorized":False,
    }

def successful_sample_material(plan):
    coeff=plan["probes"][0]["native_c"]
    return {
        "quadric_coefficients":coeff,
        "variable_raw_moments":[float(i) for i in range(10)],
        "moment_jacobian":[[float(i==j) for j in range(10)] for i in range(10)],
        "evaluation_map_identity":"c"*64,
        "topology_hash":FEATURE,
        "geometry_hash":"e"*64,
        "derivative_defined":True,
    }

class P30BAuthorityTest(unittest.TestCase):
    def test_01_plan_reconstructed_from_registered_seed(self):
        p=plan()
        self.assertEqual(len(authority.validate_plan(p)["probes"]),36)
        self.assertEqual(p["probes"][0]["native_c_sha256"],
                         p30.canonical_hash(p["probes"][0]["native_c"]))

    def test_02_missing_W0_W2_is_explicit_block_not_native_authorization(self):
        p=plan()
        approvals={
            "w0":{"state":"MISSING","head":authority.EXPECTED_W0_FROZEN},
            "w2":{"state":"MISSING","head":authority.EXPECTED_W2_REVIEW_BASE}
        }
        result=authority.evaluate(p,approvals,b"synthetic",b"synthetic")
        self.assertEqual(result["status"],"BLOCKED_WAITING_INDEPENDENT_W0_W2_APPROVAL")
        self.assertFalse(result["real_native_pilot_authorized"])
        with self.assertRaisesRegex(authority.GateRejected,"DIAGNOSTIC_OWNER_APPROVALS_NOT_READY"):
            authority.make_lock(result)

    def test_03_synthetic_valid_W0_contract_does_not_grant_science(self):
        p=plan()
        w0=authority.validate_owner(owner(p),p,b"unused")
        self.assertEqual(w0["step_radians"],0.002)
        self.assertGreater(w0["max_normalized_jacobian_error"],0)

    def test_04_synthetic_valid_W2_feature_receipt_does_not_grant_training(self):
        p=plan()
        w2=authority.validate_teacher(teacher(p),p,W0_DIGEST)
        self.assertEqual(w2["base_feature_branch_sha256"],FEATURE)

    def test_05_wrong_owner_physical_tip_and_budget_rejected(self):
        p=plan()
        tests=[
            ("real_support_tip_and_shaft_reviewed",False,"W0_CASE_OR_TIP_APPROVAL_MISSING"),
            ("approved_physical_case",False,"W0_CASE_OR_TIP_APPROVAL_MISSING"),
            ("maximum_real_native_points",36,"W0_PILOT_SCOPE_CHANGED"),
            ("step_radians",0.004,"W0_PILOT_SCOPE_CHANGED"),
            ("length_ref",-1.,"W0_OWNER_NUMERIC_BUDGET_MISSING"),
            ("max_normalized_jacobian_error",float("nan"),"W0_OWNER_NUMERIC_BUDGET_MISSING"),
            ("newton_authorized",True,"W0_SCIENTIFIC_RELEASE_NOT_SUPPORTED"),
            ("training_authorized",True,"W0_SCIENTIFIC_RELEASE_NOT_SUPPORTED"),
        ]
        for key,value,error in tests:
            with self.subTest(key=key):
                record=owner(p);record[key]=value
                with self.assertRaisesRegex(authority.GateRejected,error):
                    authority.validate_owner(record,p,b"")

    def test_06_W2_cannot_promote_smooth_or_swap_Heart_label(self):
        p=plan()
        tests=[
            ("base_feature_branch_sha256","0"*64,"W2_BASE_FEATURE_INDEPENDENT_REVIEW_MISSING"),
            ("independent_feature_branch_reviewed",False,"W2_BASE_FEATURE_INDEPENDENT_REVIEW_MISSING"),
            ("w0_approval_sha256","d"*64,"W2_TEAPOT_APPROVAL_IDENTITY_MISMATCH"),
            ("native_Jc_numerically_certified",True,"W2_PREMATURE_DERIVATIVE_OR_NEWTON_RELEASE"),
            ("smooth_neighborhood_certified",True,"W2_PREMATURE_DERIVATIVE_OR_NEWTON_RELEASE"),
            ("Newton_authorized",True,"W2_PREMATURE_DERIVATIVE_OR_NEWTON_RELEASE"),
            ("training_authorized",True,"W2_PREMATURE_DERIVATIVE_OR_NEWTON_RELEASE"),
        ]
        for key,value,error in tests:
            with self.subTest(key=key):
                record=teacher(p);record[key]=value
                with self.assertRaisesRegex(authority.GateRejected,error):
                    authority.validate_teacher(record,p,W0_DIGEST)

    def test_07_duplicate_keys_and_nan_rejected(self):
        with self.assertRaisesRegex(authority.GateRejected,"DUPLICATE_JSON_KEY"):
            authority.strict_json(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(authority.GateRejected,"NONFINITE_JSON"):
            authority.strict_json(b'{"x":NaN}')

    def test_08_plan_mutation_fails_before_any_native_execution(self):
        for key,value in [
            ("status","NATIVE_COMPLETED"),("pilot_probe_count",36),
            ("completed_new_native_evaluations",12),("training_admissible",True)
        ]:
            p=plan();p[key]=value
            with self.subTest(key=key),self.assertRaises(authority.GateRejected):
                authority.validate_plan(p)
        p=plan()
        p["probes"][0]["native_c"][0]+=.01
        with self.assertRaisesRegex(authority.GateRejected,"PLAN_RECONSTRUCTION_OR_ORDER_MISMATCH"):
            authority.validate_plan(p)

    def test_09_registration_lock_refuses_missing_owner_receipts(self):
        with self.assertRaisesRegex(authority.GateRejected,"DIAGNOSTIC_OWNER_APPROVALS_NOT_READY"):
            authority.make_lock({"status":"BLOCKED_WAITING_INDEPENDENT_W0_W2_APPROVAL"})

    def test_10_pure_matching_mock_lock_is_only_external_review_candidate(self):
        readiness={"status":"DIAGNOSTIC_PILOT_APPROVALS_PRESENT_NOT_EXECUTED",
                   "real_native_pilot_authorized":True,"new_native_calls":0,
                   **authority.CLOSED}
        lock=authority.make_lock(readiness)
        self.assertEqual(lock["status"],"EXTERNAL_REVIEW_REQUIRED_BEFORE_NATIVE_PILOT")
        self.assertFalse(lock["native_calls_allowed_by_this_lock"])
        self.assertFalse(lock["scientific_admission"])

class P30BNativeJournalTest(unittest.TestCase):
    def test_11_sample_shapes_and_frozen_one_call_count(self):
        p=plan();m=successful_sample_material(p)
        out=native.validate_native_output(
            m,p["probes"][0]["native_c"],{"context_sha256":"c"*64},
            {"source":1,"boolean":1,"integration":1,"derivative":1},FEATURE)
        self.assertEqual(out["status"],"REAL_CHERCHI_TANGENT_POINT_OBSERVED_DIAGNOSTIC_ONLY")
        self.assertTrue(out["base_feature_branch_matches"])
        self.assertFalse(out["Newton_accepted"])
        self.assertFalse(out["training_admissible"])

    def test_12_branch_change_is_diagnostic_not_smooth_proof(self):
        p=plan();m=successful_sample_material(p);m["topology_hash"]="f"*64
        result=native.validate_native_output(
            m,p["probes"][0]["native_c"],{"context_sha256":"c"*64},
            {"source":1,"boolean":1,"integration":1,"derivative":1},FEATURE)
        self.assertFalse(result["base_feature_branch_matches"])
        self.assertFalse(result["native_derivative_neighborhood_certified"])

    def test_13_wrong_counts_context_or_J_shape_rejected(self):
        p=plan();m=successful_sample_material(p)
        for badcounts in (
            {"source":2,"boolean":1,"integration":1,"derivative":1},
            {"source":1,"boolean":0,"integration":1,"derivative":1},
            {"source":1,"boolean":1,"integration":0,"derivative":1},
        ):
            with self.assertRaisesRegex(native.SampleRejected,"ONE_FRESH_SOURCE"):
                native.validate_native_output(m,p["probes"][0]["native_c"],
                    {"context_sha256":"c"*64},badcounts,FEATURE)
        m["moment_jacobian"]=[[0.]*9 for _ in range(10)]
        with self.assertRaisesRegex(native.SampleRejected,"REAL_JC_NOT_FINITE_10X10"):
            native.validate_native_output(m,p["probes"][0]["native_c"],
                {"context_sha256":"c"*64},
                {"source":1,"boolean":1,"integration":1,"derivative":1},FEATURE)

    def test_14_resource_gate_honors_24_gib_and_zero_swap(self):
        good={"physical_memory_bytes":60*1024**3,"host_swap_bytes":0,
              "cgroup":{"memory.max":str(native.ADDRESS_BYTES),"memory.swap.max":"0"}}
        native.require_real_resources(good)
        for key,value,err in [
            ("physical_memory_bytes",10*1024**3,"PHYSICAL_RAM_BELOW_20_GIB"),
            ("host_swap_bytes",1,"HOST_SWAP_NOT_ZERO"),
        ]:
            altered=copy.deepcopy(good);altered[key]=value
            with self.assertRaisesRegex(native.SampleRejected,err):
                native.require_real_resources(altered)
        changed=copy.deepcopy(good);changed["cgroup"]["memory.max"]="8589934592"
        with self.assertRaisesRegex(native.SampleRejected,"REQUIRES_24_GIB"):
            native.require_real_resources(changed)

    def test_15_append_only_attempt_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/"point-000"
            p,records=native.next_attempt(parent)
            self.assertEqual(p.name,"attempt-000")
            self.assertEqual(records,[])
            p.mkdir(parents=True)
            p2,records=native.next_attempt(parent)
            self.assertEqual(p2.name,"attempt-001")
            self.assertEqual(len(records),1)
            (parent/"attempt-003").mkdir()
            with self.assertRaisesRegex(native.SampleRejected,"NONCANONICAL_OR_MISSING_ATTEMPT_SLOT"):
                native.next_attempt(parent)

    def test_16_failed_attempt_never_counts_as_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/"point-000"/"attempt-000";parent.mkdir(parents=True)
            native.new_json(parent/"ATTEMPT_RESULT.json",
                            {"status":"FAILED_OR_TIMED_OUT_PRESERVE_FOR_INDEPENDENT_REVIEW"})
            self.assertIsNone(native.existing_verified_success(
                parent.parent,0,plan(),"e"*64))

    def test_17_no_success_without_final_zero_exit_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/"point-000"/"attempt-000";parent.mkdir(parents=True)
            p=plan();sample=successful_sample_material(p)
            native.new_json(parent/"MATERIAL_SAME_CALL.json",sample)
            record={**native.validate_native_output(
                sample,p["probes"][0]["native_c"],{"context_sha256":"c"*64},
                {"source":1,"boolean":1,"derivative":1,"integration":1},FEATURE),
                "sample_index":0,"native_c_sha256":p["probes"][0]["native_c_sha256"],
                "registered_lock_sha256":"e"*64,
                "material_sha256":native.sha(parent/"MATERIAL_SAME_CALL.json"),
                "newton_evaluations":0}
            native.new_json(parent/"SAMPLE_RECEIPT.json",record)
            with self.assertRaisesRegex(native.SampleRejected,"SAMPLE_NOT_COMPLETED_SUCCESSFULLY"):
                native.existing_verified_success(parent.parent,0,p,"e"*64)

    def test_18_tampered_sample_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            parent=Path(d)/"point-000"/"attempt-000";parent.mkdir(parents=True)
            p=plan();mat=successful_sample_material(p)
            native.new_json(parent/"MATERIAL_SAME_CALL.json",mat)
            (parent/"stdout.log").write_bytes(b"")
            (parent/"stderr.log").write_bytes(b"")
            record={**native.validate_native_output(
                mat,p["probes"][0]["native_c"],{"context_sha256":"c"*64},
                {"source":1,"boolean":1,"derivative":1,"integration":1},FEATURE),
                "sample_index":0,"native_c_sha256":p["probes"][0]["native_c_sha256"],
                "registered_lock_sha256":"e"*64,
                "material_sha256":native.sha(parent/"MATERIAL_SAME_CALL.json"),
                "newton_evaluations":0}
            native.new_json(parent/"SAMPLE_RECEIPT.json",record)
            native.new_json(parent/"ATTEMPT_RESULT.json",
                            {"schema":"W4_P30B_ATTEMPT_RESULT_V1",
                             "status":"SUCCESS_DIAGNOSTIC_ONLY",
                             "worker_exit_code":0,"sample_index":0,
                             "material_sha256":record["material_sha256"],
                             "scientific_admission":False,
                             "stdout_sha256":native.sha(parent/"stdout.log"),
                             "stderr_sha256":native.sha(parent/"stderr.log")})
            self.assertIsNotNone(native.existing_verified_success(parent.parent,0,p,"e"*64))
            altered=json.loads((parent/"SAMPLE_RECEIPT.json").read_text())
            altered["training_admissible"]=True
            (parent/"SAMPLE_RECEIPT.json").write_text(json.dumps(altered))
            with self.assertRaisesRegex(native.SampleRejected,"PREVIOUS_SAMPLE_RECEIPT_TAMPERED"):
                native.existing_verified_success(parent.parent,0,p,"e"*64)

    def test_19_zero_native_calls_in_tests(self):
        self.assertEqual(len(native.MODULES),3)
        self.assertEqual(native.N_PILOT,12)
        self.assertEqual(native.POINT_MAX_SECONDS,900)
        self.assertEqual(native.P30_MAX_SECONDS,3600)
        self.assertFalse(native.CLOSED["training_admissible"])

if __name__=="__main__":
    unittest.main()
