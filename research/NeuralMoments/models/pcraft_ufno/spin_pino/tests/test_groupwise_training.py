import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.dataset import generate_splits
from research.NeuralMoments.models.pcraft_ufno.spin_pino.train import (
    _augment_with_groupwise_cube_rotations, run_seed,
)


class GroupwiseTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_same_geometry_queries_share_one_exact_rotation(self):
        data=generate_splits(seed=991,train_geometries_per_family=4,
            test_ellipsoid_geometries=2,queries_per_geometry=2,grid_size=8)["fit"]
        n=len(data[0])
        augmented=_augment_with_groupwise_cube_rotations(data,seed=12345)
        self.assertEqual(len(augmented[4]),2*n)
        groups={}
        for i,row in enumerate(data[4]):
            groups.setdefault(row["geometry_id"],[]).append(i)
        offset=n
        for gid,indices in groups.items():
            rotated=[offset+i for i in indices]
            rows=[augmented[4][i] for i in rotated]
            self.assertEqual(len({r["geometry_id"] for r in rows}),1)
            self.assertEqual(len({str(r["rotation_matrix"]) for r in rows}),1)
            self.assertTrue(all(r["augmentation"]=="EXACT_GROUPWISE_CUBE_ROTATION_LABEL_TRANSFORM" for r in rows))
            for a,b in zip(rotated,rotated[1:]):
                self.assertTrue(torch.equal(augmented[0][a],augmented[0][b]))
                self.assertTrue(torch.equal(augmented[1][a],augmented[1][b]) is False or
                                torch.allclose(augmented[1][a],augmented[1][b]))
        self.assertEqual(len({r["geometry_id"] for r in augmented[4][n:]}),len(groups))

    def test_checkpointed_full_pino_training_path(self):
        result=run_seed(
            seed=19,train_geometries_per_family=4,
            test_ellipsoid_geometries=2,queries_per_geometry=1,
            steps=1,batch_size=1,grid_size=16,points_per_axis=4,
            preconditioned_loss=True,moment_parameterization="logistic_atom",
            rotation_augmentation=True,rotation_augmentation_mode="cube_group",
            evaluation_rotation_mode="cube",use_gradient_checkpoint=True,
            device="cpu",
        )
        self.assertTrue(result["claims"]["trained_spin_model"])
        self.assertTrue(result["model_config"]["use_gradient_checkpoint"])
        self.assertEqual(result["model_config"]["grid_size"],16)


if __name__=="__main__":
    unittest.main()
