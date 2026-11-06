"""M7c: PINO SO(3)-covariance consistency loss ablation."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .train import run_seed


CONDITIONS = (
    {"name": "pino_baseline", "rotation_augmentation": False, "lambda_equivariance": 0.0},
    {"name": "so3_augmentation_only", "rotation_augmentation": True, "lambda_equivariance": 0.0},
    {"name": "equivariance_loss_only", "rotation_augmentation": False, "lambda_equivariance": 0.05},
    {"name": "so3_augmentation_plus_equivariance", "rotation_augmentation": True, "lambda_equivariance": 0.05},
)


def run(*, seeds=(131, 137, 139), steps=120, batch_size=8, device="cpu"):
    rows = []
    for condition in CONDITIONS:
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
                lambda_equivariance=condition["lambda_equivariance"],
                rotation_augmentation=condition["rotation_augmentation"],
                rotation_augmentation_mode="so3",
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
            "fit_samples_mean": statistics.mean(
                row["loss_conditioning"]["fit_samples_after_augmentation"] for row in per_seed
            ),
            "unrotated": {
                "r_relative_l2": avg("held_out_ellipsoid_metrics", "r_relative_l2"),
                "J_relative_l2": avg("held_out_ellipsoid_metrics", "J_relative_l2"),
            },
            "so3_rotated": {
                "r_relative_l2": avg("held_out_rotated_ellipsoid_metrics", "r_relative_l2"),
                "J_relative_l2": avg("held_out_rotated_ellipsoid_metrics", "J_relative_l2"),
            },
            "mean_training_seconds": statistics.mean(row["training"]["seconds"] for row in per_seed),
            "mean_equivariance_loss_last": statistics.mean(
                row["training"]["history"][-1]["train_equivariance"] for row in per_seed
            ),
            "per_seed": per_seed,
        })
        rows[-1]["combined_so3_score"] = (
            rows[-1]["so3_rotated"]["r_relative_l2"]
            + rows[-1]["so3_rotated"]["J_relative_l2"]
        ) / 2.0

    return {
        "schema": "SPIN_PINO_M7C_SO3_COVARIANCE_LOSS_V1",
        "primary_backbone": "P-CRAFT PINO UFNO3d",
        "label_source": "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "w2_or_cherchi_labels_used": False,
        "same_splits_seeds_steps_and_so3_test_transforms": True,
        "equivariance_definition": "r(RD,S_R c) ≈ T_R r(D,c); J(RD,S_R c) ≈ T_R J(D,c) S_R^{-1}",
        "models": rows,
        "selection_rule": "promote consistency loss only if rotated held-out r/J improve without unacceptable unrotated regression or latency",
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
            "unrotated_r": row["unrotated"]["r_relative_l2"],
            "unrotated_J": row["unrotated"]["J_relative_l2"],
            "so3_r": row["so3_rotated"]["r_relative_l2"],
            "so3_J": row["so3_rotated"]["J_relative_l2"],
            "combined_so3": row["combined_so3_score"],
            "seconds": row["mean_training_seconds"],
        }
        for row in result["models"]
    ], indent=2))


if __name__ == "__main__":
    main()
