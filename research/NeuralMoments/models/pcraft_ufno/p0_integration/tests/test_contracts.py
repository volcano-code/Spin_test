import math
import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.p0_integration.contracts import (
    MomentQuadratureResult, native_quadric_value, raw_monomials,
)
from research.NeuralMoments.models.pcraft_ufno.p0_integration.quadrann_adapter import quadrature_moments
from research.NeuralMoments.models.pcraft_ufno.p0_integration.neuraloperator_adapter import (
    SplitConformalMomentCalibrator, voxel_geometry_to_point_cloud,
)


class P0Contracts(unittest.TestCase):
    def test_native_cross_terms_and_raw_moment_order(self):
        point = torch.tensor([[[1.0, 2.0, 3.0]]], dtype=torch.float64)
        c = torch.zeros((1, 10), dtype=torch.float64)
        c[0, 7] = 1.0
        c[0, 8] = 2.0
        c[0, 9] = 3.0
        self.assertEqual(float(native_quadric_value(point, c)[0, 0]), 2*2*3 + 2*2*1*3 + 2*3*1*2)
        self.assertTrue(torch.equal(raw_monomials(point), torch.tensor([[[1,1,2,3,1,4,9,6,3,2]]], dtype=torch.float64)))
        batched_points = torch.tensor([[[1., 2., 3.], [0., 1., 2.]], [[2., 1., 0.], [1., 0., 2.]]], dtype=torch.float64)
        batched_c = torch.zeros((2, 10), dtype=torch.float64)
        batched_c[:, 7] = 1.0
        values = native_quadric_value(batched_points, batched_c)
        self.assertEqual(values.shape, (2, 2))
        self.assertTrue(torch.allclose(values, torch.tensor([[12., 4.], [0., 0.]], dtype=torch.float64)))

    def test_quadrature_moments_uniform_point_cloud(self):
        points = torch.tensor([[[-0.5, 0, 0], [0.5, 0, 0]]], dtype=torch.float64)
        density = torch.ones((1, 2), dtype=torch.float64)
        weights = torch.tensor([[0.5, 0.5]], dtype=torch.float64)
        result = quadrature_moments(points, density, 2.0, weights)
        expected = torch.tensor([[2, 0, 0, 0, 0.5, 0, 0, 0, 0, 0]], dtype=torch.float64)
        self.assertTrue(torch.allclose(result.moments, expected))
        self.assertIsNone(result.jacobian)
        self.assertFalse(result.training_admitted)
        self.assertIn("WITHHELD", result.derivative_status)

    def test_result_refuses_jacobian_or_training_admission(self):
        with self.assertRaises(ValueError):
            MomentQuadratureResult(torch.zeros((1, 10)), jacobian=torch.zeros((1, 10, 10)))
        with self.assertRaises(ValueError):
            MomentQuadratureResult(torch.zeros((1, 10)), training_admitted=True)

    def test_conformal_finite_sample_rank_and_infinite_small_sample(self):
        mean = torch.zeros((20, 10))
        scale = torch.ones_like(mean)
        target = torch.arange(1, 21, dtype=torch.float32).unsqueeze(-1).repeat(1, 10)
        calibrator = SplitConformalMomentCalibrator(alpha=0.1).fit(mean, scale, target)
        self.assertTrue(calibrator.calibrated)
        self.assertEqual(calibrator.qhat, 19.0)
        small = SplitConformalMomentCalibrator(alpha=0.1).fit(mean[:5], scale[:5], target[:5])
        self.assertFalse(small.calibrated)
        self.assertTrue(math.isinf(small.qhat))

    def test_voxel_to_point_cloud_preserves_four_channels(self):
        geometry = torch.zeros((1, 4, 4, 4, 4))
        geometry[:, 0] = 0.5
        geometry[:, 1, 1:3, 1:3, 1:3] = 1
        points, features = voxel_geometry_to_point_cloud(geometry, max_points=32)
        self.assertEqual(points.shape, (1, 32, 3))
        self.assertEqual(features.shape, (1, 32, 4))
        self.assertTrue(bool(((points >= 0) & (points <= 1)).all()))


if __name__ == "__main__":
    unittest.main()
