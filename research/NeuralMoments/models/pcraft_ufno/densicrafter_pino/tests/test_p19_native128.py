"""P19 native 128 transfer, shell scaling and input-gradient checkpoint contracts."""
import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p17_trained_pino import _surface_masks


class P19Native128Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_native_128_preprocess_and_strict_64_to_128_transfer(self):
        torch.manual_seed(19)
        model64=SpinPINO(width=8,modes=4,n_layers=4,grid_size=64,
            points_per_axis=8,hidden_dim=48,smoothing=.04,
            moment_parameterization="logistic_atom",temperature=.12)
        model128=SpinPINO(width=8,modes=4,n_layers=4,grid_size=128,
            points_per_axis=8,hidden_dim=48,smoothing=.04,
            moment_parameterization="logistic_atom",temperature=.12,
            use_gradient_checkpoint=True)
        loaded=model128.load_state_dict(model64.state_dict(),strict=True)
        self.assertEqual(loaded.missing_keys,[])
        self.assertEqual(loaded.unexpected_keys,[])
        x=torch.zeros((1,4,128,128,128))
        prepared=model128.encoder._prepare_geometry(x)
        self.assertEqual(tuple(prepared.shape[-3:]),(128,128,128))
        self.assertEqual(model128.encoder.grid_size,128)
        self.assertEqual(model128.quadrature_xyz.shape[0],512)

    def test_checkpointed_frozen_pino_keeps_density_input_gradient(self):
        model=SpinPINO(width=4,modes=2,n_layers=2,grid_size=16,
            points_per_axis=4,hidden_dim=32,moment_parameterization="logistic_atom",
            use_gradient_checkpoint=True)
        for p in model.parameters(): p.requires_grad_(False)
        model.train()
        density=torch.full((1,1,16,16,16),.8,requires_grad=True)
        occupancy=torch.ones_like(density)
        zeros=torch.zeros_like(density)
        geometry=torch.cat((density,occupancy,zeros,zeros),1)
        c=torch.zeros((1,10))
        c[:,0]=1.0
        weights=model.encode_geometry(geometry)
        moments=model.moment_from_weights(weights,c)
        moments.square().sum().backward()
        self.assertIsNotNone(density.grad)
        self.assertTrue(bool(torch.isfinite(density.grad).all()))
        self.assertGreater(float(density.grad.abs().sum()),0.)
        self.assertTrue(all(p.grad is None for p in model.parameters()))


    def test_resolution_aware_contact_matches_original_at_64(self):
        from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.bridge import (
            resolution_aware_bottom_contact_region,
        )
        from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.third_party.densicrafter_core import (
            get_smooth_bottom_contact_region,
        )
        torch.manual_seed(7)
        rho=torch.rand((1,9,11,64))
        actual=resolution_aware_bottom_contact_region(rho,exp=4.,reference_resolution=64)
        original=get_smooth_bottom_contact_region(rho,0,exp=4.)
        self.assertTrue(torch.equal(actual,original))

    def test_same_physical_height_has_same_contact_weight_at_64_and_128(self):
        from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.bridge import (
            resolution_aware_bottom_contact_region,
        )
        rho64=torch.zeros((1,2,2,64))
        rho128=torch.zeros((1,2,2,128))
        rho64[:,:,:,16]=1.0
        rho128[:,:,:,32]=1.0
        c64=resolution_aware_bottom_contact_region(rho64,exp=4.,reference_resolution=64)
        c128=resolution_aware_bottom_contact_region(rho128,exp=4.,reference_resolution=64)
        self.assertTrue(torch.allclose(c64,c128,rtol=1e-6,atol=0.0))

    def test_128_grid_four_cell_shell_matches_64_grid_two_cell_scale(self):
        n=32
        x=torch.linspace(-1,1,n)
        xyz=torch.stack(torch.meshgrid(x,x,x,indexing="ij"),-1)
        occ=(xyz.square().sum(-1)<.72**2)[None,None]
        shell,design=_surface_masks(occ,wall_cells=4)
        self.assertTrue(torch.equal(shell|design,occ))
        self.assertFalse(bool((shell&design).any()))
        self.assertTrue(bool(shell.any() and design.any()))


if __name__=="__main__":
    unittest.main()
