"""P25.2: evaluate UQNO abstention on untouched geometry-disjoint test cases.

No threshold is selected from this report. We sweep declared candidate error
tolerances and report geometry-level fallback rate and unsafe acceptance.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from .p25_uqno_gate import CalibratedUQNO

TOLERANCES = (0.05, 0.10, 0.20, 0.30)


def _evaluate_target(report, checkpoint, target):
    gate = CalibratedUQNO(checkpoint, target=target)
    label_key = "hardcut_error" if target == "hardcut" else "analytic_p0_error"
    groups = defaultdict(list)
    for row in report["test_cases"]:
        groups[row["geometry_id"]].append(row)
    if len(groups) < 8:
        raise ValueError("insufficient held-out geometries for gate evaluation")
    output = {}
    for tolerance in TOLERANCES:
        fallback = []
        accepted_errors = []
        accepted_unsafe = []
        per_geometry = []
        for gid, rows in sorted(groups.items()):
            uppers = []
            actuals = []
            for row in rows:
                interval = gate.predict_interval(row["features"], confidence=.95)
                uppers.append(float(interval["upper"].reshape(-1)[0]))
                actuals.append(float(row[label_key]))
            predicted_upper = max(uppers)
            actual_max = max(actuals)
            use_fallback = predicted_upper > tolerance
            fallback.append(use_fallback)
            if not use_fallback:
                accepted_errors.append(actual_max)
                accepted_unsafe.append(actual_max > tolerance)
            per_geometry.append({
                "geometry_id": gid,
                "family": rows[0]["family"],
                "predicted_upper_max": predicted_upper,
                "actual_error_max": actual_max,
                "fallback": use_fallback,
            })
        accepted = len(accepted_errors)
        output[str(tolerance)] = {
            "geometry_count": len(groups),
            "fallback_geometry_count": sum(fallback),
            "fallback_fraction": sum(fallback)/len(fallback),
            "accepted_geometry_count": accepted,
            "accepted_actual_error_mean": (
                sum(accepted_errors)/accepted if accepted else None
            ),
            "unsafe_accepted_geometry_count": sum(accepted_unsafe),
            "unsafe_acceptance_fraction": (
                sum(accepted_unsafe)/accepted if accepted else None
            ),
            "per_geometry": per_geometry,
        }
    return output


def run(report_path, checkpoint_dir):
    report = json.loads(Path(report_path).read_text())
    checkpoint_dir = Path(checkpoint_dir)
    hard = _evaluate_target(
        report, checkpoint_dir/"w6_p25_uqno_hardcut.pt", "hardcut"
    )
    analytic = _evaluate_target(
        report, checkpoint_dir/"w6_p25_uqno_analytic_p0.pt", "analytic_p0"
    )
    return {
        "schema": "W6_P25_2_UQNO_HELDOUT_GATE_EVALUATION_V1",
        "unique_test_geometries": len({
            x["geometry_id"] for x in report["test_cases"]
        }),
        "declared_error_tolerances": list(TOLERANCES),
        "confidence": .95,
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
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--checkpoint-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(a.report, a.checkpoint_dir)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({
        "hardcut": result["hardcut_error_gate"],
        "analytic": result["analytic_p0_error_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
