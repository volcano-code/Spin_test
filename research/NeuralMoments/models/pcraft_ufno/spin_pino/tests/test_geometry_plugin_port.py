import copy
import unittest

import torch
from torch import nn

from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO


class DummyGeometryPlugin(nn.Module):
    def __init__(self, output_dim=12):
        super().__init__()
        self.proj = nn.Linear(4, output_dim)

    def forward(self, canonical_geometry):
        pooled = canonical_geometry.mean(dim=(2, 3, 4))
        return self.proj(pooled)


class BadShapePlugin(nn.Module):
    def forward(self, canonical_geometry):
        return canonical_geometry.mean(dim=(2, 3, 4))


class GeometryPluginPortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def _model(self):
        return SpinPINO(
            width=8, modes=4, n_layers=4, grid_size=16,
            points_per_axis=4, hidden_dim=24,
            moment_parameterization="logistic_atom",
            geometry_adapter="none",
        )

    def _inputs(self):
        D, c, _, _, _ = sample_dataset(
            ("sphere",), per_family=2, seed=20261109,
            grid_size=16, queries_per_geometry=1,
        )
        return D, c

    def test_zero_gate_preserves_pino_output_exactly(self):
        model = self._model()
        D, c = self._inputs()
        before = model(D, c)
        model.attach_geometry_plugin(DummyGeometryPlugin(12), input_dim=12)
        after = model(D, c)
        self.assertTrue(torch.equal(before, after))
        self.assertEqual(float(model.geometry_plugin_gate.detach()), 0.0)

    def test_gate_and_plugin_receive_gradients_after_opening(self):
        model = self._model()
        D, c = self._inputs()
        plugin = DummyGeometryPlugin(12)
        model.attach_geometry_plugin(plugin, input_dim=12)
        with torch.no_grad():
            model.geometry_plugin_gate.fill_(0.1)
        loss = model(D, c).square().mean()
        loss.backward()
        self.assertIsNotNone(model.geometry_plugin_gate.grad)
        self.assertGreater(float(model.geometry_plugin_gate.grad.abs()), 0.0)
        self.assertTrue(all(p.grad is not None for p in plugin.parameters()))

    def test_invalid_plugin_output_shape_is_rejected(self):
        model = self._model()
        D, c = self._inputs()
        model.attach_geometry_plugin(BadShapePlugin(), input_dim=12)
        with self.assertRaises(ValueError):
            model(D, c)

    def test_only_one_external_geometry_plugin_can_be_attached(self):
        model = self._model()
        model.attach_geometry_plugin(DummyGeometryPlugin(12), input_dim=12)
        with self.assertRaises(RuntimeError):
            model.attach_geometry_plugin(DummyGeometryPlugin(12), input_dim=12)


if __name__ == "__main__":
    unittest.main()
