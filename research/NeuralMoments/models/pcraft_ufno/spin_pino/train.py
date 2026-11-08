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
from .loss_conditioning import DiagonalMomentResidualPreconditioner, pcgrad_backward
from .equivariance import (
    augment_with_cube_rotations,
    augment_with_random_so3,
    cube_rotation,
    random_so3_rotation,
    rotate_geometry_voxels,
    transform_native_coefficients,
    transform_raw_moments,
    transform_native_jacobian,
)




def _augment_with_groupwise_cube_rotations(data, *, seed: int):
    """Append one exact cube rotation per geometry ID, shared by all queries."""
    if len(data) != 5:
        raise ValueError("expected (D,c,r,J,metadata)")
    D, coefficients, moments, jacobians, metadata = data
    if D.ndim != 5 or D.shape[1] != 4:
        raise ValueError("D must be [N,4,X,Y,Z]")
    n = D.shape[0]
    if any(x.shape[0] != n for x in (coefficients, moments, jacobians)) or len(metadata) != n:
        raise ValueError("sample count mismatch")
    groups = {}
    for i, row in enumerate(metadata):
        groups.setdefault(row.get("geometry_id", f"sample-{i}"), []).append(i)
    rotated_D, rotated_c, rotated_r, rotated_J, rotated_meta = [], [], [], [], []
    for group_index, (geometry_id, indices) in enumerate(groups.items()):
        idx = torch.as_tensor(indices, dtype=torch.long, device=D.device)
        R = cube_rotation(seed + group_index, dtype=D.dtype, device=D.device)
        rotated_D.append(rotate_geometry_voxels(D.index_select(0, idx), R))
        rotated_c.append(transform_native_coefficients(coefficients.index_select(0, idx), R))
        rotated_r.append(transform_raw_moments(moments.index_select(0, idx), R))
        rotated_J.append(transform_native_jacobian(jacobians.index_select(0, idx), R))
        new_id = f"{geometry_id}__group_cube_{(seed + group_index) % 24:02d}"
        for index in indices:
            row = copy.deepcopy(metadata[index])
            row["parent_geometry_id"] = geometry_id
            row["geometry_id"] = new_id
            row["augmentation"] = "EXACT_GROUPWISE_CUBE_ROTATION_LABEL_TRANSFORM"
            row["rotation_matrix"] = [[float(v) for v in line] for line in R.cpu().tolist()]
            rotated_meta.append(row)
    return (
        torch.cat((D, torch.cat(rotated_D, dim=0)), dim=0),
        torch.cat((coefficients, torch.cat(rotated_c, dim=0)), dim=0),
        torch.cat((moments, torch.cat(rotated_r, dim=0)), dim=0),
        torch.cat((jacobians, torch.cat(rotated_J, dim=0)), dim=0),
        list(metadata) + rotated_meta,
    )


def _evaluate(model, data, *, batch_size=None):
    D, c, target_r, target_J, _ = data
    model.eval()
    chunk = len(D) if batch_size is None else int(batch_size)
    if chunk < 1:
        raise ValueError("evaluation batch_size must be positive")
    pred_r_parts, pred_J_parts = [], []
    with torch.no_grad():
        for start in range(0, len(D), chunk):
            end = min(start + chunk, len(D))
            z = model.encode_geometry(D[start:end])
            pred_r_parts.append(model.moment_from_weights(z, c[start:end]))
            pred_J_parts.append(model.jacobian_from_weights(z, c[start:end]))
    pred_r = torch.cat(pred_r_parts, dim=0)
    pred_J = torch.cat(pred_J_parts, dim=0)
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



def _so3_covariance_loss(model, geometry, coefficients, reference_r, reference_J, *, seed):
    """Paired SO(3) consistency using exact coefficient/moment/J transforms.

    Voxel geometry is trilinearly resampled; its interpolation perturbation is
    therefore part of the consistency residual and is kept at a small weight.
    """
    rotated_D, rotated_c, expected_r, expected_J = [], [], [], []
    for i in range(geometry.shape[0]):
        R = random_so3_rotation(seed + i, dtype=geometry.dtype, device=geometry.device)
        rotated_D.append(rotate_geometry_voxels(geometry[i:i+1], R))
        rotated_c.append(transform_native_coefficients(coefficients[i:i+1], R))
        expected_r.append(transform_raw_moments(reference_r[i:i+1], R))
        expected_J.append(transform_native_jacobian(reference_J[i:i+1], R))
    D_rot = torch.cat(rotated_D, dim=0)
    c_rot = torch.cat(rotated_c, dim=0)
    r_expected = torch.cat(expected_r, dim=0)
    J_expected = torch.cat(expected_J, dim=0)
    w_rot = model.encode_geometry(D_rot)
    r_rot = model.moment_from_weights(w_rot, c_rot)
    J_rot = model.jacobian_from_weights(w_rot, c_rot)
    r_scale = r_expected.detach().square().mean().clamp_min(1e-8)
    J_scale = J_expected.detach().square().mean().clamp_min(1e-8)
    loss_r = (r_rot - r_expected).square().mean() / r_scale
    loss_J = (J_rot - J_expected).square().mean() / J_scale
    return loss_r + 0.25 * loss_J, loss_r.detach(), loss_J.detach()

def run_seed(
    *,
    seed: int,
    train_geometries_per_family: int = 16,
    test_ellipsoid_geometries: int = 8,
    queries_per_geometry: int = 2,
    steps: int = 120,
    batch_size: int = 8,
    eval_batch_size: int | None = None,
    grid_size: int = 8,
    points_per_axis: int = 4,
    smoothing: float = 0.04,
    preconditioned_loss: bool = False,
    pcgrad: bool = False,
    moment_parameterization: str = "smooth_hinge",
    temperature: float = 0.12,
    geometry_adapter: str = "none",
    lambda_equivariance: float = 0.0,
    rotation_augmentation: bool = False,
    rotation_augmentation_mode: str = "cube",
    evaluation_rotation_mode: str = "so3",
    use_gradient_checkpoint: bool = False,
    initial_state_dict: dict | None = None,
    initial_state_source: str = "random_initialization",
    device: str = "cpu",
):
    if eval_batch_size is not None and eval_batch_size < 1:
        raise ValueError("eval_batch_size must be positive")
    if not math.isfinite(lambda_equivariance) or lambda_equivariance < 0:
        raise ValueError("lambda_equivariance must be finite and nonnegative")
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
    if rotation_augmentation:
        if rotation_augmentation_mode == "cube":
            fit = augment_with_cube_rotations(fit, seed=seed + 700001)
        elif rotation_augmentation_mode == "cube_group":
            fit = _augment_with_groupwise_cube_rotations(fit, seed=seed + 700001)
        elif rotation_augmentation_mode == "so3":
            fit = augment_with_random_so3(fit, seed=seed + 700001)
        else:
            raise ValueError("rotation_augmentation_mode must be cube, cube_group or so3")

    # Every training condition is evaluated on the same arbitrary-SO(3)
    # transformed held-out geometries. Evaluate only the appended rotated
    # samples, not the concatenated original+rotated tuple.
    if evaluation_rotation_mode == "cube":
        test_augmented = augment_with_cube_rotations(test, seed=seed + 900001)
    elif evaluation_rotation_mode == "so3":
        test_augmented = augment_with_random_so3(test, seed=seed + 900001)
    else:
        raise ValueError("evaluation_rotation_mode must be cube or so3")
    n_test = test[0].shape[0]
    rotated_test = tuple(x[n_test:] for x in test_augmented[:4]) + (test_augmented[4][n_test:],)
    model = SpinPINO(
        width=4 if grid_size <= 8 else 8,
        modes=2 if grid_size <= 8 else 4,
        n_layers=2 if grid_size <= 8 else 4,
        grid_size=grid_size,
        points_per_axis=points_per_axis,
        hidden_dim=48,
        smoothing=smoothing,
        moment_parameterization=moment_parameterization,
        temperature=temperature,
        geometry_adapter=geometry_adapter,
        use_gradient_checkpoint=use_gradient_checkpoint,
    ).to(device)
    if initial_state_dict is not None:
        # Strict shape/key match: 64^3 -> 128^3 transfer is valid only
        # because spectral weights and the Spin quadrature head are grid-size
        # independent. Never silently drop missing/unexpected parameters.
        model.load_state_dict(initial_state_dict, strict=True)
    elif initial_state_source != "random_initialization":
        raise ValueError("initial_state_source requires initial_state_dict")
    preconditioner = (
        DiagonalMomentResidualPreconditioner.fit(fit[2], fit[3]).to(device=device, dtype=fit[2].dtype)
        if preconditioned_loss else None
    )
    criterion = SpinPINOLoss(
        lambda_data=1.0, lambda_physics=0.05, lambda_jacobian=0.25,
        moment_scale=preconditioner.moment_scale if preconditioner else None,
        jacobian_scale=preconditioner.jacobian_scale if preconditioner else None,
    )
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
        equivariance_loss = losses["total"].new_zeros(())
        equivariance_r = losses["total"].new_zeros(())
        equivariance_J = losses["total"].new_zeros(())
        if lambda_equivariance > 0:
            reference_r = model.moment_from_weights(weights, c)
            reference_J = model.jacobian_from_weights(weights, c)
            equivariance_loss, equivariance_r, equivariance_J = _so3_covariance_loss(
                model, D, c, reference_r, reference_J,
                seed=seed * 1000003 + step * 101,
            )
        total_loss = losses["total"] + lambda_equivariance * equivariance_loss
        if not bool(torch.isfinite(total_loss)):
            raise FloatingPointError(f"nonfinite Spin-PINO loss at step {step}")
        optimizer.zero_grad(set_to_none=True)
        grad_stats = None
        if pcgrad:
            terms = (losses["data"], losses["physics"], losses["jacobian_supervision"])
            scales = (criterion.lambda_data, criterion.lambda_physics, criterion.lambda_jacobian)
            if lambda_equivariance > 0:
                terms = terms + (equivariance_loss,)
                scales = scales + (lambda_equivariance,)
            grad_stats = pcgrad_backward(terms, model.parameters(), scales)
        else:
            total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        if step == 1 or step % 10 == 0 or step == steps:
            val = _evaluate(model, validation, batch_size=eval_batch_size)
            score = val["r_mae"] + 0.25 * val["J_mae"]
            history.append({
                "step": step,
                "train_total": float(total_loss.detach()),
                "train_data": float(losses["data"].detach()),
                "train_equivariance": float(equivariance_loss.detach()),
                "train_equivariance_r": float(equivariance_r),
                "train_equivariance_J": float(equivariance_J),
                "train_physics": float(losses["physics"].detach()),
                "train_jacobian": float(losses["jacobian_supervision"].detach()),
                "gradient_conflict": grad_stats,
                "validation_score": score,
                "validation": val,
            })
            if score < best_score:
                best_score = score
                best_step = step
                best_state = copy.deepcopy(model.state_dict())
    training_seconds = time.perf_counter() - started
    model.load_state_dict(best_state)
    fit_metrics = _evaluate(model, fit, batch_size=eval_batch_size)
    validation_metrics = _evaluate(model, validation, batch_size=eval_batch_size)
    test_metrics = _evaluate(model, test, batch_size=eval_batch_size)
    return {
        "schema": "SPIN_PINO_ANALYTIC_P0_TRAINING_V1",
        "seed": seed,
        "label_source": splits["metadata"]["label_source"],
        "w2_or_cherchi_labels_used": False,
        "derivative_scope": splits["metadata"]["derivative_scope"],
        "dataset": splits["metadata"],
        "trainable_parameters": model.real_parameter_count(),
        "adapter_gate": (
            float(torch.tanh(model.transolver_plus_gate).detach())
            if model.transolver_plus_gate is not None else 0.0
        ),
        "loss_conditioning": {
            "diagonal_preconditioner": bool(preconditioned_loss),
            "pcgrad": bool(pcgrad),
            "preconditioner_fit_split_only": True,
            "preconditioner": preconditioner.as_dict() if preconditioner else None,
            "rotation_augmentation": bool(rotation_augmentation),
            "rotation_augmentation_mode": rotation_augmentation_mode,
            "geometry_adapter": geometry_adapter,
            "evaluation_rotation_mode": evaluation_rotation_mode,
            "use_gradient_checkpoint": bool(use_gradient_checkpoint),
            "lambda_equivariance": float(lambda_equivariance),
            "fit_samples_after_augmentation": int(len(fit[0])),
        },
        "model_config": {"grid_size": grid_size, "points_per_axis": points_per_axis,
                         "smoothing": smoothing, "moment_parameterization": moment_parameterization,
                         "temperature": temperature, "geometry_adapter": geometry_adapter,
                         "use_gradient_checkpoint": bool(use_gradient_checkpoint),
                         "initial_state_source": initial_state_source,
                         "lambda_equivariance": float(lambda_equivariance),
                         "width": 4 if grid_size <= 8 else 8,
                         "modes": 2 if grid_size <= 8 else 4},
        "training": {
            "steps": steps,
            "batch_size": batch_size,
            "eval_batch_size": eval_batch_size,
            "initial_state_source": initial_state_source,
            "selected_step": best_step,
            "seconds": training_seconds,
            "optimizer": "Adam",
            "learning_rate": 1.5e-3,
            "history": history,
        },
        "fit_metrics": fit_metrics,
        "validation_metrics": validation_metrics,
        "held_out_ellipsoid_metrics": test_metrics,
        "held_out_rotated_ellipsoid_metrics": _evaluate(model, rotated_test, batch_size=eval_batch_size),
        "rotation_evaluation_diagnostics": {
            "mean_occupied_centers_clipped_fraction": float(np.mean([
                row.get("source_occupied_voxel_centers_outside_target_cube_fraction", 0.0)
                for row in rotated_test[4]
            ])),
            "mean_soft_occupancy_mass_ratio": float(np.mean([
                row.get("soft_occupancy_mass_ratio", 1.0)
                for row in rotated_test[4]
            ])),
            "rotation_mode": evaluation_rotation_mode,
            "n_rotated_test_samples": len(rotated_test[4]),
        },
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
    parser.add_argument("--eval-batch-size", type=int, default=None)
    parser.add_argument("--grid-size", type=int, default=8)
    parser.add_argument("--points-per-axis", type=int, default=4)
    parser.add_argument("--smoothing", type=float, default=0.04)
    parser.add_argument("--preconditioned-loss", action="store_true")
    parser.add_argument("--pcgrad", action="store_true")
    parser.add_argument("--moment-parameterization", choices=("smooth_hinge", "logistic_atom"), default="smooth_hinge")
    parser.add_argument("--temperature", type=float, default=0.12)
    parser.add_argument("--geometry-adapter", choices=("none", "transolver_plus"), default="none")
    parser.add_argument("--lambda-equivariance", type=float, default=0.0)
    parser.add_argument("--rotation-augmentation", action="store_true")
    parser.add_argument("--rotation-augmentation-mode", choices=("cube", "cube_group", "so3"), default="cube")
    parser.add_argument("--use-gradient-checkpoint", action="store_true")
    parser.add_argument("--evaluation-rotation-mode", choices=("cube", "so3"), default="so3")
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
            eval_batch_size=args.eval_batch_size,
            grid_size=args.grid_size,
            points_per_axis=args.points_per_axis,
            smoothing=args.smoothing,
            preconditioned_loss=args.preconditioned_loss,
            pcgrad=args.pcgrad,
            moment_parameterization=args.moment_parameterization,
            temperature=args.temperature,
            geometry_adapter=args.geometry_adapter,
            lambda_equivariance=args.lambda_equivariance,
            rotation_augmentation=args.rotation_augmentation,
            rotation_augmentation_mode=args.rotation_augmentation_mode,
            evaluation_rotation_mode=args.evaluation_rotation_mode,
            use_gradient_checkpoint=args.use_gradient_checkpoint,
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
