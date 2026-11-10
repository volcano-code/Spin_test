import tempfile
import unittest
from pathlib import Path

import torch

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_uqno_gate import _UQNO
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_uqno_gate_eval import (
    _evaluate_target,
)


class P25MarginalQueryGateEvaluationTests(unittest.TestCase):
    def _checkpoint(self, path, target):
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
                "calibration_query_upper_residual_q90": 0.5,
                "calibration_query_upper_residual_q95": 0.8,
                "feature_ood_standardized_max_q95": 5.5,
                "training_feature_q01": [-1.0]*5,
                "training_feature_q99": [1.0]*5,
            },
        }, path)

    def test_query_level_counts_and_geometry_diagnostic_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            checkpoint = Path(d) / "hardcut.pt"
            self._checkpoint(checkpoint, "hardcut")
            rows = []
            for i in range(16):
                rows.append({
                    "geometry_id": f"g{i}",
                    "family": ("box", "sphere", "ellipsoid")[i % 3],
                    "features": [0.0]*5,
                    "hardcut_error": 0.02,
                })
            result = _evaluate_target({"test_cases": rows}, checkpoint, "hardcut")
            item = result["1.0"]
            self.assertEqual(item["calibration_unit"], "marginal_query")
            self.assertEqual(item["query_count"], 16)
            self.assertEqual(item["geometry_count"], 16)
            self.assertEqual(item["accepted_query_count"], 16)
            self.assertEqual(item["fallback_query_count"], 0)
            self.assertEqual(item["geometry_any_fallback_fraction"], 0.0)


if __name__ == "__main__":
    unittest.main()
