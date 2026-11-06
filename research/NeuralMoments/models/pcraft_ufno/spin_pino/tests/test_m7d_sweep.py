import unittest

from research.NeuralMoments.models.pcraft_ufno.spin_pino.m7d_sweep import LAMBDAS


class SpinPINOM7DSweepTests(unittest.TestCase):
    def test_lambda_grid_contains_baseline_and_stronger_constraints(self):
        self.assertEqual(LAMBDAS[0], 0.0)
        self.assertIn(0.05, LAMBDAS)
        self.assertIn(0.2, LAMBDAS)
        self.assertIn(0.5, LAMBDAS)
        self.assertIn(1.0, LAMBDAS)
        self.assertEqual(tuple(sorted(LAMBDAS)), LAMBDAS)


if __name__ == "__main__":
    unittest.main()
