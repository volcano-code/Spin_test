"""Lightweight, geometry-cached MLP counterpart with similar capacity."""

from __future__ import annotations

from torch import nn
import torch

from ..deeponet.interface import (
    broadcast_geometry, count_parameters, jacrev_cached, linear_macs,
)


class GeometryMLPMoment(nn.Module):
    def __init__(self, *, geometry_dim: int = 9, width: int = 48,
                 latent: int = 32, head_width: int = 72) -> None:
        super().__init__()
        self.geometry_dim = geometry_dim
        self.latent = latent
        self.cached_dim = latent
        self.geometry_encoder = nn.Sequential(
            nn.Linear(geometry_dim, width), nn.Tanh(),
            nn.Linear(width, width), nn.Tanh(),
            nn.Linear(width, latent), nn.Tanh(),
        )
        self.head = nn.Sequential(
            nn.Linear(latent + 10, head_width), nn.Tanh(),
            nn.Linear(head_width, head_width), nn.Tanh(),
            nn.Linear(head_width, 10),
        )

    def encode_geometry(self, d: torch.Tensor) -> torch.Tensor:
        if d.ndim not in (1, 2) or d.shape[-1] != self.geometry_dim:
            raise ValueError(f"D must have trailing dimension {self.geometry_dim}")
        return self.geometry_encoder(d)

    def moment(self, z_d: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        z_d, c, unbatched = broadcast_geometry(z_d, c, self.latent)
        out = self.head(torch.cat((z_d, c), dim=-1))
        return out[0] if unbatched else out

    def forward(self, d: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        return self.moment(self.encode_geometry(d), c)

    def jacobian(self, z_d: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        return jacrev_cached(self, z_d, c)

    def complexity(self) -> dict[str, int]:
        geom = linear_macs(self.geometry_encoder)
        head = linear_macs(self.head)
        return {"parameters": count_parameters(self), "encode_macs": geom,
                "warm_query_macs": head, "cold_query_macs": geom + head}
