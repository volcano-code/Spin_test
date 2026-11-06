"""PINO-first Transolver++ auxiliary geometry-adapter ablation."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .train import run_seed


def run(*, seeds=(131, 137, 139), steps=120, batch_size=8, device="cpu"):
    conditions = (
        {"name": "pino_only", "geometry_adapter": "none"},
        {"name": "pino_plus_transolver_plus_eidetic", "geometry_adapter": "transolver_plus"},
    )
    rows = []
    for condition in conditions:
        per_seed = []
        for seed in seeds:
            result = run_seed(
                seed=seed,
                train_geometries_per_family=16,
                test_ellipsoid_geometries=8,
                queries_per_geometry=2,
                steps=steps,
                batch_size=batch_size,
                grid_size=8,
                points_per_axis=6,
                smoothing=0.02,
                moment_parameterization="logistic_atom",
                temperature=0.12,
                geometry_adapter=condition["geometry_adapter"],
                evaluation_rotation_mode="so3",
                device=device,
            )
            result.pop("checkpoint_state", None)
            per_seed.append(result)

        def avg(split, metric):
            return statistics.mean(row[split][metric] for row in per_seed)

        rows.append({
            "condition": condition,
            "seeds": list(seeds),
            "steps": steps,
            "batch_size": batch_size,
            "parameters_mean": statistics.mean(row["trainable_parameters"] for row in per_seed),
            "held_out_unrotated": {
                "r_mae": avg("held_out_ellipsoid_metrics", "r_mae"),
                "J_mae": avg("held_out_ellipsoid_metrics", "J_mae"),
                "r_relative_l2": avg("held_out_ellipsoid_metrics", "r_relative_l2"),
                "J_relative_l2": avg("held_out_ellipsoid_metrics", "J_relative_l2"),
            },
            "held_out_so3": {
                "r_mae": avg("held_out_rotated_ellipsoid_metrics", "r_mae"),
                "J_mae": avg("held_out_rotated_ellipsoid_metrics", "J_mae"),
                "r_relative_l2": avg("held_out_rotated_ellipsoid_metrics", "r_relative_l2"),
                "J_relative_l2": avg("held_out_rotated_ellipsoid_metrics", "J_relative_l2"),
            },
            "mean_training_seconds": statistics.mean(row["training"]["seconds"] for row in per_seed),
            "mean_adapter_gate": statistics.mean(
                row.get("adapter_gate", 0.0) for row in per_seed
            ),
            "per_seed": per_seed,
        })

    for row in rows:
        row["combined_so3_score"] = (
            row["held_out_so3"]["r_relative_l2"]
            + row["held_out_so3"]["J_relative_l2"]
        ) / 2.0

    return {
        "schema": "SPIN_PINO_M8_TRANSOLVER_PLUS_ADAPTER_V1",
        "primary_backbone": "P-CRAFT PINO UFNO3d",
        "plugin": "Transolver++ Physics_Attention_1D_Eidetic",
        "plugin_role": "zero-initialized gated residual geometry-feature adapter; never replaces PINO",
        "upstream": "thuml/Transolver_plus@d5a23bc734a0ebac56384cf72049a26af9673452",
        "label_source": "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "w2_or_cherchi_labels_used": False,
        "same_splits_seeds_steps_optimizer": True,
        "same_so3_test_transforms": True,
        "models": rows,
        "selection_rule": "promote plugin only if held-out r/J improves at acceptable parameter and latency cost",
        "claims": {
            "cherchi_supervised": False,
            "newton_admitted": False,
            "arbitrary_quadric_certified": False,
            "real_spin_end_to_end_validated": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="131,137,139")
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        seeds=tuple(int(x) for x in args.seeds.split(",")),
        steps=args.steps,
        batch_size=args.batch_size,
        device=args.device,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps([
        {
            "condition": row["condition"]["name"],
            "parameters": row["parameters_mean"],
            "r_so3_relative_l2": row["held_out_so3"]["r_relative_l2"],
            "J_so3_relative_l2": row["held_out_so3"]["J_relative_l2"],
            "combined_so3": row["combined_so3_score"],
            "train_seconds": row["mean_training_seconds"],
        }
        for row in result["models"]
    ], indent=2))


if __name__ == "__main__":
    main()
