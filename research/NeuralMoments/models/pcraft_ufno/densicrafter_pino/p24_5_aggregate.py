"""Standard-library-only aggregation for P24.5 domain/resolution diagnosis."""
import argparse
import json
import math
import statistics
from pathlib import Path

SEEDS = (271, 277, 281)


def _f(x, label):
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"nonfinite {label}")
    return v


def aggregate(input_dir):
    root = Path(input_dir)
    reports = []
    for seed in SEEDS:
        p = root / f"w6_p24_5_seed{seed}.json"
        if not p.is_file():
            raise FileNotFoundError(p)
        d = json.loads(p.read_text())
        if d.get("seed") != seed or len(d.get("cases", [])) != 4:
            raise ValueError(f"invalid P24.5 seed/case count: {p}")
        for family in ("sphere", "ellipsoid"):
            rows = [x for x in d["cases"] if x["family"] == family]
            if {x["resolution"] for x in rows} != {64, 128}:
                raise ValueError(f"missing resolution pair for {seed}/{family}")
            if len({x["geometry_id"] for x in rows}) != 1:
                raise ValueError(f"geometry mismatch across resolutions for {seed}/{family}")
        reports.append(d)

    rows = [x for d in reports for x in d["cases"]]

    def mean_case(family, resolution, key):
        vals = [_f(x[key], key) for x in rows
                if x["family"] == family and x["resolution"] == resolution]
        return statistics.mean(vals)

    summary = {}
    for family in ("sphere", "ellipsoid"):
        summary[family] = {}
        for resolution in (64, 128):
            base_r = mean_case(family, resolution,
                               "baseline_pino") if False else None
            selected = [x for x in rows if x["family"] == family and x["resolution"] == resolution]
            br = [_f(x["baseline_pino"]["r_relative_l2_to_analytic_p0"], "base_r") for x in selected]
            qr = [_f(x["quadrann_pino"]["r_relative_l2_to_analytic_p0"], "quad_r") for x in selected]
            bj = [_f(x["baseline_pino"]["J_relative_l2_to_analytic_p0"], "base_J") for x in selected]
            qj = [_f(x["quadrann_pino"]["J_relative_l2_to_analytic_p0"], "quad_J") for x in selected]
            ess = [_f(x["quadrann_proposal"]["effective_sample_size"], "ESS") for x in selected]
            cv = [_f(x["quadrann_proposal"]["coefficient_of_variation"], "CV") for x in selected]
            summary[family][str(resolution)] = {
                "baseline_r_mean": statistics.mean(br),
                "quadrann_r_mean": statistics.mean(qr),
                "r_error_delta_mean": statistics.mean(qr)-statistics.mean(br),
                "baseline_J_mean": statistics.mean(bj),
                "quadrann_J_mean": statistics.mean(qj),
                "J_error_delta_mean": statistics.mean(qj)-statistics.mean(bj),
                "proposal_ess_mean": statistics.mean(ess),
                "proposal_cv_mean": statistics.mean(cv),
            }
    # Diagnostic interpretation only: explicitly avoid automatic promotion.
    return {
        "schema": "W6_P24_5_DOMAIN_RESOLUTION_AGGREGATE_V1",
        "seeds": list(SEEDS),
        "summary": summary,
        "per_seed": reports,
        "decision": "DIAGNOSIS_ONLY_NO_PROMOTION",
        "claims": {
            "PINO_remains_primary": True,
            "QuadrANN_production_default": False,
            "Cherchi": False,
            "native_Newton": False,
            "FEM_FEA": False,
            "512_cube": False,
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
