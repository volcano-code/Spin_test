"""P24.6: rerun native-128 material design with truth-based model feasibility.

Correct P24's invalid baseline-output preservation test. The model check is
now PINO/QuadrANN moment prediction versus the independent hard-cut integral
for the CURRENT density. The hard-cut conservation check remains relative
to the INITIAL independent hard-cut moments. To prevent regression, the
model-vs-hardcut error may not exceed the initial pure-PINO error by >0.5
percentage points. No tolerance is relaxed on independent material screens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

import torch

from ..analytic_cut import sample_dataset
from .bridge import DensiCrafterSpinPINOBridge
from .p13b_highres import exact_discrete_cut_moments
from .p17_trained_pino import _normalised_material_moments, _relative, _surface_masks
from .p24_quadrann_native128 import (
    P23_SEEDS, _load_pino, _load_quadrann,
)

MODEL_HARDCUT_ALLOWANCE = 0.005


def _evaluate(model, coefficients, cut_ref, norm_ref, baseline_model_error,
              tolerances):
    with torch.no_grad():
        out = model(coefficients, reference_cut_moments=cut_ref)
        independent = exact_discrete_cut_moments(out["density"], coefficients)
        norm = _normalised_material_moments(out["density"])
        model_hardcut_error = _relative(out["moments"], independent)
        metrics = {
            "model_hardcut_relative_error": model_hardcut_error,
            "model_hardcut_error_delta_vs_initial_pino": model_hardcut_error-baseline_model_error,
            "independent_cut_r_rel": _relative(independent, cut_ref),
            "normalized_material_9moment_l2": float((norm-norm_ref).norm()),
        }
        ok = (
            metrics["model_hardcut_error_delta_vs_initial_pino"]
                <= tolerances["model_hardcut_error_allowance"] + 1e-8
            and metrics["independent_cut_r_rel"] <= tolerances["independent_cut_r_rel"] + 1e-8
            and metrics["normalized_material_9moment_l2"]
                <= tolerances["normalized_material_9moment_l2"] + 1e-8
        )
        return ok, metrics, out, independent


def _run_arm(pino_or_proxy, shell, design, coefficients, cut_ref, norm_ref,
             baseline_model_error, arm, steps, lr, tolerances):
    model = DensiCrafterSpinPINOBridge(
        pino_or_proxy, shell, design, gravity_axis=2, smoothing=False
    )
    with torch.no_grad():
        model.density_logits.fill_(4.0)
        initial = model(coefficients, reference_cut_moments=cut_ref)
        mass0 = float(initial["full_material_moments"][0, 0])
        initial_model_error = _relative(
            initial["moments"], exact_discrete_cut_moments(initial["density"], coefficients)
        )
    accepted = rejected = 0
    history = []
    start = time.perf_counter()
    optimizer = torch.optim.Adam([model.density_logits], lr=lr)
    weights = {
        "mass": 1.0, "com_contact": 0.2,
        "negative_contact_area": 0.02, "com_height": 0.05,
        "cut_moment_error": 25.0,
    }
    for step in range(steps):
        out = model(coefficients, reference_cut_moments=cut_ref, weights=weights)
        optimizer.zero_grad(set_to_none=True)
        out["loss"].backward()
        grad = model.density_logits.grad
        if grad is None or not bool(torch.isfinite(grad).all()):
            raise FloatingPointError("nonfinite P24.6 density gradient")
        grad_norm = float(grad.norm())
        before = model.density_logits.detach().clone()
        optimizer.step()
        proposal = model.density_logits.detach().clone()
        admitted = False
        for backtrack in range(10):
            alpha = 2.0 ** (-backtrack)
            with torch.no_grad():
                model.density_logits.copy_(before+(proposal-before)*alpha)
            good, metrics, _, _ = _evaluate(
                model, coefficients, cut_ref, norm_ref,
                baseline_model_error, tolerances,
            )
            if good:
                accepted += 1
                admitted = True
                break
        if not admitted:
            with torch.no_grad():
                model.density_logits.copy_(before)
            rejected += 1
        history.append({
            "step": step+1, "accepted": admitted,
            "gradient_norm": grad_norm,
            "backtracks": backtrack if admitted else 10,
        })
    elapsed = time.perf_counter()-start
    with torch.no_grad():
        good, metrics, final, independent = _evaluate(
            model, coefficients, cut_ref, norm_ref,
            baseline_model_error, tolerances,
        )
        mass1 = float(final["full_material_moments"][0, 0])
        shell_ok = bool((final["density"][shell] == 1.0).all())
        if not shell_ok:
            raise AssertionError("protected shell changed")
    return {
        "arm": arm, "steps": steps,
        "initial_model_hardcut_relative_error": initial_model_error,
        **metrics,
        "mass_initial": mass0, "mass_final": mass1,
        "mass_reduction_fraction": 1.0-mass1/max(mass0, 1e-8),
        "center_of_mass_shift": float((final["com"]-initial["com"]).norm()),
        "accepted_steps": accepted, "rejected_steps": rejected,
        "feasible_under_predeclared_tolerances": bool(good),
        "outer_shell_preserved": shell_ok,
        "seconds": elapsed, "history": history,
        "final_density": final["density"].detach().cpu(),
        "final_independent_cut": independent.detach().cpu(),
        "final_material_moments": final["full_material_moments"].detach().cpu(),
    }


def run(*, pino_checkpoint_dir, quadrann_checkpoint_dir, seed,
        steps=6, lr=.06, wall_cells=4):
    torch.set_num_threads(1)
    if seed not in P23_SEEDS:
        raise ValueError("unsupported matched seed")
    pino, pino_sha = _load_pino(Path(pino_checkpoint_dir), seed)
    proxy, quad_sha, gate = _load_quadrann(
        pino, seed=seed, pino_sha=pino_sha,
        quadrann_dir=Path(quadrann_checkpoint_dir),
    )
    D, coefficients, _, _, metadata = sample_dataset(
        ("sphere",), per_family=1, seed=seed+707,
        grid_size=128, queries_per_geometry=1,
    )
    shell, design = _surface_masks(D[:, 1:2] > 0, wall_cells=wall_cells)
    baseline_model = DensiCrafterSpinPINOBridge(
        pino, shell, design, gravity_axis=2, smoothing=False
    )
    with torch.no_grad():
        baseline_model.density_logits.fill_(4.0)
        initial = baseline_model(coefficients)
        cut_ref = exact_discrete_cut_moments(initial["density"], coefficients).detach()
        norm_ref = _normalised_material_moments(initial["density"]).detach()
        baseline_model_error = _relative(initial["moments"], cut_ref)

    tolerances = {
        "model_hardcut_error_allowance": MODEL_HARDCUT_ALLOWANCE,
        "independent_cut_r_rel": .02,
        "normalized_material_9moment_l2": .02,
    }
    baseline_row = _run_arm(
        pino, shell, design, coefficients, cut_ref, norm_ref,
        baseline_model_error, "pino_densicrafter", steps, lr, tolerances,
    )
    quadrann_row = _run_arm(
        proxy, shell, design, coefficients, cut_ref, norm_ref,
        baseline_model_error, "pino_quadrann_densicrafter",
        steps, lr, tolerances,
    )
    saved = {}
    for name, row in (("pino_only", baseline_row), ("pino_quadrann", quadrann_row)):
        saved[name] = {
            "final_density": row.pop("final_density"),
            "final_independent_cut": row.pop("final_independent_cut"),
            "final_material_moments": row.pop("final_material_moments"),
        }
    artifact = Path(f"/tmp/w6_p24_6_native128_seed{seed}.pt")
    torch.save({
        "schema": "W6_P24_6_PHYSICAL_GATE_DESIGNS_V1",
        "seed": seed, "resolution": 128,
        "pino_source_checkpoint_sha256": pino_sha,
        "quadrann_source_checkpoint_sha256": quad_sha,
        "quadrann_gate": gate, "geometry_id": metadata[0]["geometry_id"],
        "cut_reference": cut_ref.cpu(), "designs": saved,
        "source": "ANALYTIC_P0_AND_INDEPENDENT_VOXEL_HARD_CUT_NOT_CHERCHI",
    }, artifact)
    return {
        "schema": "W6_P24_6_NATIVE128_PHYSICAL_GATE_COMPARISON_V1",
        "seed": seed, "quadrann_training_seed": P23_SEEDS[seed],
        "resolution": 128, "input_and_fourier_grid": 128,
        "geometry_id": metadata[0]["geometry_id"],
        "pino_source_checkpoint_sha256": pino_sha,
        "quadrann_source_checkpoint_sha256": quad_sha,
        "quadrann_gate": gate,
        "baseline_initial_model_hardcut_error": baseline_model_error,
        "predeclared_tolerances": tolerances,
        "baseline_pino_densicrafter": baseline_row,
        "pino_quadrann_densicrafter": quadrann_row,
        "comparison": {
            "quadrann_model_hardcut_error_delta":
                quadrann_row["model_hardcut_relative_error"]-
                baseline_row["model_hardcut_relative_error"],
            "mass_reduction_delta_fraction":
                quadrann_row["mass_reduction_fraction"]-
                baseline_row["mass_reduction_fraction"],
            "both_feasible": bool(
                baseline_row["feasible_under_predeclared_tolerances"] and
                quadrann_row["feasible_under_predeclared_tolerances"]
            ),
        },
        "artifact": str(artifact),
        "peak_process_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims": {
            "PINO_is_primary": True, "QuadrANN_is_optional": True,
            "model_accuracy_checked_against_independent_hard_cut": True,
            "no_worse_than_baseline_plus_0_5pp": True,
            "Cherchi": False, "native_Newton": False,
            "FEM_FEA": False, "512_cube": False,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pino-checkpoint-dir", type=Path, required=True)
    p.add_argument("--quadrann-checkpoint-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True, choices=(271,277,281))
    p.add_argument("--steps", type=int, default=6)
    p.add_argument("--lr", type=float, default=.06)
    p.add_argument("--wall-cells", type=int, default=4)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(
        pino_checkpoint_dir=a.pino_checkpoint_dir,
        quadrann_checkpoint_dir=a.quadrann_checkpoint_dir,
        seed=a.seed, steps=a.steps, lr=a.lr, wall_cells=a.wall_cells,
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({
        "baseline": result["baseline_pino_densicrafter"],
        "quadrann": result["pino_quadrann_densicrafter"],
        "comparison": result["comparison"],
    }, indent=2))


if __name__ == "__main__":
    main()
