"""CPU only, paired cold-vs-cache geometry/coefficients and sparse 512 bridge."""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import torch

from .m9b_cache import PinnedPINOQueryCache, SourceBoundRotationCache
from .mass_transport import conservative_rotate_geometry
from .sparse_bridge import sparse_to_pino_grid
from .spin_pino import SpinPINO


def _geometry(n=8):
    axis = torch.linspace(-1, 1, n)
    xyz = torch.stack(torch.meshgrid(axis, axis, axis, indexing="ij"), -1)
    occ = (xyz.square().sum(-1) <= .65 ** 2).float()
    return torch.stack((.8 * occ, occ, torch.zeros_like(occ),
                        torch.zeros_like(occ)), 0).unsqueeze(0)


def run(queries=6, source_resolution=512, sparse_records=4096):
    if queries < 2 or sparse_records < 1 or sparse_records > source_resolution ** 3:
        raise ValueError("invalid query or sparse count")
    torch.manual_seed(20261107)
    torch.set_num_threads(1)
    D = _geometry(8)
    angle = .37
    R = torch.tensor([[math.cos(angle), -math.sin(angle), 0.],
                      [math.sin(angle), math.cos(angle), 0.],
                      [0., 0., 1.]], dtype=D.dtype)
    controls = torch.randn((queries, 1, 10))
    model = SpinPINO(
        width=4, modes=2, n_layers=2, grid_size=8,
        points_per_axis=4, hidden_dim=32,
        moment_parameterization="logistic_atom", temperature=.12,
    ).eval()
    cache_rotation = SourceBoundRotationCache()
    cache_pino = PinnedPINOQueryCache(model)
    baseline, cached = [], []
    start = time.perf_counter()
    with torch.no_grad():
        for c in controls:
            rotated, _ = conservative_rotate_geometry(D, R)
            z = model.encode_geometry(rotated)
            baseline.append((
                model.moment_from_weights(z, c),
                model.jacobian_from_weights(z, c),
            ))
    baseline_seconds = time.perf_counter() - start
    start = time.perf_counter()
    with torch.no_grad():
        for c in controls:
            rotated, _, _ = cache_rotation.rotate(D, R)
            r, J, _ = cache_pino.evaluate(rotated, c)
            cached.append((r, J))
    cached_seconds = time.perf_counter() - start
    max_abs_diff = max(
        float(torch.max((x-y).abs()))
        for (r0, J0), (r1, J1) in zip(baseline, cached)
        for x,y in ((r0,r1),(J0,J1))
    )
    if max_abs_diff > 1e-6:
        raise AssertionError("cached predictions differ from independent baseline")
    n = source_resolution
    index = (torch.arange(sparse_records,dtype=torch.long)*10007+701) % (n**3)
    xyz = torch.stack((index//(n*n),(index//n)%n,index%n),-1)
    sparse_indices = torch.cat((torch.zeros((len(index),1),dtype=torch.long),xyz),-1)
    vals = torch.tensor([[0.7, 1., 0., 0.]],dtype=torch.float32).repeat(len(index),1)
    start = time.perf_counter()
    low, ledger = sparse_to_pino_grid(
        sparse_indices, vals, batch_size=1,
        source_resolution=n, pino_grid_size=16,
    )
    sparse_seconds = time.perf_counter()-start
    # 512^3 coordinate domain -> sparse data -> 16^3 reduced bridge ->
    # existing 8^3 PINO trunk/head. This is an interface smoke, NOT a
    # full-resolution spectral-network evaluation or trained prediction.
    start = time.perf_counter()
    with torch.no_grad():
        sparse_z = model.encode_geometry(low)
        sparse_r = model.moment_from_weights(sparse_z, controls[0])
        sparse_J = model.jacobian_from_weights(sparse_z, controls[0])
    sparse_pino_seconds = time.perf_counter()-start
    if (sparse_r.shape != (1,10) or sparse_J.shape != (1,10,10)
            or not bool(torch.isfinite(sparse_r).all() and torch.isfinite(sparse_J).all())):
        raise AssertionError("sparse-to-reduced-PINO head contract failed")
    return {
        "schema": "SPIN_PINO_M9B_CACHE_AND_SPARSE_BRIDGE_V1",
        "benchmark": "fixed 8^3 geometry/R, different coefficients; CPU single-thread, no neural training",
        "queries": queries,
        "baseline_total_seconds": baseline_seconds,
        "cached_total_seconds": cached_seconds,
        "measured_speed_ratio": baseline_seconds/max(cached_seconds,1e-12),
        "max_abs_r_J_difference": max_abs_diff,
        "geometry_cache_hits": cache_rotation.hits,
        "geometry_cache_misses": cache_rotation.misses,
        "pino_cache_hits": cache_pino.hits,
        "pino_cache_misses": cache_pino.misses,
        "sparse_source_resolution": n,
        "sparse_records": sparse_records,
        "sparse_bridge_seconds": sparse_seconds,
        "sparse_to_reduced_pino_forward_seconds": sparse_pino_seconds,
        "sparse_reduced_pino_head_contract": True,
        "model_internal_pino_grid_size": 8,
        "coarse_grid_shape": list(low.shape),
        "coarse_grid_allocated_bytes": low.numel()*low.element_size(),
        "sparse_raw_input_bytes": sparse_indices.numel()*sparse_indices.element_size()+vals.numel()*vals.element_size(),
        "mass_error_relative": ledger["relative_mass_error_max"],
        "moment_drift_relative_l2": ledger["relative_ten_moment_drift_max"],
        "full_resolution_dense_allocated": False,
        "full_resolution_PINO_training": False,
        "model_trained_on_Cherchi": False,
        "native_Spin_Newton_admitted": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queries", type=int, default=6)
    p.add_argument("--source-resolution", type=int, default=512)
    p.add_argument("--sparse-records", type=int, default=4096)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(a.queries, a.source_resolution, a.sparse_records)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
