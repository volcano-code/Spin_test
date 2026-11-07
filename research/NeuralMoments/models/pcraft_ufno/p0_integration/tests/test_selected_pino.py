"""Genuine upstream GINO/QuadrANN/UQNO integration into PINO's weights."""
import math
import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.p0_integration.selected_pino import (
    SelectedPINOCandidates, GroupwiseConformalScreen,
)


def make_pino():
    torch.manual_seed(81)
    return SpinPINO(
        width=4, modes=2, n_layers=2, grid_size=8, points_per_axis=4,
        hidden_dim=32, moment_parameterization="logistic_atom",
        temperature=.12,
    )


def geometry():
    grid = torch.linspace(-1., 1., 8)
    xyz = torch.stack(torch.meshgrid(grid, grid, grid, indexing="ij"), -1)
    occ = (xyz.square().sum(-1) <= .65**2).float()
    return torch.stack((.8*occ, occ, torch.zeros_like(occ),
                        torch.zeros_like(occ)), dim=0).unsqueeze(0)


def coefficients():
    return torch.tensor([[.2, .0, -.1, .7, .1, .02, -.03, .05, .01, .0]])


class SelectedAdapterContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_pino_only_and_derivative_admission_fail_closed(self):
        base = make_pino().eval()
        model = SelectedPINOCandidates(base).eval()
        D, c = geometry(), coefficients()
        with torch.no_grad():
            r0, j0 = base(D, c, with_jacobian=True)
            out = model(D, c)
        self.assertTrue(torch.equal(out.result.moments, r0))
        self.assertTrue(torch.equal(out.diagnostic_model_jacobian, j0))
        self.assertIsNone(out.result.jacobian)
        self.assertIsNone(out.result.uncertainty)
        self.assertFalse(out.result.training_admitted)
        self.assertFalse(out.newton_derivative_admitted)

    def test_original_gino_quadrann_uqno_have_exact_zero_gate_parity(self):
        D, c = geometry(), coefficients()
        base = make_pino().eval()
        model = SelectedPINOCandidates(
            base, gino=True, quadrann=True, uqno=True,
            gino_hidden=8, max_gino_points=48,
        ).eval()
        with torch.no_grad():
            r0, j0 = base(D,c,with_jacobian=True)
            o = model(D,c)
        self.assertTrue(torch.equal(o.result.moments, r0))
        self.assertTrue(torch.equal(o.diagnostic_model_jacobian, j0))
        self.assertEqual(o.result.uncertainty.shape, (1,10))
        self.assertTrue(bool((o.result.uncertainty > 0).all()))
        self.assertFalse(o.newton_derivative_admitted)
        self.assertIsNone(o.result.jacobian)

    def test_enabled_gates_still_preserve_pino_physical_moment_structure(self):
        D,c = geometry(),coefficients()
        model=SelectedPINOCandidates(
            make_pino(),gino=True,quadrann=True,uqno=False,max_gino_points=48
        ).eval()
        with torch.no_grad():
            baseline=model(D,c)
            model.gino_gate.fill_(.8)
            model.quadrann_gate.fill_(.8)
            active=model(D,c)
            neg=model(D,-c)
        w=active.geometry_weights
        self.assertTrue(bool((w >= 0).all()))
        self.assertGreater(float((active.result.moments-baseline.result.moments).abs().max()), 1e-8)
        full = w @ model.pino.monomials
        self.assertTrue(torch.allclose(active.result.moments + neg.result.moments,full,atol=1e-5))
        self.assertLess(float((active.diagnostic_model_jacobian@c.unsqueeze(-1)).abs().max()),1e-5)
        self.assertIsNone(active.result.jacobian)


class GroupwiseCalibrationContracts(unittest.TestCase):
    def test_fit_groups_by_geometry_and_holdout_is_strict(self):
        gate=GroupwiseConformalScreen(alpha=.25)
        mean=torch.zeros(8,10)
        scale=torch.ones_like(mean)
        truth=torch.zeros_like(mean)
        truth[1,0]=2.
        ids=["A","A","B","B","C","C","D","D"]
        with self.assertRaisesRegex(ValueError,"disjoint"):
            gate.fit(mean,scale,truth,ids,training_geometry_ids=["A"])
        gate.fit(mean,scale,truth,ids,training_geometry_ids=["fit-1"])
        self.assertAlmostEqual(gate.qhat,2.0)
        out=SelectedPINOCandidates(make_pino())(geometry(), coefficients())
        blocked=gate.screen(out,"A",max_simultaneous_radius=1.)
        self.assertTrue(blocked.exact_required)
        self.assertEqual(blocked.reason,"GEOMETRY_NOT_HELD_OUT")

    def test_insufficient_calibration_and_native_newton_blocked(self):
        mean=torch.zeros(2,10)
        scale=torch.ones_like(mean)
        gate=GroupwiseConformalScreen(alpha=.1)
        gate.fit(mean,scale,mean,["A","B"])
        self.assertTrue(math.isinf(gate.qhat))
        proposal=SelectedPINOCandidates(make_pino())(geometry(),coefficients())
        self.assertTrue(gate.screen(proposal,"new",max_simultaneous_radius=.2).exact_required)
        self.assertEqual(gate.screen(proposal,"new",max_simultaneous_radius=.2,
                                     for_native_newton=True).reason,"NATIVE_NEWTON_UNCERTIFIED_J")

    def test_calibrated_uqno_can_issue_screening_only_not_newton(self):
        model=SelectedPINOCandidates(make_pino(),uqno=True).eval()
        D,c=geometry(),coefficients()
        with torch.no_grad():
            proposal=model(D,c)
        mean=torch.zeros(8,10);scale=torch.ones_like(mean)
        gate=GroupwiseConformalScreen(alpha=.25)
        gate.fit(mean,scale,mean,["A","A","B","B","C","C","D","D"])
        status=gate.screen(proposal,"test-unique",max_simultaneous_radius=100.)
        self.assertFalse(status.exact_required)
        self.assertEqual(status.reason,"SCREENING_ONLY_NOT_NEWTON")
        self.assertFalse(status.native_newton_admitted)
        bad=gate.screen(proposal,"test-unique",max_simultaneous_radius=1e-12)
        self.assertFalse(bad.exact_required)  # qhat=0; zero radius
        with self.assertRaises(ValueError):
            gate.fit(mean,-scale,mean,["A","A","B","B","C","C","D","D"])


if __name__=="__main__":
    unittest.main()
