import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.equivariance import (
    random_so3_rotation, transform_raw_moments, transform_native_jacobian,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.orbit_ensemble import (
    orbit_average, make_so3_orbit,
)

class _Dummy:
    def encode_geometry(self, D):
        return D[:, 0].mean(dim=(1,2,3)).unsqueeze(-1)
    def moment_from_weights(self, z, c):
        s=z[:, :1]
        return torch.cat((s, s*0, s*0, s*0, s*0, s*0, s*0, s*0, s*0, s*0), dim=-1)
    def jacobian_from_weights(self, z, c):
        return torch.zeros((c.shape[0],10,10),dtype=c.dtype,device=c.device)

class OrbitEnsembleTests(unittest.TestCase):
    def test_so3_orbit_rotations_are_proper(self):
        rotations=make_so3_orbit(4,seed=42)
        self.assertEqual(len(rotations),4)
        for R in rotations:
            self.assertTrue(torch.allclose(R.T@R,torch.eye(3),atol=1e-6))
            self.assertAlmostEqual(float(torch.det(R)),1.0,places=5)
    def test_identity_only_matches_direct_forward(self):
        D=torch.rand((2,4,8,8,8)); c=torch.randn((2,10)); model=_Dummy()
        direct=model.moment_from_weights(model.encode_geometry(D),c)
        out=orbit_average(model,D,c,[torch.eye(3)],with_jacobian=True)
        self.assertTrue(torch.allclose(out["moments"],direct,atol=1e-6))
        self.assertEqual(out["jacobian"].shape,(2,10,10))
        self.assertEqual(int(out["views"]),1)
    def test_rotation_transform_roundtrip(self):
        R=random_so3_rotation(13,dtype=torch.float64)
        r=torch.randn((2,10),dtype=torch.float64); J=torch.randn((2,10,10),dtype=torch.float64)
        r2=transform_raw_moments(transform_raw_moments(r,R),R.T)
        J2=transform_native_jacobian(transform_native_jacobian(J,R),R.T)
        self.assertTrue(torch.allclose(r2,r,atol=1e-10,rtol=1e-10))
        self.assertTrue(torch.allclose(J2,J,atol=1e-10,rtol=1e-10))

if __name__=="__main__":
    unittest.main()
