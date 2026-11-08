"""P24: compare native-128 DensiCrafter design with and without trained QuadrANN.

PINO stays frozen and remains the sole ten-moment/Jacobian backbone.
QuadrANN is a frozen geometry-conditioned proposal learned in P23; only
DensiCrafter density logits are optimized. All feasibility checks include
the independent cell-centered hard-cut reference. This is analytic P0, not
Cherchi/CAD/Newton certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
from pathlib import Path

import torch
from torch import nn

from ..analytic_cut import sample_dataset
from ..spin_pino.spin_pino import SpinPINO
from ..p0_integration.selected_pino import SelectedPINOCandidates
from .bridge import DensiCrafterSpinPINOBridge
from .p13b_highres import exact_discrete_cut_moments
from .p17_trained_pino import (
    _normalised_material_moments,
    _relative,
    _run_arm,
    _surface_masks,
)

P23_SEEDS = {271: 883, 277: 887, 281: 991}
QUADRANN_UPSTREAM = "111dd611aaeac1fb98c76385706b003ea8ef94be"


class _QuadrANNPINOProxy(nn.Module):
    """Expose the standard DensiCrafter PINO interface with P23 weights."""
    def __init__(self, pino: nn.Module, selected: SelectedPINOCandidates):
        super().__init__()
        self.pino = pino
        self.selected = selected

    def encode_geometry(self, geometry: torch.Tensor) -> torch.Tensor:
        return self.selected.geometry_weights(geometry)

    def moment_from_weights(self, weights: torch.Tensor,
                            coefficients: torch.Tensor) -> torch.Tensor:
        return self.pino.moment_from_weights(weights, coefficients)

    def jacobian_from_weights(self, weights: torch.Tensor,
                              coefficients: torch.Tensor) -> torch.Tensor:
        return self.pino.jacobian_from_weights(weights, coefficients)


def _load_pino(checkpoint_dir: Path, seed: int) -> tuple[SpinPINO, str]:
    source = checkpoint_dir / f"w6_p14_grid64_seed{seed}.pt"
    if not source.is_file():
        raise FileNotFoundError(source)
    package = torch.load(source, map_location="cpu", weights_only=False)
    if package.get("seed") != seed or package.get("grid_size") != 64:
        raise ValueError("P14 source checkpoint provenance mismatch")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    pino = SpinPINO(
        width=8, modes=4, n_layers=4, grid_size=128,
        points_per_axis=8, hidden_dim=48, smoothing=.04,
        moment_parameterization="logistic_atom", temperature=.12,
        geometry_adapter="none", use_gradient_checkpoint=True,
    )
    incompatible = pino.load_state_dict(package["state_dict"], strict=True)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise AssertionError("strict 64^3-to-128^3 PINO transfer failed")
    for parameter in pino.parameters():
        parameter.requires_grad_(False)
    # Match P19: train mode enables non-reentrant activation checkpointing;
    # all PINO parameters remain frozen.
    pino.train()
    return pino, digest


def _load_quadrann(pino: SpinPINO, *, seed: int, pino_sha: str,
                   quadrann_dir: Path) -> tuple[_QuadrANNPINOProxy, str, float]:
    train_seed = P23_SEEDS[seed]
    source = quadrann_dir / f"w6_p21_quadrann_pino{seed}_seed{train_seed}.pt"
    if not source.is_file():
        raise FileNotFoundError(source)
    package = torch.load(source, map_location="cpu", weights_only=False)
    if package.get("pino_seed") != seed or package.get("training_seed") != train_seed:
        raise ValueError("P23 QuadrANN seed provenance mismatch")
    if package.get("pino_source_checkpoint_sha256") != pino_sha:
        raise ValueError("P23 QuadrANN was not trained against this exact P14 PINO checkpoint")
    if package.get("quadrann_upstream") != f"kesmarag/QuadrANN@{QUADRANN_UPSTREAM}":
        raise ValueError("unexpected QuadrANN upstream source pin")
    if package.get("quadrann_license") != "MIT":
        raise ValueError("QuadrANN license provenance missing")
    selected = SelectedPINOCandidates(
        pino, quadrann=True, quadrann_condition_on_material=True,
        quadrann_max_points=128, quadrann_kernel_width=.45,
    )
    selected.quadrann_adapter.model.load_state_dict(
        package["quadrann_state_dict"], strict=True
    )
    gate = float(package["quadrann_gate"])
    if not torch.isfinite(torch.tensor(gate)) or gate <= 0:
        raise ValueError("P23 selected QuadrANN gate must be finite and positive")
    with torch.no_grad():
        selected.quadrann_gate.copy_(torch.tensor(gate, dtype=selected.quadrann_gate.dtype))
    for parameter in selected.parameters():
        parameter.requires_grad_(False)
    # Keep input gradients through both frozen networks, while disabling any
    # upstream stochastic training behavior.
    selected.train()
    selected.quadrann_adapter.model.eval()
    selected.pino.train()
    proxy = _QuadrANNPINOProxy(pino, selected)
    return proxy, hashlib.sha256(source.read_bytes()).hexdigest(), gate


def run(*, pino_checkpoint_dir: Path, quadrann_checkpoint_dir: Path,
        seed: int, steps: int = 6, lr: float = .06, wall_cells: int = 4):
    torch.set_num_threads(1)
    if seed not in P23_SEEDS:
        raise ValueError(f"unsupported matched seed {seed}")
    if steps < 1 or lr <= 0 or wall_cells < 1:
        raise ValueError("steps, learning rate and wall thickness must be positive")

    pino, pino_sha = _load_pino(pino_checkpoint_dir, seed)
    proxy, quadrann_sha, quadrann_gate = _load_quadrann(
        pino, seed=seed, pino_sha=pino_sha,
        quadrann_dir=quadrann_checkpoint_dir,
    )

    data = sample_dataset(("sphere",), per_family=1, seed=seed + 707,
                          grid_size=128, queries_per_geometry=1)
    D, coefficients, _, _, metadata = data
    if tuple(D.shape[-3:]) != (128, 128, 128):
        raise AssertionError("P24 input was silently downsampled")
    occupancy = D[:, 1:2] > 0
    shell, design = _surface_masks(occupancy, wall_cells=wall_cells)

    baseline = DensiCrafterSpinPINOBridge(
        pino, shell, design, gravity_axis=2, smoothing=False
    )
    with torch.no_grad():
        baseline.density_logits.fill_(4.)
        initial = baseline(coefficients)
        model_ref = initial["moments"].detach().clone()
        cut_ref = exact_discrete_cut_moments(
            initial["density"], coefficients
        ).detach().clone()
        norm_ref = _normalised_material_moments(
            initial["density"]
        ).detach().clone()

    tolerances = {
        "model_r_rel": .02,
        "independent_cut_r_rel": .02,
        "normalized_material_9moment_l2": .02,
    }
    # Same geometry, initialization, reference moments, optimizer and budget.
    # Only the frozen geometry proposal differs between the two arms.
    baseline_row = _run_arm(
        pino, shell, design, coefficients, model_ref, cut_ref, norm_ref,
        "feasible_joint", steps, lr, tolerances,
    )
    quadrann_row = _run_arm(
        proxy, shell, design, coefficients, model_ref, cut_ref, norm_ref,
        "feasible_joint", steps, lr, tolerances, require_feasible=False,
    )
    saved = {}
    for name, row in (("pino_only", baseline_row), ("pino_quadrann", quadrann_row)):
        saved[name] = {
            "final_density": row.pop("final_density"),
            "final_independent_cut": row.pop("final_independent_cut"),
            "final_material_moments": row.pop("final_material_moments"),
        }
    artifact = Path(f"/tmp/w6_p24_native128_seed{seed}.pt")
    torch.save({
        "schema": "W6_P24_NATIVE128_PINO_QUADRANN_DENSICRAFTER_TENSORS_V1",
        "seed": seed, "resolution": 128,
        "pino_source_checkpoint_sha256": pino_sha,
        "quadrann_source_checkpoint_sha256": quadrann_sha,
        "quadrann_gate": quadrann_gate,
        "geometry_id": metadata[0]["geometry_id"],
        "protected_shell_cells": int(shell.sum()),
        "design_cells": int(design.sum()),
        "designs": saved,
        "source": "ANALYTIC_P0_NOT_CHERCHI",
    }, artifact)

    base_feasible = baseline_row["feasible_under_predeclared_tolerances"]
    quad_feasible = quadrann_row["feasible_under_predeclared_tolerances"]
    return {
        "schema": "W6_P24_NATIVE128_QUADRANN_DENSICRAFTER_COMPARISON_V1",
        "seed": seed, "quadrann_training_seed": P23_SEEDS[seed],
        "resolution": 128, "input_and_fourier_grid": 128,
        "pino": "P-CRAFT SpinPINO factorized F-FNO/U-FNO",
        "quadrann_upstream": f"kesmarag/QuadrANN@{QUADRANN_UPSTREAM}",
        "pino_source_checkpoint_sha256": pino_sha,
        "quadrann_source_checkpoint_sha256": quadrann_sha,
        "quadrann_gate": quadrann_gate,
        "pino_parameters_frozen": True,
        "quadrann_parameters_frozen": True,
        "densicrafter_density_logits_trainable": True,
        "geometry_id": metadata[0]["geometry_id"],
        "wall_cells": wall_cells,
        "protected_shell_cells": int(shell.sum()),
        "design_cells": int(design.sum()),
        "steps_per_arm": steps, "learning_rate": lr,
        "predeclared_tolerances": tolerances,
        "baseline_pino_densicrafter": baseline_row,
        "pino_quadrann_densicrafter": quadrann_row,
        "comparison": {
            "both_feasible": bool(base_feasible and quad_feasible),
            "mass_reduction_delta_fraction": (
                quadrann_row["mass_reduction_fraction"]
                - baseline_row["mass_reduction_fraction"]
            ),
            "hard_cut_error_delta": (
                quadrann_row["independent_hard_cut_relative_error"]
                - baseline_row["independent_hard_cut_relative_error"]
            ),
            "model_cut_error_delta": (
                quadrann_row["model_cut_moment_relative_error"]
                - baseline_row["model_cut_moment_relative_error"]
            ),
            "com_shift_delta": (
                quadrann_row["center_of_mass_shift"]
                - baseline_row["center_of_mass_shift"]
            ),
        },
        "artifact": str(artifact),
        "peak_process_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims": {
            "PINO_is_primary_moment_and_Jacobian_backbone": True,
            "QuadrANN_is_frozen_optional_geometry_proposal": True,
            "DensiCrafter_density_is_the_only_trainable_component": True,
            "native_128_input_and_Fourier_grid": True,
            "independent_voxel_hard_cut_screen": True,
            "Cherchi": False, "native_Newton": False,
            "FEM_FEA": False, "millimeter_wall_certified": False,
            "512_cube": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pino-checkpoint-dir", type=Path, required=True)
    parser.add_argument("--quadrann-checkpoint-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True, choices=(271, 277, 281))
    parser.add_argument("--steps", type=int, default=6)
    parser.add_argument("--lr", type=float, default=.06)
    parser.add_argument("--wall-cells", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(
        pino_checkpoint_dir=args.pino_checkpoint_dir,
        quadrann_checkpoint_dir=args.quadrann_checkpoint_dir,
        seed=args.seed, steps=args.steps, lr=args.lr,
        wall_cells=args.wall_cells,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True,
                                       allow_nan=False) + "\n")
    print(json.dumps(result["comparison"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
