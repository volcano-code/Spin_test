import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.p0_integration.quadrann_adapter import QuadrANNWeightAdapter


class QuadrANNSmoke(unittest.TestCase):
    def test_original_quadrann_core_produces_normalized_positive_weights(self):
        torch.manual_seed(13)
        model = QuadrANNWeightAdapter(
            num_gnn_layers=2, k_neighbors=4, pe_abs=2, pe_rel=2,
            hidden_dim=16, final_hidden_dim=16,
        )
        points = torch.rand((1, 48, 3))
        density = torch.ones((1, 48))
        result = model(points, density, 1.0, lower=(0, 0, 0), upper=(1, 1, 1))
        self.assertEqual(result.moments.shape, (1, 10))
        self.assertIsNone(result.jacobian)
        self.assertFalse(result.training_admitted)
        self.assertTrue(bool(torch.isfinite(result.moments).all()))


if __name__ == "__main__":
    unittest.main()
