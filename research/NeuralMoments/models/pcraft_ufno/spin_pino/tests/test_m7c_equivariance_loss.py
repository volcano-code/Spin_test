import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.train import run_seed


class SpinPINOM7CEquivarianceLossTests(unittest.TestCase):
    def test_covariance_loss_training_is_finite_and_logged(self):
        result = run_seed(
            seed=20261107,
            train_geometries_per_family=4,
            test_ellipsoid_geometries=2,
            queries_per_geometry=2,
            steps=2,
            batch_size=4,
            grid_size=8,
            points_per_axis=4,
            smoothing=0.02,
            moment_parameterization="logistic_atom",
            temperature=0.12,
            geometry_adapter="none",
            lambda_equivariance=0.05,
            rotation_augmentation=False,
            evaluation_rotation_mode="so3",
            device="cpu",
        )
        self.assertEqual(result["loss_conditioning"]["lambda_equivariance"], 0.05)
        self.assertEqual(result["rotation_evaluation_diagnostics"]["rotation_mode"], "so3")
        for row in result["training"]["history"]:
            self.assertTrue(torch.isfinite(torch.tensor(row["train_total"])))
            self.assertTrue(torch.isfinite(torch.tensor(row["train_equivariance"])))
            self.assertGreaterEqual(row["train_equivariance"], 0.0)


if __name__ == "__main__":
    unittest.main()
