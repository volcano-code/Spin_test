import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_uqno_baseline_eval import (
    _metrics, _ridge_fit_predict, _spearman,
)


class P25UQNOBaselineContracts(unittest.TestCase):
    def test_ridge_fit_uses_train_data_and_returns_finite_predictions(self):
        x_train = torch.arange(40, dtype=torch.float64).reshape(20, 2) / 10
        y_train = 0.3 + 0.7 * x_train[:, 0] - 0.2 * x_train[:, 1]
        x_test = torch.tensor([[0.2, 0.4], [1.1, 0.8]], dtype=torch.float64)
        pred = _ridge_fit_predict(x_train, y_train, x_test)
        self.assertEqual(tuple(pred.shape), (2,))
        self.assertTrue(torch.isfinite(pred).all())

    def test_spearman_detects_monotonic_risk_order(self):
        y = torch.tensor([0.1, 0.3, 0.2, 0.8], dtype=torch.float64)
        self.assertGreater(_spearman(y, y * 2.0), 0.99)

    def test_metrics_are_finite_and_include_risk_coverage(self):
        y = torch.tensor([0.1, 0.2, 0.3, 0.4], dtype=torch.float64)
        pred = torch.tensor([0.11, 0.19, 0.28, 0.42], dtype=torch.float64)
        risk = torch.tensor([0.12, 0.21, 0.31, 0.45], dtype=torch.float64)
        result = _metrics(y, pred, risk)
        self.assertIn("risk_coverage_aurc", result)
        self.assertTrue(all(torch.isfinite(torch.tensor(v)) for v in result.values()))


if __name__ == "__main__":
    unittest.main()
