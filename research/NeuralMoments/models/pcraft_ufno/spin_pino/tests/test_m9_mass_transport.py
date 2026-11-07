"""M9 bounded conservative-rotation contracts, independent of PINO training."""
import math
import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.mass_transport import (
    conservative_rotate_geometry, sampled_material_moments,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.equivariance import (
    transform_raw_moments, rotate_geometry_voxels,
)


def rz(angle, dtype=torch.float64):
    c, s = math.cos(angle), math.sin(angle)
    return torch.tensor([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=dtype)


def ball(n=8, radius=.7, center=(0, 0, 0), density=.8, dtype=torch.float64):
    ax = torch.linspace(-1, 1, n, dtype=dtype)
    xyz = torch.stack(torch.meshgrid(ax, ax, ax, indexing="ij"), -1)
    mask = (((xyz-torch.tensor(center, dtype=dtype))/radius)**2).sum(-1) <= 1
    occ = mask.to(dtype)
    rho = density*occ
    return torch.stack((rho, occ, torch.zeros_like(occ), torch.zeros_like(occ)), 0).unsqueeze(0)


class M9TransportTests(unittest.TestCase):
    def test_identity_is_bit_exact(self):
        D=ball()
        out, stats=conservative_rotate_geometry(D,torch.eye(3,dtype=D.dtype))
        self.assertTrue(torch.equal(D,out))
        self.assertEqual(stats["mass_relative_error"],0)

    def test_exact_cube_rotation_ten_sampled_moments(self):
        D=ball(center=(.18,-.18,0))
        R=rz(math.pi/2)
        out, stats=conservative_rotate_geometry(D,R)
        expected=transform_raw_moments(sampled_material_moments(D),R)
        self.assertTrue(torch.allclose(sampled_material_moments(out),expected,atol=1e-10,rtol=1e-10))
        self.assertLess(stats["mass_relative_error"],1e-7)

    def test_arbitrary_rotation_conserves_mass_and_occupancy(self):
        D=ball()
        out, stats=conservative_rotate_geometry(D,rz(.37))
        self.assertLess(stats["mass_relative_error"],1e-6)
        self.assertLess(stats["occupancy_relative_error"],1e-6)
        self.assertLessEqual(float(out[:,:2].max()),1.000001)
        self.assertGreaterEqual(float(out[:,:2].min()),0.0)

    def test_rotated_full_cube_fails_closed(self):
        D=torch.ones((1,4,8,8,8),dtype=torch.float64)
        with self.assertRaisesRegex(ValueError,"exit target cube"):
            conservative_rotate_geometry(D,rz(.37))

    def test_invalid_and_empty_support_fail_closed(self):
        D=ball()
        D[:,0]=0
        with self.assertRaises(ValueError):
            conservative_rotate_geometry(D,rz(.37))
        D[:,0]=-1
        with self.assertRaises(ValueError):
            conservative_rotate_geometry(D,rz(.37))

    def test_diagnostic_accepts_roundoff_outside_unit_range_without_authorizing_transport(self):
        D=ball()
        D[:,0]=1.0+2e-6
        moments=sampled_material_moments(D)
        self.assertTrue(torch.isfinite(moments).all())
        with self.assertRaises(ValueError):
            conservative_rotate_geometry(D,rz(.37))

    def test_discrete_mass_error_below_pull_interpolation(self):
        D=ball()
        R=rz(.37)
        baseline=rotate_geometry_voxels(D,R)
        candidate,_=conservative_rotate_geometry(D,R)
        reference=sampled_material_moments(D)[:,0]
        old=(sampled_material_moments(baseline)[:,0]-reference).abs()
        new=(sampled_material_moments(candidate)[:,0]-reference).abs()
        self.assertLess(float(new),1e-7)
        self.assertGreater(float(old),float(new))


if __name__ == "__main__":
    unittest.main()
