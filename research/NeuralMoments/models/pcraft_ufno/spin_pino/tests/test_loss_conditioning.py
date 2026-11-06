import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.loss_conditioning import (
    DiagonalMomentResidualPreconditioner,
    project_conflicting_gradients,
)


class PINOLossConditioningTests(unittest.TestCase):
    def test_diagonal_preconditioner_is_positive_and_fit_split_scoped(self):
        r = torch.randn(24, 10)
        J = torch.randn(24, 10, 10)
        p = DiagonalMomentResidualPreconditioner.fit(r, J)
        self.assertEqual(p.fit_samples, 24)
        self.assertEqual(p.moment_scale.shape, (10,))
        self.assertEqual(p.jacobian_scale.shape, (10, 10))
        self.assertTrue(bool((p.moment_scale > 0).all()))
        self.assertTrue(bool((p.jacobian_scale > 0).all()))
        self.assertFalse(p.as_dict()["validation_or_test_used_for_fit"])

    def test_pcgrad_projects_conflicting_task_gradients(self):
        g1 = torch.tensor([1.0, 0.0])
        g2 = torch.tensor([-1.0, 1.0])
        projected, stats = project_conflicting_gradients((g1, g2))
        self.assertGreaterEqual(float(torch.dot(projected[0], g2)), -1e-6)
        self.assertGreaterEqual(float(torch.dot(projected[1], g1)), -1e-6)
        self.assertGreater(stats["projection_count"], 0)
        self.assertLess(stats["raw_pairwise_cosines"]["0_1"], 0.0)


if __name__ == "__main__":
    unittest.main()
