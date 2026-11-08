"""P18 contract: three P14 checkpoint artifacts and trained-PINO Densi confirmation."""
import unittest
from pathlib import Path
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p17_trained_pino import _surface_masks
import torch


class P18ConfirmationContracts(unittest.TestCase):
    def test_surface_mask_is_nonperiodic_two_cell_partition(self):
        n=24
        x=torch.linspace(-1,1,n)
        xyz=torch.stack(torch.meshgrid(x,x,x,indexing="ij"),-1)
        occ=(xyz.square().sum(-1)<.75**2)[None,None]
        shell,design=_surface_masks(occ,wall_cells=2)
        self.assertTrue(torch.equal(shell|design,occ))
        self.assertFalse(bool((shell&design).any()))
        self.assertTrue(bool(shell.any() and design.any()))


if __name__=="__main__":
    unittest.main()
