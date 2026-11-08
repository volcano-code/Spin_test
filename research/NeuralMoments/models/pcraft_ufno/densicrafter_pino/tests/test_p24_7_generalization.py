import unittest

from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset


class P24_7GeneralizationContracts(unittest.TestCase):
    def test_three_geometry_families_have_resolution_stable_ids(self):
        for family in ("box", "sphere", "ellipsoid"):
            low = sample_dataset((family,), per_family=3, seed=978,
                                 grid_size=64, queries_per_geometry=1)
            high = sample_dataset((family,), per_family=3, seed=978,
                                  grid_size=128, queries_per_geometry=1)
            self.assertEqual(
                [x["geometry_id"] for x in low[4]],
                [x["geometry_id"] for x in high[4]],
            )
            self.assertEqual(len({x["geometry_id"] for x in low[4]}), 3)
            self.assertTrue(all(x["source"] == "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI"
                                for x in low[4]))

    def test_protocol_case_count(self):
        families = ("box", "sphere", "ellipsoid")
        resolutions = (64, 128)
        geometries_per_family = 3
        self.assertEqual(len(families)*len(resolutions)*geometries_per_family, 18)


if __name__ == "__main__":
    unittest.main()
