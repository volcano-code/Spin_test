"""Frozen-network residual adaptation for 0/1/2/4/8 oracle queries.

The adapter sees actual independent teacher r labels, never network-generated
pseudo-truth. It freezes the network, fits a ridge-regularized affine residual
in c and adds that correction at prediction time. Jacobians are analytic for
the correction and jacrev-based for the base network.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

SUPPORTED_QUERY_COUNTS = (0, 1, 2, 4, 8)


@dataclass
class ResidualAdapter:
    model: nn.Module
    z_d: torch.Tensor
    coefficients: torch.Tensor  # [11, 10], rows: constant and each c coordinate
    support_count: int

    def predict(self, c: torch.Tensor) -> torch.Tensor:
        if c.shape[-1] != 10 or c.ndim not in (1, 2):
            raise ValueError("c must have shape [10] or [Q,10]")
        design = torch.cat((torch.ones_like(c[..., :1]), c), dim=-1)
        return self.model.moment(self.z_d, c) + design @ self.coefficients

    def jacobian(self, c: torch.Tensor) -> torch.Tensor:
        j = self.model.jacobian(self.z_d, c)
        return j + self.coefficients[1:].T


def fit_residual_adapter(model: nn.Module, z_d: torch.Tensor,
                         support_c: torch.Tensor, support_r: torch.Tensor,
                         *, ridge: float = 1e-3) -> ResidualAdapter:
    """Fit a constant+linear correction; 0 support points is a no-op.

    Inputs must be same dtype/device; accepts only preregistered query counts.
    The 11-parameter affine fit is underdetermined at k<=8 by design and
    uses positive ridge regularization. No backprop updates model weights.
    """
    if support_c.ndim != 2 or support_c.shape[1] != 10:
        raise ValueError("support_c must have shape [K,10]")
    k = support_c.shape[0]
    if k not in SUPPORTED_QUERY_COUNTS or support_r.shape != (k, 10):
        raise ValueError("query count must be 0,1,2,4,8 and r shape [K,10]")
    if ridge <= 0:
        raise ValueError("ridge must be strictly positive")
    if not bool(torch.isfinite(support_c).all() and torch.isfinite(support_r).all()):
        raise ValueError("support data must be finite")
    if z_d.ndim != 1:
        raise ValueError("encode one geometry into a [latent] vector for adaptation")
    if z_d.dtype != support_c.dtype or z_d.device != support_c.device or support_r.dtype != support_c.dtype or support_r.device != support_c.device:
        raise ValueError("adapter tensors must match dtype and device")
    with torch.no_grad():
        z = z_d.detach()
        coefficients = torch.zeros((11, 10), dtype=support_c.dtype, device=support_c.device)
        if k:
            design = torch.cat((torch.ones((k, 1), dtype=support_c.dtype, device=support_c.device), support_c), dim=1)
            residual = support_r - model.moment(z, support_c)
            matrix = design.T @ design + ridge * torch.eye(11, dtype=support_c.dtype, device=support_c.device)
            coefficients = torch.linalg.solve(matrix, design.T @ residual)
    return ResidualAdapter(model=model, z_d=z, coefficients=coefficients.detach(), support_count=k)
