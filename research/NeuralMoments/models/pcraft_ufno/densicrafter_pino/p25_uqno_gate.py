"""P25.2: calibrated UQNO abstention gate with caller-supplied exact fallback.

The UQNO predicts a calibrated upper bound on one explicit error target.
It never replaces P-CRAFT PINO. If the bound exceeds a caller-declared
application tolerance, this wrapper abstains and invokes the supplied exact
reference callback. In current cloud experiments that callback may be the
independent voxel hard-cut integral only; it must not be labelled Cherchi.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Any

import torch
from torch import nn


class _UQNO(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 96), nn.GELU(),
            nn.Linear(96, 48), nn.GELU(),
            nn.Linear(48, 2),
        )

    def forward(self, x):
        out = self.net(x)
        return out[:, 0], out[:, 1].clamp(-8.0, 4.0)


class CalibratedUQNO:
    """Loads one separately trained/calibrated UQNO error-target checkpoint."""

    def __init__(self, checkpoint: str | Path, *, target: str):
        if target not in ("hardcut", "analytic_p0"):
            raise ValueError("target must be hardcut or analytic_p0")
        package = torch.load(checkpoint, map_location="cpu", weights_only=False)
        expected = (
            "W6_P25_UQNO_HARDCUT_PREDICTOR_V1"
            if target == "hardcut"
            else "W6_P25_UQNO_ANALYTIC_P0_PREDICTOR_V1"
        )
        if package.get("schema") != expected:
            raise ValueError("UQNO checkpoint target/schema mismatch")
        self.model = _UQNO(int(package["feature_dim"]))
        self.model.load_state_dict(package["state_dict"], strict=True)
        self.model.eval()
        self.input_mean = torch.as_tensor(package["input_mean"], dtype=torch.float32)
        self.input_scale = torch.as_tensor(package["input_scale"], dtype=torch.float32)
        self.input_min = torch.as_tensor(metrics["training_feature_q01"], dtype=torch.float32)
        self.input_max = torch.as_tensor(metrics["training_feature_q99"], dtype=torch.float32)
        self.target_log_mean = torch.as_tensor(package["target_log_mean"], dtype=torch.float32)
        self.target_log_scale = torch.as_tensor(package["target_log_scale"], dtype=torch.float32)
        metrics = package["metrics"]
        self.q90 = float(metrics["calibration_standardized_residual_q90"])
        self.q95 = float(metrics["calibration_standardized_residual_q95"])
        if not (torch.isfinite(self.input_mean).all() and
                torch.isfinite(self.input_scale).all() and
                torch.isfinite(self.input_min).all() and
                torch.isfinite(self.input_max).all() and
                torch.isfinite(self.target_log_mean).all() and
                torch.isfinite(self.target_log_scale).all()):
            raise ValueError("nonfinite UQNO normalization parameters")
        if bool((self.input_scale <= 0).any()) or bool((self.input_max <= self.input_min).any()) or float(self.target_log_scale) <= 0:
            raise ValueError("invalid UQNO normalization scale")
        if not (0 < self.q90 < 100 and 0 < self.q95 < 100):
            raise ValueError("invalid conformal residual quantiles")
        self.target = target

    @torch.no_grad()
    def predict_interval(self, features, *, confidence: float = .95):
        if confidence not in (.90, .95):
            raise ValueError("only calibrated 90% or 95% intervals are available")
        x = torch.as_tensor(features, dtype=torch.float32)
        if x.ndim == 1:
            x = x.unsqueeze(0)
        if x.ndim != 2 or x.shape[1] != self.input_mean.numel():
            raise ValueError("feature shape mismatch")
        if not bool(torch.isfinite(x).all()):
            raise ValueError("features must be finite")
        x = ((x-self.input_mean)/self.input_scale).clamp(-10, 10)
        mu, logvar = self.model(x)
        log_mu = mu*self.target_log_scale+self.target_log_mean
        sigma = torch.exp(.5*logvar)*self.target_log_scale
        q = self.q90 if confidence == .90 else self.q95
        lower = torch.exp(log_mu-q*sigma).clamp_min(0)
        median = torch.exp(log_mu)
        upper = torch.exp(log_mu+q*sigma)
        return {
            "target": self.target,
            "confidence": confidence,
            "lower": lower,
            "median": median,
            "upper": upper,
        }

    @torch.no_grad()
    def should_fallback(self, features, *, error_tolerance: float,
                        confidence: float = .95):
        if error_tolerance <= 0 or not torch.isfinite(torch.tensor(error_tolerance)):
            raise ValueError("error_tolerance must be finite and positive")
        try:
            raw = torch.as_tensor(features, dtype=torch.float32)
            if raw.ndim == 1:
                raw = raw.unsqueeze(0)
            if raw.ndim != 2 or raw.shape[1] != self.input_mean.numel() or not bool(torch.isfinite(raw).all()):
                raise ValueError("invalid feature shape or nonfinite values")
            ood = ((raw < self.input_min) | (raw > self.input_max)).any(dim=1)
            if bool(ood.any()):
                return {
                    "fallback": True, "interval": None,
                    "error_tolerance": float(error_tolerance),
                    "reason": "FEATURE_OUTSIDE_TRAINING_01_99_ENVELOPE",
                }
            interval = self.predict_interval(raw, confidence=confidence)
            fallback = bool((interval["upper"] > error_tolerance).any())
            return {
                "fallback": fallback,
                "interval": interval,
                "error_tolerance": float(error_tolerance),
                "reason": "UQNO_UPPER_BOUND_EXCEEDS_TOLERANCE"
                          if fallback else "UQNO_UPPER_BOUND_WITHIN_TOLERANCE",
            }
        except (ValueError, RuntimeError, KeyError):
            return {
                "fallback": True, "interval": None,
                "error_tolerance": float(error_tolerance),
                "reason": "INVALID_OR_UNCALIBRATED_FEATURES",
            }

    def predict_or_fallback(self, features, approximate_result: Any,
                            exact_fallback: Callable[[], Any], *,
                            error_tolerance: float, confidence: float = .95):
        """Fail closed: exact_fallback is called on uncertainty or invalid features.

        The callback must compute the exact reference for the current task.
        This wrapper does not infer whether that callback is Cherchi or a
        discrete voxel hard-cut integral; callers must record its provenance.
        """
        decision = self.should_fallback(
            features, error_tolerance=error_tolerance, confidence=confidence
        )
        if decision["fallback"]:
            return {
                "value": exact_fallback(),
                "source": "CALLER_SUPPLIED_EXACT_FALLBACK",
                "fallback_used": True,
                "decision": decision,
            }
        return {
            "value": approximate_result,
            "source": "PINO_PRIMARY_BACKBONE_WITH_UQNO_GATE",
            "fallback_used": False,
            "decision": decision,
        }
