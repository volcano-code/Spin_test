"""P30 mechanism and model-internal derivative tests; no native teacher claim."""
import copy
import unittest
import torch
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO, SpinPINOLoss
from research.NeuralMoments.models.pcraft_ufno.spin_pino.material_core import (
    MaterialAwareSpinPINO, MaterialSliceMixer, material_fields, scale_context,
)

CONFIG = dict(width=4, modes=2, n_layers=2, grid_size=8,
              points_per_axis=4, hidden_dim=16, temperature=.12,
              moment_parameterization="logistic_atom")


def geometry(batch=2, n=8):
    torch.manual_seed(51)
    occ = (torch.rand(batch, 1, n, n, n) > .3).float()
    rho = .3 + .7 * torch.rand_like(occ)
    return torch.cat((rho, occ, torch.zeros_like(occ), torch.zeros_like(occ)), 1)


class MaterialCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def setUp(self):
        torch.manual_seed(73)

    def models(self, checkpoint=False):
        config = {**CONFIG, 'use_gradient_checkpoint': checkpoint}
        base = SpinPINO(**config)
        model = MaterialAwareSpinPINO(**config, slices=4)
        model.load_baseline(base)
        return base, model

    def open_gates(self, model):
        with torch.no_grad():
            for mix in model.encoder.mixers.values():
                mix.gate.fill_(.3)

    def test_zero_gates_preserve_baseline_moments_and_jacobian(self):
        base, model = self.models()
        d, c = geometry(), torch.randn(2, 10)
        with torch.no_grad():
            r0, j0 = base(d, c, with_jacobian=True)
            r1, j1 = model(d, c, with_jacobian=True)
        self.assertTrue(torch.equal(r0, r1))
        self.assertTrue(torch.equal(j0, j1))

    def test_baseline_checkpoint_remains_strict_loadable(self):
        base, _ = self.models()
        another = SpinPINO(**CONFIG)
        another.load_state_dict(base.state_dict(), strict=True)

    def test_changed_temperature_is_rejected(self):
        base, _ = self.models()
        model = MaterialAwareSpinPINO(**{**CONFIG, 'temperature': .2})
        with self.assertRaises(ValueError):
            model.load_baseline(base)

    def test_no_extra_external_encoder_is_enabled(self):
        _, model = self.models()
        self.assertIsNone(model.transolver_plus_adapter)
        self.assertIsNone(model.geometry_plugin)
        with self.assertRaises(ValueError):
            MaterialAwareSpinPINO(geometry_adapter='transolver_plus')

    def test_material_product_is_formed_before_pooling(self):
        d = torch.zeros(1, 4, 4, 4, 4)
        d[:, 0, :2] = 1
        d[:, 1, 2:] = 1
        ctx = scale_context(material_fields(d), (2, 2, 2))
        self.assertEqual(float(ctx[:, 0].sum()), 0.)

    def test_partition_mass_sum_and_empty_support_are_finite(self):
        mix = MaterialSliceMixer(4, 4)
        hidden = torch.randn(2, 4, 8, 8, 8)
        ctx = scale_context(material_fields(torch.zeros(2, 4, 8, 8, 8)), (8,8,8))
        delta = mix.increment(hidden, ctx)
        self.assertTrue(torch.isfinite(delta).all())
        self.assertEqual(float(delta.abs().max()), 0.)

    def test_weighted_latent_increment_has_zero_material_mean(self):
        d = geometry()
        ctx = scale_context(material_fields(d), (8,8,8))
        mix = MaterialSliceMixer(4, 5)
        delta = mix.increment(torch.randn(2,4,8,8,8), ctx)
        mean = (delta * ctx[:, :1]).sum((2,3,4)) / ctx[:, :1].sum((2,3,4))
        self.assertLess(float(mean.abs().max()), 1e-7)

    def test_increment_is_zero_at_vacuum_voxels(self):
        d = geometry()
        ctx = scale_context(material_fields(d), (8,8,8))
        delta = MaterialSliceMixer(4, 5).increment(torch.randn(2,4,8,8,8), ctx)
        void = (ctx[:, :1] == 0).expand_as(delta)
        self.assertEqual(float(delta[void].abs().max()), 0.)

    def test_void_hidden_values_do_not_change_material_message(self):
        d = geometry()
        ctx = scale_context(material_fields(d), (8,8,8))
        h = torch.randn(2,4,8,8,8)
        changed = torch.where((ctx[:, :1] == 0).expand_as(h), h + 100, h)
        mix = MaterialSliceMixer(4, 5)
        self.assertTrue(torch.allclose(mix.increment(h,ctx), mix.increment(changed,ctx), atol=1e-7))

    def test_same_parameter_uniform_control_is_available(self):
        a, b = MaterialSliceMixer(4, 4), MaterialSliceMixer(4, 4, measure='uniform')
        self.assertEqual(sum(p.numel() for p in a.parameters()), sum(p.numel() for p in b.parameters()))
        b.load_state_dict(a.state_dict(), strict=True)

    def test_active_core_changes_moments(self):
        base, model = self.models()
        self.open_gates(model)
        d, c = geometry(), torch.randn(2,10)
        self.assertGreater(float((base(d,c)-model(d,c)).abs().max()), 1e-7)

    def test_density_and_internal_parameters_receive_gradients(self):
        _, model = self.models()
        self.open_gates(model)
        d = geometry().requires_grad_(True)
        model(d, torch.randn(2,10)).square().sum().backward()
        self.assertTrue(torch.isfinite(d.grad).all())
        self.assertGreater(float(d.grad[:,0].abs().sum()), 0.)
        for mix in model.encoder.mixers.values():
            self.assertIsNotNone(mix.assignment.weight.grad)
            self.assertTrue(torch.isfinite(mix.assignment.weight.grad).all())
            self.assertGreater(float(mix.assignment.weight.grad.abs().sum()), 0.)

    def test_zero_initialized_gates_have_learning_signal(self):
        _, model = self.models()
        model(geometry(), torch.randn(2,10)).square().sum().backward()
        self.assertTrue(any(float(m.gate.grad.abs()) > 0 for m in model.encoder.mixers.values()))

    def test_material_weights_nonnegative_and_empty_geometry_zero(self):
        _, model = self.models()
        self.open_gates(model)
        w = model.encode_geometry(geometry())
        self.assertTrue((w >= 0).all())
        empty = model(torch.zeros(1,4,8,8,8), torch.ones(1,10))
        self.assertEqual(float(empty.abs().max()), 0.)

    def test_cached_queries_equal_full_forward(self):
        _, model = self.models()
        self.open_gates(model)
        d, c = geometry(), torch.randn(2,10)
        w = model.encode_geometry(d)
        self.assertTrue(torch.equal(model.moment_from_weights(w,c), model(d,c)))
        self.assertTrue(torch.equal(model.moment_from_weights(w,-c), model(d,-c)))

    def test_logistic_jacobian_matches_autodiff_and_finite_difference(self):
        _, model = self.models()
        self.open_gates(model)
        w = model.encode_geometry(geometry(batch=1)).detach().double()
        c = torch.randn(1,10,dtype=torch.double)
        analytic = model.jacobian_from_weights(w,c)[0]
        auto = torch.autograd.functional.jacobian(lambda z:model.moment_from_weights(w,z),c)[0,:,0,:]
        self.assertTrue(torch.allclose(analytic, auto, atol=1e-10, rtol=1e-9))
        columns=[]
        for i in range(10):
            step=torch.zeros_like(c);step[0,i]=1e-5
            columns.append(((model.moment_from_weights(w,c+step)-model.moment_from_weights(w,c-step))/(2e-5))[0])
        fd=torch.stack(columns,dim=-1)
        self.assertLess(float((analytic-fd).norm()/analytic.norm()), 1e-7)

    def test_complement_positive_scale_and_radial_identity(self):
        _, model = self.models()
        self.open_gates(model)
        w = model.encode_geometry(geometry()).detach().double()
        c = torch.randn(2,10,dtype=torch.double)
        r = model.moment_from_weights(w,c)
        full=w @ model.monomials.double()
        self.assertTrue(torch.allclose(r+model.moment_from_weights(w,-c),full,atol=1e-10))
        self.assertTrue(torch.allclose(r,model.moment_from_weights(w,3.7*c),atol=1e-10))
        self.assertLess(float(torch.bmm(model.jacobian_from_weights(w,c),c.unsqueeze(-1)).abs().max()), 1e-10)

    def test_checkpoint_recomputation_matches_outputs_and_gradients(self):
        _, plain = self.models()
        _, checked = self.models(checkpoint=True)
        self.open_gates(plain)
        checked.load_state_dict(plain.state_dict(),strict=True)
        a=geometry().requires_grad_(True); b=a.detach().clone().requires_grad_(True)
        c=torch.randn(2,10)
        x=plain(a,c); y=checked(b,c)
        x.square().sum().backward();y.square().sum().backward()
        self.assertTrue(torch.equal(x,y))
        self.assertTrue(torch.allclose(a.grad,b.grad,atol=1e-6,rtol=1e-5))
        for (na,pa),(nb,pb) in zip(plain.named_parameters(),checked.named_parameters()):
            self.assertEqual(na,nb)
            if pa.grad is not None:
                self.assertTrue(torch.allclose(pa.grad,pb.grad,atol=1e-6,rtol=1e-5),na)

    def test_invalid_geometry_and_shape_are_rejected(self):
        d=geometry();d[:,0]=-1
        with self.assertRaises(ValueError): material_fields(d)
        with self.assertRaises(ValueError):
            MaterialSliceMixer(4)(torch.ones(1,4,4,4,4),torch.ones(1,7,4,4,4))


if __name__ == '__main__':
    unittest.main(verbosity=2)
