import unittest

from research.NeuralMoments.models.pcraft_ufno.densicrafter_pino.p25_3_quadrann_policy import (
    ConditionalQuadrANNPolicy, QuadrANNPolicyReceipt,
)


class FakeGate:
    def __init__(self, fallback=False, reason="UQNO_UPPER_BOUND_WITHIN_TOLERANCE"):
        self.fallback = fallback
        self.reason = reason

    def should_fallback(self, features, *, error_tolerance, confidence):
        return {
            "fallback": self.fallback,
            "reason": self.reason,
            "upper": 0.02 if not self.fallback else 0.4,
        }


def receipt(status="VALIDATED", target="hardcut", families=("box",)):
    return QuadrANNPolicyReceipt(
        validation_status=status,
        target=target,
        admitted_families=tuple(families),
        evidence_id="independent-heldout-validation-v1",
    )


class P25_3ConditionalPolicyTests(unittest.TestCase):
    def test_admitted_family_and_low_risk_activates_quadrann(self):
        policy = ConditionalQuadrANNPolicy(FakeGate(), receipt())
        result = policy.execute(
            family="box", features=[0.0], pino_result="pino",
            quadrann_result="pino+q", exact_fallback=lambda: "exact",
            error_tolerance=.1,
        )
        self.assertEqual(result["value"], "pino+q")
        self.assertEqual(result["decision"]["route"], "PINO_PLUS_QUADRANN")

    def test_unvalidated_receipt_never_activates_quadrann(self):
        policy = ConditionalQuadrANNPolicy(FakeGate(), receipt(status="PILOT_ONLY"))
        result = policy.decide(
            family="box", features=[0.0], error_tolerance=.1,
        )
        self.assertEqual(result["route"], "PINO_ONLY")

    def test_non_admitted_family_uses_pino_only(self):
        policy = ConditionalQuadrANNPolicy(FakeGate(), receipt(families=("box",)))
        result = policy.decide(
            family="ellipsoid", features=[0.0], error_tolerance=.1,
        )
        self.assertEqual(result["route"], "PINO_ONLY")
        self.assertEqual(result["reason"], "GEOMETRY_FAMILY_NOT_ADMITTED")

    def test_high_risk_uses_pino_only_not_quadrann(self):
        gate = FakeGate(fallback=True, reason="UQNO_UPPER_BOUND_EXCEEDS_TOLERANCE")
        policy = ConditionalQuadrANNPolicy(gate, receipt())
        result = policy.decide(
            family="box", features=[0.0], error_tolerance=.1,
        )
        self.assertEqual(result["route"], "PINO_ONLY")

    def test_ood_forces_exact_fallback(self):
        gate = FakeGate(fallback=True, reason="FEATURE_OUTSIDE_TRAINING_01_99_ENVELOPE")
        policy = ConditionalQuadrANNPolicy(gate, receipt())
        result = policy.execute(
            family="box", features=[9.0], pino_result="pino",
            quadrann_result="pino+q", exact_fallback=lambda: "voxel-hardcut",
            error_tolerance=.1,
        )
        self.assertEqual(result["value"], "voxel-hardcut")
        self.assertEqual(result["decision"]["route"], "EXACT_FALLBACK")

    def test_wrong_error_target_disables_quadrann(self):
        policy = ConditionalQuadrANNPolicy(
            FakeGate(), receipt(target="analytic_p0")
        )
        self.assertEqual(
            policy.decide(family="box", features=[0.0], error_tolerance=.1)["route"],
            "PINO_ONLY",
        )

    def test_exact_required_overrides_all_neural_routes(self):
        policy = ConditionalQuadrANNPolicy(FakeGate(), receipt())
        result = policy.decide(
            family="box", features=[0.0], error_tolerance=.1,
            exact_required=True,
        )
        self.assertEqual(result["route"], "EXACT_FALLBACK")


if __name__ == "__main__":
    unittest.main()
