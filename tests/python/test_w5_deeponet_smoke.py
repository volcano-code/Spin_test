"""Standalone W5 tests (no CAD, no native compiler, no external teacher)."""

from __future__ import annotations

import math
import unittest

import torch

from research.NeuralMoments.models.deeponet import DeepONetMoment
from research.NeuralMoments.models.deeponet.analytic import (
    FAMILIES, analytic_labels, analytic_moment_data, make_geometry,
    sample_families, validate_geometry,
)
from research.NeuralMoments.models.deeponet.adapt import (
    SUPPORTED_QUERY_COUNTS, fit_residual_adapter,
)
from research.NeuralMoments.models.deeponet.smoke import run
from research.NeuralMoments.models.geometry_mlp import GeometryMLPMoment


class W5AnalyticOracleTests(unittest.TestCase):
    def test_box_mass_and_shifted_second_moments(self) -> None:
        d = make_geometry("box", (0.2, -0.3, 0.4), (0.5, 0.6, 0.7))
        b, g = analytic_moment_data(d)
        volume = 8 * 0.5 * 0.6 * 0.7
        self.assertAlmostEqual(b[0].item(), volume, places=12)
        self.assertAlmostEqual(b[1].item(), volume * 0.2, places=12)
        self.assertAlmostEqual(b[4].item(), volume * (0.2**2 + 0.5**2 / 3), places=12)
        self.assertAlmostEqual(b[7].item(), volume * 0.2 * (-0.3), places=12)
        self.assertAlmostEqual(g[0, 4].item(), b[4].item(), places=12)
        self.assertAlmostEqual(g[1, 1].item(), b[4].item(), places=12)
        self.assertLess(torch.linalg.eigvalsh(g).min().item(), 0.1)
        self.assertGreater(torch.linalg.eigvalsh(g).min().item(), 0)

    def test_sphere_ellipsoid_independent_fourth_moments(self) -> None:
        for family, axes in (("sphere", (0.5, 0.5, 0.5)),
                             ("ellipsoid", (0.4, 0.6, 0.8))):
            d = make_geometry(family, (0, 0, 0), axes)
            b, g = analytic_moment_data(d)
            volume = math.tau * 2 / 3 * math.prod(axes)
            self.assertAlmostEqual(b[0].item(), volume, places=12)
            self.assertAlmostEqual(b[4].item(), volume * axes[0]**2 / 5, places=12)
            self.assertAlmostEqual(g[4, 4].item(), volume * 3 * axes[0]**4 / 35, places=12)
            self.assertAlmostEqual(g[4, 5].item(), volume * axes[0]**2 * axes[1]**2 / 35, places=12)
            self.assertAlmostEqual(g[7, 7].item(), g[4, 5].item(), places=12)
            self.assertTrue(torch.allclose(g, g.T, atol=1e-12, rtol=0))

    def test_exact_labels_jacobian_and_directional_finite_difference(self) -> None:
        d = make_geometry("ellipsoid", (.09, -.12, .03), (.4, .5, .65))
        c = torch.linspace(-0.02, 0.025, 10, dtype=torch.float64)
        r, j = analytic_labels(d, c)
        direction = torch.arange(1, 11, dtype=torch.float64)
        direction /= direction.norm()
        eps = 1e-5
        plus = analytic_labels(d, c + eps * direction)[0]
        minus = analytic_labels(d, c - eps * direction)[0]
        self.assertTrue(torch.allclose((plus - minus) / (2 * eps), j @ direction, atol=1e-10, rtol=1e-9))
        self.assertTrue(torch.isfinite(r).all())

    def test_invalid_geometry_and_oracle_nans_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_geometry("sphere", (0, 0, 0), (.5, .4, .5))
        with self.assertRaises(ValueError):
            make_geometry("box", (0, 0, 0), (-1, 1, 1))
        with self.assertRaises(ValueError):
            validate_geometry(torch.zeros(9, dtype=torch.float64))
        with self.assertRaises(ValueError):
            analytic_labels(make_geometry("box", (0, 0, 0), (1, 1, 1)), torch.full((10,), float("nan")))

    def test_seed_and_family_exclusivity(self) -> None:
        x = sample_families(("box", "sphere"), 3, seed=31)
        y = sample_families(("box", "sphere"), 3, seed=31)
        for a, b in zip(x, y):
            self.assertTrue(torch.equal(a, b))
        test = sample_families(("ellipsoid",), 3, seed=32)
        self.assertTrue(torch.all(x[0][:, 2] == 0))
        self.assertTrue(torch.all(test[0][:, 2] == 1))
        self.assertEqual(len(x[0]), 12)
        self.assertEqual(len(test[0]), 6)


class W5ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        torch.set_num_threads(1)
        torch.manual_seed(7)
        self.d = make_geometry("box", (.08, -.12, .03), (.4, .5, .6)).float()
        self.c = torch.linspace(-.02, .02, 10)

    def test_both_models_share_api_and_support_cached_many_queries(self) -> None:
        for cls in (DeepONetMoment, GeometryMLPMoment):
            with self.subTest(model=cls.__name__):
                model = cls()
                z = model.encode_geometry(self.d)
                self.assertEqual(tuple(z.shape), (model.cached_dim,))
                self.assertEqual(tuple(model.moment(z, self.c).shape), (10,))
                self.assertEqual(tuple(model.moment(z, self.c.repeat(5, 1)).shape), (5, 10))
                self.assertTrue(torch.allclose(model(self.d, self.c), model.moment(z, self.c)))
                self.assertEqual(tuple(model.jacobian(z, self.c).shape), (10, 10))
                self.assertEqual(tuple(model.jacobian(z, self.c.repeat(3, 1)).shape), (3, 10, 10))
                # Batched geometry and controls also accepted, excluding ambiguity.
                self.assertEqual(tuple(model(self.d.repeat(3, 1), self.c.repeat(3, 1)).shape), (3, 10))
                with self.assertRaises(ValueError):
                    model.moment(z.repeat(2, 1), self.c.repeat(3, 1))

    def test_deeponet_branch_is_evaluated_only_at_geometry_encode(self) -> None:
        from unittest.mock import patch

        model = DeepONetMoment()
        with patch.object(model.branch, "forward", wraps=model.branch.forward) as branch_forward:
            z = model.encode_geometry(self.d)
            self.assertEqual(branch_forward.call_count, 1)
            for _ in range(5):
                model.moment(z, self.c)
            model.moment(z, self.c.repeat(4, 1))
            model.jacobian(z, self.c)
            self.assertEqual(branch_forward.call_count, 1)

    def test_jacrev_agrees_with_independent_central_difference(self) -> None:
        eps = 1e-3
        for cls in (DeepONetMoment, GeometryMLPMoment):
            with self.subTest(model=cls.__name__):
                model = cls()
                z = model.encode_geometry(self.d)
                got = model.jacobian(z, self.c)
                columns = []
                for i in range(10):
                    delta = torch.zeros(10)
                    delta[i] = eps
                    columns.append((model.moment(z, self.c + delta) - model.moment(z, self.c - delta)) / (2 * eps))
                finite_diff = torch.stack(columns, dim=1)
                self.assertTrue(torch.allclose(got, finite_diff, atol=4e-5, rtol=4e-4))

    def test_derivative_loss_backpropagates_into_both_models(self) -> None:
        for cls in (DeepONetMoment, GeometryMLPMoment):
            with self.subTest(model=cls.__name__):
                model = cls()
                z = model.encode_geometry(self.d)
                jac = model.jacobian(z, self.c)
                (jac.square().sum()).backward()
                gradients = [p.grad for p in model.parameters()]
                self.assertTrue(any(g is not None and torch.isfinite(g).all() and g.abs().sum() > 0 for g in gradients))

    def test_capacity_is_comparable_and_linear_macs_are_explicit(self) -> None:
        a, b = DeepONetMoment(), GeometryMLPMoment()
        ca, cb = a.complexity(), b.complexity()
        self.assertLess(abs(ca["parameters"] - cb["parameters"]) / ca["parameters"], 0.15)
        for comp in (ca, cb):
            self.assertGreater(comp["encode_macs"], 0)
            self.assertGreater(comp["warm_query_macs"], 0)
            self.assertEqual(comp["cold_query_macs"], comp["encode_macs"] + comp["warm_query_macs"])

    def test_adapter_zero_and_nonzero_support_freeze_network(self) -> None:
        model = DeepONetMoment()
        z = model.encode_geometry(self.d).detach()
        support_c = torch.linspace(-.02, .02, 80).reshape(8, 10)
        support_r = torch.stack([analytic_labels(self.d.double(), cc.double())[0].float() for cc in support_c])
        state_before = {k: v.clone() for k, v in model.state_dict().items()}
        for k in SUPPORTED_QUERY_COUNTS:
            fit = fit_residual_adapter(model, z, support_c[:k], support_r[:k])
            self.assertEqual(fit.support_count, k)
            self.assertEqual(tuple(fit.jacobian(self.c).shape), (10, 10))
            self.assertTrue(torch.isfinite(fit.predict(self.c)).all())
            if k == 0:
                self.assertTrue(torch.equal(fit.predict(self.c), model.moment(z, self.c)))
            if k == 1:
                initial = (model.moment(z, support_c[:1]) - support_r[:1]).norm()
                corrected = (fit.predict(support_c[:1]) - support_r[:1]).norm()
                self.assertLess(corrected.item(), initial.item())
        for k, v in model.state_dict().items():
            self.assertTrue(torch.equal(v, state_before[k]))
        with self.assertRaises(ValueError):
            fit_residual_adapter(model, z, support_c[:3], support_r[:3])

    def test_end_to_end_analytic_smoke_reports_all_four_arms(self) -> None:
        report = run(seed=7, steps=2, per_family=2, repeats=2)
        self.assertEqual(report["status"], "synthetic_architecture_smoke_only")
        self.assertEqual(report["train_geometry_families"], ["box", "sphere"])
        self.assertEqual(report["test_geometry_families"], ["ellipsoid"])
        self.assertEqual(set(report["model_results"]), {"deeponet", "geometry_mlp"})
        for variants in report["model_results"].values():
            self.assertEqual(set(variants), {"residual_only", "derivative_enhanced"})
            for info in variants.values():
                for key in ("r_mae", "J_mae", "directional_derivative_mae", "step_l2_error"):
                    self.assertTrue(math.isfinite(info["heldout_metrics"][key]))
                self.assertEqual(set(info["adaptation"]), {"0", "1", "2", "4", "8"})
                self.assertGreater(info["performance"]["cached_jacrev_10x10_ms"], 0)
                self.assertEqual(info["training"]["gpu_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
