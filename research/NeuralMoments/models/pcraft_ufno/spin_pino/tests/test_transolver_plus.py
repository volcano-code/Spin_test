import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.spin_pino.transolver_plus_adapter import (
    PhysicsAttention1DEidetic,
    TransolverPlusGeometryAdapter,
)


class TransolverPlusAdapterTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(20261106)
        self.geometry = torch.rand((2, 4, 8, 8, 8), dtype=torch.float32)

    def _model(self, adapter):
        return SpinPINO(
            width=4, modes=2, n_layers=2, grid_size=8,
            points_per_axis=3, hidden_dim=24, smoothing=0.02,
            moment_parameterization="logistic_atom",
            geometry_adapter=adapter,
            transolver_hidden_dim=32, transolver_heads=4,
            transolver_slices=8, transolver_layers=1,
        )

    def test_eidetic_attention_cpu_forward(self):
        layer = PhysicsAttention1DEidetic(32, heads=4, dim_head=8, slice_num=8)
        y = layer(torch.rand((2, 64, 32)))
        self.assertEqual(y.shape, (2, 64, 32))
        self.assertTrue(bool(torch.isfinite(y).all()))

    def test_adapter_returns_pino_latent_dimension(self):
        adapter = TransolverPlusGeometryAdapter(
            pino_feature_dim=24, hidden_dim=32, heads=4, slice_num=8, n_layers=1
        )
        y = adapter(self.geometry)
        self.assertEqual(y.shape, (2, 24))
        self.assertTrue(bool(torch.isfinite(y).all()))

    def test_zero_gate_initialization_is_exactly_pino_only(self):
        base = self._model("none")
        plugin = self._model("transolver_plus")
        plugin.load_state_dict(base.state_dict(), strict=False)
        base.eval()
        plugin.eval()
        with torch.no_grad():
            w_base = base.encode_geometry(self.geometry)
            w_plugin = plugin.encode_geometry(self.geometry)
        self.assertTrue(torch.equal(w_base, w_plugin))
        self.assertEqual(float(plugin.transolver_plus_gate.detach()), 0.0)
        self.assertEqual(type(plugin.encoder).__name__, "PINOFeatureEncoder")

    def test_plugin_gate_and_adapter_receive_gradients(self):
        model = self._model("transolver_plus")
        weights = model.encode_geometry(self.geometry)
        self.assertEqual(weights.shape, (2, 27))
        self.assertTrue(bool(torch.isfinite(weights).all()))
        weights.sum().backward()
        self.assertIsNotNone(model.transolver_plus_gate.grad)
        self.assertIsNotNone(model.transolver_plus_adapter.input_projection[0].weight.grad)

    def test_plugin_disabled_preserves_default_model(self):
        model = self._model("none")
        self.assertIsNone(model.transolver_plus_adapter)
        self.assertIsNone(model.transolver_plus_gate)


if __name__ == "__main__":
    unittest.main()
