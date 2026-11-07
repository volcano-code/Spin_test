"""P13b 32/64 cloud CPU resolutions, independent physical ledger and feasibility."""
import math
import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p13b_highres import (
    masks, exact_discrete_cut_moments, _pino, run, stress_128,
)
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.bridge import physical_grid


class P13BMaterialConstraints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_two_cell_wall_and_nonempty_design_32(self):
        shell,design=masks(32,wall_cells=2)
        self.assertEqual(tuple(shell.shape),(1,1,32,32,32))
        self.assertTrue(bool((shell&design).sum()==0))
        self.assertTrue(bool(shell[:,:,:2].all()))
        self.assertTrue(bool(shell[:,:,-2:].all()))
        self.assertTrue(bool(design[:,:,2:-2,2:-2,2:-2].all()))
        self.assertEqual(int(design.sum()),28**3)

    def test_discrete_cut_is_independent_of_pino_and_respects_cross_2(self):
        density=torch.ones((1,1,8,8,8))
        c=torch.tensor([[0.,0.,0.,1.,0.,0.,0.,0.,0.,0.]])
        r=exact_discrete_cut_moments(density,c)
        self.assertAlmostEqual(float(r[0,0]),4.,places=5)
        self.assertGreater(float(r[0,3]),0.)
        c2=torch.zeros_like(c)
        c2[:,7]=1.
        cross=exact_discrete_cut_moments(density,c2)
        self.assertAlmostEqual(float(cross[0,0]),4.,places=5)

    def test_32_small_three_objective_and_hard_feasible(self):
        receipt=run(resolutions=(32,),steps=3,wall_cells=2)
        rows=receipt["case_results"][0]["results"]
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]["arm"],"densicrafter_only")
        self.assertEqual(rows[-1]["arm"],"feasible_joint")
        self.assertTrue(rows[-1]["feasible_under_predeclared_tolerances"])
        self.assertTrue(all(r["outer_shell_preserved"] for r in rows))
        self.assertTrue(all(r["PINO_grid_size"]==8 for r in rows))
        self.assertTrue(all(math.isfinite(r["mass_final"]) for r in rows))

    def test_spectral_grid_aliasing_is_reported_not_hidden(self):
        n=32
        a=torch.full((1,4,n,n,n),.5,dtype=torch.float32)
        a[:,1]=1; a[:,2:]=0
        b=a.clone()
        # Every coarse 4-cell pool has 2 high + 2 low z subcells.
        parity=(torch.arange(n)%4 <2).float()
        b[:,0]=parity.view(1,1,1,n).expand(1,n,n,n)
        pino=_pino()
        pooled1=pino.encoder._prepare_geometry(a)
        pooled2=pino.encoder._prepare_geometry(b)
        self.assertTrue(torch.allclose(pooled1,pooled2,atol=1e-6))
        c=torch.tensor([[-.08,0.,0.,1.,0.,0.,0.,0.,0.,0.]])
        true_a=exact_discrete_cut_moments(a[:,0:1],c)
        true_b=exact_discrete_cut_moments(b[:,0:1],c)
        self.assertGreater(float((true_a-true_b).abs().max()),1e-3)

    def test_stress_128_must_not_claim_native_fno_resolution(self):
        # Cheap real gradient at 32^3 in tests. Dedicated CI stress step
        # covers 128^3 and records time/RSS to its own artifact.
        result=stress_128(32)
        self.assertTrue(result["full_resolution_density_design_gradient"])
        self.assertFalse(result["full_resolution_operator"])
        self.assertEqual(result["internal_PINO_operator_grid"],8)


if __name__=="__main__":
    unittest.main()
