"""M10 opt-in multiscale sparse-detail conditioning for the P-CRAFT Spin-PINO.

The P-CRAFT factorized-FNO/U-FNO remains the primary trunk; the sparse
branch can only reweight its physically supported nonnegative quadrature
atoms. Sparse levels are *features*, not a full 512^3 spectral operator.

No exact continuum/Cherchi teacher values are consumed. Raw fine-grid
material moments are independently computed from the supplied geometry.
"""
from __future__ import annotations

import math

import torch
from torch import Tensor, nn

from .sparse_bridge import sparse_to_pino_grid


def _relative_cell_features(indices: Tensor, values: Tensor,
                            source_resolution: int, level: int,
                            batch_size: int, encoder: nn.Module) -> Tensor:
    """Mass-weighted local bin features without allocating a dense level^3 grid.

    Differentiable w.r.t. material values and model parameters. Sparse indices
    are intentionally immutable integer coordinates (not differentiable).
    """
    if level < 2 or level > source_resolution or source_resolution % level:
        raise ValueError("sparse level must divide source resolution")
    device, dtype = values.device, values.dtype
    material = values[:, 0] * values[:, 1]
    xyzi = indices[:, 1:]
    bins = xyzi // (source_resolution // level)
    linear = ((indices[:, 0] * level + bins[:, 0]) * level
              + bins[:, 1]) * level + bins[:, 2]
    unique, inverse = torch.unique(linear, sorted=True, return_inverse=True)
    bin_batch = torch.div(unique, level ** 3, rounding_mode="floor")
    position = ((xyzi.to(dtype) + 0.5) * (2.0 / source_resolution) - 1.0)
    center = ((bins.to(dtype) + 0.5) * (2.0 / level) - 1.0)
    offset = (position - center) * (level / 2.0)  # inside [-0.5,0.5]
    nbins = unique.numel()
    mass_sum = torch.zeros((nbins,), device=device, dtype=dtype)
    occ_sum = torch.zeros_like(mass_sum)
    rel_sum = torch.zeros((nbins, 3), device=device, dtype=dtype)
    rel_square = torch.zeros_like(rel_sum)
    mass_sum.index_add_(0, inverse, material)
    occ_sum.index_add_(0, inverse, values[:, 1])
    rel_sum.index_add_(0, inverse, offset * material.unsqueeze(-1))
    rel_square.index_add_(0, inverse, offset.square() * material.unsqueeze(-1))
    count = torch.zeros_like(mass_sum)
    count.index_add_(0, inverse, torch.ones_like(material))
    bin_center = torch.stack((
        (unique // (level ** 2)) % level,
        (unique // level) % level,
        unique % level,
    ), dim=-1).to(dtype)
    bin_center = (bin_center + 0.5) * (2.0 / level) - 1.0
    total = torch.zeros((batch_size,), device=device, dtype=dtype)
    total.index_add_(0, bin_batch, mass_sum)
    denom = mass_sum.unsqueeze(-1).clamp_min(1e-16)
    features = torch.cat((
        bin_center,
        rel_sum / denom,
        rel_square / denom,
        (mass_sum / total[bin_batch].clamp_min(1e-16)).unsqueeze(-1),
        (occ_sum / count.clamp_min(1.0)).unsqueeze(-1),
    ), dim=-1)
    assert features.shape[1] == 11
    embed = encoder(features)
    pooled = torch.zeros((batch_size, embed.shape[-1]), dtype=dtype, device=device)
    pooled.index_add_(0, bin_batch, embed * mass_sum.unsqueeze(-1))
    return pooled / total.unsqueeze(-1).clamp_min(1e-16)


class SparseMultiscaleDetail(nn.Module):
    """Pool sparse local material features at several native-coordinate scales."""

    def __init__(self, levels=(16, 32, 64), width: int = 24):
        super().__init__()
        levels = tuple(int(x) for x in levels)
        if not levels or len(set(levels)) != len(levels) or min(levels) < 2:
            raise ValueError("provide distinct positive sparse levels")
        if width < 4:
            raise ValueError("detail width must be >=4")
        self.levels = levels
        self.layers = nn.ModuleList([
            nn.Sequential(nn.Linear(11, width), nn.SiLU(),
                          nn.Linear(width, width), nn.SiLU())
            for _ in levels
        ])
        self.readout = nn.Sequential(nn.Linear(width * len(levels) + 20, width),
                                     nn.SiLU(), nn.Linear(width, width))
        self.width = width

    def forward(self, indices: Tensor, values: Tensor, *,
                source_resolution: int, batch_size: int,
                fine_moments: Tensor, coarse_moments: Tensor):
        if values.dtype not in (torch.float32, torch.float64):
            raise TypeError("sparse detail requires float32 or float64 values")
        if not all(source_resolution % level == 0 for level in self.levels):
            raise ValueError("all sparse levels must divide source resolution")
        per_level = [
            _relative_cell_features(indices, values, source_resolution, level,
                                    batch_size, layer)
            for level, layer in zip(self.levels, self.layers)
        ]
        mass = fine_moments[:, :1].to(dtype=values.dtype).clamp_min(1e-12)
        fine = fine_moments.to(dtype=values.dtype) / mass
        delta = (fine_moments - coarse_moments).to(dtype=values.dtype) / mass
        packed = torch.cat((*per_level, fine, delta), dim=-1)
        out = self.readout(packed)
        if not bool(torch.isfinite(out).all()):
            raise FloatingPointError("nonfinite sparse-detail features")
        return out


class SparseDetailSpinPINO(nn.Module):
    """PINO-primary wrapper with an optional zero-initialized detail gate.

    All predicted r/J flow through the original model's moment/Jacobian
    heads. This modifier cannot introduce quadrature atoms where the PINO
    support mask is exactly zero. The residual is bounded and nonnegative.
    """

    def __init__(self, pino: nn.Module, *, levels=(16, 32, 64),
                 width: int = 24, coarse_grid_size: int = 16):
        super().__init__()
        if coarse_grid_size < 4:
            raise ValueError("coarse grid size must be >=4")
        if not hasattr(pino, "monomials") or not hasattr(pino, "encode_geometry"):
            raise TypeError("P-CRAFT SpinPINO-compatible model required")
        self.pino = pino
        self.coarse_grid_size = coarse_grid_size
        self.sparse_detail = SparseMultiscaleDetail(levels=levels, width=width)
        self.delta_head = nn.Linear(width, int(pino.monomials.shape[0]))
        self.detail_gate = nn.Parameter(torch.zeros(()))

    def encode_sparse(self, indices: Tensor, values: Tensor, *,
                      batch_size: int, source_resolution: int = 512):
        coarse, ledger = sparse_to_pino_grid(
            indices, values, batch_size=batch_size,
            source_resolution=source_resolution,
            pino_grid_size=self.coarse_grid_size,
        )
        pino_weights = self.pino.encode_geometry(coarse)
        local = self.sparse_detail(
            indices, values, source_resolution=source_resolution,
            batch_size=batch_size,
            fine_moments=ledger["fine_ten_moments"],
            coarse_moments=ledger["coarse_ten_moments"],
        )
        # bounded factor in [exp(-2),exp(2)], init = identity, so existing
        # PINO weights and physics identities remain intact at initialization.
        correction = 2.0 * torch.tanh(self.detail_gate) * torch.tanh(self.delta_head(local))
        weights = pino_weights * torch.exp(correction)
        if not bool(torch.isfinite(weights).all()) or bool((weights < 0).any()):
            raise FloatingPointError("invalid sparse-conditioned quadrature")
        diagnostics = dict(ledger)
        diagnostics.update({
            "detail_levels": self.sparse_detail.levels,
            "detail_gate_value": float(torch.tanh(self.detail_gate).detach()),
            "pino_primary_trunk": True,
            "full_resolution_spectral_operator": False,
            "uses_Cherchi_labels": False,
        })
        return weights, diagnostics

    def forward(self, indices: Tensor, values: Tensor, coefficients: Tensor, *,
                batch_size: int, source_resolution: int = 512,
                with_jacobian: bool = False, return_diagnostics: bool = False):
        weights, diagnostics = self.encode_sparse(
            indices, values, batch_size=batch_size,
            source_resolution=source_resolution,
        )
        if coefficients.shape != (batch_size, 10):
            raise ValueError("native coefficients must be [B,10]")
        r = self.pino.moment_from_weights(weights, coefficients)
        J = self.pino.jacobian_from_weights(weights, coefficients) if with_jacobian else None
        if return_diagnostics:
            return r, J, diagnostics
        return (r, J) if with_jacobian else r
