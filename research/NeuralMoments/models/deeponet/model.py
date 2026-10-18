"""Geometry-cached, ten-output DeepONet-style moment regressor."""

from __future__ import annotations

from torch import nn
import torch

from .interface import broadcast_geometry, count_parameters, jacrev_cached, linear_macs


class DeepONetMoment(nn.Module):
    """Branch(D) times trunk(c), with a geometry-dependent ten-vector bias.

    Geometry is encoded only by encode_geometry(D). Use moment(z, c_batch)
    to amortize geometry across many controls, or forward(D, c) for a
    one-shot prediction. This is W5's prototype, not the original paper
    implementation and not yet a W0-contracted production surrogate.
    """

    def __init__(self, *, geometry_dim: int = 9, width: int = 48,
                 latent: int = 32, rank: int = 16) -> None:
        super().__init__()
        self.geometry_dim = geometry_dim
        self.latent = latent
        self.rank = rank
        self.cached_dim = 10 * (rank + 1)  # per-output basis plus geometry bias
        self.geometry_encoder = nn.Sequential(
            nn.Linear(geometry_dim, width), nn.Tanh(),
            nn.Linear(width, width), nn.Tanh(),
            nn.Linear(width, latent), nn.Tanh(),
        )
        self.branch = nn.Linear(latent, 10 * rank)
        self.geometry_bias = nn.Linear(latent, 10)
        self.trunk = nn.Sequential(
            nn.Linear(10, width), nn.Tanh(),
            nn.Linear(width, width), nn.Tanh(),
            nn.Linear(width, rank),
        )

    def encode_geometry(self, d: torch.Tensor) -> torch.Tensor:
        if d.ndim not in (1, 2) or d.shape[-1] != self.geometry_dim:
            raise ValueError(f"D must have trailing dimension {self.geometry_dim}")
        latent = self.geometry_encoder(d)
        return torch.cat((self.branch(latent), self.geometry_bias(latent)), dim=-1)

    def moment(self, z_d: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        z_d, c, unbatched = broadcast_geometry(z_d, c, self.cached_dim)
        branch = z_d[:, :10 * self.rank].reshape(-1, 10, self.rank)
        bias = z_d[:, 10 * self.rank:]
        trunk = self.trunk(c).unsqueeze(1)
        # Branch and bias were computed ONCE in encode_geometry(D).
        out = (branch * trunk).sum(dim=-1) * (self.rank ** -0.5) + bias
        return out[0] if unbatched else out

    def forward(self, d: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        return self.moment(self.encode_geometry(d), c)

    def jacobian(self, z_d: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        return jacrev_cached(self, z_d, c)

    def complexity(self) -> dict[str, int]:
        geom = linear_macs(self.geometry_encoder) + linear_macs(self.branch) + linear_macs(self.geometry_bias)
        head = linear_macs(self.trunk) + 10 * self.rank
        return {"parameters": count_parameters(self), "encode_macs": geom,
                "warm_query_macs": head, "cold_query_macs": geom + head}
