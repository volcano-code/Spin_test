import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.p0_integration.selected_pino import SelectedPINOCandidates
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.bridge import DensiCrafterSpinPINOBridge
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p17_trained_pino import _surface_masks
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p24_quadrann_native128 import _QuadrANNPINOProxy


class P24QuadrANNNative128Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def _stack(self, grid=16):
        pino = SpinPINO(
            width=8, modes=4, n_layers=4, grid_size=grid,
            points_per_axis=8, hidden_dim=48, smoothing=.04,
            moment_parameterization="logistic_atom", temperature=.12,
            geometry_adapter="none",
        )
        selected = SelectedPINOCandidates(
            pino, quadrann=True, quadrann_condition_on_material=True,
            quadrann_max_points=128, quadrann_kernel_width=.45,
        )
        with torch.no_grad():
            selected.quadrann_gate.fill_(.03)
        for parameter in selected.parameters():
            parameter.requires_grad_(False)
        selected.train()
        selected.quadrann_adapter.model.eval()
        selected.pino.train()
        return pino, selected, _QuadrANNPINOProxy(pino, selected)

    def test_quadrann_proposal_maps_to_fixed_pino_nodes(self):
        pino, selected, proxy = self._stack()
        D, c, _, _, _ = sample_dataset(
            ("sphere",), per_family=1, seed=1701,
            grid_size=16, queries_per_geometry=1,
        )
        weights = proxy.encode_geometry(D)
        self.assertEqual(tuple(weights.shape), (1, pino.monomials.shape[0]))
        self.assertTrue(torch.isfinite(weights).all())
        self.assertTrue((weights >= 0).all())
        self.assertGreater(float(weights.sum()), 0.)

    def test_density_gradient_flows_through_frozen_quadrann_and_pino(self):
        pino, selected, proxy = self._stack()
        # A bottom-supported block is required by the DensiCrafter contact
        # term; centered analytic spheres do not necessarily touch the floor
        # at this tiny 16^3 contract-test resolution.
        D = torch.zeros(1, 4, 16, 16, 16)
        D[:, 0, 3:13, 3:13, 0:12] = 1.0
        D[:, 1, 3:13, 3:13, 0:12] = 1.0
        c = torch.zeros(1, 10)
        c[:, 3] = 1.0
        shell, design = _surface_masks(D[:, 1:2] > 0, wall_cells=1)
        model = DensiCrafterSpinPINOBridge(
            proxy, shell, design, gravity_axis=2, smoothing=False,
        )
        with torch.no_grad():
            model.density_logits.fill_(2.)
        out = model(c)
        loss = out["moments"].square().mean() + out["terms"]["mass"]
        loss.backward()
        grad = model.density_logits.grad
        self.assertIsNotNone(grad)
        self.assertTrue(torch.isfinite(grad).all())
        self.assertGreater(float(grad.abs().sum()), 0.)
        self.assertTrue(all(not p.requires_grad for p in pino.parameters()))
        self.assertTrue(all(not p.requires_grad for p in selected.quadrann_adapter.parameters()))


if __name__ == "__main__":
    unittest.main()
