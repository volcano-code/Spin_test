"""M6 rotation-generalization experiment for logistic-head Spin-PINO."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .train import run_seed


def run(*, seeds=(131,137,139), steps=120, batch_size=8):
    conditions = (
        {"name": "no_rotation_augmentation", "rotation_augmentation": False},
        {"name": "cube_rotation_augmentation", "rotation_augmentation": True, "mode": "cube"},
        {"name": "arbitrary_so3_rotation_augmentation", "rotation_augmentation": True, "mode": "so3"},
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
                rotation_augmentation=condition["rotation_augmentation"],
                rotation_augmentation_mode=condition.get("mode", "cube"),
                device="cpu",
            )
            result.pop("checkpoint_state", None)
            per_seed.append(result)
        def avg(metric, split):
            return statistics.mean(
                row[split][metric] for row in per_seed
            )
        rows.append({
            "condition": condition,
            "seeds": list(seeds),
            "steps": steps,
            "batch_size": batch_size,
            "fit_samples_mean": statistics.mean(
                row["loss_conditioning"]["fit_samples_after_augmentation"] for row in per_seed
            ),
            "unrotated_test": {
                "r_mae": avg("r_mae","held_out_ellipsoid_metrics"),
                "J_mae": avg("J_mae","held_out_ellipsoid_metrics"),
                "r_relative_l2": avg("r_relative_l2","held_out_ellipsoid_metrics"),
                "J_relative_l2": avg("J_relative_l2","held_out_ellipsoid_metrics"),
            },
            "rotated_test": {
                "r_mae": avg("r_mae","held_out_rotated_ellipsoid_metrics"),
                "J_mae": avg("J_mae","held_out_rotated_ellipsoid_metrics"),
                "r_relative_l2": avg("r_relative_l2","held_out_rotated_ellipsoid_metrics"),
                "J_relative_l2": avg("J_relative_l2","held_out_rotated_ellipsoid_metrics"),
            },
            "mean_training_seconds": statistics.mean(row["training"]["seconds"] for row in per_seed),
            "per_seed": per_seed,
        })
    return {
        "schema": "SPIN_PINO_M6_CUBE_ROTATION_GENERALIZATION_V1",
        "label_source": "ANALYTIC_CONTINUUM_P0_WITH_EXACT_ROTATION_TRANSFORMS_NOT_W2_CHERCHI",
        "w2_or_cherchi_labels_used": False,
        "rotation_group": "24 proper signed-permutation cube rotations (SO(3) subgroup)",
        "same_base_splits_seeds_optimizer_steps": True,
        "models": rows,
        "limits": [
            "Only the 24 cube-preserving rotations are tested, not arbitrary SO(3).",
            "Voxel rotation uses exact grid-aligned signed permutations.",
            "The source analytic task remains vertical-plane cuts transformed by exact coordinate rules.",
            "No arbitrary quadric/CAD derivative or Newton certification."
        ],
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",default="131,137,139")
    parser.add_argument("--steps",type=int,default=120)
    parser.add_argument("--batch-size",type=int,default=8)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=run(seeds=tuple(int(x) for x in args.seeds.split(",")),
               steps=args.steps,batch_size=args.batch_size)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps([{
        "condition":x["condition"]["name"],
        "unrotated_r":x["unrotated_test"]["r_relative_l2"],
        "unrotated_J":x["unrotated_test"]["J_relative_l2"],
        "rotated_r":x["rotated_test"]["r_relative_l2"],
        "rotated_J":x["rotated_test"]["J_relative_l2"],
    } for x in result["models"]],indent=2))


if __name__=="__main__":
    main()
