"""M6 exact new-source tests; numerical truth is analytic P0, NEVER Cherchi."""
import copy
import math
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.NeuralMoments.models.deeponet.m6_analytic_rollout import (
    AnalyticCapOracle, ReplayPolicy, check_w2_manifest, guarded_analytic_step)
from research.NeuralMoments.models.deeponet.native_p0 import (
    cap_jacobian_native, cap_moments, dh_native_c, native_vertical_c)


class SafeAnalyticRolloutTests(unittest.TestCase):
    def setUp(self):
        self.R = 1.2
        self.density = 1.3
        self.h = 0.25
        self.target_h = 0.1
        self.true = cap_moments(self.R, self.h, density=self.density)
        self.J = cap_jacobian_native(self.R, self.h, density=self.density)
        self.target = cap_moments(self.R, self.target_h, density=self.density)

    def run_step(self, **overrides):
        args = dict(radius=self.R, density=self.density, current_h=self.h,
                    target_r=self.target, predicted_r=self.true,
                    predicted_Jc=self.J)
        args.update(overrides)
        return guarded_analytic_step(**args)

    def test_true_derivative_accepts_improving_step_without_material_claim(self):
        out = self.run_step()
        self.assertTrue(out["accepted"], out)
        self.assertLess(out["loss_after"], out["loss_before"])
        self.assertEqual(out["reason"], "ANALYTIC_P0_DECREASE_ONLY")
        self.assertEqual(out["truth_source"], "ANALYTIC_P0_ONLY")
        self.assertEqual(out["native_cherchi_calls"], 0)
        self.assertFalse(out["teacher_training_admissible"])
        self.assertTrue(out["requires_external_commit"])
        self.assertGreaterEqual(out["truth_calls"], 2)
        self.assertLessEqual(out["truth_calls"], 4)
        self.assertEqual(len(out["geometry_spec_sha256"]), 64)
        self.assertAlmostEqual(np.linalg.norm(out["next_c"]), 1, places=12)
        self.assertGreater(np.dot(out["current_c"], out["next_c"]), 0)

    def test_reversed_jacobian_never_commits_true_loss_increase(self):
        out = self.run_step(predicted_Jc=-self.J)
        self.assertFalse(out["accepted"])
        self.assertEqual(out["next_c"], out["current_c"])
        self.assertEqual(out["reason"], "NO_INDEPENDENT_TRUE_DECREASE_FALLBACK")
        self.assertAlmostEqual(out["loss_before"], out["loss_after"])
        self.assertLessEqual(out["truth_calls"], 4)

    def test_no_model_gradient_is_no_move(self):
        out = self.run_step(predicted_Jc=np.zeros((10, 10)))
        self.assertFalse(out["accepted"])
        self.assertIn("SURROGATE_REJECTED", out["reason"])
        self.assertEqual(out["truth_calls"], 1)
        self.assertEqual(out["current_c"], out["next_c"])

    def test_input_nan_and_shape_fail_closed(self):
        for bad in (np.full(10, float("nan")), np.ones(9), [[1]]):
            with self.subTest(bad=str(bad)[:24]):
                with self.assertRaises(ValueError):
                    self.run_step(predicted_r=bad)
        with self.assertRaises(ValueError):
            self.run_step(predicted_Jc=np.zeros((10, 9)))
        with self.assertRaises(ValueError):
            self.run_step(target_r=np.zeros(11))

    def test_query_budget_cannot_be_bypassed(self):
        with self.assertRaisesRegex(ValueError, "INVALID_QUERY_BUDGET"):
            self.run_step(policy=ReplayPolicy(max_truth_calls=1))
        with self.assertRaisesRegex(ValueError, "INVALID_QUERY_BUDGET"):
            self.run_step(policy=ReplayPolicy(max_truth_calls=2, max_backtracks=2))
        out=self.run_step(policy=ReplayPolicy(max_truth_calls=2,max_backtracks=0))
        self.assertLessEqual(out["truth_calls"],2)

    def test_policy_rejects_negative_nonfinite_and_boolean_budgets(self):
        for policy in (ReplayPolicy(max_truth_calls=True),
                       ReplayPolicy(max_backtracks=-1),
                       ReplayPolicy(shrink=1.2),
                       ReplayPolicy(shrink=float("nan")),
                       ReplayPolicy(trust_radius=0),
                       ReplayPolicy(min_true_drop=-1)):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                self.run_step(policy=policy)

    def test_stress_density_preserves_units_and_true_progress(self):
        for rho in (0.5, 1.0, 20.0):
            with self.subTest(rho=rho):
                out = self.run_step(density=rho,
                    predicted_r=cap_moments(self.R,self.h,density=rho),
                    predicted_Jc=cap_jacobian_native(self.R,self.h,density=rho),
                    target_r=cap_moments(self.R,self.target_h,density=rho))
                self.assertTrue(out["accepted"])
                self.assertLess(out["loss_after"],out["loss_before"])

    def test_native_polynomial_is_not_an_arbitrary_model(self):
        oracle=AnalyticCapOracle(self.R,self.density)
        c=native_vertical_c(self.h)
        self.assertTrue(np.allclose(oracle.moments(c), self.true))
        self.assertEqual(oracle.calls,1)
        bad=c.copy();bad[7]=0.02;bad/=np.linalg.norm(bad)
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_NONPLANAR"):
            oracle.moments(bad)
        self.assertEqual(oracle.calls,2)  # failed queries are billed
        with self.assertRaises(ValueError):oracle.moments(-c)
        with self.assertRaises(ValueError):oracle.moments(np.full(10,np.nan))
        self.assertEqual(oracle.calls,4)

    def test_analytic_identity_changes_with_density_and_radius(self):
        a=AnalyticCapOracle(self.R,self.density)
        self.assertEqual(a.spec_sha256,AnalyticCapOracle(self.R,self.density).spec_sha256)
        self.assertNotEqual(a.spec_sha256,AnalyticCapOracle(self.R*1.01,self.density).spec_sha256)
        self.assertNotEqual(a.spec_sha256,AnalyticCapOracle(self.R,self.density*1.01).spec_sha256)

    def test_w0_native_jacobian_rule_only_for_known_smooth_cap(self):
        c=native_vertical_c(self.h)
        b=np.array([1.]*7+[2.]*3)
        H=self.J/b[None,:]
        np.testing.assert_allclose(H,H.T,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(self.J@c,np.zeros(10),atol=1e-12)
        eps=1e-6
        finite=(cap_moments(self.R,self.h+eps,density=self.density)-
                cap_moments(self.R,self.h-eps,density=self.density))/(2*eps)
        np.testing.assert_allclose(self.J@dh_native_c(self.h),finite,rtol=2e-7,atol=2e-8)

    def test_invalid_sphere_and_outside_cut(self):
        with self.assertRaises(ValueError):AnalyticCapOracle(0,1)
        with self.assertRaises(ValueError):AnalyticCapOracle(1,-1)
        with self.assertRaisesRegex(ValueError,"CUT_OUTSIDE"):
            self.run_step(current_h=1.21)
        with self.assertRaisesRegex(ValueError,"CUT_OUTSIDE"):
            AnalyticCapOracle(1,1).moments(native_vertical_c(1.1))

    def test_malformed_w2_manifest_is_not_admitted(self):
        valid=dict(schema="w2-cherchi-teacher-v1-pre-w0",status="ADAPTER_SMOKE_ONLY",
                   native_teacher_runs=0,training_samples=0)
        report=check_w2_manifest(valid)
        self.assertFalse(report["teacher_training_admissible"])
        for key in ("native_teacher_runs","training_samples"):
            bogus=copy.deepcopy(valid);bogus[key]=True
            with self.assertRaisesRegex(ValueError,"INVALID_W2"):
                check_w2_manifest(bogus)
        with self.assertRaises(ValueError):
            check_w2_manifest(dict(valid,schema="unknown"))

    def test_self_reported_native_counts_cannot_promote_teacher(self):
        fake=dict(schema="w2-cherchi-teacher-v1-pre-w0",status="NATIVE_VERIFIED",
                  native_teacher_runs=999,training_samples=999,
                  native_cherchi=True,proof="I promise")
        out=check_w2_manifest(fake)
        self.assertEqual(out["declared_native_runs"],999)
        self.assertFalse(out["teacher_training_admissible"])

    def test_single_truth_call_without_candidate(self):
        out=self.run_step(predicted_r=self.target)
        self.assertFalse(out["accepted"])
        self.assertEqual(out["truth_calls"],1)
        self.assertEqual(out["next_c"],out["current_c"])

if __name__=="__main__":
    unittest.main()
