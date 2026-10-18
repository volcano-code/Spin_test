"""Shared cached-geometry interfaces for the two W5 architectures."""

from __future__ import annotations

import torch


def broadcast_geometry(z: torch.Tensor, c: torch.Tensor, latent_size: int) -> tuple[torch.Tensor, torch.Tensor, bool]:
    if z.ndim not in (1, 2) or z.shape[-1] != latent_size:
        raise ValueError(f"encoded geometry must end in {latent_size}, got {tuple(z.shape)}")
    if c.ndim not in (1, 2) or c.shape[-1] != 10:
        raise ValueError(f"c must end in dimension 10, got {tuple(c.shape)}")
    if z.device != c.device or z.dtype != c.dtype:
        raise ValueError("cached z and c must share dtype and device")
    unbatched = z.ndim == 1 and c.ndim == 1
    z = z.unsqueeze(0) if z.ndim == 1 else z
    c = c.unsqueeze(0) if c.ndim == 1 else c
    if z.shape[0] != c.shape[0] and z.shape[0] != 1 and c.shape[0] != 1:
        raise ValueError("batched geometries and controls need equal or singleton batch dimensions")
    batch = max(z.shape[0], c.shape[0])
    return z.expand(batch, -1), c.expand(batch, -1), unbatched


def jacrev_cached(model: torch.nn.Module, z: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
    """Differentiate r solely with respect to c; no redundant geometry encoding."""
    if c.ndim == 1:
        if z.ndim == 2 and z.shape[0] == 1:
            z = z[0]
        if z.ndim != 1:
            raise ValueError("unbatched c requires one encoded geometry")
        return torch.func.jacrev(lambda control: model.moment(z, control))(c)
    if c.ndim != 2 or c.shape[1] != 10:
        raise ValueError("controls must have shape [10] or [batch,10]")
    if z.ndim == 1:
        z = z.unsqueeze(0).expand(c.shape[0], -1)
    elif z.ndim == 2 and z.shape[0] == 1:
        z = z.expand(c.shape[0], -1)
    elif z.ndim != 2 or z.shape[0] != c.shape[0]:
        raise ValueError("batched geometry/control dimensions mismatch")
    return torch.vmap(lambda zz, cc: torch.func.jacrev(lambda x: model.moment(zz, x))(cc))(z, c)


def count_parameters(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def linear_macs(module: torch.nn.Module) -> int:
    """Inferred linear-layer multiply-accumulates for a single input."""
    return sum(m.in_features * m.out_features for m in module.modules() if isinstance(m, torch.nn.Linear))
