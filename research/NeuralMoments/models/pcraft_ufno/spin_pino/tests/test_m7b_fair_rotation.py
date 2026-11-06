import unittest

from research.NeuralMoments.models.pcraft_ufno.spin_pino.train import run_seed


class SpinPINOM7BFairRotationTests(unittest.TestCase):
    def test_all_training_conditions_use_same_so3_test_transform(self):
        common = dict(
            seed=20261106,
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
            evaluation_rotation_mode="so3",
            device="cpu",
        )
        plain = run_seed(rotation_augmentation=False, **common)
        augmented = run_seed(
            rotation_augmentation=True,
            rotation_augmentation_mode="so3",
            **common,
        )
        self.assertEqual(
            plain["rotation_evaluation_diagnostics"]["rotation_mode"], "so3"
        )
        self.assertEqual(
            augmented["rotation_evaluation_diagnostics"]["rotation_mode"], "so3"
        )
        self.assertEqual(
            plain["rotation_evaluation_diagnostics"]["n_rotated_test_samples"], 4
        )
        self.assertEqual(
            augmented["rotation_evaluation_diagnostics"]["n_rotated_test_samples"], 4
        )
        self.assertEqual(
            plain["rotation_evaluation_diagnostics"]["mean_occupied_centers_clipped_fraction"],
            augmented["rotation_evaluation_diagnostics"]["mean_occupied_centers_clipped_fraction"],
        )
        self.assertEqual(
            plain["rotation_evaluation_diagnostics"]["mean_soft_occupancy_mass_ratio"],
            augmented["rotation_evaluation_diagnostics"]["mean_soft_occupancy_mass_ratio"],
        )
        self.assertFalse(plain["loss_conditioning"]["rotation_augmentation"])
        self.assertTrue(augmented["loss_conditioning"]["rotation_augmentation"])


if __name__ == "__main__":
    unittest.main()
