"""P-CRAFT-inspired factorized U-FNO geometry encoder + ten-moment surrogate.

This is an independent architecture inspired by the F-FNO/UFNO topology in
volcano-code/test@24eda3e9 (structural/models/pino.py), NOT a port of its FEM
weights, 9-channel field decoder, PINO PDE loss, or pretrained model.

The coefficient/moment ordering is anchored to Spin_test's frozen native source:
 c = (constant, x, y, z, xx, yy, zz, yz, xz, xy), with polynomial cross
 terms 2*c[7]*yz + 2*c[8]*xz + 2*c[9]*xy;
 r = (mass, x, y, z, xx, yy, zz, yz, xz, xy) raw density-weighted integrals.
This smoke API is provisional until W0 publishes its MomentContractV1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
from torch import Tensor, nn
import torch.nn.functional as F
from torch.func import jacrev, vmap

CHANNELS = ("density", "occupancy", "sdf", "internal_boundary")
NUM_MOMENTS = 10


def _single_channel(name: str, x: Tensor) -> Tensor:
    if not isinstance(x, Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if x.ndim == 4:
        x = x.unsqueeze(1)
    if x.ndim != 5 or x.shape[1] != 1:
        raise ValueError(f"{name} must have shape [B,1,X,Y,Z] or [B,X,Y,Z]")
    if any(s < 4 for s in x.shape[2:]):
        raise ValueError(f"{name} spatial dimensions must be >= 4")
    if not x.is_floating_point() or not bool(torch.isfinite(x).all()):
        raise ValueError(f"{name} must be finite floating-point data")
    return x


def canonical_geometry(geometry: Tensor | Mapping[str, Tensor], *, sdf_scale: float = 1.0) -> Tensor:
    """Produce canonical [B,4,X,Y,Z]: rho, occupancy, tanh(SDF/scale), inner BC.

    Tensor input is already canonical. Mapping SDF uses the convention SDF < 0
    inside; unspecified channels are imputed and are NOT measured observations.
    Coordinates, true density units, voxel spacing and SDF scale must be fixed
    by W0 before physical-model training.
    """
    if isinstance(geometry, Tensor):
        if geometry.ndim != 5 or geometry.shape[1] != 4:
            raise ValueError("canonical geometry tensor must be [B,4,X,Y,Z]")
        if any(s < 4 for s in geometry.shape[2:]) or not geometry.is_floating_point():
            raise ValueError("invalid canonical geometry shape or dtype")
        if not bool(torch.isfinite(geometry).all()):
            raise ValueError("geometry values must be finite")
        return geometry
    if not isinstance(geometry, Mapping):
        raise TypeError("geometry must be a four-channel tensor or channel mapping")
    if not isinstance(sdf_scale, (float, int)) or not (0 < sdf_scale < float("inf")):
        raise ValueError("sdf_scale must be positive and finite")
    allowed = {"density", "occupancy", "sdf", "signed_distance", "internal_boundary", "inner_boundary"}
    unknown = set(geometry) - allowed
    if unknown:
        raise ValueError(f"unknown geometry channels: {sorted(unknown)}")
    if not ({"density", "occupancy", "sdf", "signed_distance"} & set(geometry)):
        raise ValueError("provide at least density, occupancy, or sdf")
    if "sdf" in geometry and "signed_distance" in geometry:
        raise ValueError("provide only one of sdf and signed_distance")
    if "internal_boundary" in geometry and "inner_boundary" in geometry:
        raise ValueError("provide only one internal boundary alias")
    normalized = {name: _single_channel(name, value) for name, value in geometry.items()}
    first = next(iter(normalized.values()))
    for name, value in normalized.items():
        if value.shape != first.shape or value.device != first.device:
            raise ValueError(f"{name} shape/device does not match other channels")
    dtype = first.dtype
    normalized = {key: value.to(dtype=dtype) for key, value in normalized.items()}
    sdf = normalized.get("sdf", normalized.get("signed_distance"))
    rho = normalized.get("density")
    occupancy = normalized.get("occupancy")
    if rho is None:
        rho = occupancy if occupancy is not None else torch.sigmoid(-sdf / sdf_scale)
    rho = rho.clamp(0, 1)
    if occupancy is None:
        occupancy = (sdf < 0).to(dtype) if sdf is not None else (rho >= 0.5).to(dtype)
    occupancy = occupancy.clamp(0, 1)
    sdf_ch = torch.tanh(sdf / sdf_scale) if sdf is not None else torch.zeros_like(rho)
    inner = normalized.get("internal_boundary", normalized.get("inner_boundary"))
    boundary = inner.clamp(0, 1) if inner is not None else torch.zeros_like(rho)
    return torch.cat((rho, occupancy, sdf_ch, boundary), dim=1)


def positive_projective_coefficients(c: Tensor) -> Tensor:
    """Normalize c so positive scaling is equivalent but sign inversion is not."""
    if c.ndim != 2 or c.shape[1] != NUM_MOMENTS or not c.is_floating_point():
        raise ValueError("c must have shape [B,10] and floating dtype")
    if not bool(torch.isfinite(c).all()):
        raise ValueError("c must be finite")
    norms = torch.linalg.vector_norm(c, dim=-1, keepdim=True)
    if bool((norms <= 1e-12).any()):
        raise ValueError("zero/near-zero quadric coefficient vector")
    return c / norms


class FactorizedSpectralConv3d(nn.Module):
    """Three independent 1D real Fourier transforms with safe mode clipping.

    Unlike the source FEM layer, this encoder limits kept modes to each
    dimension's rFFT length; it does not allocate a dense 3D spectrum.
    """

    def __init__(self, in_channels: int, out_channels: int, modes: int):
        super().__init__()
        if min(in_channels, out_channels, modes) < 1:
            raise ValueError("channels and modes must be positive")
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.modes = modes
        scale = 1.0 / (in_channels * out_channels)
        self.weights = nn.ParameterList([
            nn.Parameter(scale * torch.randn(in_channels, out_channels, modes, dtype=torch.cfloat))
            for _ in range(3)
        ])

    def forward(self, x: Tensor) -> Tensor:
        if x.ndim != 5 or x.shape[1] != self.in_channels:
            raise ValueError("spectral convolution expects [B,in_channels,X,Y,Z]")
        # Explicit float32 FFT avoids half precision/CPU FFT instability.
        x = x.float()
        out = torch.zeros((x.shape[0], self.out_channels, *x.shape[2:]),
                          dtype=x.dtype, device=x.device)
        for spatial_axis, weights in zip((2, 3, 4), self.weights):
            ft = torch.fft.rfft(x, dim=spatial_axis)
            moved = ft.movedim(spatial_axis, 2)
            n_modes = min(self.modes, moved.shape[2])
            result = torch.einsum("bcpuv,cop->bopuv", moved[:, :, :n_modes], weights[:, :, :n_modes])
            out_ft = torch.zeros((x.shape[0], self.out_channels, *moved.shape[2:]),
                                 dtype=ft.dtype, device=x.device)
            out_ft[:, :, :n_modes] = result
            out = out + torch.fft.irfft(out_ft.movedim(2, spatial_axis),
                                         n=x.shape[spatial_axis], dim=spatial_axis)
        return out


class SpectralBlock(nn.Module):
    def __init__(self, width: int, modes: int):
        super().__init__()
        self.freq = FactorizedSpectralConv3d(width, width, modes)
        self.local = nn.Conv3d(width, width, kernel_size=1)
        self.norm = nn.GroupNorm(1, width)

    def forward(self, x: Tensor) -> Tensor:
        return F.gelu(self.norm(self.freq(x) + self.local(x)))


class UFNOGeometryEncoder(nn.Module):
    """U-shaped factorized Fourier encoder with latent-only pooled readout.

    No full-resolution stress/displacement decoder or 9-channel field is made.
    The input is downsampled to a bounded FFT grid before lifting.
    """

    def __init__(self, *, width: int = 8, modes: int = 4, latent_dim: int = 32,
                 grid_size: int = 16):
        super().__init__()
        if width < 2 or modes < 1 or latent_dim < 1 or grid_size < 8 or grid_size % 4:
            raise ValueError("width>=2, modes>=1, latent_dim>=1, grid_size>=8 divisible by 4")
        self.grid_size = grid_size
        self.latent_dim = latent_dim
        self.lift = nn.Conv3d(7, width, 1)  # 4 geometry + 3 coordinates
        self.enc1 = SpectralBlock(width, modes)
        self.down1 = nn.Conv3d(width, 2 * width, 3, stride=2, padding=1)
        self.enc2 = SpectralBlock(2 * width, max(1, modes // 2))
        self.down2 = nn.Conv3d(2 * width, 4 * width, 3, stride=2, padding=1)
        self.bottleneck = SpectralBlock(4 * width, max(1, modes // 4))
        self.up2 = nn.Conv3d(4 * width, 2 * width, 1)
        self.dec2 = SpectralBlock(2 * width, max(1, modes // 2))
        self.up1 = nn.Conv3d(2 * width, width, 1)
        self.dec1 = SpectralBlock(width, modes)
        self.project = nn.Sequential(nn.Linear(7 * width, 2 * latent_dim), nn.GELU(),
                                     nn.Linear(2 * latent_dim, latent_dim))

    def forward(self, geometry: Tensor | Mapping[str, Tensor]) -> Tensor:
        x = canonical_geometry(geometry)
        x = x.to(dtype=self.lift.weight.dtype)
        if x.shape[2:] != (self.grid_size,) * 3:
            if any(s > self.grid_size for s in x.shape[2:]):
                x = F.adaptive_avg_pool3d(x, self.grid_size)
            else:
                x = F.interpolate(x, size=(self.grid_size,) * 3,
                                  mode="trilinear", align_corners=False)
        coords = [torch.linspace(-1, 1, n, dtype=x.dtype, device=x.device)
                  for n in x.shape[2:]]
        xyz = torch.stack(torch.meshgrid(*coords, indexing="ij"), dim=0)
        lifted = self.lift(torch.cat((x, xyz.unsqueeze(0).expand(x.shape[0], -1, -1, -1, -1)), 1))
        h1 = self.enc1(lifted)
        h2 = self.enc2(self.down1(h1))
        h3 = self.bottleneck(self.down2(h2))
        d2 = self.dec2(self.up2(F.interpolate(h3, size=h2.shape[2:], mode="trilinear",
                                              align_corners=False)) + h2)
        d1 = self.dec1(self.up1(F.interpolate(d2, size=h1.shape[2:], mode="trilinear",
                                               align_corners=False)) + h1)
        pooled = torch.cat((h3.mean((2, 3, 4)), d2.mean((2, 3, 4)),
                            d1.mean((2, 3, 4))), dim=-1)
        return self.project(pooled)  # [B,latent_dim]


@dataclass(frozen=True)
class CachedGeometry:
    """Explicit one-time geometry embedding; re-encode after changing model weights."""
    z: Tensor


class UFNOMoment(nn.Module):
    """encode_geometry(D)->z_D; moment(z_D,c)->r[10]; jacobian(z_D,c)->J[10,10]."""

    def __init__(self, *, width: int = 8, modes: int = 4, latent_dim: int = 32,
                 head_width: int = 64, grid_size: int = 16):
        super().__init__()
        self.encoder = UFNOGeometryEncoder(width=width, modes=modes,
                                           latent_dim=latent_dim, grid_size=grid_size)
        self.head = nn.Sequential(nn.Linear(latent_dim + 10, head_width), nn.GELU(),
                                  nn.Linear(head_width, head_width), nn.GELU(),
                                  nn.Linear(head_width, NUM_MOMENTS))

    def encode_geometry(self, geometry: Tensor | Mapping[str, Tensor]) -> Tensor:
        return self.encoder(geometry)

    def cache_geometry(self, geometry: Tensor | Mapping[str, Tensor], *, detach: bool = True) -> CachedGeometry:
        z = self.encode_geometry(geometry)
        return CachedGeometry(z.detach() if detach else z)

    def _validate_inputs(self, z: Tensor | CachedGeometry, c: Tensor) -> tuple[Tensor, Tensor]:
        if isinstance(z, CachedGeometry):
            z = z.z
        if z.ndim != 2 or z.shape[1] != self.encoder.latent_dim:
            raise ValueError("z_D must be [B,latent_dim]")
        if c.shape != (z.shape[0], NUM_MOMENTS):
            raise ValueError("c must be [B,10] with the same batch size as z_D")
        if z.device != c.device:
            raise ValueError("z_D and c must use the same device")
        return z, positive_projective_coefficients(c).to(z.dtype)

    def moment(self, z: Tensor | CachedGeometry, c: Tensor) -> Tensor:
        z, c_unit = self._validate_inputs(z, c)
        return self.head(torch.cat((z, c_unit), dim=-1))

    def jacobian(self, z: Tensor | CachedGeometry, c: Tensor) -> Tensor:
        """Raw-coordinate d r_i / d c_j, NOT in general symmetric."""
        if isinstance(z, CachedGeometry):
            z = z.z
        # Validate before vmap: vectorized jacrev must not branch on tensor bool.
        self._validate_inputs(z, c)

        def one(z_i: Tensor, c_i: Tensor) -> Tensor:
            unit = c_i / torch.linalg.vector_norm(c_i)
            return self.head(torch.cat((z_i, unit.to(z_i.dtype)), dim=-1))

        return vmap(jacrev(one, argnums=1))(z, c)

    def forward(self, geometry: Tensor | Mapping[str, Tensor], c: Tensor,
                *, with_jacobian: bool = False):
        z = self.encode_geometry(geometry)
        r = self.moment(z, c)
        if with_jacobian:
            return r, self.jacobian(z, c)
        return r


def count_real_parameters(model: nn.Module) -> int:
    """Trainable real scalar DOF (complex parameters count twice)."""
    return sum(p.numel() * (2 if p.is_complex() else 1)
               for p in model.parameters() if p.requires_grad)
