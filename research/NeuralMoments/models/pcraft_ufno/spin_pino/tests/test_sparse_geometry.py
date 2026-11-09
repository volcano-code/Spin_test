import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset
from research.NeuralMoments.models.pcraft_ufno.spin_pino.sparse_geometry import SparseGeometryBatch


class SparseGeometryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_dense_sparse_roundtrip_preserves_occupied_values(self):
        dense, _, _, _, _ = sample_dataset(
            ("sphere",), per_family=2, seed=20261109,
            grid_size=16, queries_per_geometry=1,
        )
        sparse = SparseGeometryBatch.from_dense(dense)
        reconstructed = sparse.to_dense()
        mask = dense[:, 1] > 0.5
        self.assertTrue(torch.equal(reconstructed[:, 1] > 0.5, mask))
        self.assertTrue(torch.allclose(reconstructed[mask.unsqueeze(1).expand_as(dense)].reshape(-1),
                                       dense[mask.unsqueeze(1).expand_as(dense)].reshape(-1)))
        self.assertEqual(sparse.active_counts().shape, (2,))
        self.assertTrue(bool((sparse.active_counts() > 0).all()))

    def test_empty_batch_member_is_preserved(self):
        dense = torch.zeros(2, 4, 8, 8, 8)
        dense[0, 1, 2:6, 2:6, 2:6] = 1
        sparse = SparseGeometryBatch.from_dense(dense)
        self.assertEqual(sparse.active_counts().tolist(), [64, 0])
        self.assertEqual(tuple(sparse.to_dense().shape), tuple(dense.shape))

    def test_duplicate_coordinates_are_rejected(self):
        coords = torch.tensor([[0, 1, 1, 1], [0, 1, 1, 1]], dtype=torch.int64)
        values = torch.ones(2, 4)
        with self.assertRaises(ValueError):
            SparseGeometryBatch(coords, values, 1, (4, 4, 4))

    def test_out_of_bounds_coordinates_are_rejected(self):
        coords = torch.tensor([[0, 4, 1, 1]], dtype=torch.int64)
        values = torch.ones(1, 4)
        with self.assertRaises(ValueError):
            SparseGeometryBatch(coords, values, 1, (4, 4, 4))

    def test_invalid_dense_input_is_rejected(self):
        with self.assertRaises(ValueError):
            SparseGeometryBatch.from_dense(torch.zeros(1, 3, 8, 8, 8))


if __name__ == "__main__":
    unittest.main()
