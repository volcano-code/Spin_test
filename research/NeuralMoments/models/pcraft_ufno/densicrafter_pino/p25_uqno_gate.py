"""P25.2: calibrated UQNO abstention gate with caller-supplied exact fallback.

The UQNO predicts a calibrated upper bound on one explicit error target.
It never replaces P-CRAFT PINO. If the bound exceeds a caller-declared
application tolerance, this wrapper abstains and invokes the supplied exact
reference callback. In current cloud experiments that callback may be the
independent voxel hard-cut integral only; it must not be labelled Cherchi.
"""
from __future__ import annotations

from pathlib import Path
import math
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
        metrics = package["metrics"]
        self.input_mean = torch.as_tensor(package["input_mean"], dtype=torch.float32)
        self.input_scale = torch.as_tensor(package["input_scale"], dtype=torch.float32)
        self.input_min = torch.as_tensor(metrics["training_feature_q01"], dtype=torch.float32)
        self.input_max = torch.as_tensor(metrics["training_feature_q99"], dtype=torch.float32)
        self.target_log_mean = torch.as_tensor(package["target_log_mean"], dtype=torch.float32)
        self.target_log_scale = torch.as_tensor(package["target_log_scale"], dtype=torch.float32)
        self.q90 = float(metrics["calibration_standardized_residual_q90"])
        self.q95 = float(metrics["calibration_standardized_residual_q95"])
        self.feature_ood_threshold = float(metrics["feature_ood_standardized_max_q95"])
        self.query_q90 = float(metrics["calibration_query_upper_residual_q90"])
        self.query_q95 = float(metrics["calibration_query_upper_residual_q95"])
        self.family_query_quantiles = metrics.get("family_query_upper_residual_quantiles", {})
        if not (torch.isfinite(self.input_mean).all() and
                torch.isfinite(self.input_scale).all() and
                torch.isfinite(self.input_min).all() and
                torch.isfinite(self.input_max).all() and
                torch.isfinite(self.target_log_mean).all() and
                torch.isfinite(self.target_log_scale).all()):
            raise ValueError("nonfinite UQNO normalization parameters")
        if bool((self.input_scale <= 0).any()) or bool((self.input_max < self.input_min).any()) or float(self.target_log_scale) <= 0:
            raise ValueError("invalid UQNO normalization scale")
        if not (0 < self.q90 < 100 and 0 < self.q95 < 100):
            raise ValueError("invalid conformal residual quantiles")
        if not (0 < self.feature_ood_threshold < 100):
            raise ValueError("invalid geometry-calibrated OOD threshold")
        if not (math.isfinite(self.query_q90) and math.isfinite(self.query_q95)
                and 0 <= self.query_q90 < 100 and 0 <= self.query_q95 < 100):
            raise ValueError("invalid query-marginal conformal residual quantiles")
        for family_name, family_values in self.family_query_quantiles.items():
            q90 = float(family_values["q90"])
            q95 = float(family_values["q95"])
            if not (math.isfinite(q90) and math.isfinite(q95)
                    and 0 <= q90 < 100 and 0 <= q95 < 100):
                raise ValueError(f"invalid family calibration quantiles: {family_name}")
            if int(family_values.get("calibration_geometries", 0)) < 8:
                raise ValueError(f"insufficient family calibration geometries: {family_name}")
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
    def predict_query_upper_bound(self, features, *, confidence: float = .95, family: str | None = None):
        """Marginal one-query upper bound; not simultaneous geometry coverage."""
        if confidence not in (.90, .95):
            raise ValueError("only calibrated 90% or 95% query bounds are available")
        x = torch.as_tensor(features, dtype=torch.float32)
        if x.ndim == 1:
            x = x.unsqueeze(0)
        if x.ndim != 2 or x.shape[1] != self.input_mean.numel():
            raise ValueError("feature shape mismatch")
        if not bool(torch.isfinite(x).all()):
            raise ValueError("features must be finite")
        x = ((x-self.input_mean)/self.input_scale).clamp(-10, 10)
        mu, _ = self.model(x)
        log_mu = mu*self.target_log_scale+self.target_log_mean
        family_info = self.family_query_quantiles.get(family) if family is not None else None
        if family_info is not None:
            q = float(family_info["q90"] if confidence == .90 else family_info["q95"])
            calibration_source = family_info.get("source", "family_conditional_marginal_query")
        else:
            q = self.query_q90 if confidence == .90 else self.query_q95
            calibration_source = "global_marginal_query_fallback"
        median = torch.exp(log_mu)
        upper = torch.exp(log_mu+q)
        return {
            "target": self.target,
            "confidence": confidence,
            "calibration_unit": "family_conditional_marginal_query" if family_info is not None else "global_marginal_query_fallback",
            "family": family,
            "calibration_source": calibration_source,
            "median": median,
            "upper": upper,
            "log_residual_quantile": q,
        }

    @torch.no_grad()
    def should_fallback(self, features, *, error_tolerance: float,
                        confidence: float = .95, family: str | None = None):
        if error_tolerance <= 0 or not torch.isfinite(torch.tensor(error_tolerance)):
            raise ValueError("error_tolerance must be finite and positive")
        try:
            raw = torch.as_tensor(features, dtype=torch.float32)
            if raw.ndim == 1:
                raw = raw.unsqueeze(0)
            if raw.ndim != 2 or raw.shape[1] != self.input_mean.numel() or not bool(torch.isfinite(raw).all()):
                raise ValueError("invalid feature shape or nonfinite values")
            # Per-feature 1-99% checks create multiple-comparison false positives
            # for 349-dimensional inputs. Use a geometry-calibrated max score.
            standardized_max = ((raw-self.input_mean)/self.input_scale).abs().amax(dim=1)
            if bool((standardized_max > self.feature_ood_threshold).any()):
                return {
                    "fallback": True, "interval": None,
                    "error_tolerance": float(error_tolerance),
                    "reason": "FEATURE_OUTSIDE_GEOMETRY_CALIBRATED_OOD_ENVELOPE",
                }
            interval = self.predict_query_upper_bound(raw, confidence=confidence, family=family)
            fallback = bool((interval["upper"] > error_tolerance).any())
            return {
                "fallback": fallback,
                "interval": interval,
                "error_tolerance": float(error_tolerance),
                "reason": "UQNO_QUERY_UPPER_BOUND_EXCEEDS_TOLERANCE"
                          if fallback else "UQNO_QUERY_UPPER_BOUND_WITHIN_TOLERANCE",
            }
        except (ValueError, RuntimeError, KeyError):
            return {
                "fallback": True, "interval": None,
                "error_tolerance": float(error_tolerance),
                "reason": "INVALID_OR_UNCALIBRATED_FEATURES",
            }

    def predict_or_fallback(self, features, approximate_result: Any,
                            exact_fallback: Callable[[], Any], *,
                            error_tolerance: float, confidence: float = .95,
                            family: str | None = None):
        """Fail closed: exact_fallback is called on uncertainty or invalid features.

        The callback must compute the exact reference for the current task.
        This wrapper does not infer whether that callback is Cherchi or a
        discrete voxel hard-cut integral; callers must record its provenance.
        """
        decision = self.should_fallback(
            features, error_tolerance=error_tolerance, confidence=confidence,
            family=family,
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
