"""W5 M6: budgeted surrogate decisions with independent *analytic P0* replay.

This module is deliberately not a Cherchi or arbitrary CAD evaluator. It can
accept a candidate ONLY in a verified horizontal-cut sphere-cap experiment.
It cannot certify native mesh material, train from W2 records, modify geometry,
or silently promote the legacy M5 identity_verified boolean to a native proof.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import time
from typing import Mapping

import numpy as np

from .m5_decision_gate import GatePolicy, propose_step
from .native_p0 import cap_jacobian_native, cap_moments, dh_native_c, native_vertical_c


@dataclass(frozen=True)
class ReplayPolicy:
    max_truth_calls: int = 4       # Includes rejected/failed evaluation attempts.
    max_backtracks: int = 2
    shrink: float = 0.5
    trust_radius: float = 0.15
    damping: float = 0.01
    min_true_drop: float = 1e-11
    min_relative_drop: float = 1e-8

    def validate(self) -> None:
        if (type(self.max_truth_calls) is not int or self.max_truth_calls < 2
                or type(self.max_backtracks) is not int or self.max_backtracks < 0
                or self.max_backtracks + 2 > self.max_truth_calls):
            raise ValueError("INVALID_QUERY_BUDGET")
        if (not all(math.isfinite(v) for v in
                    (self.shrink, self.trust_radius, self.damping,
                     self.min_true_drop, self.min_relative_drop))
                or not 0 < self.shrink < 1 or self.trust_radius <= 0
                or self.damping <= 0 or self.min_true_drop < 0
                or self.min_relative_drop < 0):
            raise ValueError("INVALID_ROLLOUT_POLICY")


def _v10(value, name: str) -> np.ndarray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}_INVALID") from exc
    if array.shape != (10,) or not np.isfinite(array).all():
        raise ValueError(f"{name}_INVALID")
    return array.copy()


def _J10(value) -> np.ndarray:
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("PREDICTED_J_INVALID") from exc
    if matrix.shape != (10, 10) or not np.isfinite(matrix).all():
        raise ValueError("PREDICTED_J_INVALID")
    return matrix.copy()


def _scalar(value, name: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name}_INVALID") from exc
    if not math.isfinite(x):
        raise ValueError(f"{name}_INVALID")
    return x


class AnalyticCapOracle:
    """Finite-sample analytic truth only; rejects arbitrary native quadrics.

    `spec_sha256` authenticates *this canonical analytic specification*, not an
    OBJ/CAD original/F/D byte identity or verified Cherchi geometry.
    """

    def __init__(self, radius: float, density: float):
        self.radius = _scalar(radius, "RADIUS")
        self.density = _scalar(density, "DENSITY")
        if self.radius <= 0 or self.density <= 0:
            raise ValueError("INVALID_P0_GEOMETRY")
        self.calls = 0
        spec = {"family": "analytic_sphere_cap_horizontal_only", "radius": self.radius,
                "density": self.density, "coordinate_frame": "original_origin_zero",
                "truth": "ANALYTIC_P0_NOT_NATIVE_CHERCHI"}
        self.spec_sha256 = hashlib.sha256(json.dumps(
            spec, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")).hexdigest()

    def moments(self, c_native) -> np.ndarray:
        """One independently evaluated truth query (including failed attempts)."""
        self.calls += 1
        c = _v10(c_native, "NATIVE_C")
        if abs(np.linalg.norm(c) - 1) > 1e-12 or c[3] <= 0:
            raise ValueError("NONUNIT_OR_NEGATIVE_NATIVE_C")
        if np.max(np.abs(c[[1, 2, 4, 5, 6, 7, 8, 9]])) > 1e-12:
            raise ValueError("UNSUPPORTED_NONPLANAR_NATIVE_C")
        h = -c[0] / c[3]
        if not -self.radius < h < self.radius:
            raise ValueError("CUT_OUTSIDE_SMOOTH_INTERIOR")
        return cap_moments(self.radius, h, density=self.density)


def check_w2_manifest(manifest: Mapping) -> dict:
    """Report but NEVER approve W2 pre-W0 manifest as independent teacher truth.

    Counts and self-asserted proof do not provide independent material seals.
    """
    if not isinstance(manifest, Mapping) or manifest.get("schema") != "w2-cherchi-teacher-v1-pre-w0":
        raise ValueError("UNRECOGNIZED_W2_MANIFEST")
    runs, samples = manifest.get("native_teacher_runs"), manifest.get("training_samples")
    if (type(runs) is not int or runs < 0
            or type(samples) is not int or samples < 0):
        raise ValueError("INVALID_W2_SAMPLE_COUNTS")
    return {"teacher_training_admissible": False,
            "declared_native_runs": runs, "declared_training_samples": samples,
            "reason": "W2 pre-W0 manifest does not certify independently pinned F/D CAD material and derivatives"}


def guarded_analytic_step(*, radius: float, density: float, current_h: float,
                          target_r, predicted_r, predicted_Jc,
                          policy: ReplayPolicy = ReplayPolicy()) -> dict:
    """Propose one horizontal-cut update, verify each trial with analytic truth.

    Predicted arrays may come from a network but are ALWAYS treated as
    untrusted. The M5 identity flag is set only for *this validated analytic
    fixture's coefficient/frame*, never as native-teacher evidence. The
    candidate is *not* automatically committed by the real Spin optimizer.
    """
    policy.validate()
    started = time.perf_counter()
    oracle = AnalyticCapOracle(radius, density)
    h = _scalar(current_h, "CUT_HEIGHT")
    if not -oracle.radius < h < oracle.radius:
        raise ValueError("CUT_OUTSIDE_SMOOTH_INTERIOR")
    goal, estimate, J = (_v10(target_r, "TARGET_R"),
                         _v10(predicted_r, "PREDICTED_R"), _J10(predicted_Jc))
    c = native_vertical_c(h)
    scales = oracle.density * np.array([oracle.radius ** 3] +
                                        [oracle.radius ** 4] * 3 +
                                        [oracle.radius ** 5] * 6)
    tangent = dh_native_c(h)
    tangent /= np.linalg.norm(tangent)
    basis = tangent.reshape(10, 1)

    def result(*, accepted: bool, reason: str, after: float | None,
               next_c, proposed: dict | None = None, attempt: int = 0) -> dict:
        return {"accepted": accepted, "reason": reason,
                "truth_source": "ANALYTIC_P0_ONLY",
                "geometry_spec_sha256": oracle.spec_sha256,
                "teacher_training_admissible": False,
                "native_cherchi_calls": 0,
                "truth_calls": oracle.calls,
                "attempts": attempt,
                "current_c": c.tolist(),
                "next_c": next_c.tolist(),
                "loss_before": before,
                "loss_after": after,
                "actual_drop": None if after is None else before - after,
                "predicted_drop": None if proposed is None else proposed.get("predicted_reduction"),
                "requires_external_commit": True,
                "wall_seconds": time.perf_counter() - started}

    # One actual truth read for the original state; it is NOT the model's r.
    truth = oracle.moments(c)
    before = 0.5 * float(np.linalg.norm((truth - goal) / scales) ** 2)
    # M5's 10xk tensor corresponds to dr/d(native ambient c) times the
    # orthonormal one-dimensional tangent basis. W0 r and Jc share scaling.
    proposal = propose_step(estimate / scales, (J / scales[:, None]) @ basis,
                            goal / scales, native_c=c,
                            policy=GatePolicy(damping=policy.damping,
                                              trust_radius=policy.trust_radius),
                            derivative_status="VALID", identity_verified=True,
                            tangent_basis=basis)
    if not proposal["admitted"]:
        return result(accepted=False, reason="SURROGATE_REJECTED:"+proposal["reason"],
                      after=before, next_c=c, proposed=proposal)

    proposed_c = _v10(proposal["candidate_c"], "CANDIDATE_C")
    for attempt in range(policy.max_backtracks + 1):
        if oracle.calls >= policy.max_truth_calls:
            return result(accepted=False, reason="TRUTH_QUERY_BUDGET_EXHAUSTED",
                          after=before, next_c=c, proposed=proposal, attempt=attempt)
        alpha = policy.shrink ** attempt
        trial = c + alpha * (proposed_c - c)
        trial_norm = float(np.linalg.norm(trial))
        if trial_norm < 1e-14 or not np.isfinite(trial_norm):
            return result(accepted=False, reason="INVALID_TRIAL_COEFFICIENT",
                          after=before, next_c=c, proposed=proposal, attempt=attempt)
        trial /= trial_norm
        # No projective sign inversion and no tangent-plane escape.
        if float(c @ trial) <= 0:
            return result(accepted=False, reason="PROJECTIVE_SIGN_FLIP",
                          after=before, next_c=c, proposed=proposal, attempt=attempt)
        try:
            trial_truth = oracle.moments(trial)
        except (ValueError, ArithmeticError):
            continue  # Failed queries also count against the budget.
        after = 0.5 * float(np.linalg.norm((trial_truth - goal) / scales) ** 2)
        required = policy.min_true_drop + policy.min_relative_drop * before
        if before - after > required:
            return result(accepted=True, reason="ANALYTIC_P0_DECREASE_ONLY",
                          after=after, next_c=trial,
                          proposed=proposal, attempt=attempt+1)
    return result(accepted=False, reason="NO_INDEPENDENT_TRUE_DECREASE_FALLBACK",
                  after=before, next_c=c, proposed=proposal,
                  attempt=policy.max_backtracks+1)
