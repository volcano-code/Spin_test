"""M9: paired held-out SO(3) test of conservative voxel transport vs pull."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
import torch

from .dataset import generate_splits
from .equivariance import (
    random_so3_rotation, rotate_geometry_voxels, transform_native_coefficients,
    transform_raw_moments, transform_native_jacobian,
)
from .mass_transport import conservative_rotate_geometry, sampled_material_moments
from .orbit_sweep import metrics
from .spin_pino import SpinPINO
from .train import run_seed


def _infer(model, D, c):
    start = time.perf_counter()
    with torch.no_grad():
        z = model.encode_geometry(D)
        pred_r = model.moment_from_weights(z, c)
        pred_J = model.jacobian_from_weights(z, c)
    return pred_r, pred_J, time.perf_counter() - start


def run(seeds=(131, 137, 139), steps=120):
    """Freeze one PINO checkpoint per seed; change only inference geometry."""
    if not seeds or steps < 1:
        raise ValueError("seeds must be nonempty and steps positive")
    torch.set_num_threads(1)
    per_seed = []
    for seed in seeds:
        trained = run_seed(
            seed=seed, steps=steps, batch_size=8, grid_size=8,
            points_per_axis=6, smoothing=0.02,
            moment_parameterization="logistic_atom", temperature=0.12, device="cpu",
        )
        model = SpinPINO(
            width=4, modes=2, n_layers=2, grid_size=8,
            points_per_axis=6, hidden_dim=48, smoothing=0.02,
            moment_parameterization="logistic_atom", temperature=0.12,
        )
        model.load_state_dict(trained["checkpoint_state"])
        model.eval()
        src_D, src_c, src_r, src_J, metadata = generate_splits(
            seed=seed, train_geometries_per_family=16,
            test_ellipsoid_geometries=8, queries_per_geometry=2,
            grid_size=8,
        )["test"]
        baseline_D, conservative_D, target_c, target_r, target_J = [], [], [], [], []
        samples = []
        for i in range(len(src_D)):
            D = src_D[i:i+1]
            R = random_so3_rotation(seed + 900001 + i, dtype=D.dtype, device=D.device)
            t0 = time.perf_counter()
            base = rotate_geometry_voxels(D, R)
            base_seconds = time.perf_counter() - t0
            t1 = time.perf_counter()
            rejected = False
            reason = None
            try:
                converted, diagnostics = conservative_rotate_geometry(D, R)
            except (ValueError, ArithmeticError) as exc:
                rejected, reason = True, str(exc)
                converted = base
                diagnostics = None
            conservative_seconds = time.perf_counter() - t1
            reference = transform_raw_moments(sampled_material_moments(D), R)
            base_mom = sampled_material_moments(base)
            new_mom = sampled_material_moments(converted)
            covariance_denominator = torch.linalg.vector_norm(reference,dim=-1).clamp_min(1e-12)
            baseline_D.append(base)
            conservative_D.append(converted)
            target_c.append(transform_native_coefficients(src_c[i:i+1], R))
            target_r.append(transform_raw_moments(src_r[i:i+1], R))
            target_J.append(transform_native_jacobian(src_J[i:i+1], R))
            samples.append({
                "geometry_id": metadata[i]["geometry_id"],
                "query_index": int(metadata[i]["query_index"]),
                "candidate_rejected": rejected,
                "fallback_reason": reason,
                "mass_transport_diagnostics": diagnostics,
                "baseline_sampled_mass_relative_error": float(
                    (base_mom[:,0]-reference[:,0]).abs().div(reference[:,0].abs().clamp_min(1e-12)).max()),
                "candidate_sampled_mass_relative_error": float(
                    (new_mom[:,0]-reference[:,0]).abs().div(reference[:,0].abs().clamp_min(1e-12)).max()),
                "baseline_discrete_ten_moment_covariance_relative_l2": float(
                    (torch.linalg.vector_norm(base_mom-reference,dim=-1)/covariance_denominator).max()),
                "candidate_discrete_ten_moment_covariance_relative_l2": float(
                    (torch.linalg.vector_norm(new_mom-reference,dim=-1)/covariance_denominator).max()),
                "baseline_preprocess_seconds": base_seconds,
                "candidate_preprocess_seconds": conservative_seconds,
            })
        D_base = torch.cat(baseline_D)
        D_candidate = torch.cat(conservative_D)
        c, r, J = (torch.cat(rows) for rows in (target_c, target_r, target_J))
        r_base,J_base,base_inference_seconds = _infer(model,D_base,c)
        r_new,J_new,candidate_inference_seconds = _infer(model,D_candidate,c)
        per_seed.append({
            "seed": seed,
            "labels": "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
            "checkpoint_selected_step": trained["training"]["selected_step"],
            "trainable_parameters": model.real_parameter_count(),
            "same_model_state_for_both_conditions": True,
            "same_transformed_controls_and_labels": True,
            "test_samples": len(samples),
            "candidate_rejections": sum(row["candidate_rejected"] for row in samples),
            "baseline_metrics": metrics(r_base,J_base,r,J),
            "candidate_metrics": metrics(r_new,J_new,r,J),
            "baseline_inference_seconds": base_inference_seconds,
            "candidate_inference_seconds": candidate_inference_seconds,
            "samples": samples,
        })
    keys = ("r_mae", "J_mae", "r_relative_l2", "J_relative_l2")
    aggregate = {
        "baseline_metrics": {k:statistics.mean(p["baseline_metrics"][k] for p in per_seed) for k in keys},
        "candidate_metrics": {k:statistics.mean(p["candidate_metrics"][k] for p in per_seed) for k in keys},
        "candidate_rejections": sum(p["candidate_rejections"] for p in per_seed),
        "total_test_samples": sum(p["test_samples"] for p in per_seed),
        "mean_baseline_sampled_mass_relative_error": statistics.mean(s["baseline_sampled_mass_relative_error"] for p in per_seed for s in p["samples"]),
        "mean_candidate_sampled_mass_relative_error": statistics.mean(s["candidate_sampled_mass_relative_error"] for p in per_seed for s in p["samples"]),
        "mean_baseline_discrete_ten_moment_covariance_relative_l2": statistics.mean(s["baseline_discrete_ten_moment_covariance_relative_l2"] for p in per_seed for s in p["samples"]),
        "mean_candidate_discrete_ten_moment_covariance_relative_l2": statistics.mean(s["candidate_discrete_ten_moment_covariance_relative_l2"] for p in per_seed for s in p["samples"]),
        "mean_baseline_preprocess_seconds": statistics.mean(s["baseline_preprocess_seconds"] for p in per_seed for s in p["samples"]),
        "mean_candidate_preprocess_seconds": statistics.mean(s["candidate_preprocess_seconds"] for p in per_seed for s in p["samples"]),
        "mean_baseline_inference_seconds": statistics.mean(p["baseline_inference_seconds"] for p in per_seed),
        "mean_candidate_inference_seconds": statistics.mean(p["candidate_inference_seconds"] for p in per_seed),
    }
    return {
        "schema": "SPIN_PINO_M9_BOUNDED_DISCRETE_MASS_TRANSPORT_V1",
        "seeds": list(seeds), "steps": steps,
        "design": "same trained PINO, one pass per view, identical SO3 controls and continuum analytic reference",
        "source_labels": "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI",
        "aggregate": aggregate, "per_seed": per_seed,
        "limitations": [
            "Discrete voxel-center sum conservation is not continuum conservation.",
            "The 10-moment covariance diagnostic uses a low-resolution grid, not a CAD oracle.",
            "Candidate explicitly falls back to baseline on out-of-domain or infeasible projection.",
            "This alters model inputs without retraining; accuracy may decrease.",
            "No native Cherchi/Newton or high-resolution GPU verification.",
        ],
        "claims": {"cherchi_supervised": False, "newton_admitted": False,
                   "real_spin_end_to_end_validated": False},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds",default="131,137,139")
    p.add_argument("--steps",type=int,default=120)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    result=run(tuple(int(x) for x in a.seeds.split(",")),a.steps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result["aggregate"],indent=2))

if __name__ == "__main__":
    main()
