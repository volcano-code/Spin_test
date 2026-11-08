"""Fail-closed aggregation for P24.7 matched geometry generalization."""
import argparse
import json
import math
import statistics
from pathlib import Path

SEEDS = (271, 277, 281)
FAMILIES = ("box", "sphere", "ellipsoid")
RESOLUTIONS = (64, 128)


def finite(x, name):
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"nonfinite {name}")
    return v


def mean(xs):
    return statistics.mean([finite(x, "aggregate value") for x in xs])


def aggregate(input_dir):
    root = Path(input_dir)
    reports = []
    for seed in SEEDS:
        p = root / f"w6_p24_7_seed{seed}.json"
        if not p.is_file():
            raise FileNotFoundError(p)
        d = json.loads(p.read_text())
        if d.get("seed") != seed or d.get("geometries_per_family") != 3:
            raise ValueError(f"seed or geometry count mismatch: {p}")
        if d.get("total_geometry_resolution_cases") != 18:
            raise ValueError(f"unexpected P24.7 case count: {p}")
        reports.append(d)

    summary = {}
    for family in FAMILIES:
        summary[family] = {}
        for resolution in RESOLUTIONS:
            cases = [
                c for report in reports for c in report["cases"]
                if c["family"] == family and c["resolution"] == resolution
            ]
            rows = [g for c in cases for g in c["geometries"]]
            if len(rows) != 9:
                raise ValueError(f"{family}/{resolution}: expected 9 geometry instances")
            summary[family][str(resolution)] = {
                "geometry_count": len(rows),
                "base_r_analytic_mean": mean(x["base_r_analytic_rel"] for x in rows),
                "quad_r_analytic_mean": mean(x["quad_r_analytic_rel"] for x in rows),
                "r_analytic_delta": mean(x["quad_r_analytic_rel"]-x["base_r_analytic_rel"] for x in rows),
                "base_J_analytic_mean": mean(x["base_J_analytic_rel"] for x in rows),
                "quad_J_analytic_mean": mean(x["quad_J_analytic_rel"] for x in rows),
                "J_analytic_delta": mean(x["quad_J_analytic_rel"]-x["base_J_analytic_rel"] for x in rows),
                "base_r_hardcut_mean": mean(x["base_r_hardcut_rel"] for x in rows),
                "quad_r_hardcut_mean": mean(x["quad_r_hardcut_rel"] for x in rows),
                "r_hardcut_delta": mean(x["quad_r_hardcut_rel"]-x["base_r_hardcut_rel"] for x in rows),
                "proposal_ess_mean": mean(x["proposal_ess"] for x in rows),
                "proposal_entropy_mean": mean(x["proposal_entropy"] for x in rows),
            }

    # Report per-seed and family consistency; do not promote automatically.
    per_seed = []
    for report in reports:
        per_seed.append({
            "seed": report["seed"],
            "families": {
                family: {
                    str(resolution): {
                        "r_analytic_delta": mean(
                            g["quad_r_analytic_rel"]-g["base_r_analytic_rel"]
                            for c in report["cases"] if c["family"] == family and c["resolution"] == resolution
                            for g in c["geometries"]
                        ),
                        "J_analytic_delta": mean(
                            g["quad_J_analytic_rel"]-g["base_J_analytic_rel"]
                            for c in report["cases"] if c["family"] == family and c["resolution"] == resolution
                            for g in c["geometries"]
                        ),
                        "r_hardcut_delta": mean(
                            g["quad_r_hardcut_rel"]-g["base_r_hardcut_rel"]
                            for c in report["cases"] if c["family"] == family and c["resolution"] == resolution
                            for g in c["geometries"]
                        ),
                    } for resolution in RESOLUTIONS
                } for family in FAMILIES
            },
        })

    return {
        "schema": "W6_P24_7_GENERALIZATION_AGGREGATE_V1",
        "seeds": list(SEEDS), "families": list(FAMILIES),
        "resolutions": list(RESOLUTIONS), "geometries_per_family_per_seed": 3,
        "summary": summary, "per_seed": per_seed, "raw_reports": reports,
        "decision": "CONDITIONAL_GENERALIZATION_EVIDENCE_ONLY",
        "claims": {
            "PINO_remains_primary": True,
            "QuadrANN_production_default": False,
            "analytic_P0_vertical_cut_only": True,
            "Cherchi": False, "native_Newton": False,
            "FEM_FEA": False, "512_cube": False,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = aggregate(a.input_dir)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
