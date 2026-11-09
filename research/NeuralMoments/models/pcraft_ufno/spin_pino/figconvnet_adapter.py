"""P26.1b adapter from canonical voxel geometry to official FIGConvUNet.

This wrapper does not vendor PhysicsNeMo. The caller constructs the pinned
official FIGConvUNet and injects it. Occupied voxel centers are deterministically
sampled into point coordinates and four per-point geometry features. Point
features are pooled (mean + max) and projected to the feature width expected
by SpinPINO.attach_geometry_plugin. The P-CRAFT PINO trunk remains primary.
"""
from __future__ import annotations

from typing import Tuple

import torch
from torch import Tensor, nn

from ..model import canonical_geometry


class FIGConvNetPointEncoder(nn.Module):
    """Adapt a PhysicsNeMo FIGConvUNet to SpinPINO's geometry plugin port."""

    def __init__(
        self,
        figconv_model: nn.Module,
        *,
        num_points: int = 4096,
        figconv_out_channels: int,
        output_dim: int,
    ):
        super().__init__()
        if not isinstance(figconv_model, nn.Module):
            raise TypeError("figconv_model must be a torch.nn.Module")
        if num_points < 32:
            raise ValueError("num_points must be >=32")
        if figconv_out_channels < 1 or output_dim < 1:
            raise ValueError("feature dimensions must be positive")
        self.figconv_model = figconv_model
        self.num_points = int(num_points)
        self.figconv_out_channels = int(figconv_out_channels)
        self.output_dim = int(output_dim)
        self.projection = nn.Sequential(
            nn.Linear(2 * figconv_out_channels, output_dim),
            nn.GELU(),
            nn.Linear(output_dim, output_dim),
        )

    def _sample_one(self, geometry: Tensor) -> Tuple[Tensor, Tensor]:
        # geometry: [4,X,Y,Z], channels = density, occupancy, normalized SDF,
        # internal boundary. Coordinates are normalized to [-1,1].
        occupancy = geometry[1] > 0.5
        coords = torch.nonzero(occupancy, as_tuple=False)
        if coords.numel() == 0:
            raise ValueError("FIGConvNet cannot encode an empty occupancy grid")
        if coords.shape[0] >= self.num_points:
            pick = torch.linspace(
                0, coords.shape[0]-1, self.num_points,
                device=coords.device,
            ).round().long()
            coords = coords.index_select(0, pick)
        else:
            repeat = torch.arange(self.num_points, device=coords.device) % coords.shape[0]
            coords = coords.index_select(0, repeat)
        spatial = torch.as_tensor(
            geometry.shape[1:], device=geometry.device, dtype=geometry.dtype
        )
        denom = (spatial - 1).clamp_min(1)
        vertices = 2.0 * coords.to(geometry.dtype) / denom - 1.0
        ix, iy, iz = coords.unbind(-1)
        features = geometry[:, ix, iy, iz].transpose(0, 1).contiguous()
        return vertices.contiguous(), features

    def forward(self, geometry: Tensor) -> Tensor:
        canonical = canonical_geometry(geometry)
        if canonical.ndim != 5 or canonical.shape[1] != 4:
            raise ValueError("canonical geometry must have shape [B,4,X,Y,Z]")
        vertices, features = [], []
        for item in canonical:
            v, f = self._sample_one(item)
            vertices.append(v)
            features.append(f)
        vertices = torch.stack(vertices, dim=0)
        features = torch.stack(features, dim=0)
        point_output, _ = self.figconv_model(vertices, features)
        if point_output.ndim != 3 or point_output.shape[:2] != vertices.shape[:2]:
            raise ValueError("FIGConvUNet must return point features [B,N,C]")
        if point_output.shape[-1] != self.figconv_out_channels:
            raise ValueError(
                f"FIGConvUNet output channels {point_output.shape[-1]} "
                f"!= configured {self.figconv_out_channels}"
            )
        pooled = torch.cat(
            (point_output.mean(dim=1), point_output.amax(dim=1)), dim=-1
        )
        result = self.projection(pooled)
        if not bool(torch.isfinite(result).all()):
            raise ValueError("FIGConvNet adapter produced nonfinite features")
        return result
