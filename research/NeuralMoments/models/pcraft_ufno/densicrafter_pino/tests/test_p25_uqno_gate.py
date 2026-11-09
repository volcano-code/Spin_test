import tempfile
import unittest
from pathlib import Path

import torch

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_uqno_gate import (
    CalibratedUQNO, _UQNO,
)


class P25UQNOGateContracts(unittest.TestCase):
    def _checkpoint(self, path, target="hardcut"):
        torch.manual_seed(7)
        model = _UQNO(5)
        schema = (
            "W6_P25_UQNO_HARDCUT_PREDICTOR_V1"
            if target == "hardcut"
            else "W6_P25_UQNO_ANALYTIC_P0_PREDICTOR_V1"
        )
        torch.save({
            "schema": schema,
            "state_dict": model.state_dict(),
            "input_mean": torch.zeros(5),
            "input_scale": torch.ones(5),
            "target_log_mean": torch.tensor(-3.0),
            "target_log_scale": torch.tensor(.5),
            "feature_dim": 5,
            "metrics": {
                "calibration_standardized_residual_q90": 1.64,
                "calibration_standardized_residual_q95": 1.96,
                "training_feature_q01": [-1.0]*5,
                "training_feature_q99": [1.0]*5,
            },
        }, path)

    def test_predict_interval_is_finite_and_ordered(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"uq.pt"
            self._checkpoint(p)
            uq = CalibratedUQNO(p, target="hardcut")
            out = uq.predict_interval(torch.zeros(5), confidence=.95)
            self.assertTrue(torch.isfinite(out["lower"]).all())
            self.assertTrue(torch.all(out["lower"] <= out["median"]))
            self.assertTrue(torch.all(out["median"] <= out["upper"]))

    def test_low_risk_keeps_pino_result_high_risk_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"uq.pt"
            self._checkpoint(p)
            uq = CalibratedUQNO(p, target="hardcut")
            calls = []
            exact = lambda: calls.append("called") or "hardcut"
            low = uq.predict_or_fallback(
                torch.zeros(5), "pino", exact,
                error_tolerance=100.0, confidence=.95,
            )
            self.assertFalse(low["fallback_used"])
            self.assertEqual(low["value"], "pino")
            high = uq.predict_or_fallback(
                torch.zeros(5), "pino", exact,
                error_tolerance=1e-12, confidence=.95,
            )
            self.assertTrue(high["fallback_used"])
            self.assertEqual(high["value"], "hardcut")
            self.assertEqual(calls, ["called"])

    def test_wrong_target_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"uq.pt"
            self._checkpoint(p, target="analytic_p0")
            with self.assertRaises(ValueError):
                CalibratedUQNO(p, target="hardcut")

    def test_nonfinite_features_trigger_exact_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"uq.pt"
            self._checkpoint(p)
            uq = CalibratedUQNO(p, target="hardcut")
            result = uq.predict_or_fallback(
                [float("nan")]*5, "pino", lambda: "hardcut",
                error_tolerance=.1,
            )
            self.assertTrue(result["fallback_used"])
            self.assertEqual(result["value"], "hardcut")

    def test_out_of_distribution_features_trigger_exact_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"uq.pt"
            self._checkpoint(p)
            uq = CalibratedUQNO(p, target="hardcut")
            result = uq.predict_or_fallback(
                [2.0]*5, "pino", lambda: "hardcut",
                error_tolerance=.1,
            )
            self.assertTrue(result["fallback_used"])
            self.assertEqual(result["decision"]["reason"], "FEATURE_OUTSIDE_TRAINING_01_99_ENVELOPE")


if __name__ == "__main__":
    unittest.main()
