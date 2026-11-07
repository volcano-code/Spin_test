"""Tests that the selected upstream pilot has a reproducible P0-only scope."""
import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.p0_integration.selected_pilot import run


class SelectedPilotContract(unittest.TestCase):
    def test_pilot_frozen_pino_and_no_newton_admission(self):
        torch.set_num_threads(1)
        result=run(seed=13,steps=2,train_geometries_per_family=4,
                   test_ellipsoids=2)
        self.assertLess(result["zero_gate_r_J_max_absolute_difference"],2e-6)
        self.assertEqual(len(result["conditions"]),4)
        self.assertTrue(result["claims"]["PCRAFT_PINO_primary"])
        self.assertFalse(result["claims"]["trained_upstream_auxiliary_adapters"])
        self.assertTrue(result["groupwise_conformal"]["native_newton_exact_required"])
        self.assertFalse(result["groupwise_conformal"]["native_newton_admitted"])
        self.assertEqual(result["source_label"],
                         "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI")
        for x in result["conditions"]:
            self.assertGreater(x["test"]["r_relative_l2"],0.)
            self.assertGreater(x["test"]["J_relative_l2"],0.)


if __name__=="__main__":
    unittest.main()
