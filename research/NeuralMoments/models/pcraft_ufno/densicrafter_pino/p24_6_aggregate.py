"""Standard-library-only aggregation for P24.6 truth-based feasibility."""
import argparse
import json
import math
import statistics
from pathlib import Path

SEEDS = (271, 277, 281)


def finite(v, name):
    x = float(v)
    if not math.isfinite(x):
        raise ValueError(f"nonfinite {name}")
    return x


def aggregate(input_dir):
    root = Path(input_dir)
    rows = []
    for seed in SEEDS:
        p = root / f"w6_p24_6_native128_seed{seed}.json"
        if not p.is_file():
            raise FileNotFoundError(p)
        d = json.loads(p.read_text())
        if d.get("seed") != seed or d.get("resolution") != 128:
            raise ValueError(f"seed/resolution mismatch: {p}")
        if d.get("predeclared_tolerances", {}).get("model_hardcut_error_allowance") != .005:
            raise ValueError(f"unexpected model error allowance: {p}")
        rows.append(d)

    q = [d["pino_quadrann_densicrafter"] for d in rows]
    b = [d["baseline_pino_densicrafter"] for d in rows]
    feasible = [x["feasible_under_predeclared_tolerances"] is True for x in q]
    gains = [finite(x["mass_reduction_fraction"], "quadrann mass") > 0 for x in q]
    no_error_regression = [
        finite(x["model_hardcut_relative_error"], "quad hardcut") <=
        finite(y["model_hardcut_relative_error"], "base hardcut") + .005 + 1e-8
        for x, y in zip(q, b)
    ]
    promoted = all(feasible) and all(gains) and all(no_error_regression)

    def stats(vals):
        vals = [finite(x, "aggregate") for x in vals]
        return {"mean": statistics.mean(vals),
                "std_population": statistics.pstdev(vals),
                "min": min(vals), "max": max(vals)}

    return {
        "schema": "W6_P24_6_NATIVE128_PHYSICAL_GATE_AGGREGATE_V1",
        "seeds": list(SEEDS),
        "aggregate": {
            "baseline_mass_reduction_fraction": stats(
                [x["mass_reduction_fraction"] for x in b]),
            "quadrann_mass_reduction_fraction": stats(
                [x["mass_reduction_fraction"] for x in q]),
            "baseline_model_hardcut_error": stats(
                [x["model_hardcut_relative_error"] for x in b]),
            "quadrann_model_hardcut_error": stats(
                [x["model_hardcut_relative_error"] for x in q]),
            "model_hardcut_error_delta": stats([
                x["model_hardcut_relative_error"]-y["model_hardcut_relative_error"]
                for x, y in zip(q, b)]),
            "quadrann_accepted_steps_total": sum(x["accepted_steps"] for x in q),
            "quadrann_rejected_steps_total": sum(x["rejected_steps"] for x in q),
            "quadrann_feasible_seed_count": sum(feasible),
            "quadrann_mass_gain_seed_count": sum(gains),
            "quadrann_no_error_regression_seed_count": sum(no_error_regression),
        },
        "per_seed": [{
            "seed": d["seed"],
            "geometry_id": d["geometry_id"],
            "quadrann_gate": d["quadrann_gate"],
            "baseline": d["baseline_pino_densicrafter"],
            "quadrann": d["pino_quadrann_densicrafter"],
            "comparison": d["comparison"],
        } for d in rows],
        "decision": "P24_6_ALL_SEEDS_PASS" if promoted else "KEEP_OPTIONAL_FAIL_CLOSED",
        "claims": {
            "PINO_remains_primary": True,
            "QuadrANN_production_default": False,
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
    print(json.dumps(result["aggregate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
