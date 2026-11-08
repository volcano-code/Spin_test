"""P17 trained-PINO DensiCrafter coupling and protected shell checks."""
import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p17_trained_pino import _surface_masks


class P17SurfaceTests(unittest.TestCase):
    def test_two_voxel_surface_shell_is_exact_partition(self):
        n=16
        x=torch.linspace(-1,1,n)
        xyz=torch.stack(torch.meshgrid(x,x,x,indexing="ij"),-1)
        occ=(xyz.square().sum(-1)<.72**2)[None,None]
        shell,design=_surface_masks(occ,wall_cells=2)
        self.assertTrue(bool((shell&design).sum()==0))
        self.assertTrue(torch.equal(shell|design,occ))
        self.assertTrue(bool(shell.any() and design.any()))
        self.assertEqual(shell.dtype,torch.bool)
        self.assertEqual(design.dtype,torch.bool)

    def test_too_thin_geometry_fails_closed(self):
        occ=torch.zeros((1,1,16,16,16),dtype=torch.bool)
        occ[:,:,7:9,7:9,7:9]=True
        with self.assertRaisesRegex(ValueError,"too small"):
            _surface_masks(occ,wall_cells=2)


if __name__=="__main__":
    unittest.main()
