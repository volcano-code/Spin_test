"""M9b tests: fail-closed cache state and discrete sparse 512^3 input."""
import math
import unittest

import torch
from torch import nn

from research.NeuralMoments.models.pcraft_ufno.spin_pino.m9b_cache import (
    PinnedPINOQueryCache, SourceBoundRotationCache,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.sparse_bridge import (
    sparse_to_pino_grid,
)


def ball(n=8):
    ax = torch.linspace(-1.0, 1.0, n)
    xyz = torch.stack(torch.meshgrid(ax, ax, ax, indexing="ij"), -1)
    occ = (xyz.square().sum(-1) <= 0.6 ** 2).float()
    return torch.stack((0.8 * occ, occ, torch.zeros_like(occ),
                        torch.zeros_like(occ)), 0).unsqueeze(0)


def rot_z(angle):
    c, s = math.cos(angle), math.sin(angle)
    return torch.tensor([[c, -s, 0], [s, c, 0], [0, 0, 1]],
                        dtype=torch.float32)


class TinyMomentModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.gain = nn.Parameter(torch.tensor(1.75))
        self.encode_calls = 0

    def encode_geometry(self, D):
        self.encode_calls += 1
        return D[:, 0].mean((1, 2, 3)).unsqueeze(1) * self.gain

    def moment_from_weights(self, z, c):
        return z * c

    def jacobian_from_weights(self, z, c):
        return torch.diag_embed(z.expand_as(c))


class M9bCacheContracts(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_model_scalar_parameter_and_batched_coefficient_reuse(self):
        model = TinyMomentModel().eval()
        cache = PinnedPINOQueryCache(model)
        D = ball()
        c1 = torch.randn(1, 10)
        c2 = torch.randn(1, 10)
        with torch.no_grad():
            r1, j1, a = cache.evaluate(D, c1)
            r2, j2, b = cache.evaluate(D, c2)
        self.assertFalse(a["geometry_hit"])
        self.assertTrue(b["geometry_hit"])
        self.assertEqual(model.encode_calls, 1)
        self.assertTrue(torch.allclose(r2, model.moment_from_weights(model.encode_geometry(D), c2)))
        self.assertTrue(torch.allclose(j1, j2))
        self.assertEqual(cache.hits, 1)

    def test_mutating_model_rejected_not_stale(self):
        model = TinyMomentModel().eval()
        cache = PinnedPINOQueryCache(model)
        with torch.no_grad():
            cache.evaluate(ball(), torch.ones(1, 10))
            model.gain.add_(0.1)
            with self.assertRaisesRegex(RuntimeError, "mutated"):
                cache.evaluate(ball(), torch.ones(1, 10))

    def test_mutating_geometry_and_cached_result_is_safe(self):
        D = ball()
        R = rot_z(0.37)
        cache = SourceBoundRotationCache(max_entries=2)
        with torch.no_grad():
            first, _, hit1 = cache.rotate(D, R)
            second, _, hit2 = cache.rotate(D, R)
            first.zero_()
            third, _, hit3 = cache.rotate(D, R)
            D[:, 0, 3, 3, 3] = 0.2
            fourth, _, hit4 = cache.rotate(D, R)
        self.assertEqual([hit1, hit2, hit3, hit4], [False, True, True, False])
        self.assertTrue(torch.equal(second, third))
        self.assertTrue(torch.isfinite(fourth).all())
        self.assertEqual(cache.entries, 2)

    def test_cache_does_not_train_or_backpropagate(self):
        model = TinyMomentModel().train()
        with self.assertRaises(ValueError):
            PinnedPINOQueryCache(model)
        model.eval()
        cache = PinnedPINOQueryCache(model)
        with self.assertRaisesRegex(RuntimeError, "no_grad"):
            cache.evaluate(ball(), torch.ones(1, 10))
        rotation_cache = SourceBoundRotationCache()
        with self.assertRaisesRegex(RuntimeError, "no_grad"):
            rotation_cache.rotate(ball(), rot_z(0.37))


class SparseBridgeContracts(unittest.TestCase):
    def test_sparse_512_no_full_dense_allocation(self):
        n = 512
        ix = (torch.arange(4096, dtype=torch.int64) * 10007 + 701) % n**3
        coords = torch.stack((ix // (n*n), (ix // n) % n, ix % n), -1)
        indices = torch.cat((torch.zeros((ix.numel(), 1), dtype=torch.int64), coords), -1)
        values = torch.tensor([[0.7, 1., 0., 0.]], dtype=torch.float32).repeat(len(ix), 1)
        coarse, ledger = sparse_to_pino_grid(
            indices, values, batch_size=1, source_resolution=n, pino_grid_size=16
        )
        self.assertEqual(tuple(coarse.shape), (1,4,16,16,16))
        self.assertFalse(ledger["dense_512_allocated"])
        self.assertFalse(ledger["full_resolution_spectral_operator"])
        self.assertLess(ledger["relative_mass_error_max"], 1e-6)
        self.assertEqual(ledger["sparse_records"], len(ix))
        self.assertTrue(bool((coarse[:, :2] >= 0).all() and (coarse[:, :2] <= 1).all()))
        self.assertLess(coarse.numel() * coarse.element_size(), 100000)

    def test_no_coarsening_preserves_all_ten_cell_moments(self):
        n = 8
        ax = torch.arange(n, dtype=torch.long)
        xyz = torch.stack(torch.meshgrid(ax, ax, ax, indexing="ij"), -1).reshape(-1,3)
        indices = torch.cat((torch.zeros((xyz.shape[0],1),dtype=torch.long),xyz),-1)
        values = torch.zeros((len(xyz),4))
        values[:,0] = (xyz[:,0] % 3 + 1).float() / 4
        values[:,1] = (xyz[:,1] % 2 + 1).float() / 2
        coarse, ledger = sparse_to_pino_grid(
            indices, values, batch_size=1, source_resolution=n, pino_grid_size=n
        )
        self.assertTrue(torch.allclose(coarse[0,0].flatten(), values[:,0], atol=1e-6))
        self.assertTrue(torch.allclose(coarse[0,1].flatten(), values[:,1], atol=1e-6))
        self.assertTrue(torch.allclose(ledger["fine_ten_moments"],
                                       ledger["coarse_ten_moments"], atol=1e-6))

    def test_duplicate_oob_and_ambiguous_proxy_fail_closed(self):
        index = torch.tensor([[0, 2, 3, 4]], dtype=torch.long)
        vals = torch.tensor([[0.8, 1., 0., 0.]])
        opts = dict(batch_size=1, source_resolution=512, pino_grid_size=16)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            sparse_to_pino_grid(index.repeat(2,1), vals.repeat(2,1), **opts)
        bad = index.clone(); bad[0,1] = 512
        with self.assertRaisesRegex(ValueError, "outside"):
            sparse_to_pino_grid(bad, vals, **opts)
        vals[0,2] = .1
        with self.assertRaisesRegex(ValueError, "SDF"):
            sparse_to_pino_grid(index, vals, **opts)

    def test_multiple_batches_and_nonnegative_gradient(self):
        inds = torch.tensor([[0,1,1,1],[0,2,2,2],[1,3,3,3],[1,4,4,4]],dtype=torch.long)
        vals = torch.tensor([[0.3, 1., 0., 0.],[0.6,.5,0.,0.],
                             [0.5,1.,0.,0.],[0.8,.7,0.,0.]],requires_grad=True)
        coarse, ledger = sparse_to_pino_grid(
            inds, vals, batch_size=2, source_resolution=8, pino_grid_size=4
        )
        self.assertEqual(coarse.shape[0],2)
        self.assertLess(ledger["relative_mass_error_max"],1e-5)
        (coarse[:,0]*coarse[:,1]).sum().backward()
        self.assertIsNotNone(vals.grad)
        self.assertTrue(bool(torch.isfinite(vals.grad).all()))


if __name__ == "__main__":
    unittest.main()
