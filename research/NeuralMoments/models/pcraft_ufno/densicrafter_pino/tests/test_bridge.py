"""P13a upstream DensiCrafter density-design core coupled to PINO."""
import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.bridge import (
    DensiCrafterSpinPINOBridge,material_moments,physical_grid,
)
from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.third_party.densicrafter_core import (
    mass_penalty, compute_mass_center,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO


def make_pino():
    torch.manual_seed(20261107)
    return SpinPINO(width=4,modes=2,n_layers=2,grid_size=8,
                    points_per_axis=4,hidden_dim=32,
                    moment_parameterization="logistic_atom",temperature=.12)


def masks(n=8):
    shell=torch.zeros((1,1,n,n,n),dtype=torch.bool)
    shell[:,:,0,:,:]=True; shell[:,:,-1,:,:]=True
    shell[:,:,:,0,:]=True; shell[:,:,:,-1,:]=True
    shell[:,:,:,:,0]=True; shell[:,:,:,:,-1]=True
    design=~shell
    return shell,design


def coeff():
    return torch.tensor([[.15,.08,0.,.7,0.,.02,0.,0.,0.,0.]])


class DensiPINOCoupling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_pinned_core_mass_com(self):
        shell,design=masks()
        rho=torch.where(shell,1.,torch.where(design,.5,0.))
        grid=physical_grid(rho.shape[-3:],device=rho.device,dtype=rho.dtype)
        self.assertAlmostEqual(float(mass_penalty(rho)),float(rho.mean()))
        center=compute_mass_center(rho[:,0],grid).transpose(0,1)
        self.assertTrue(torch.allclose(center,torch.zeros_like(center),atol=1e-6))
        full=material_moments(rho)
        self.assertAlmostEqual(float(full[0,0]),float(rho.sum())/64.,places=6)

    def test_frozen_surface_and_gradient_from_actual_pino_head(self):
        shell,design=masks()
        model=DensiCrafterSpinPINOBridge(make_pino(),shell,design)
        c=coeff()
        result=model(c)
        self.assertTrue(bool((result["density"][shell]==1).all()))
        self.assertTrue(bool((result["density"][design]>0).all()))
        self.assertFalse(result["native_jacobian_admitted"])
        self.assertEqual(tuple(result["moments"].shape),(1,10))
        self.assertEqual(tuple(result["model_jacobian_diagnostic"].shape),(1,10,10))
        result["moments"].sum().backward()
        grad=model.density_logits.grad
        self.assertIsNotNone(grad)
        self.assertTrue(torch.isfinite(grad).all())
        self.assertGreater(float(grad[design].abs().sum()),0.)
        self.assertTrue(bool((grad[shell]==0).all()))

    def test_ground_axis_rotation_equivalence(self):
        shell,design=masks()
        m0=DensiCrafterSpinPINOBridge(make_pino(),shell,design,gravity_axis=2)
        m1=DensiCrafterSpinPINOBridge(make_pino(),
                                     shell.permute(0,1,4,3,2),
                                     design.permute(0,1,4,3,2),gravity_axis=0)
        with torch.no_grad():
            m0.density_logits[:,:,2:5,3:6,1:4]=1.3
            m1.density_logits.copy_(m0.density_logits.permute(0,1,4,3,2))
        a=m0(coeff());b=m1(coeff())
        for k in ("mass","com_contact","negative_contact_area","com_height"):
            self.assertTrue(torch.allclose(a["terms"][k],b["terms"][k],atol=1e-5),k)

    def test_nonperiodic_smoothing_and_shell_lock(self):
        shell,design=masks()
        model=DensiCrafterSpinPINOBridge(make_pino(),shell,design,smoothing=True)
        with torch.no_grad():
            model.density_logits.fill_(-15.)
        baseline=model.density().detach().clone()
        with torch.no_grad():
            model.density_logits[:,:,1,1,1]=15.
        d=model.density()
        # sigmoid(-15) is positive (~3e-7). The correct non-wrapping
        # property is NO CHANGE at the opposite corner after a local
        # perturbation, not a mathematically exact zero density.
        self.assertTrue(torch.equal(d[0,0,-2,-2,-2],baseline[0,0,-2,-2,-2]))
        self.assertGreater(float(d[0,0,1,1,1]),float(baseline[0,0,1,1,1]))
        self.assertEqual(float(d[0,0,0,0,0]),1.)
        self.assertLess(float(d[0,0,-2,-2,-2]),1e-5)

    def test_density_design_optimization_is_joint_and_bounded(self):
        shell,design=masks()
        model=DensiCrafterSpinPINOBridge(make_pino(),shell,design)
        for param in model.pino.parameters():
            param.requires_grad_(False)
        c=coeff()
        with torch.no_grad():
            target=model(c)["moments"].detach()
        optimizer=torch.optim.Adam([model.density_logits],lr=.1)
        initial=model(c,reference_cut_moments=target,
                      weights={"mass":1.,"cut_moment_error":3.})["loss"].item()
        for _ in range(7):
            out=model(c,reference_cut_moments=target,
                      weights={"mass":1.,"cut_moment_error":3.})
            optimizer.zero_grad(set_to_none=True)
            out["loss"].backward()
            optimizer.step()
        last=model(c,reference_cut_moments=target,
                   weights={"mass":1.,"cut_moment_error":3.})
        self.assertLess(float(last["loss"]),initial)
        self.assertTrue(bool((last["density"][shell]==1).all()))
        self.assertTrue(bool(torch.isfinite(last["moments"]).all()))

    def test_fail_closed_masks_and_unknown_penalty(self):
        shell,design=masks()
        with self.assertRaisesRegex(ValueError,"overlap"):
            DensiCrafterSpinPINOBridge(make_pino(),shell,shell)
        m=DensiCrafterSpinPINOBridge(make_pino(),shell,design)
        with self.assertRaises(ValueError):
            m(coeff(),weights={"unknown":1})


if __name__=="__main__":
    unittest.main()
