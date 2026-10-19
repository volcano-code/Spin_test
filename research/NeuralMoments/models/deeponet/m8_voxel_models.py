"""W5 M8: parity of *input information*, not identical encoder architectures.

Both W5 candidates now receive the same raw four-channel voxel tensor as W6;
no label-derived or pre-cut moments are passed to the encoder.  The small
learnable depthwise spatial trunk produces a 9-vector compatible with the
unchanged source-pinned W5 DeepONet/Geometry-MLP heads.  The resulting models
are new M8 voxel variants, not historical W5 M4 weights.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.func import jacrev, vmap
from .model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment


class FourChannelSpatialEncoder(nn.Module):
    """Per-channel 3D stencil + signed spatial moments, shared raw information.

    A depthwise convolution sees every raw voxel channel, while signed x/y/z
    pooling avoids collapsing all placements to identical global means.
    """
    def __init__(self) -> None:
        super().__init__()
        self.depthwise = nn.Conv3d(4, 4, kernel_size=3, padding=1, groups=4)
        self.project = nn.Sequential(nn.Linear(16, 9), nn.Tanh())

    def forward(self, D: torch.Tensor) -> torch.Tensor:
        if not isinstance(D, torch.Tensor) or D.ndim != 5 or D.shape[1] != 4:
            raise ValueError('expected D [B,4,X,Y,Z]')
        if D.shape[0] < 1 or min(D.shape[-3:]) < 8 or not D.is_floating_point() or not bool(torch.isfinite(D).all()):
            raise ValueError('nonfinite/undersized 4-channel voxels')
        features = torch.nn.functional.gelu(self.depthwise(D))
        coords = [torch.linspace(-1., 1., n, dtype=D.dtype, device=D.device)
                  for n in D.shape[-3:]]
        basis = torch.stack(torch.meshgrid(*coords, indexing='ij'), dim=0)
        global_mean = features.mean((-3,-2,-1))
        signed_means = (features.unsqueeze(2) * basis.unsqueeze(0)).mean((-3,-2,-1))
        all_features = torch.cat((global_mean, signed_means.flatten(1)), dim=1)
        return self.project(all_features)


class VoxelMomentCandidate(nn.Module):
    """Geometry cached once; W0-native positive-ray c semantics and full Jc."""
    def __init__(self, kind: str):
        super().__init__()
        if kind not in ('deeponet','geometry_mlp'):
            raise ValueError('unsupported W5 architecture')
        self.kind = kind
        self.voxel_encoder = FourChannelSpatialEncoder()
        self.core = (DeepONetMoment(geometry_dim=9) if kind == 'deeponet'
                     else GeometryMLPMoment(geometry_dim=9))

    def encode_geometry(self, D: torch.Tensor) -> torch.Tensor:
        return self.core.encode_geometry(self.voxel_encoder(D))

    @staticmethod
    def _checked_inputs(z: torch.Tensor, c: torch.Tensor) -> None:
        if c.ndim != 2 or c.shape[-1] != 10 or z.ndim != 2 or z.shape[0] != c.shape[0]:
            raise ValueError('expected matching [B,latent] and [B,10]')
        if z.device != c.device or z.dtype != c.dtype:
            raise ValueError('geometry/control device or dtype mismatch')
        if not bool(torch.isfinite(c).all()) or bool((torch.linalg.vector_norm(c, dim=-1) <= 1e-12).any()):
            raise ValueError('invalid native c')

    def moment(self, z: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        self._checked_inputs(z, c)
        native_ray = c / torch.linalg.vector_norm(c, dim=-1, keepdim=True)
        return self.core.moment(z, native_ray)

    def jacobian(self, z: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        self._checked_inputs(z, c)
        # No data-dependent bool inside vmap. Derivative includes d(c/||c||)/dc.
        def one(zz: torch.Tensor, cc: torch.Tensor) -> torch.Tensor:
            return self.core.moment(zz, cc / torch.linalg.vector_norm(cc))
        return vmap(jacrev(one, argnums=1))(z, c)

    def forward(self, D: torch.Tensor, c: torch.Tensor) -> torch.Tensor:
        return self.moment(self.encode_geometry(D), c)

    def real_parameter_count(self) -> int:
        return sum(p.numel()*(2 if p.is_complex() else 1)
                   for p in self.parameters() if p.requires_grad)
