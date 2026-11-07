"""P13b source-vs-internal Fourier resolution contract."""
import unittest

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p13b_operator_grid import run


class OperatorResolutionGate(unittest.TestCase):
    def test_32_source_8_fourier_downsamples_away_true_material_detail(self):
        result=run(source_resolution=32,operator_grid=8)
        self.assertLess(result["internal_encoder_preprocess_max_difference"],1e-6)
        self.assertGreater(result["independent_discrete_cut_max_difference"],1e-4)
        self.assertFalse(result["is_native_Fourier_grid_at_source_resolution"])

    def test_32_source_16_fourier_retains_selected_detail_and_gradient(self):
        result=run(source_resolution=32,operator_grid=16)
        self.assertGreater(result["internal_encoder_preprocess_max_difference"],.05)
        self.assertTrue(result["backward_finite"])
        self.assertGreater(result["full_input_density_gradient_norm"],0.)
        self.assertEqual(result["PINO_Fourier_operator_grid_size"],16)


if __name__=="__main__":
    unittest.main()
