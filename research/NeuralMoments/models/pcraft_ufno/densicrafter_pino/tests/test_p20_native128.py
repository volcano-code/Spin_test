import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p17_trained_pino import _surface_masks
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.bridge import resolution_aware_bottom_contact_region

class P20Native128Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls): torch.set_num_threads(1)
    def test_distinct_seeded_spheres(self):
        from research.NeuralMoments.models.pcraft_ufno.analytic_cut import sample_dataset
        ids=[sample_dataset(("sphere",),per_family=1,seed=s+707,grid_size=16,queries_per_geometry=1)[4][0]["geometry_id"] for s in (271,277,281)]
        self.assertEqual(len(set(ids)),3)
    def test_contact_matches_original_64_formula(self):
        torch.manual_seed(4);x=torch.rand((1,3,3,64));w=4.0**(-torch.arange(64,dtype=x.dtype))
        expected=(x*w.view(1,1,1,-1)).max(-1).values
        actual=resolution_aware_bottom_contact_region(x,exp=4.,reference_resolution=64)
        self.assertTrue(torch.equal(actual,expected))
    def test_four_cell_shell_partition(self):
        n=32;a=torch.linspace(-1,1,n);xyz=torch.stack(torch.meshgrid(a,a,a,indexing="ij"),-1)
        occ=(xyz.square().sum(-1)<.72**2)[None,None]
        shell,design=_surface_masks(occ,wall_cells=4)
        self.assertTrue(torch.equal(shell|design,occ));self.assertFalse(bool((shell&design).any()))
        self.assertTrue(bool(shell.any() and design.any()))
if __name__=="__main__": unittest.main()
