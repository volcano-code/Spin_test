"""M5 optional real Cherchi W0/W2 exact-reference parity after one native call.

M4 authenticates source/Boolean, native material-region subset and exact r_D.
This bridge uses the *saved same-call material* to recheck all ten moments
through independently pinned W2 mathematical code, without reconstructing
Cherchi source, running an extra Boolean, or authorizing training.
"""
from __future__ import annotations

from fractions import Fraction
import math

from .native_teacher_replay import (ReplayRejected, audit_live_native_once,
                                    compare_floats, vector10)
from .cross_oracle_gate import cross_check_exact_boundary


def audit_native_w0_w2_once(*, evaluator, problem, c, pins):
    """Run real M4 native replay once; only then check W2 exact oracle.

    Callers must use a real InProcessCherchiEvaluator. The M4 live gate itself
    enforces genuine module type, SHA pins and independent exact native regions.
    A symbolic/mock unit test cannot turn this into a physical certificate.
    """
    baseline = audit_live_native_once(evaluator=evaluator,problem=problem,c=c,pins=pins)
    if (baseline.get("native_execution_observed") is not True or
            baseline.get("native_region_proved") is not True or
            baseline.get("mathematical_replay_passed") is not True):
        raise ReplayRejected("M4_GENUINE_NATIVE_REPLAY_REQUIRED")
    material = evaluator.material(c)  # Read saved source attachment; no new Boolean.
    try:
        density = float(evaluator.request.material_density)
    except (ValueError,TypeError,OverflowError,AttributeError) as exc:
        raise ReplayRejected("FROZEN_DESIGN_DENSITY_MISSING") from exc
    if not math.isfinite(density) or density <= 0:
        raise ReplayRejected("INVALID_DESIGN_DENSITY")
    rho = Fraction.from_float(density)
    density_token = f"{rho.numerator}/{rho.denominator}"
    result = cross_check_exact_boundary(
        material.get("variable_rational_vertices"),
        material.get("variable_faces"),density_token)
    expected = [Fraction(x) for x in result["exact_r10"]]
    report_r = vector10(material.get("variable_raw_moments"),"saved_native_rD")
    delta,conversion_bound = compare_floats(report_r,expected,label="W2_cross_oracle_rD")
    return {
        "schema":"W0_M5_LIVE_W0_W2_PARITY_V1",
        "m4_native_evidence":baseline,
        "w2_exact_math_reference":result,
        "native_w2_r10_max_absolute_error":delta,
        "binary64_conversion_bound":conversion_bound,
        "additional_cherchi_source_calls":0,
        "complete_partition_certificate":False,
        "smooth_neighborhood_certificate":False,
        "training_admissible":False,
        "status":"NATIVE_PARITY_CHECKED_FULL_PARTITION_AND_DERIVATIVE_PENDING",
    }
