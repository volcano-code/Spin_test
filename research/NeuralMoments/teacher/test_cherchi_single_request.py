"""Mock single-call integration tests; not evidence that native Cherchi was run."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from native_cherchi_teacher import verify
from cherchi_single_request import evaluate_one, sha256_file

class MockEvaluator:
    context_identity="frozen-context"
    fixed=np.array([2.0]+[0.0]*9)
    stage_seconds={"source":0.01}
    def __call__(self,q):
        variable=np.array([3.0]+[0.0]*9)
        return dict(variable_raw_moments=variable,raw_moments=variable+self.fixed,
                    moment_jacobian=np.zeros((10,10)),derivative_defined=True,
                    geometry_hash="g",topology_hash="t",evaluation_map_identity=self.context_identity,
                    boolean_backend_identity="mock",derivative_identity="mock")

class TestSingleRequest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model=Path(self.tmp.name)/"model.obj"
        self.native=Path(self.tmp.name)/"native.so"
        self.model.write_bytes(b"closed-model-placeholder")
        self.native.write_bytes(b"test-module-placeholder")
    def invoke(self,evaluator):
        return evaluate_one(evaluator,[0]*10,model_path=self.model,native_module_path=self.native,
            geometry={"kind":"mock_only"},density=1,frame={"name":"physical"})
    def check(self,record):
        return verify(record,expected_q=[0]*10,expected_model_sha256=sha256_file(self.model),
                      expected_native_module_sha256=sha256_file(self.native))
    def test_success_does_not_grant_derivative(self):
        p=self.check(self.invoke(MockEvaluator()))
        self.assertEqual(p["r_D"][0],3)
        self.assertEqual(p["r_F"][0],2)
        self.assertIsNone(p["J_D"])
        self.assertEqual(p["split"],"excluded")
        self.assertEqual(p["derivative_status"],"UNKNOWN")
        self.assertFalse(p["exact_proof"]["native_cherchi"])
    def test_numpy_moment_rows_and_mock_provenance(self):
        record=self.invoke(MockEvaluator())
        p=self.check(record)
        self.assertEqual(p["r_D"],[3.0]+[0.0]*9)
        self.assertFalse(p["exact_proof"]["native_cherchi"])
    def test_numpy_nan_rejected_and_recorded(self):
        class Nonfinite(MockEvaluator):
            def __call__(self,q):
                packet=super().__call__(q)
                packet["variable_raw_moments"][0]=float("nan")
                return packet
        p=self.check(self.invoke(Nonfinite()))
        self.assertEqual(p["derivative_status"],"INVALID")
        self.assertIn("NONFINITE_COMPONENT",p["failure_reason"])
    def test_mock_cannot_forge_derivative_contract(self):
        record=evaluate_one(MockEvaluator(),[0]*10,model_path=self.model,
            native_module_path=self.native,geometry={"kind":"mock_only"},
            density=1,frame={"name":"physical"},
            derivative_contract={"schema":"MomentContractV1",
                "contract_sha256":"c"*64,"verified_neighborhood":True},
            split="train")
        p=self.check(record)
        self.assertEqual(p["split"],"excluded")
        self.assertEqual(p["derivative_status"],"INVALID")
        self.assertIsNone(p["J_D"])
        self.assertIn("MOCK_OR_UNAUTHENTICATED",p["failure_reason"])

    def test_failure_still_sealed(self):
        class Broken(MockEvaluator):
            def __call__(self,q): raise RuntimeError("native failed")
        p=self.check(self.invoke(Broken()))
        self.assertEqual(p["topology_status"],"FAILED")
        self.assertIn("native failed",p["failure_reason"])
        self.assertIsNone(p["r_D"])
    def test_double_count_rejected(self):
        class Bad(MockEvaluator):
            def __call__(self,q):
                packet=super().__call__(q)
                packet["raw_moments"]=packet["variable_raw_moments"]
                return packet
        p=self.check(self.invoke(Bad()))
        self.assertEqual(p["derivative_status"],"INVALID")
        self.assertIn("DOUBLE_COUNT",p["failure_reason"])

if __name__=="__main__": unittest.main()
