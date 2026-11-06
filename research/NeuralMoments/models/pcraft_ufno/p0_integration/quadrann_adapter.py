"""QuadrANN point-cloud weighting adapter; moment-only, no Jacobian."""

from __future__ import annotations

from typing import Sequence

import torch
from torch import Tensor

from .contracts import MomentQuadratureResult, raw_monomials


def _as_batch_scalar(name: str, value, batch: int, *, device, dtype) -> Tensor:
    result = torch.as_tensor(value, device=device, dtype=dtype)
    if result.ndim == 0:
        result = result.expand(batch)
    if result.shape != (batch,) or not bool(torch.isfinite(result).all()):
        raise ValueError(f"{name} must be a finite scalar or [B] tensor")
    return result


def quadrature_moments(
    points: Tensor,
    density: Tensor,
    domain_measure,
    weights: Tensor,
    *,
    source: str = "QuadrANN",
) -> MomentQuadratureResult:
    """Integrate raw moments from points, positive learned weights and known measure.

    points are world-space coordinates sampled uniformly from the cut domain.
    domain_measure must come from an independent measure estimator/reference;
    it is never inferred from the learned weights. The learned weights only
    redistribute the sampled points. This returns r_D only; J_D is withheld.
    """
    if points.ndim != 3 or points.shape[-1] != 3:
        raise ValueError("points must have shape [B,N,3]")
    batch, count, _ = points.shape
    if count < 2:
        raise ValueError("at least two quadrature points are required")
    if density.shape == (batch, count, 1):
        density = density.squeeze(-1)
    if density.shape != (batch, count):
        raise ValueError("density must have shape [B,N] or [B,N,1]")
    if weights.shape != (batch, count):
        raise ValueError("weights must have shape [B,N]")
    density = density.to(device=points.device, dtype=points.dtype)
    weights = weights.to(device=points.device, dtype=points.dtype)
    for name, tensor in (("points", points), ("density", density), ("weights", weights)):
        if not tensor.is_floating_point() or not bool(torch.isfinite(tensor).all()):
            raise ValueError(f"{name} must be finite floating-point data")
    if bool((density < 0).any()) or bool((weights < 0).any()):
        raise ValueError("density and quadrature weights must be nonnegative")
    weight_sum = weights.sum(dim=-1, keepdim=True)
    if bool((weight_sum <= 0).any()):
        raise ValueError("each point cloud must have positive total weight")
    weights = weights / weight_sum
    measure = _as_batch_scalar("domain_measure", domain_measure, batch,
                               device=points.device, dtype=points.dtype)
    if bool((measure <= 0).any()):
        raise ValueError("domain_measure must be positive")
    basis = raw_monomials(points)
    moments = measure[:, None] * (weights[..., None] * density[..., None] * basis).sum(dim=1)
    return MomentQuadratureResult(
        moments=moments,
        jacobian=None,
        uncertainty=None,
        source=source,
        derivative_status="WITHHELD_QUADRANN_HAS_NO_CERTIFIED_JACOBIAN",
        training_admitted=False,
    )


class QuadrANNWeightAdapter(torch.nn.Module):
    """Thin wrapper around the pinned MIT upstream QuadrANN model core."""

    def __init__(
        self,
        model: torch.nn.Module | None = None,
        *,
        num_gnn_layers: int = 3,
        k_neighbors: int = 16,
        pe_abs: int = 3,
        pe_rel: int = 5,
        hidden_dim: int = 64,
        final_hidden_dim: int = 128,
    ):
        super().__init__()
        if model is None:
            try:
                from .third_party.quadrann_core import QuadrANN
            except ImportError as exc:
                raise RuntimeError(
                    "QuadrANN requires torch-geometric and torch-scatter; "
                    "install p0_integration/requirements-quadrann.txt"
                ) from exc
            model = QuadrANN(
                dim=3,
                num_gnn_layers=num_gnn_layers,
                k_neighbors=k_neighbors,
                pe_abs=pe_abs,
                pe_rel=pe_rel,
                hidden_dim=hidden_dim,
                final_hidden_dim=final_hidden_dim,
            )
        self.model = model

    def forward(self, points_world: Tensor, density: Tensor, domain_measure, *,
                lower: Sequence[float] = (-1.0, -1.0, -1.0),
                upper: Sequence[float] = (1.0, 1.0, 1.0)) -> MomentQuadratureResult:
        lo = torch.as_tensor(lower, dtype=points_world.dtype, device=points_world.device)
        hi = torch.as_tensor(upper, dtype=points_world.dtype, device=points_world.device)
        if lo.shape != (3,) or hi.shape != (3,) or not bool((hi > lo).all()):
            raise ValueError("lower and upper must be increasing 3-vectors")
        normalized = (points_world - lo) / (hi - lo)
        if bool(((normalized < 0) | (normalized > 1)).any()):
            raise ValueError("points must lie inside the declared bounding box")
        try:
            model_dtype = next(self.model.parameters()).dtype
        except StopIteration:
            model_dtype = normalized.dtype
        weights = self.model(normalized.to(dtype=model_dtype)).to(dtype=points_world.dtype)
        return quadrature_moments(points_world, density, domain_measure, weights)
