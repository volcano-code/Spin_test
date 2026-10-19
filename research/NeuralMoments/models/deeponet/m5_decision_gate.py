"""M5: untrusted surrogate step proposals, requiring independent native re-evaluation."""
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class GatePolicy:
    damping: float = 1e-2
    trust_radius: float = 0.1
    max_condition: float = 1e9
    min_predicted_reduction: float = 0.0

def _vector(x, shape):
    a = np.asarray(x, dtype=np.float64)
    if a.shape != shape or not np.isfinite(a).all():
        raise ValueError("INVALID_FINITE_SHAPE")
    return a.copy()

def propose_step(r, jacobian, target, *, native_c, policy=GatePolicy(),
                 derivative_status="UNKNOWN", identity_verified=False,
                 tangent_basis=None):
    """Return a *candidate*, never a commit. J is native dr/dc or 10xk tangent."""
    def reject(reason):
        return dict(admitted=False, reason=reason, candidate_c=None,
                    predicted_reduction=None, requires_native_recheck=True)
    if not identity_verified or derivative_status != "VALID":
        return reject("UNVERIFIED_NATIVE_IDENTITY_OR_DERIVATIVE")
    try:
        c = _vector(native_c, (10,))
        r = _vector(r, (10,))
        goal = _vector(target, (10,))
        if not 0.999999 <= np.linalg.norm(c) <= 1.000001:
            return reject("NATIVE_C_NOT_NORMALIZED")
        if any(not math.isfinite(v) or v <= 0 for v in
               (policy.damping, policy.trust_radius, policy.max_condition)):
            return reject("INVALID_POLICY")
        if (not math.isfinite(policy.min_predicted_reduction)
                or policy.min_predicted_reduction < 0):
            return reject("INVALID_POLICY")
        if tangent_basis is None:
            B = np.eye(10)
            J = _vector(jacobian, (10, 10))
            category = "AMBIENT_10X10"
        else:
            raw = np.asarray(tangent_basis, dtype=np.float64)
            if raw.ndim != 2 or raw.shape[0] != 10 or not 1 <= raw.shape[1] <= 9:
                return reject("INVALID_TANGENT_BASIS")
            k = raw.shape[1]
            B = _vector(raw, (10, k))
            J = _vector(jacobian, (10, k))
            if not np.allclose(B.T @ B, np.eye(k), rtol=1e-8, atol=1e-8):
                return reject("NON_ORTHONORMAL_TANGENT_BASIS")
            if np.max(np.abs(c @ B)) > 1e-8:
                return reject("TANGENT_NOT_ORTHOGONAL_TO_NATIVE_C")
            category = "TANGENT_10XK"
        residual = r - goal
        H = J.T @ J + policy.damping * np.eye(J.shape[1])
        condition = float(np.linalg.cond(H))
        if not np.isfinite(condition) or condition > policy.max_condition:
            return reject("ILL_CONDITIONED_SYSTEM")
        step = B @ (-np.linalg.solve(H, J.T @ residual))
        size = float(np.linalg.norm(step))
        if size > policy.trust_radius:
            step *= policy.trust_radius / size
        candidate = c + step
        norm = float(np.linalg.norm(candidate))
        if not np.isfinite(norm) or norm <= 1e-14:
            return reject("INVALID_CANDIDATE")
        candidate /= norm
        if float(c @ candidate) <= 0:
            return reject("PROJECTIVE_SIGN_FLIP")
        dc = candidate - c
        linear_change = J @ (dc if tangent_basis is None else B.T @ dc)
        predicted = residual + linear_change
        gain = 0.5 * float(residual @ residual - predicted @ predicted)
        if gain <= policy.min_predicted_reduction:
            return reject("INSUFFICIENT_PREDICTED_REDUCTION")
        return dict(admitted=True, reason="CANDIDATE_ONLY",
                    candidate_c=candidate.tolist(), predicted_reduction=gain,
                    step_native_norm=float(np.linalg.norm(dc)),
                    condition=condition, jacobian_type=category,
                    requires_native_recheck=True)
    except (ValueError, TypeError, np.linalg.LinAlgError):
        return reject("INVALID_OR_SINGULAR_INPUT")

def verify_with_native(proposal, native_evaluator, target, *, original_c,
                       max_true_increase=0.0):
    """Caller-authenticated native evaluator required; no material certificate is implied."""
    def reject(reason):
        return dict(accepted=False, reason=reason, requires_external_commit=True)
    if not proposal.get("admitted") or proposal.get("candidate_c") is None:
        return reject("NO_ADMITTED_CANDIDATE")
    if native_evaluator is None:
        return reject("NATIVE_EVALUATOR_UNAVAILABLE")
    try:
        if not math.isfinite(max_true_increase) or max_true_increase < 0:
            return reject("INVALID_TOLERANCE")
        old_c = _vector(original_c, (10,))
        new_c = _vector(proposal["candidate_c"], (10,))
        if not 0.999999 <= np.linalg.norm(old_c) <= 1.000001:
            return reject("INVALID_ORIGINAL_C")
        if not 0.999999 <= np.linalg.norm(new_c) <= 1.000001 or old_c @ new_c <= 0:
            return reject("INVALID_CANDIDATE_C")
        old = _vector(native_evaluator(old_c.copy()), (10,))
        new = _vector(native_evaluator(new_c.copy()), (10,))
        goal = _vector(target, (10,))
        before = 0.5 * float(np.sum((old-goal)**2))
        after = 0.5 * float(np.sum((new-goal)**2))
        if after > before + max_true_increase:
            return reject("NATIVE_OBJECTIVE_DID_NOT_IMPROVE")
        return dict(accepted=True, reason="NATIVE_OBJECTIVE_CHECK_ONLY",
                    native_loss_before=before, native_loss_after=after,
                    requires_external_commit=True)
    except (ValueError, TypeError, ArithmeticError, RuntimeError):
        return reject("NATIVE_RECHECK_FAILED")
