"""Standard-library-only P24 three-seed aggregation and promotion decision."""
import argparse
import json
import math
import statistics
from pathlib import Path

EXPECTED = (271, 277, 281)


def _finite(value, label):
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"nonfinite {label}")
    return x


def aggregate(input_dir):
    root = Path(input_dir)
    rows = []
    for seed in EXPECTED:
        path = root / f"w6_p24_native128_seed{seed}.json"
        if not path.is_file():
            raise FileNotFoundError(path)
        d = json.loads(path.read_text())
        if d.get("seed") != seed or d.get("resolution") != 128:
            raise ValueError(f"seed/resolution provenance mismatch: {path}")
        if d.get("input_and_fourier_grid") != 128:
            raise ValueError(f"native Fourier grid not 128: {path}")
        if d.get("pino_parameters_frozen") is not True:
            raise ValueError(f"PINO must remain frozen: {path}")
        if d.get("quadrann_parameters_frozen") is not True:
            raise ValueError(f"QuadrANN must remain frozen: {path}")
        if d.get("densicrafter_density_logits_trainable") is not True:
            raise ValueError(f"DensiCrafter density must be trainable: {path}")
        base = d["baseline_pino_densicrafter"]
        quad = d["pino_quadrann_densicrafter"]
        for label, arm in (("baseline", base), ("quadrann", quad)):
            for key in ("mass_reduction_fraction", "model_cut_moment_relative_error",
                        "independent_hard_cut_relative_error",
                        "normalized_material_9moment_l2", "center_of_mass_shift"):
                _finite(arm[key], f"{label}.{key}")
            if arm["outer_shell_preserved"] is not True:
                raise AssertionError(f"{label} protected shell changed: {path}")
        if base["feasible_under_predeclared_tolerances"] is not True:
            raise AssertionError(f"baseline feasibility failed: {path}")
        rows.append(d)

    def stats(key):
        values = [_finite(d["comparison"][key], key) for d in rows]
        return {
            "mean": statistics.mean(values),
            "std_population": statistics.pstdev(values),
            "min": min(values),
            "max": max(values),
        }

    all_quad_feasible = all(
        d["pino_quadrann_densicrafter"]["feasible_under_predeclared_tolerances"] is True
        for d in rows
    )
    all_mass_gain = all(d["comparison"]["mass_reduction_delta_fraction"] > 0 for d in rows)
    no_hardcut_regression = all(
        d["comparison"]["hard_cut_error_delta"] <= 1e-8 for d in rows
    )
    promote = all_quad_feasible and all_mass_gain and no_hardcut_regression
    return {
        "schema": "W6_P24_NATIVE128_QUADRANN_DENSICRAFTER_THREE_SEED_V1",
        "seeds": list(EXPECTED),
        "primary_backbone": "P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "quadrann_role": "optional frozen geometry-conditioned proposal",
        "design_role": "DensiCrafter density logits only",
        "aggregate": {
            "mass_reduction_delta_fraction": stats("mass_reduction_delta_fraction"),
            "hard_cut_error_delta": stats("hard_cut_error_delta"),
            "model_cut_error_delta": stats("model_cut_error_delta"),
            "com_shift_delta": stats("com_shift_delta"),
            "all_quadrann_designs_feasible": all_quad_feasible,
            "all_three_mass_reduction_gains": all_mass_gain,
            "no_hard_cut_regression_all_seeds": no_hardcut_regression,
        },
        "per_seed": [{
            "seed": d["seed"],
            "quadrann_training_seed": d["quadrann_training_seed"],
            "geometry_id": d["geometry_id"],
            "quadrann_gate": d["quadrann_gate"],
            "baseline": d["baseline_pino_densicrafter"],
            "quadrann": d["pino_quadrann_densicrafter"],
            "comparison": d["comparison"],
            "pino_source_checkpoint_sha256": d["pino_source_checkpoint_sha256"],
            "quadrann_source_checkpoint_sha256": d["quadrann_source_checkpoint_sha256"],
        } for d in rows],
        "decision": "RETAIN_OPTIONAL_P24_POSITIVE" if promote else "KEEP_OPTIONAL_NO_PROMOTION",
        "claims": {
            "PINO_remains_primary": True,
            "QuadrANN_is_optional": True,
            "production_default": False,
            "Cherchi_admitted": False,
            "Newton_admitted": False,
            "FEM_FEA": False,
            "512_cube": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(result["aggregate"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
