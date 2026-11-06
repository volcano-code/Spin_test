"""Pinned NeuralOperator GINO/UQNO adapters for W6 ten-moment prediction."""

from __future__ import annotations

import math
from typing import Optional

import torch
from torch import Tensor, nn
import torch.nn.functional as F
from torch.func import jacrev, vmap


def _unit_positive_coefficients(coefficients: Tensor) -> Tensor:
    if coefficients.ndim != 2 or coefficients.shape[-1] != 10:
        raise ValueError("native coefficients must have shape [B,10]")
    if not coefficients.is_floating_point() or not bool(torch.isfinite(coefficients).all()):
        raise ValueError("native coefficients must be finite floating-point values")
    norm = torch.linalg.vector_norm(coefficients, dim=-1, keepdim=True)
    if bool((norm <= 1e-12).any()):
        raise ValueError("zero/near-zero native coefficient vector")
    return coefficients / norm


def voxel_geometry_to_point_cloud(geometry: Tensor, max_points: int = 2048):
    """Convert one canonical [1,4,X,Y,Z] volume into shared GINO points/features.

    Coordinates are normalized to [0,1]. All voxels are eligible, including
    empty cells, so occupancy/SDF/boundary features remain observable. Sampling
    is deterministic and evenly strided; it is a baseline adapter, not a
    conservative geometry representation.
    """
    if geometry.ndim != 5 or geometry.shape[0] != 1 or geometry.shape[1] != 4:
        raise ValueError("geometry must be canonical [1,4,X,Y,Z]")
    if not geometry.is_floating_point() or not bool(torch.isfinite(geometry).all()):
        raise ValueError("geometry must be finite floating-point data")
    if max_points < 8:
        raise ValueError("max_points must be at least eight")
    _, _, nx, ny, nz = geometry.shape
    axes = [torch.linspace(0, 1, n, dtype=geometry.dtype, device=geometry.device)
            for n in (nx, ny, nz)]
    grid = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=-1).reshape(-1, 3)
    features = geometry[0].permute(1, 2, 3, 0).reshape(-1, 4)
    if grid.shape[0] > max_points:
        indices = torch.linspace(0, grid.shape[0] - 1, max_points,
                                 device=geometry.device).round().long().unique()
        grid, features = grid[indices], features[indices]
    return grid.unsqueeze(0), features.unsqueeze(0)


class CoefficientMomentHead(nn.Module):
    """Ten raw variable-domain moments conditioned on a pooled geometry code."""

    def __init__(self, geometry_channels: int, hidden_channels: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(geometry_channels + 10, hidden_channels),
            nn.GELU(),
            nn.Linear(hidden_channels, hidden_channels),
            nn.GELU(),
            nn.Linear(hidden_channels, 10),
        )

    def forward(self, geometry_code: Tensor, coefficients: Tensor) -> Tensor:
        if geometry_code.ndim != 2 or geometry_code.shape[0] != coefficients.shape[0]:
            raise ValueError("geometry_code and coefficients must share batch size")
        return self.net(torch.cat((geometry_code, _unit_positive_coefficients(coefficients)), dim=-1))


class GINOMomentOperator(nn.Module):
    """GINO geometry encoder plus a Spin-specific ten-moment coefficient head.

    GINO is used as an encoder, not as a drop-in moment/Jacobian solver.
    The pooled geometry code is conditioned on the native ten coefficients.
    Its derivative is diagnostic only and is never admitted to Newton.
    """

    def __init__(
        self,
        *,
        latent_resolution: int = 8,
        hidden_channels: int = 16,
        fno_modes: int = 2,
        fno_layers: int = 1,
        in_gno_radius: float = 2.0,
        out_gno_radius: float = 2.0,
    ):
        super().__init__()
        if latent_resolution < 4 or fno_modes < 1 or fno_modes >= latent_resolution // 2:
            raise ValueError("require latent_resolution>=4 and 1<=fno_modes<resolution/2")
        try:
            from neuralop.models import GINO
        except ImportError as exc:
            raise RuntimeError(
                "GINO requires the pinned NeuralOperator package; "
                "install p0_integration/requirements-neuraloperator.txt"
            ) from exc
        self.encoder = GINO(
            in_channels=4,
            out_channels=hidden_channels,
            gno_coord_dim=3,
            in_gno_radius=in_gno_radius,
            out_gno_radius=out_gno_radius,
            fno_in_channels=4,
            fno_n_modes=(fno_modes, fno_modes, fno_modes),
            fno_hidden_channels=hidden_channels,
            fno_n_layers=fno_layers,
            gno_use_open3d=False,
            gno_use_torch_scatter=False,
            in_gno_channel_mlp_hidden_layers=[hidden_channels, hidden_channels],
            out_gno_channel_mlp_hidden_layers=[hidden_channels, hidden_channels],
        )
        axes = [torch.linspace(0, 1, latent_resolution) for _ in range(3)]
        grid = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=-1).unsqueeze(0)
        output_resolution = max(2, latent_resolution // 2)
        output_axes = [torch.linspace(0, 1, output_resolution) for _ in range(3)]
        output_grid = torch.stack(torch.meshgrid(*output_axes, indexing="ij"), dim=-1).unsqueeze(0)
        self.register_buffer("latent_queries", grid)
        self.register_buffer("output_queries", output_grid.reshape(1, -1, 3))
        self.head = CoefficientMomentHead(hidden_channels, hidden_channels)

    def encode(self, input_geom: Tensor, point_features: Tensor) -> Tensor:
        if input_geom.ndim != 3 or input_geom.shape[0] != 1 or input_geom.shape[-1] != 3:
            raise ValueError("GINO shared input_geom must have shape [1,N,3]")
        if point_features.ndim != 3 or point_features.shape[-1] != 4:
            raise ValueError("point_features must have shape [B,N,4]")
        if point_features.shape[1] != input_geom.shape[1]:
            raise ValueError("input_geom and point_features point counts differ")
        if input_geom.device != point_features.device:
            raise ValueError("input_geom and point_features must share a device")
        if not bool(torch.isfinite(input_geom).all()) or not bool(torch.isfinite(point_features).all()):
            raise ValueError("GINO inputs must be finite")
        latent = self.encoder(
            input_geom=input_geom,
            latent_queries=self.latent_queries.to(input_geom),
            output_queries=self.output_queries.to(input_geom),
            x=point_features,
        )
        if not isinstance(latent, Tensor) or latent.ndim != 3:
            raise RuntimeError("GINO must return [B,N_query,C] tensor output")
        return latent.mean(dim=1)

    def forward(self, input_geom: Tensor, point_features: Tensor, coefficients: Tensor) -> Tensor:
        if coefficients.shape[0] != point_features.shape[0]:
            raise ValueError("coefficient and point-feature batch sizes differ")
        geometry_code = self.encode(input_geom, point_features)
        return self.head(geometry_code, coefficients)

    def forward_voxels(self, geometry: Tensor, coefficients: Tensor, max_points: int = 2048) -> Tensor:
        points, features = voxel_geometry_to_point_cloud(geometry, max_points=max_points)
        return self.forward(points, features, coefficients)

    def jacobian_diagnostic(self, input_geom: Tensor, point_features: Tensor,
                            coefficients: Tensor) -> Tensor:
        geometry_code = self.encode(input_geom, point_features)
        _unit_positive_coefficients(coefficients)  # validate outside vmap
        def one(code: Tensor, coeff: Tensor) -> Tensor:
            unit = coeff / torch.linalg.vector_norm(coeff)
            return self.head.net(torch.cat((code, unit), dim=-1).unsqueeze(0)).squeeze(0)
        return vmap(jacrev(one, argnums=1))(geometry_code, coefficients)


class PositiveResidualHead(nn.Module):
    """Constrain UQNO residual outputs to positive per-moment scales."""

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model

    def forward(self, *args, **kwargs) -> Tensor:
        return F.softplus(self.model(*args, **kwargs)) + 1e-8


class SplitConformalMomentCalibrator:
    """Finite-sample simultaneous conformal scaling across all ten moments."""

    def __init__(self, alpha: float = 0.1):
        if not 0 < alpha < 1:
            raise ValueError("alpha must lie in (0,1)")
        self.alpha = float(alpha)
        self.qhat: Optional[float] = None
        self.n_calibration = 0

    def fit(self, mean: Tensor, scale: Tensor, target: Tensor):
        if mean.shape != scale.shape or mean.shape != target.shape or mean.ndim != 2 or mean.shape[-1] != 10:
            raise ValueError("mean, scale and target must all have shape [N,10]")
        if not all(bool(torch.isfinite(x).all()) for x in (mean, scale, target)):
            raise ValueError("calibration tensors must be finite")
        if bool((scale <= 0).any()):
            raise ValueError("predicted scales must be strictly positive")
        scores = ((target - mean).abs() / scale).amax(dim=-1)
        n = int(scores.numel())
        rank = math.ceil((n + 1) * (1.0 - self.alpha))
        self.n_calibration = n
        if rank > n:
            self.qhat = math.inf
        else:
            self.qhat = float(torch.sort(scores).values[rank - 1].item())
        return self

    def radius(self, scale: Tensor) -> Tensor:
        if self.qhat is None:
            raise RuntimeError("calibrator has not been fitted")
        return scale * self.qhat

    @property
    def calibrated(self) -> bool:
        return self.qhat is not None and math.isfinite(self.qhat)


class UQNOAdapter(nn.Module):
    """Wrap a W6 moment head in upstream UQNO and split-conformal calibration.

    UQNO predicts a residual scale; calibration uses a separate held-out set.
    This only quantifies prediction error. It does not certify physical validity
    or authorize the predicted Jacobian for Newton.
    """

    def __init__(self, base_head: nn.Module, residual_head: nn.Module):
        super().__init__()
        try:
            from neuralop.models import UQNO
        except ImportError as exc:
            raise RuntimeError(
                "UQNO requires the pinned NeuralOperator package; "
                "install p0_integration/requirements-neuraloperator.txt"
            ) from exc
        self.model = UQNO(
            base_model=base_head,
            residual_model=PositiveResidualHead(residual_head),
        )

    def forward(self, geometry_code: Tensor, coefficients: Tensor):
        mean, scale = self.model(geometry_code, coefficients)
        return mean, scale
