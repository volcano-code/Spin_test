"""P14 real high-resolution end-to-end P-CRAFT PINO training contract."""
import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.spin_pino.train import run_seed


class P14NativePINOTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_native_grid_is_not_adaptively_pooled(self):
        for grid in (16,32):
            model=SpinPINO(width=8,modes=4,n_layers=4,grid_size=grid,
                           points_per_axis=8,hidden_dim=48,
                           moment_parameterization="logistic_atom")
            x=torch.zeros((1,4,grid,grid,grid))
            prepared=model.encoder._prepare_geometry(x)
            self.assertEqual(tuple(prepared.shape[-3:]),(grid,grid,grid))
            self.assertEqual(model.encoder.grid_size,grid)
            self.assertEqual(model.quadrature_xyz.shape[0],512)

    def test_full_pino_end_to_end_training_at_native_16(self):
        result=run_seed(
            seed=17,train_geometries_per_family=4,
            test_ellipsoid_geometries=2,queries_per_geometry=1,
            steps=1,batch_size=1,grid_size=16,points_per_axis=4,
            preconditioned_loss=True,pcgrad=False,
            moment_parameterization="logistic_atom",
            rotation_augmentation=False,evaluation_rotation_mode="cube",
            device="cpu",
        )
        self.assertTrue(result["claims"]["trained_spin_model"])
        self.assertFalse(result["claims"]["cherchi_supervised"])
        self.assertEqual(result["model_config"]["grid_size"],16)
        self.assertEqual(result["training"]["steps"],1)
        self.assertGreater(result["trainable_parameters"],0)
        self.assertTrue(torch.isfinite(torch.tensor(
            result["held_out_ellipsoid_metrics"]["r_relative_l2"]
        )))


if __name__=="__main__":
    unittest.main()
