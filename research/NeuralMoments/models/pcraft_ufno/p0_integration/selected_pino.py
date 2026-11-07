"""W6 P11: PINO-first selected GINO/QuadrANN/UQNO experimental bridge.

This is not a new standalone neural operator and never replaces the frozen
P-CRAFT U-FNO + Spin moment/Jacobian head. Official pinned GINO, UQNO and
licensed QuadrANN core are imported via W6's already validated P0 adapters.

Geometry-conditioned positive quadrature proposals are fixed for a given
geometry (not a function of c). Spin-PINO alone evaluates the cut c and the
model-internal coefficient Jacobian. The public result *withholds* J_D until
W0/W2/Cherchi native smooth-neighborhood admission.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import torch
from torch import Tensor, nn

from .contracts import MomentQuadratureResult
from .neuraloperator_adapter import (
    GINOMomentOperator,
    SplitConformalMomentCalibrator,
    UQNOAdapter,
    voxel_geometry_to_point_cloud,
)
from .quadrann_adapter import QuadrANNWeightAdapter


class _PINOMean(nn.Module):
    """Forward the original PINO moment head; no new unconstrained r head."""
    def __init__(self, pino: nn.Module):
        super().__init__()
        self.pino = pino

    def forward(self, material_weights: Tensor, coefficients: Tensor) -> Tensor:
        return self.pino.moment_from_weights(material_weights, coefficients)


class _ScaleFromMomentState(nn.Module):
    """Untrained positive-residual scale precursor for upstream UQNO."""
    def __init__(self, node_count: int, hidden_dim: int = 24):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(node_count + 10, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, 10),
        )

    def forward(self, material_weights: Tensor, coefficients: Tensor) -> Tensor:
        coeff = coefficients / torch.linalg.vector_norm(
            coefficients, dim=-1, keepdim=True
        ).clamp_min(1e-12)
        return self.net(torch.cat((material_weights, coeff), dim=-1))


@dataclass(frozen=True)
class SelectedProposal:
    result: MomentQuadratureResult
    diagnostic_model_jacobian: Tensor
    geometry_weights: Tensor
    pino_primary: bool
    newton_derivative_admitted: bool
    source_pin: str


class SelectedPINOCandidates(nn.Module):
    """P-CRAFT PINO core + optional *original code* feature/proposal adapters.

    A zero gate is the unmodified PINO path even if all upstream components
    are instantiated and invoked. Active gates give nonnegative weights,
    but do not guarantee superior accuracy or native derivative validity.
    """

    def __init__(
        self, pino: nn.Module, *, gino: bool = False,
        quadrann: bool = False, uqno: bool = False,
        gino_hidden: int = 8, max_gino_points: int = 64,
    ):
        super().__init__()
        if not (hasattr(pino, "encode_geometry")
                and hasattr(pino, "moment_from_weights")
                and hasattr(pino, "jacobian_from_weights")
                and hasattr(pino, "quadrature_xyz")
                and hasattr(pino, "monomials")):
            raise TypeError("P-CRAFT SpinPINO with ten-moment head is required")
        if max_gino_points < 8:
            raise ValueError("max_gino_points must be >=8")
        self.pino = pino
        self.max_gino_points = int(max_gino_points)
        n_nodes = int(pino.monomials.shape[0])
        self.gino_adapter = (
            GINOMomentOperator(
                latent_resolution=8, hidden_channels=gino_hidden,
                fno_modes=2, fno_layers=1,
            ) if gino else None
        )
        self.gino_correction = (
            nn.Linear(gino_hidden, n_nodes, bias=False)
            if gino else None
        )
        self.gino_gate = nn.Parameter(torch.zeros(())) if gino else None
        self.quadrann_adapter = (
            QuadrANNWeightAdapter(
                num_gnn_layers=2, k_neighbors=4, pe_abs=2, pe_rel=2,
                hidden_dim=16, final_hidden_dim=16,
            ) if quadrann else None
        )
        self.quadrann_gate = (
            nn.Parameter(torch.zeros(())) if quadrann else None
        )
        self.uqno_adapter = (
            UQNOAdapter(_PINOMean(pino), _ScaleFromMomentState(n_nodes))
            if uqno else None
        )

    def geometry_weights(self, geometry: Tensor) -> Tensor:
        if geometry.ndim != 5 or geometry.shape[1] != 4:
            raise ValueError("geometry must be canonical [B,4,X,Y,Z]")
        if not bool(torch.isfinite(geometry).all()):
            raise ValueError("geometry must be finite")
        w = self.pino.encode_geometry(geometry)
        if self.gino_adapter is not None:
            codes = []
            for one in geometry.split(1, dim=0):
                points, features = voxel_geometry_to_point_cloud(
                    one, max_points=self.max_gino_points
                )
                codes.append(self.gino_adapter.encode(points, features))
            gino_code = torch.cat(codes, dim=0)
            local = torch.tanh(self.gino_correction(gino_code))
            w = w * torch.exp(2.0 * torch.tanh(self.gino_gate) * local)
        if self.quadrann_adapter is not None:
            # Original QuadrANN core returns geometry-conditioned weights
            # on the FIXED native-coordinate PINO quadrature nodes.
            # Keep it independent of c to preserve PINO's analytic d r/d c.
            pts = self.pino.quadrature_xyz.to(geometry)
            normalized = (pts + 1.0) / 2.0
            q = self.quadrann_adapter.model(
                normalized.unsqueeze(0)
            ).to(w)
            if q.shape != (1, w.shape[1]) or not bool(torch.isfinite(q).all()):
                raise ValueError("invalid QuadrANN node weight shape or value")
            if bool((q < 0).any()) or bool((q.sum(dim=-1) <= 0).any()):
                raise ValueError("QuadrANN must provide nonnegative positive-total proposal")
            relative = q / q.mean(dim=-1, keepdim=True).clamp_min(1e-12)
            bounded = torch.tanh(torch.log(relative.clamp_min(1e-12)))
            w = w * torch.exp(2.0 * torch.tanh(self.quadrann_gate) * bounded)
        if not bool(torch.isfinite(w).all()) or bool((w < 0).any()):
            raise ValueError("nonfinite/negative PINO proposal weights")
        return w

    def forward(self, geometry: Tensor, coefficients: Tensor) -> SelectedProposal:
        weights = self.geometry_weights(geometry)
        r = self.pino.moment_from_weights(weights, coefficients)
        J_diagnostic = self.pino.jacobian_from_weights(weights, coefficients)
        if self.uqno_adapter is not None:
            predicted_r, scale = self.uqno_adapter(weights, coefficients)
            if not torch.allclose(predicted_r, r, rtol=1e-5, atol=1e-6):
                raise ArithmeticError("UQNO mean changed PINO primary prediction")
        else:
            scale = None
        return SelectedProposal(
            result=MomentQuadratureResult(
                moments=r, uncertainty=scale, jacobian=None,
                source="W6_PINO_SELECTED_ORIGINAL_GINO_QUADRANN_UQNO",
                derivative_status="WITHHELD_MODEL_J_DIAGNOSTIC_ONLY",
                training_admitted=False,
            ),
            diagnostic_model_jacobian=J_diagnostic,
            geometry_weights=weights,
            pino_primary=True,
            newton_derivative_admitted=False,
            source_pin="W6_P0_UPSTREAM_PINS_V1",
        )


@dataclass(frozen=True)
class ScreeningStatus:
    exact_required: bool
    reason: str
    simultaneous_radius: Optional[Tensor]
    native_newton_admitted: bool = False


class GroupwiseConformalScreen:
    """Group geometry-ID conformal uncertainty for *screening only*.

    Multiple c queries from one geometry are grouped before calibration.
    Returns a fail-closed exact-evaluation REQUEST, never performs Cherchi
    itself and never certifies Newton derivatives or topology events.
    """

    def __init__(self, alpha: float = 0.2):
        if not isinstance(alpha, (float, int)) or not math.isfinite(float(alpha)) or not 0.0 < alpha < 1.0:
            raise ValueError("alpha must be finite in (0,1)")
        self.alpha = float(alpha)
        self.qhat: Optional[float] = None
        self.calibration_geometry_ids: frozenset[str] = frozenset()
        self.training_geometry_ids: frozenset[str] = frozenset()

    def fit(
        self, mean: Tensor, scale: Tensor, truth: Tensor,
        geometry_ids: Sequence[str], *, training_geometry_ids: Sequence[str] = (),
    ):
        if (mean.ndim != 2 or mean.shape[-1] != 10
                or scale.shape != mean.shape or truth.shape != mean.shape
                or len(geometry_ids) != mean.shape[0]):
            raise ValueError("calibration rows must be matched [N,10]")
        if not all(isinstance(x, str) and x.strip() for x in geometry_ids):
            raise ValueError("every calibration sample must have a geometry ID")
        if not all(bool(torch.isfinite(x).all()) for x in (mean, scale, truth)):
            raise ValueError("nonfinite calibration data")
        if bool((scale <= 0).any()):
            raise ValueError("positive residual scale required")
        train = frozenset(training_geometry_ids)
        ids = frozenset(geometry_ids)
        if not ids or ids & train:
            raise ValueError("calibration geometries must be disjoint from training")
        scores = ((mean - truth).abs() / scale).amax(dim=-1)
        # Group-aware maximum over every query and every moment component.
        groups = {}
        for i, gid in enumerate(geometry_ids):
            groups[gid] = max(groups.get(gid, 0.0), float(scores[i]))
        ordered = sorted(groups.values())
        rank = math.ceil((len(ordered) + 1) * (1.0 - self.alpha))
        self.qhat = math.inf if rank > len(ordered) else ordered[rank - 1]
        self.training_geometry_ids = train
        self.calibration_geometry_ids = ids
        return self

    def screen(
        self, proposal: SelectedProposal, geometry_id: str, *,
        max_simultaneous_radius: float,
        for_native_newton: bool = False,
    ) -> ScreeningStatus:
        if not geometry_id or geometry_id in self.training_geometry_ids or geometry_id in self.calibration_geometry_ids:
            return ScreeningStatus(True, "GEOMETRY_NOT_HELD_OUT", None)
        if for_native_newton:
            return ScreeningStatus(True, "NATIVE_NEWTON_UNCERTIFIED_J", None)
        if self.qhat is None or not math.isfinite(self.qhat):
            return ScreeningStatus(True, "CALIBRATION_UNAVAILABLE", None)
        if (not math.isfinite(max_simultaneous_radius)
                or max_simultaneous_radius <= 0):
            return ScreeningStatus(True, "INVALID_RISK_TOLERANCE", None)
        if proposal.result.uncertainty is None:
            return ScreeningStatus(True, "NO_PREDICTIVE_SCALE", None)
        radius = proposal.result.uncertainty * self.qhat
        if not bool(torch.isfinite(radius).all()):
            return ScreeningStatus(True, "NONFINITE_RADIUS", None)
        if bool((radius > max_simultaneous_radius).any()):
            return ScreeningStatus(True, "RADIUS_ABOVE_THRESHOLD", radius)
        return ScreeningStatus(False, "SCREENING_ONLY_NOT_NEWTON", radius)
