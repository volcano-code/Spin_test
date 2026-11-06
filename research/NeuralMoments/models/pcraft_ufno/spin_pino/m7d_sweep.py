"""M7d: validation-selected weight sweep for the PINO SO(3)-covariance loss."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .train import run_seed


LAMBDAS = (0.0, 0.05, 0.2, 0.5, 1.0)


def run(*, seeds=(131, 137, 139), steps=300, batch_size=8, device="cpu"):
    rows = []
    for lam in LAMBDAS:
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
                geometry_adapter="none",
                lambda_equivariance=lam,
                rotation_augmentation=False,
                evaluation_rotation_mode="so3",
                device=device,
            )
            result.pop("checkpoint_state", None)
            per_seed.append(result)

        def avg(split, metric):
            return statistics.mean(row[split][metric] for row in per_seed)

        validation_score = statistics.mean(
            row["validation_metrics"]["r_mae"] + 0.25 * row["validation_metrics"]["J_mae"]
            for row in per_seed
        )
        row = {
            "lambda_equivariance": lam,
            "seeds": list(seeds),
            "steps": steps,
            "batch_size": batch_size,
            "mean_validation_selection_score": validation_score,
            "mean_selected_steps": statistics.mean(row["training"]["selected_step"] for row in per_seed),
            "mean_training_seconds": statistics.mean(row["training"]["seconds"] for row in per_seed),
            "unrotated": {
                "r_relative_l2": avg("held_out_ellipsoid_metrics", "r_relative_l2"),
                "J_relative_l2": avg("held_out_ellipsoid_metrics", "J_relative_l2"),
            },
            "so3_rotated": {
                "r_relative_l2": avg("held_out_rotated_ellipsoid_metrics", "r_relative_l2"),
                "J_relative_l2": avg("held_out_rotated_ellipsoid_metrics", "J_relative_l2"),
            },
            "mean_equivariance_loss_last": statistics.mean(
                result["training"]["history"][-1]["train_equivariance"] for result in per_seed
            ),
            "per_seed": per_seed,
        }
        row["combined_so3_test_score"] = (
            row["so3_rotated"]["r_relative_l2"]
            + row["so3_rotated"]["J_relative_l2"]
        ) / 2.0
        rows.append(row)

    selected = min(rows, key=lambda row: row["mean_validation_selection_score"])
    return {
        "schema": "SPIN_PINO_M7D_EQUIVARIANCE_WEIGHT_SWEEP_V1",
        "primary_backbone": "P-CRAFT PINO UFNO3d",
        "label_source": "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "w2_or_cherchi_labels_used": False,
        "same_splits_seeds_and_so3_test_transforms": True,
        "steps": steps,
        "selection_rule": "select lambda by mean validation r_mae + 0.25*J_mae; held-out SO3 test is confirmatory only",
        "selected_lambda_by_validation": selected["lambda_equivariance"],
        "models": rows,
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
    parser.add_argument("--steps", type=int, default=300)
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
    print(json.dumps({
        "selected_lambda_by_validation": result["selected_lambda_by_validation"],
        "rows": [{
            "lambda": row["lambda_equivariance"],
            "validation_score": row["mean_validation_selection_score"],
            "so3_r": row["so3_rotated"]["r_relative_l2"],
            "so3_J": row["so3_rotated"]["J_relative_l2"],
            "combined_test": row["combined_so3_test_score"],
            "seconds": row["mean_training_seconds"],
        } for row in result["models"]],
    }, indent=2))


if __name__ == "__main__":
    main()
