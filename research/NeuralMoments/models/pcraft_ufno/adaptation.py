"""Optional 0/1/2 true-teacher-query residual adaptation on cached geometry.

This is a local correction interface, not physics validation or teacher data.
Do not fit on test labels when reporting zero-shot results. The two-query
secant has no guaranteed extrapolation quality and must be separately audited.
"""
from __future__ import annotations

import torch
from torch import Tensor

from .model import CachedGeometry, UFNOMoment, positive_projective_coefficients


class ResidualAdapter:
    """Keeps W6 geometry frozen while correcting the predicted moments."""

    def __init__(self, model: UFNOMoment, z: Tensor | CachedGeometry,
                 support_c: Tensor, support_r: Tensor):
        if isinstance(z, CachedGeometry):
            z = z.z
        if z.ndim != 2:
            raise ValueError("z must have shape [B,latent_dim]")
        if support_c.ndim != 3 or support_c.shape[0] != z.shape[0] or support_c.shape[2] != 10:
            raise ValueError("support_c must be [B,K,10]")
        if support_r.shape != support_c.shape or support_c.shape[1] not in (0, 1, 2):
            raise ValueError("support_r must match support_c with 0, 1 or 2 queries")
        if not torch.isfinite(support_r).all():
            raise ValueError("support_r must be finite")
        self.model = model
        self.z = z.detach()
        self.k = support_c.shape[1]
        if self.k:
            self.anchors = positive_projective_coefficients(support_c.reshape(-1, 10)).reshape_as(support_c).detach()
            with torch.no_grad():
                base = model.moment(self.z.repeat_interleave(self.k, 0),
                                    support_c.reshape(-1, 10)).reshape_as(support_r)
            self.residuals = (support_r - base).detach()
            if self.k == 2:
                difference = self.anchors[:, 1] - self.anchors[:, 0]
                squared = difference.square().sum(-1, keepdim=True)
                if bool((squared < 1e-10).any()):
                    raise ValueError("two supports must use distinct projective coefficients")
                self.direction = difference
                self.denominator = squared

    def _correction(self, c: Tensor) -> Tensor:
        if self.k == 0:
            return torch.zeros((self.z.shape[0], 10), dtype=c.dtype, device=c.device)
        if self.k == 1:
            return self.residuals[:, 0]
        c_unit = positive_projective_coefficients(c)
        t = ((c_unit - self.anchors[:, 0]) * self.direction).sum(-1, keepdim=True) / self.denominator
        return self.residuals[:, 0] + t * (self.residuals[:, 1] - self.residuals[:, 0])

    def predict(self, c: Tensor) -> Tensor:
        return self.model.moment(self.z, c) + self._correction(c)

    def jacobian(self, c: Tensor) -> Tensor:
        result = self.model.jacobian(self.z, c)
        if self.k < 2:
            return result
        unit = positive_projective_coefficients(c)
        norm = torch.linalg.vector_norm(c, dim=-1, keepdim=True)
        eye = torch.eye(10, dtype=c.dtype, device=c.device).unsqueeze(0)
        dnorm = (eye - unit.unsqueeze(-1) * unit.unsqueeze(-2)) / norm.unsqueeze(-1)
        secant_j = ((self.residuals[:, 1] - self.residuals[:, 0]).unsqueeze(-1)
                    * (self.direction / self.denominator).unsqueeze(-2))
        return result + torch.matmul(secant_j, dnorm)
