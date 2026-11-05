"""Synthetic M22 receipt tests; no native/evidence release."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from independent_reference import integrate_exact_boundary, compare_predeclared_budget
from m22_audit_heart_label import audit
from m16_native_acceptance import file_hash
from native_cherchi_teacher import digest, seal


class TestRawReplay(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.c = [1.0] + [0.0]*9
        self.budget = [1e-10]*10
        self.mat = {"variable_rational_vertices": [[0,0,0],[1,0,0],[0,1,0],[0,0,1]],
                    "variable_faces": [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]}
        exact, ref = integrate_exact_boundary(self.mat["variable_rational_vertices"],
                                               self.mat["variable_faces"], 1.0)
        measured = list(map(float, exact))
        ref["comparison"] = compare_predeclared_budget(measured, exact, self.budget)
        self.reason = "W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED"
        proof = {"kind":"cherchi_same_call_discrete_map", "native_cherchi":True,
                 "independent_ten_moment_audit":ref, "same_call_attachment":{
                    "native_c_sha256":digest(self.c), "schema":"w2-same-call-material-binding-v1",
                    "serialized_material_sha256":digest(self.mat)}}
        self.label = seal(model_sha256="a"*64, native_module_sha256="b"*64, geometry={}, density=1,
                          frame={}, q=self.c, r_d=measured, r_f=measured, j_d=None,
                          topology_status="OBSERVED_DISCRETE_MAP", derivative_status="UNKNOWN",
                          derivative_contract=None, stage_seconds={}, peak_rss_bytes=1,
                          exact_proof=proof, split="excluded", failure_reason=self.reason)
        self.spec = self.put("spec", {"native_c":self.c, "expected_model_sha256":"a"*64,
                              "expected_native_module_sha256":"b"*64, "frame":{}, "request":{"material_density":1.0},
                              "reference_absolute_tolerances":self.budget})
        self.receipt = {"spec_sha256":file_hash(self.spec), "r_D":measured, "r_F":measured,
                        "native_child_exit_reason":self.reason, "pilot_status":"diagnostic",
                        "independent_comparison":{"maximum_absolute_error":0, "within_tolerance":True}}

    def put(self, name, value):
        path = self.root/name
        path.write_text(json.dumps(value))
        return path

    def replay(self, *, material=None, bad_hash=False):
        label = self.put("label", self.label)
        result = self.put("result", {"status":"diagnostic","label_sha256":"a"*64 if bad_hash else file_hash(label)})
        return audit(self.spec, label, result, self.receipt, self.put("mat",material) if material else None)

    def test_label_only_and_boundary_replay(self):
        self.assertFalse(self.replay()["material_reintegrated"])
        result = self.replay(material=self.mat)
        self.assertTrue(result["material_reintegrated"])
        self.assertFalse(result["training_admitted"])

    def test_changed_raw_bytes(self):
        with self.assertRaisesRegex(ValueError,"RAW_LABEL_HASH"): self.replay(bad_hash=True)

    def test_different_material(self):
        with self.assertRaisesRegex(ValueError,"MATERIAL_HASH"):
            self.replay(material=dict(self.mat,extra_metadata=1))

    def test_resealed_wrong_fraction(self):
        p=self.label["payload"]
        p["exact_proof"]["independent_ten_moment_audit"]["reference_raw_moments_exact"][0]="10/1"
        self.label["payload_sha256"]=digest(p)
        with self.assertRaisesRegex(ValueError,"STORED_COMPARISON"): self.replay()

    def test_transcript_is_not_a_raw_label(self):
        self.label=self.receipt
        with self.assertRaisesRegex(ValueError,"INVALID_ENVELOPE"): self.replay()

    def test_reject_changed_spec(self):
        self.spec.write_text(self.spec.read_text()+"\n")
        with self.assertRaisesRegex(ValueError,"SPEC_HASH"): self.replay()

    def test_block_promotion(self):
        p=self.label["payload"];p["split"]="train";self.label["payload_sha256"]=digest(p)
        with self.assertRaisesRegex(ValueError,"EXCLUDED_DIAGNOSTIC"): self.replay()
