import unittest

import torch
from torch import nn

from research.NeuralMoments.models.pcraft_ufno.p0_integration.neuraloperator_adapter import (
    GINOMomentOperator, UQNOAdapter,
)


class NeuralOperatorSmoke(unittest.TestCase):
    def test_gino_geometry_encoder_and_ten_moment_head(self):
        torch.manual_seed(17)
        model = GINOMomentOperator(latent_resolution=8, hidden_channels=8, fno_modes=2, fno_layers=1)
        geom = torch.rand((1, 48, 3))
        features = torch.rand((1, 48, 4))
        coeff = torch.randn((1, 10))
        result = model(geom, features, coeff)
        self.assertEqual(result.shape, (1, 10))
        self.assertTrue(bool(torch.isfinite(result).all()))
        jac = model.jacobian_diagnostic(geom, features, coeff)
        self.assertEqual(jac.shape, (1, 10, 10))
        self.assertTrue(bool(torch.isfinite(jac).all()))

    def test_uqno_wraps_moment_heads(self):
        class Head(nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = nn.Linear(13, 10)
            def forward(self, z, c):
                return self.linear(torch.cat((z, c), dim=-1))
        adapter = UQNOAdapter(Head(), Head())
        z = torch.rand((8, 3))
        c = torch.rand((8, 10))
        mean, scale = adapter(z, c)
        self.assertEqual(mean.shape, (8, 10))
        self.assertEqual(scale.shape, (8, 10))
        self.assertTrue(bool((scale > 0).all()))


if __name__ == "__main__":
    unittest.main()
