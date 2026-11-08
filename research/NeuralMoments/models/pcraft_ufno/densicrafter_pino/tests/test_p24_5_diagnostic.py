import unittest

from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset


class P24_5DiagnosticContracts(unittest.TestCase):
    def test_resolution_pair_uses_identical_analytic_geometry(self):
        for family in ("sphere", "ellipsoid"):
            a = sample_dataset((family,), per_family=1, seed=978,
                               grid_size=64, queries_per_geometry=1)
            b = sample_dataset((family,), per_family=1, seed=978,
                               grid_size=128, queries_per_geometry=1)
            self.assertEqual(a[4][0]["geometry_id"], b[4][0]["geometry_id"])
            self.assertEqual(a[4][0]["source"], "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI")
            self.assertEqual(b[4][0]["source"], "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI")


if __name__ == "__main__":
    unittest.main()
