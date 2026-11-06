"""Reproducible CPU-first Spin-PINO training on analytic continuum P0 labels."""

from __future__ import annotations

import argparse
import copy
import json
import math
import time
from pathlib import Path

import numpy as np
import torch

from .dataset import generate_splits
from .spin_pino import SpinPINO, SpinPINOLoss


def _evaluate(model, data):
    D, c, target_r, target_J, _ = data
    model.eval()
    with torch.no_grad():
        z = model.encode_geometry(D)
        pred_r = model.moment_from_weights(z, c)
        pred_J = model.jacobian_from_weights(z, c)
    r_abs = (pred_r - target_r).abs()
    J_abs = (pred_J - target_J).abs()
    return {
        "r_mae": float(r_abs.mean()),
        "r_max_component_mae": [float(x) for x in r_abs.mean(dim=0)],
        "r_relative_l2": float((pred_r - target_r).norm() / target_r.norm().clamp_min(1e-12)),
        "J_mae": float(J_abs.mean()),
        "J_relative_l2": float((pred_J - target_J).norm() / target_J.norm().clamp_min(1e-12)),
        "negative_mass_fraction": float((pred_r[:, 0] < -1e-7).float().mean()),
    }


def run_seed(
    *,
    seed: int,
    train_geometries_per_family: int = 16,
    test_ellipsoid_geometries: int = 8,
    queries_per_geometry: int = 2,
    steps: int = 120,
    batch_size: int = 8,
    grid_size: int = 8,
    device: str = "cpu",
):
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.set_num_threads(1)
    splits = generate_splits(
        seed=seed,
        train_geometries_per_family=train_geometries_per_family,
        test_ellipsoid_geometries=test_ellipsoid_geometries,
        queries_per_geometry=queries_per_geometry,
        grid_size=grid_size,
    )
    fit, validation, test = (splits[k] for k in ("fit", "validation", "test"))
    model = SpinPINO(
        width=4 if grid_size <= 8 else 8,
        modes=2 if grid_size <= 8 else 4,
        n_layers=2 if grid_size <= 8 else 4,
        grid_size=grid_size,
        points_per_axis=4,
        hidden_dim=48,
        smoothing=0.04,
    ).to(device)
    criterion = SpinPINOLoss(lambda_data=1.0, lambda_physics=0.05, lambda_jacobian=0.25)
    optimizer = torch.optim.Adam(model.parameters(), lr=1.5e-3)
    generator = torch.Generator().manual_seed(seed + 31337)
    best_score = math.inf
    best_step = 0
    best_state = copy.deepcopy(model.state_dict())
    history = []
    started = time.perf_counter()
    for step in range(1, steps + 1):
        model.train()
        indices = torch.randint(
            len(fit[0]), (min(batch_size, len(fit[0])),), generator=generator
        )
        D, c, target_r, target_J = (
            x[indices].to(device) for x in fit[:4]
        )
        weights = model.encode_geometry(D)
        # These Jacobians are exact analytic labels for the restricted P0
        # vertical-plane family, not diagnostic W2 records.
        losses = criterion(
            model,
            weights,
            c,
            target_moments=target_r,
            target_jacobian=target_J,
            derivative_admitted=True,
        )
        if not bool(torch.isfinite(losses["total"])):
            raise FloatingPointError(f"nonfinite Spin-PINO loss at step {step}")
        optimizer.zero_grad(set_to_none=True)
        losses["total"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        if step == 1 or step % 10 == 0 or step == steps:
            val = _evaluate(model, validation)
            score = val["r_mae"] + 0.25 * val["J_mae"]
            history.append({
                "step": step,
                "train_total": float(losses["total"].detach()),
                "train_data": float(losses["data"].detach()),
                "train_physics": float(losses["physics"].detach()),
                "train_jacobian": float(losses["jacobian_supervision"].detach()),
                "validation_score": score,
                "validation": val,
            })
            if score < best_score:
                best_score = score
                best_step = step
                best_state = copy.deepcopy(model.state_dict())
    training_seconds = time.perf_counter() - started
    model.load_state_dict(best_state)
    fit_metrics = _evaluate(model, fit)
    validation_metrics = _evaluate(model, validation)
    test_metrics = _evaluate(model, test)
    return {
        "schema": "SPIN_PINO_ANALYTIC_P0_TRAINING_V1",
        "seed": seed,
        "label_source": splits["metadata"]["label_source"],
        "w2_or_cherchi_labels_used": False,
        "derivative_scope": splits["metadata"]["derivative_scope"],
        "dataset": splits["metadata"],
        "trainable_parameters": model.real_parameter_count(),
        "training": {
            "steps": steps,
            "batch_size": batch_size,
            "selected_step": best_step,
            "seconds": training_seconds,
            "optimizer": "Adam",
            "learning_rate": 1.5e-3,
            "history": history,
        },
        "fit_metrics": fit_metrics,
        "validation_metrics": validation_metrics,
        "held_out_ellipsoid_metrics": test_metrics,
        "checkpoint_state": best_state,
        "claims": {
            "trained_spin_model": True,
            "cherchi_supervised": False,
            "arbitrary_quadric_certified": False,
            "newton_admitted": False,
            "real_spin_end_to_end_validated": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", default="131,137,139")
    parser.add_argument("--train-geometries-per-family", type=int, default=16)
    parser.add_argument("--test-ellipsoid-geometries", type=int, default=8)
    parser.add_argument("--queries-per-geometry", type=int, default=2)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--grid-size", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-checkpoints", action="store_true")
    args = parser.parse_args()
    results = []
    for seed in (int(x) for x in args.seeds.split(",")):
        result = run_seed(
            seed=seed,
            train_geometries_per_family=args.train_geometries_per_family,
            test_ellipsoid_geometries=args.test_ellipsoid_geometries,
            queries_per_geometry=args.queries_per_geometry,
            steps=args.steps,
            batch_size=args.batch_size,
            grid_size=args.grid_size,
            device=args.device,
        )
        state = result.pop("checkpoint_state")
        if args.save_checkpoints:
            checkpoint_path = args.output.with_name(f"{args.output.stem}_seed{seed}.pt")
            torch.save(state, checkpoint_path)
            result["checkpoint_path"] = str(checkpoint_path)
        results.append(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps([
        {"seed": row["seed"], "selected_step": row["training"]["selected_step"],
         "fit_r_mae": row["fit_metrics"]["r_mae"],
         "validation_r_mae": row["validation_metrics"]["r_mae"],
         "held_out_ellipsoid_r_mae": row["held_out_ellipsoid_metrics"]["r_mae"],
         "held_out_ellipsoid_J_mae": row["held_out_ellipsoid_metrics"]["J_mae"]}
        for row in results
    ], indent=2))


if __name__ == "__main__":
    main()
