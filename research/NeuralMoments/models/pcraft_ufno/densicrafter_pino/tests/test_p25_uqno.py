import unittest

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_uqno_aggregate_train import _split
from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset


class P25UQNOContracts(unittest.TestCase):
    def test_geometry_id_split_is_stable_and_grouped(self):
        gid = "geometry-example-unique"
        self.assertEqual(_split(gid), _split(gid))
        assignments = {}
        for resolution in (64, 128):
            for query in (0, 1):
                assignments[(resolution, query)] = _split(gid)
        self.assertEqual(len(set(assignments.values())), 1)

    def test_shared_collection_geometry_ids_match_across_resolution(self):
        for family in ("box", "sphere", "ellipsoid"):
            low = sample_dataset((family,), per_family=5, seed=20261108,
                                 grid_size=64, queries_per_geometry=2)
            high = sample_dataset((family,), per_family=5, seed=20261108,
                                  grid_size=128, queries_per_geometry=2)
            self.assertEqual(
                [x["geometry_id"] for x in low[4]],
                [x["geometry_id"] for x in high[4]],
            )
            self.assertEqual(
                [x["query_index"] for x in low[4]],
                [x["query_index"] for x in high[4]],
            )


if __name__ == "__main__":
    unittest.main()
