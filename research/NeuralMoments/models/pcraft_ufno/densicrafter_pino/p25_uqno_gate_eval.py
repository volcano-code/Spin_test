"""P25.5: evaluate marginal-query UQNO abstention on geometry-held-out cases.

The calibration split is geometry-disjoint. The reported query coverage is
marginal over one query at a time; it is NOT simultaneous coverage of every
query/resolution belonging to a complete geometry. Geometry-any-fallback is
reported separately as an operational diagnostic.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .p25_uqno_gate import CalibratedUQNO

TOLERANCES = (0.05, 0.10, 0.20, 0.30, 0.50, 1.00)


def _evaluate_target(report, checkpoint, target):
    gate = CalibratedUQNO(checkpoint, target=target)
    label_key = "hardcut_error" if target == "hardcut" else "analytic_p0_error"
    rows = report["test_cases"]
    groups = defaultdict(list)
    for row in rows:
        groups[row["geometry_id"]].append(row)
    if len(groups) < 8 or len(rows) < 16:
        raise ValueError("insufficient held-out geometries or query rows")

    output = {}
    for tolerance in TOLERANCES:
        query_fallback = []
        accepted_errors = []
        unsafe_accepted = []
        ood_count = 0
        upper_covered = []
        family_counts = defaultdict(lambda: {"queries": 0, "fallback": 0, "accepted": 0, "unsafe": 0, "in_domain": 0, "upper_covered": 0})
        geometry_any_fallback = []
        for row in rows:
            decision = gate.should_fallback(
                row["features"], error_tolerance=tolerance, confidence=.95
            )
            fallback = bool(decision["fallback"])
            actual = float(row[label_key])
            query_fallback.append(fallback)
            family = family_counts[row["family"]]
            family["queries"] += 1
            family["fallback"] += int(fallback)
            if decision.get("reason") == "FEATURE_OUTSIDE_GEOMETRY_CALIBRATED_OOD_ENVELOPE":
                ood_count += 1
            if decision.get("interval") is not None:
                covered = actual <= float(decision["interval"]["upper"].reshape(-1)[0])
                upper_covered.append(covered)
                family["in_domain"] += 1
                family["upper_covered"] += int(covered)
            if not fallback:
                accepted_errors.append(actual)
                unsafe = actual > tolerance
                unsafe_accepted.append(unsafe)
                family["accepted"] += 1
                family["unsafe"] += int(unsafe)

        for gid, geometry_rows in sorted(groups.items()):
            decisions = [
                gate.should_fallback(
                    row["features"], error_tolerance=tolerance, confidence=.95
                )["fallback"]
                for row in geometry_rows
            ]
            geometry_any_fallback.append(any(decisions))

        accepted = len(accepted_errors)
        output[str(tolerance)] = {
            "calibration_unit": "marginal_query",
            "query_count": len(rows),
            "fallback_query_count": sum(query_fallback),
            "fallback_query_fraction": sum(query_fallback) / len(query_fallback),
            "accepted_query_count": accepted,
            "accepted_actual_error_mean": sum(accepted_errors) / accepted if accepted else None,
            "unsafe_accepted_query_count": sum(unsafe_accepted),
            "unsafe_acceptance_fraction": sum(unsafe_accepted) / accepted if accepted else None,
            "ood_query_count": ood_count,
            "in_domain_query_count": len(upper_covered),
            "empirical_upper_bound_coverage_in_domain": (
                sum(upper_covered) / len(upper_covered) if upper_covered else None
            ),
            "geometry_count": len(groups),
            "geometry_any_fallback_count": sum(geometry_any_fallback),
            "geometry_any_fallback_fraction": sum(geometry_any_fallback) / len(groups),
            "by_geometry_family": {
                family: {
                    **values,
                    "fallback_fraction": values["fallback"] / values["queries"],
                    "unsafe_acceptance_fraction": (
                        values["unsafe"] / values["accepted"] if values["accepted"] else None
                    ),                    "empirical_upper_bound_coverage": (
                        values["upper_covered"] / values["in_domain"] if values["in_domain"] else None
                    ),
                }
                for family, values in sorted(family_counts.items())
            },
        }
    return output


def run(report_path, checkpoint_dir):
    report = json.loads(Path(report_path).read_text())
    checkpoint_dir = Path(checkpoint_dir)
    hard = _evaluate_target(
        report, checkpoint_dir / "w6_p25_uqno_hardcut.pt", "hardcut"
    )
    analytic = _evaluate_target(
        report, checkpoint_dir / "w6_p25_uqno_analytic_p0.pt", "analytic_p0"
    )
    return {
        "schema": "W6_P25_5_MARGINAL_QUERY_GATE_EVALUATION_V1",
        "unique_test_geometries": len({x["geometry_id"] for x in report["test_cases"]}),
        "test_query_count": len(report["test_cases"]),
        "declared_error_tolerances": list(TOLERANCES),
        "confidence": .95,
        "calibration_unit": "marginal_query_with_geometry_disjoint_train_calibration_test",
        "simultaneous_geometry_coverage_claim": False,
        "hardcut_error_gate": hard,
        "analytic_p0_error_gate": analytic,
        "decision": "PILOT_ONLY_NO_PRODUCTION_GATE",
        "claims": {
            "geometry_disjoint_test": True,
            "PINO_remains_primary": True,
            "fallback_is_caller_supplied": True,
            "Cherchi": False, "native_Newton": False,
            "FEM_FEA": False, "512_cube": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.report, args.checkpoint_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({
        "hardcut": result["hardcut_error_gate"],
        "analytic": result["analytic_p0_error_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
