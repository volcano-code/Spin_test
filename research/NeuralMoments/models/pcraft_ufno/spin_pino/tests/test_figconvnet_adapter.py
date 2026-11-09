import unittest

import torch
from torch import nn

from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset
from research.NeuralMoments.models.pcraft_ufno.spin_pino.figconvnet_adapter import FIGConvNetPointEncoder
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO


class DummyFIGConvUNet(nn.Module):
    def __init__(self, in_channels=4, out_channels=8):
        super().__init__()
        self.proj = nn.Linear(in_channels+3, out_channels)

    def forward(self, vertices, features=None):
        if features is None:
            raise AssertionError("Spin adapter must provide four geometry features")
        return self.proj(torch.cat((vertices, features), dim=-1)), None


class FIGConvNetAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def _geometry(self, count=2):
        D, c, _, _, _ = sample_dataset(
            ("sphere",), per_family=count, seed=20261109,
            grid_size=16, queries_per_geometry=1,
        )
        return D, c

    def test_adapter_returns_fixed_finite_features(self):
        D, _ = self._geometry()
        adapter = FIGConvNetPointEncoder(
            DummyFIGConvUNet(out_channels=8), num_points=128,
            figconv_out_channels=8, output_dim=12,
        )
        result = adapter(D)
        self.assertEqual(tuple(result.shape), (2, 12))
        self.assertTrue(torch.isfinite(result).all())

    def test_point_sampling_is_deterministic(self):
        D, _ = self._geometry()
        adapter = FIGConvNetPointEncoder(
            DummyFIGConvUNet(out_channels=8), num_points=128,
            figconv_out_channels=8, output_dim=12,
        )
        v1, f1 = adapter._sample_one(D[0])
        v2, f2 = adapter._sample_one(D[0])
        self.assertTrue(torch.equal(v1, v2))
        self.assertTrue(torch.equal(f1, f2))
        self.assertTrue(bool((v1 >= 0).all() and (v1 <= 1).all()))

    def test_custom_figconvnet_aabb_is_respected(self):
        D, _ = self._geometry()
        adapter = FIGConvNetPointEncoder(
            DummyFIGConvUNet(out_channels=8), num_points=128,
            figconv_out_channels=8, output_dim=12,
            aabb_min=(-1.0, -1.0, -1.0), aabb_max=(1.0, 1.0, 1.0),
        )
        vertices, _ = adapter._sample_one(D[0])
        self.assertTrue(bool((vertices >= -1).all() and (vertices <= 1).all()))

    def test_empty_geometry_is_rejected(self):
        empty = torch.zeros(1, 4, 16, 16, 16)
        adapter = FIGConvNetPointEncoder(
            DummyFIGConvUNet(out_channels=8), num_points=128,
            figconv_out_channels=8, output_dim=12,
        )
        with self.assertRaises(ValueError):
            adapter(empty)

    def test_adapter_attaches_without_changing_initial_pino_function(self):
        D, c = self._geometry()
        model = SpinPINO(
            width=8, modes=4, n_layers=4, grid_size=16,
            points_per_axis=4, hidden_dim=24,
            moment_parameterization="logistic_atom",
        )
        before = model(D, c)
        adapter = FIGConvNetPointEncoder(
            DummyFIGConvUNet(out_channels=8), num_points=128,
            figconv_out_channels=8, output_dim=12,
        )
        model.attach_geometry_plugin(adapter, input_dim=12)
        after = model(D, c)
        self.assertTrue(torch.equal(before, after))

    def test_adapter_and_pino_gate_receive_gradients(self):
        D, c = self._geometry()
        model = SpinPINO(
            width=8, modes=4, n_layers=4, grid_size=16,
            points_per_axis=4, hidden_dim=24,
            moment_parameterization="logistic_atom",
        )
        adapter = FIGConvNetPointEncoder(
            DummyFIGConvUNet(out_channels=8), num_points=128,
            figconv_out_channels=8, output_dim=12,
        )
        model.attach_geometry_plugin(adapter, input_dim=12)
        with torch.no_grad():
            model.geometry_plugin_gate.fill_(0.1)
        model(D, c).square().mean().backward()
        self.assertIsNotNone(model.geometry_plugin_gate.grad)
        self.assertTrue(any(p.grad is not None for p in adapter.parameters()))


if __name__ == "__main__":
    unittest.main()
