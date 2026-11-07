"""M10: prove source-grid detail reaches P-CRAFT PINO, without 512^3 dense."""
import unittest

import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.m10_sparse_detail import (
    SparseDetailSpinPINO,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.sparse_bridge import (
    sparse_to_pino_grid,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.spin_pino import SpinPINO


def _pino(grid=8):
    torch.manual_seed(123)
    return SpinPINO(width=4, modes=2, n_layers=2, grid_size=grid,
                    hidden_dim=32, points_per_axis=4,
                    moment_parameterization="logistic_atom", temperature=.12)


def _same_coarse_different_fine(n=32, shift=0):
    """Every 8^3 parent bin has identical rho/occ, but source positions move."""
    g = 8
    i = torch.arange(g, dtype=torch.long)
    parents = torch.stack(torch.meshgrid(i, i, i, indexing="ij"), -1).reshape(-1, 3)
    source = parents * (n // g) + shift
    idx = torch.cat((torch.zeros((len(source), 1), dtype=torch.long), source), -1)
    values = torch.tensor([[.8, 1., 0., 0.]]).repeat(len(idx), 1)
    return idx, values


def _sparse_512(records=4096):
    n = 512
    flat = (torch.arange(records, dtype=torch.long) * 10007 + 701) % n**3
    xyz = torch.stack((flat // (n*n), (flat // n) % n, flat % n), -1)
    idx = torch.cat((torch.zeros((len(flat),1), dtype=torch.long), xyz), -1)
    v = torch.tensor([[.8,1.,0.,0.]]).repeat(records,1)
    return idx,v


class SparseDetailM10Tests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_zero_gate_exact_original_pino_r_and_j(self):
        base = _pino()
        candidate = SparseDetailSpinPINO(
            base, levels=(8,16), width=16, coarse_grid_size=8
        ).eval()
        idx, vals = _same_coarse_different_fine()
        coarse, ledger = sparse_to_pino_grid(
            idx, vals, batch_size=1, source_resolution=32, pino_grid_size=8
        )
        c = torch.randn((1,10))
        with torch.no_grad():
            r, J = candidate(idx, vals, c, batch_size=1,
                             source_resolution=32, with_jacobian=True)
            r0, J0 = base(coarse, c, with_jacobian=True)
        self.assertTrue(torch.equal(r, r0))
        self.assertTrue(torch.equal(J, J0))
        self.assertEqual(float(candidate.detail_gate),0.)
        self.assertLess(ledger["relative_mass_error_max"], 1e-6)

    def test_identical_coarse_grid_distinct_fine_features_reach_pino_head(self):
        candidate = SparseDetailSpinPINO(
            _pino(), levels=(8,16), width=32, coarse_grid_size=8
        ).eval()
        a, va = _same_coarse_different_fine(32,shift=0)
        b, vb = _same_coarse_different_fine(32,shift=3)
        ca,_ = sparse_to_pino_grid(a,va,batch_size=1,
                                   source_resolution=32,pino_grid_size=8)
        cb,_ = sparse_to_pino_grid(b,vb,batch_size=1,
                                   source_resolution=32,pino_grid_size=8)
        self.assertTrue(torch.equal(ca,cb), "coarse PINO inputs must be identical")
        with torch.no_grad():
            candidate.detail_gate.fill_(1.5)
            wa,da = candidate.encode_sparse(a,va,batch_size=1,source_resolution=32)
            wb,db = candidate.encode_sparse(b,vb,batch_size=1,source_resolution=32)
        self.assertGreater(float((da["fine_ten_moments"]-
                                  db["fine_ten_moments"]).abs().max()),1e-4)
        self.assertGreater(float((wa-wb).abs().max()),1e-10)
        self.assertTrue(bool((wa>=0).all() and (wb>=0).all()))
        self.assertEqual(da["detail_levels"],(8,16))

    def test_sparse_512_pipeline_is_finite_but_not_full_512_pino(self):
        candidate = SparseDetailSpinPINO(
            _pino(), levels=(16,32,64), width=16, coarse_grid_size=16
        ).eval()
        idx, vals = _sparse_512()
        c = torch.randn((1,10))
        with torch.no_grad():
            r,J,stats = candidate(idx,vals,c,batch_size=1,
                                   source_resolution=512,
                                   with_jacobian=True,return_diagnostics=True)
        self.assertEqual(r.shape,(1,10))
        self.assertEqual(J.shape,(1,10,10))
        self.assertTrue(bool(torch.isfinite(r).all() and torch.isfinite(J).all()))
        self.assertEqual(stats["sparse_records"],4096)
        self.assertFalse(stats["dense_512_allocated"])
        self.assertFalse(stats["full_resolution_spectral_operator"])
        self.assertTrue(stats["pino_primary_trunk"])
        self.assertEqual(candidate.pino.encoder.grid_size,8)

    def test_physics_head_identity_preserved_with_active_detail(self):
        candidate = SparseDetailSpinPINO(
            _pino(), levels=(8,16), width=16, coarse_grid_size=8
        ).eval()
        idx,vals = _same_coarse_different_fine()
        with torch.no_grad():
            candidate.detail_gate.fill_(1.0)
            w,stats = candidate.encode_sparse(
                idx,vals,batch_size=1,source_resolution=32)
            c = torch.randn(1,10)
            r = candidate.pino.moment_from_weights(w,c)
            rneg = candidate.pino.moment_from_weights(w,-c)
            full = w @ candidate.pino.monomials
            J = candidate.pino.jacobian_from_weights(w,c)
        self.assertLess(float((r+rneg-full).abs().max()),1e-5)
        self.assertLess(float((J @ c.unsqueeze(-1)).abs().max()),1e-5)
        self.assertTrue(bool((w>=0).all()))

    def test_gradients_reach_sparse_detail_gate_and_trainable_encoder(self):
        candidate = SparseDetailSpinPINO(
            _pino(), levels=(8,16), width=16, coarse_grid_size=8
        ).train()
        idx, vals = _same_coarse_different_fine()
        r = candidate(idx,vals,torch.tensor(
            [[.2,.1,-.2,.7,.1,0.,0.,0.,0.,0.]]),
            batch_size=1,source_resolution=32)
        r.sum().backward()
        self.assertIsNotNone(candidate.detail_gate.grad)
        self.assertTrue(torch.isfinite(candidate.detail_gate.grad))
        self.assertTrue(bool(torch.isfinite(candidate.pino.weight_head[-1].weight.grad).all()))

    def test_invalid_levels_and_bad_sparse_source_fail_closed(self):
        with self.assertRaises(ValueError):
            SparseDetailSpinPINO(_pino(),levels=(16,16))
        model = SparseDetailSpinPINO(_pino(),levels=(8,16),coarse_grid_size=8)
        idx,vals = _same_coarse_different_fine()
        with self.assertRaises(ValueError):
            model.encode_sparse(idx,vals,batch_size=1,source_resolution=30)
        with self.assertRaisesRegex(ValueError,"duplicate"):
            model.encode_sparse(idx[:1].repeat(2,1),vals[:1].repeat(2,1),
                                batch_size=1,source_resolution=32)


if __name__=="__main__":
    unittest.main()
