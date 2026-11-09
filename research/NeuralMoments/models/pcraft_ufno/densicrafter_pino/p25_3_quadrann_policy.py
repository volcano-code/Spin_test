"""P25.3: fail-closed geometry-conditional QuadrANN activation policy.

P-CRAFT PINO remains the default. QuadrANN is eligible only for geometry
families explicitly admitted by an external, geometry-disjoint validation
receipt and only when a validated UQNO hard-cut upper error bound is below
the caller's tolerance. If UQNO reports high risk, use PINO-only. If input is
OOD/invalid or exactness is explicitly required, call the caller's exact
fallback. This policy never treats analytic-P0 calibration as hard-cut
calibration and never labels a voxel hard-cut callback as Cherchi.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class QuadrANNPolicyReceipt:
    """External validation receipt; never synthesize this from P24.7 means."""
    validation_status: str
    target: str
    admitted_families: tuple[str, ...]
    evidence_id: str

    @classmethod
    def from_mapping(cls, value: dict[str, Any]):
        required = ("validation_status", "target", "admitted_families", "evidence_id")
        if any(k not in value for k in required):
            raise ValueError("incomplete QuadrANN validation receipt")
        families = tuple(sorted(set(str(x) for x in value["admitted_families"])))
        if not value["evidence_id"]:
            raise ValueError("missing validation evidence id")
        return cls(
            validation_status=str(value["validation_status"]),
            target=str(value["target"]),
            admitted_families=families,
            evidence_id=str(value["evidence_id"]),
        )


class ConditionalQuadrANNPolicy:
    def __init__(self, uqno_gate, receipt: QuadrANNPolicyReceipt):
        self.uqno_gate = uqno_gate
        self.receipt = receipt

    def decide(
        self, *, family: str, features, error_tolerance: float,
        confidence: float = .95, exact_required: bool = False,
    ) -> dict[str, Any]:
        if error_tolerance <= 0:
            raise ValueError("error_tolerance must be positive")
        if exact_required:
            return {
                "route": "EXACT_FALLBACK",
                "reason": "CALLER_REQUIRES_EXACT",
                "evidence_id": self.receipt.evidence_id,
            }
        if self.receipt.validation_status != "VALIDATED":
            return {
                "route": "PINO_ONLY",
                "reason": "UQNO_OR_CONDITIONAL_POLICY_NOT_VALIDATED",
                "evidence_id": self.receipt.evidence_id,
            }
        if self.receipt.target != "hardcut":
            return {
                "route": "PINO_ONLY",
                "reason": "WRONG_ERROR_TARGET_FOR_MATERIAL_DESIGN",
                "evidence_id": self.receipt.evidence_id,
            }
        if family not in self.receipt.admitted_families:
            return {
                "route": "PINO_ONLY",
                "reason": "GEOMETRY_FAMILY_NOT_ADMITTED",
                "evidence_id": self.receipt.evidence_id,
            }
        decision = self.uqno_gate.should_fallback(
            features, error_tolerance=error_tolerance, confidence=confidence
        )
        reason = decision.get("reason", "")
        if reason in (
            "FEATURE_OUTSIDE_TRAINING_01_99_ENVELOPE",
            "INVALID_OR_UNCALIBRATED_FEATURES",
        ):
            return {
                "route": "EXACT_FALLBACK",
                "reason": reason,
                "uqno_decision": decision,
                "evidence_id": self.receipt.evidence_id,
            }
        if decision.get("fallback", True):
            return {
                "route": "PINO_ONLY",
                "reason": "QUADRANN_RISK_EXCEEDS_TOLERANCE",
                "uqno_decision": decision,
                "evidence_id": self.receipt.evidence_id,
            }
        return {
            "route": "PINO_PLUS_QUADRANN",
            "reason": "FAMILY_ADMITTED_AND_UQNO_RISK_WITHIN_TOLERANCE",
            "uqno_decision": decision,
            "evidence_id": self.receipt.evidence_id,
        }

    def execute(
        self, *, family: str, features, pino_result: Any,
        quadrann_result: Any, exact_fallback: Callable[[], Any],
        error_tolerance: float, confidence: float = .95,
        exact_required: bool = False,
    ) -> dict[str, Any]:
        decision = self.decide(
            family=family, features=features,
            error_tolerance=error_tolerance,
            confidence=confidence, exact_required=exact_required,
        )
        route = decision["route"]
        if route == "EXACT_FALLBACK":
            return {
                "value": exact_fallback(),
                "source": "CALLER_SUPPLIED_EXACT_FALLBACK",
                "decision": decision,
            }
        if route == "PINO_PLUS_QUADRANN":
            return {
                "value": quadrann_result,
                "source": "P_CRAFT_PINO_WITH_OPTIONAL_QUADRANN",
                "decision": decision,
            }
        return {
            "value": pino_result,
            "source": "P_CRAFT_PINO_PRIMARY",
            "decision": decision,
        }
