"""Isolated M5 trust-region tests (not native Cherchi validation)."""
import importlib.util
import sys
from pathlib import Path
import unittest
import numpy as np

P = Path(__file__).resolve().parents[2] / "research/NeuralMoments/models/deeponet/m5_decision_gate.py"
spec = importlib.util.spec_from_file_location("w5_m5_decision_gate", P)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

class GateTests(unittest.TestCase):
    def setUp(self):
        self.c = np.array([0.,0.,0.,1.,0.,0.,0.,0.,0.,0.])
        self.r = np.ones(10)
        self.J = np.eye(10)
        self.target = np.zeros(10)
    def gate(self, **kw):
        return mod.propose_step(self.r,self.J,self.target,native_c=self.c,**kw)
    def test_no_identity(self):
        self.assertFalse(self.gate(derivative_status="VALID")["admitted"])
    def test_no_derivative(self):
        self.assertFalse(self.gate(identity_verified=True)["admitted"])
    def test_candidate_requires_native(self):
        p=self.gate(identity_verified=True,derivative_status="VALID")
        self.assertTrue(p["admitted"])
        self.assertTrue(p["requires_native_recheck"])
        self.assertAlmostEqual(np.linalg.norm(p["candidate_c"]),1.)
        self.assertGreater(np.dot(self.c,p["candidate_c"]),0)
        self.assertFalse(mod.verify_with_native(p,None,self.target,original_c=self.c)["accepted"])
    def test_valid_tangent(self):
        B=np.eye(10)[:,[0,1,2]]
        p=mod.propose_step(self.r,self.J@B,self.target,native_c=self.c,tangent_basis=B,identity_verified=True,derivative_status="VALID")
        self.assertTrue(p["admitted"])
        self.assertEqual(p["jacobian_type"],"TANGENT_10XK")
    def test_invalid_tangent(self):
        B=np.eye(10)[:,[0,3]]
        p=mod.propose_step(self.r,self.J@B,self.target,native_c=self.c,tangent_basis=B,identity_verified=True,derivative_status="VALID")
        self.assertEqual(p["reason"],"TANGENT_NOT_ORTHOGONAL_TO_NATIVE_C")
    def test_nonfinite(self):
        J=self.J.copy();J[0,0]=np.nan
        p=mod.propose_step(self.r,J,self.target,native_c=self.c,identity_verified=True,derivative_status="VALID")
        self.assertFalse(p["admitted"])
    def test_policy(self):
        p=self.gate(identity_verified=True,derivative_status="VALID",policy=mod.GatePolicy(damping=0))
        self.assertEqual(p["reason"],"INVALID_POLICY")
    def test_trust(self):
        p=self.gate(identity_verified=True,derivative_status="VALID",policy=mod.GatePolicy(trust_radius=.002))
        self.assertLessEqual(p["step_native_norm"],.003)
    def test_condition(self):
        p=self.gate(identity_verified=True,derivative_status="VALID",policy=mod.GatePolicy(max_condition=.5))
        self.assertEqual(p["reason"],"ILL_CONDITIONED_SYSTEM")
    def test_zero(self):
        p=mod.propose_step(self.target,self.J,self.target,native_c=self.c,identity_verified=True,derivative_status="VALID")
        self.assertEqual(p["reason"],"INSUFFICIENT_PREDICTED_REDUCTION")
    def test_mock_recheck(self):
        p=self.gate(identity_verified=True,derivative_status="VALID")
        ok=mod.verify_with_native(p,lambda c: np.asarray(c),self.target,original_c=self.c)
        self.assertTrue(ok["accepted"])
        self.assertTrue(ok["requires_external_commit"])
        def worse(c):
            return np.zeros(10) if np.allclose(c,self.c) else np.ones(10)
        bad=mod.verify_with_native(p,worse,self.target,original_c=self.c)
        self.assertEqual(bad["reason"],"NATIVE_OBJECTIVE_DID_NOT_IMPROVE")
    def test_bad_native_output(self):
        p=self.gate(identity_verified=True,derivative_status="VALID")
        bad=mod.verify_with_native(p,lambda c:[float("nan")]*10,self.target,original_c=self.c)
        self.assertEqual(bad["reason"],"NATIVE_RECHECK_FAILED")

if __name__=="__main__":
    unittest.main()
