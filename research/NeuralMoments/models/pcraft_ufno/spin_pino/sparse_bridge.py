"""M9b sparse 512^3 ingestion contract for the existing PINO trunk.

This first-stage bridge never allocates a dense high-resolution volume.
It conserves *discrete cell-centered mass* when coarsening a sparse,
nonnegative material point list. The output is a low-resolution input to
the existing P-CRAFT/PINO encoder, NOT a 512^3 spectral computation.
Fine ten-moment diagnostics are retained separately to expose lost detail.

Sparse records list ALL nonzero material cells; unspecified cells are zero.
SDF/boundary values are intentionally NOT inferred from incomplete samples.
"""
from __future__ import annotations

import torch
from torch import Tensor


def _features(x: Tensor) -> Tensor:
    a, b, c = x.unbind(-1)
    return torch.stack((
        torch.ones_like(a), a, b, c, a*a, b*b, c*c,
        b*c, a*c, a*b,
    ), dim=-1)


def sparse_to_pino_grid(
    indices: Tensor,
    values: Tensor,
    *,
    batch_size: int,
    source_resolution: int = 512,
    pino_grid_size: int = 16,
) -> tuple[Tensor, dict]:
    """Sparse [N,4] (batch,i,j,k) + [N,4] rho/occ/proxies -> [B,4,g,g,g].

    Auxiliary channels must be zero for the first sparse material-only
    contract. Nonzero SDF/boundary samples are rejected instead of silently
    fabricating unknown values in unlisted empty cells.
    """
    if (not isinstance(batch_size, int) or batch_size < 1
            or not isinstance(source_resolution, int) or source_resolution < 8
            or not isinstance(pino_grid_size, int) or pino_grid_size < 4
            or source_resolution % pino_grid_size):
        raise ValueError("invalid batch/resolution; source must be divisible by PINO grid")
    if not isinstance(indices, Tensor) or not isinstance(values, Tensor):
        raise TypeError("indices and values must be tensors")
    if indices.ndim != 2 or indices.shape[1] != 4 or indices.dtype != torch.long:
        raise ValueError("indices must have shape [N,4] and int64 dtype")
    if values.shape != indices.shape or not values.is_floating_point():
        raise ValueError("values must be floating [N,4]")
    if indices.shape[0] == 0 or indices.device != values.device:
        raise ValueError("nonempty same-device sparse input is required")
    if not bool(torch.isfinite(values).all()):
        raise ValueError("nonfinite sparse input")
    if bool(((values[:, :2] < 0) | (values[:, :2] > 1)).any()):
        raise ValueError("rho/occupancy must be in [0,1]")
    if bool((values[:, 2:] != 0).any()):
        raise ValueError("sparse SDF/boundary requires an explicit full-field contract")
    n = source_resolution
    B = batch_size
    if bool(((indices[:, 0] < 0) | (indices[:, 0] >= B)).any()):
        raise ValueError("invalid batch indices")
    if bool(((indices[:, 1:] < 0) | (indices[:, 1:] >= n)).any()):
        raise ValueError("source voxel coordinates outside declared resolution")
    source_key = (((indices[:, 0] * n + indices[:, 1]) * n
                    + indices[:, 2]) * n + indices[:, 3])
    if torch.unique(source_key).numel() != indices.shape[0]:
        raise ValueError("duplicate source voxel would double-count material")

    # Sum occupancy and material jointly, NOT mean(rho)*mean(occ):
    # joint averaging preserves the discrete material measure.
    g = pino_grid_size
    factor = n // g
    gijk = indices[:, 1:] // factor
    coarse_key = (((indices[:, 0] * g + gijk[:, 0]) * g
                   + gijk[:, 1]) * g + gijk[:, 2])
    occ = values[:, 1].to(torch.float64)
    mass = values[:, 0].to(torch.float64) * occ
    N = B * g ** 3
    coarse_occ = torch.zeros(N, dtype=torch.float64, device=values.device)
    coarse_mass = torch.zeros_like(coarse_occ)
    coarse_occ.scatter_add_(0, coarse_key, occ)
    coarse_mass.scatter_add_(0, coarse_key, mass)
    cell_count = float(factor ** 3)
    coarse_occ = coarse_occ.reshape(B, g, g, g) / cell_count
    coarse_mass = coarse_mass.reshape(B, g, g, g) / cell_count
    coarse_rho = torch.where(
        coarse_occ > 0, coarse_mass / coarse_occ.clamp_min(1e-30),
        torch.zeros_like(coarse_occ),
    )
    coarse = torch.zeros(
        (B, 4, g, g, g), dtype=values.dtype, device=values.device,
    )
    coarse[:, 0] = coarse_rho.to(values.dtype)
    coarse[:, 1] = coarse_occ.to(values.dtype)

    # Independent ten-moment ledger at actual 512^3 cell-centre locations,
    # without ever making a 512^3 tensor.
    coord = (indices[:, 1:].to(torch.float64) + 0.5) * (2.0 / n) - 1.0
    phi = _features(coord)
    fine = torch.zeros((B, 10), dtype=torch.float64, device=values.device)
    fine.scatter_add_(
        0, indices[:, 0, None].expand(-1, 10),
        (mass * (2.0 / n) ** 3).unsqueeze(-1) * phi,
    )
    coords_g = (torch.arange(g, dtype=torch.float64, device=values.device)
                + 0.5) * (2.0 / g) - 1.0
    grid_g = torch.stack(
        torch.meshgrid(coords_g, coords_g, coords_g, indexing="ij"), dim=-1,
    ).reshape(-1, 3)
    coarse_phi = _features(grid_g)
    coarse_material = (coarse[:, 0].to(torch.float64)
                       * coarse[:, 1].to(torch.float64)).flatten(1)
    coarse_moments = (coarse_material @ coarse_phi) * (2.0 / g) ** 3
    if bool((fine[:, 0] <= 0).any()):
        raise ValueError("each sample must have positive material mass")
    mass_error = ((fine[:, 0] - coarse_moments[:, 0]).abs()
                  / fine[:, 0].clamp_min(1e-30))
    if bool((mass_error > 2e-5).any()):
        raise ArithmeticError("coarsening did not conserve discrete mass")
    moment_drift = (
        torch.linalg.vector_norm(fine - coarse_moments, dim=-1)
        / torch.linalg.vector_norm(fine, dim=-1).clamp_min(1e-30)
    )
    ledger = {
        "source_resolution": n,
        "pino_grid_size": g,
        "sparse_records": int(indices.shape[0]),
        "dense_512_allocated": False,
        "full_resolution_spectral_operator": False,
        "fine_ten_moments": fine.detach(),
        "coarse_ten_moments": coarse_moments.detach(),
        "relative_mass_error_max": float(mass_error.max()),
        "relative_ten_moment_drift_max": float(moment_drift.max()),
    }
    return coarse, ledger
