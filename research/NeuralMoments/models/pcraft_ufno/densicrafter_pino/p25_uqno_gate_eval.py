"""P25.6: marginal-query UQNO gate evaluation with geometry-cluster bootstrap.

Calibration and test geometries are disjoint. Query-level coverage is
marginal, not simultaneous across all queries of a geometry. Confidence
intervals resample whole geometries to respect within-geometry dependence.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from .p25_uqno_gate import CalibratedUQNO

TOLERANCES = (0.05, 0.10, 0.20, 0.30, 0.50, 1.00)
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20261110


def _cluster_bootstrap_ratio_ci(clusters, numerator_key, denominator_key,
                                *, replicates=BOOTSTRAP_REPLICATES,
                                seed=BOOTSTRAP_SEED):
    """Percentile CI for a ratio, resampling independent geometry clusters."""
    if not clusters:
        return None
    if sum(int(c[denominator_key]) for c in clusters) <= 0:
        return None
    rng = random.Random(seed)
    n = len(clusters)
    estimates = []
    for _ in range(replicates):
        sample = [clusters[rng.randrange(n)] for _ in range(n)]
        numerator = sum(int(c[numerator_key]) for c in sample)
        denominator = sum(int(c[denominator_key]) for c in sample)
        if denominator:
            estimates.append(numerator / denominator)
    estimates.sort()
    if not estimates:
        return None
    lo = estimates[int(0.025 * (len(estimates) - 1))]
    hi = estimates[int(0.975 * (len(estimates) - 1))]
    point_num = sum(int(c[numerator_key]) for c in clusters)
    point_den = sum(int(c[denominator_key]) for c in clusters)
    return {
        "estimate": point_num / point_den,
        "lower_95": lo,
        "upper_95": hi,
        "bootstrap_unit": "geometry_cluster",
        "replicates": replicates,
        "seed": seed,
    }


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
        accepted_errors = []
        geometry_records = []
        family_records = defaultdict(list)
        ood_count = 0
        upper_covered_total = 0
        in_domain_total = 0

        for gid, geometry_rows in sorted(groups.items()):
            record = {
                "geometry_id": gid,
                "family": geometry_rows[0]["family"],
                "queries": 0,
                "fallback": 0,
                "accepted": 0,
                "unsafe": 0,
                "in_domain": 0,
                "upper_covered": 0,
            }
            for row in geometry_rows:
                decision = gate.should_fallback(
                    row["features"], error_tolerance=tolerance, confidence=.95,
                    family=row["family"]
                )
                actual = float(row[label_key])
                record["queries"] += 1
                fallback = bool(decision["fallback"])
                record["fallback"] += int(fallback)
                if decision.get("reason") == "FEATURE_OUTSIDE_GEOMETRY_CALIBRATED_OOD_ENVELOPE":
                    ood_count += 1
                interval = decision.get("interval")
                if interval is not None:
                    covered = actual <= float(interval["upper"].reshape(-1)[0])
                    record["in_domain"] += 1
                    record["upper_covered"] += int(covered)
                    in_domain_total += 1
                    upper_covered_total += int(covered)
                if not fallback:
                    record["accepted"] += 1
                    unsafe = actual > tolerance
                    record["unsafe"] += int(unsafe)
                    accepted_errors.append(actual)
            geometry_records.append(record)
            family_records[record["family"]].append(record)

        query_count = sum(c["queries"] for c in geometry_records)
        fallback_count = sum(c["fallback"] for c in geometry_records)
        accepted_count = sum(c["accepted"] for c in geometry_records)
        unsafe_count = sum(c["unsafe"] for c in geometry_records)
        geometry_any_fallback = sum(c["fallback"] > 0 for c in geometry_records)
        family_output = {}
        for family, records in sorted(family_records.items()):
            fq = sum(c["queries"] for c in records)
            ff = sum(c["fallback"] for c in records)
            fa = sum(c["accepted"] for c in records)
            fu = sum(c["unsafe"] for c in records)
            fi = sum(c["in_domain"] for c in records)
            fc = sum(c["upper_covered"] for c in records)
            family_output[family] = {
                "geometry_count": len(records),
                "query_count": fq,
                "fallback_query_fraction": ff / fq if fq else None,
                "unsafe_acceptance_fraction": fu / fa if fa else None,
                "empirical_upper_bound_coverage": fc / fi if fi else None,
                "coverage_geometry_cluster_bootstrap_95ci": _cluster_bootstrap_ratio_ci(
                    records, "upper_covered", "in_domain"
                ),
            }

        output[str(tolerance)] = {
            "calibration_unit": "marginal_query",
            "query_count": query_count,
            "fallback_query_count": fallback_count,
            "fallback_query_fraction": fallback_count / query_count,
            "fallback_fraction_geometry_cluster_bootstrap_95ci": _cluster_bootstrap_ratio_ci(
                geometry_records, "fallback", "queries"
            ),
            "accepted_query_count": accepted_count,
            "accepted_actual_error_mean": (
                sum(accepted_errors) / accepted_count if accepted_count else None
            ),
            "unsafe_accepted_query_count": unsafe_count,
            "unsafe_acceptance_fraction": (
                unsafe_count / accepted_count if accepted_count else None
            ),
            "unsafe_acceptance_geometry_cluster_bootstrap_95ci": _cluster_bootstrap_ratio_ci(
                geometry_records, "unsafe", "accepted"
            ),
            "ood_query_count": ood_count,
            "in_domain_query_count": in_domain_total,
            "empirical_upper_bound_coverage_in_domain": (
                upper_covered_total / in_domain_total if in_domain_total else None
            ),
            "upper_bound_coverage_geometry_cluster_bootstrap_95ci": _cluster_bootstrap_ratio_ci(
                geometry_records, "upper_covered", "in_domain"
            ),
            "geometry_count": len(geometry_records),
            "geometry_any_fallback_count": geometry_any_fallback,
            "geometry_any_fallback_fraction": geometry_any_fallback / len(geometry_records),
            "by_geometry_family": family_output,
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
        "schema": "W6_P25_6_MARGINAL_QUERY_GATE_CLUSTER_BOOTSTRAP_V1",
        "unique_test_geometries": len({x["geometry_id"] for x in report["test_cases"]}),
        "test_query_count": len(report["test_cases"]),
        "declared_error_tolerances": list(TOLERANCES),
        "confidence": .95,
        "calibration_unit": "marginal_query_with_geometry_disjoint_train_calibration_test",
        "bootstrap_unit": "geometry_cluster",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
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
