"""P24.5: isolate QuadrANN domain/resolution shift before any retraining.

Compare the same matched P14 PINO and P23 QuadrANN checkpoints on identical
analytic sphere/ellipsoid geometries at 64^3 and 128^3. Reproduce P24's
initial DensiCrafter density field (protected shell=1, interior=sigmoid(4)).
Report analytic P0 moment/J errors, componentwise deltas, and proposal
weight concentration. This is diagnostic evidence, not Cherchi certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
from pathlib import Path

import torch

from ..analytic_cut import sample_dataset
from ..spin_pino.spin_pino import SpinPINO
from ..p0_integration.selected_pino import SelectedPINOCandidates
from .p17_trained_pino import _surface_masks

SEEDS = {271: 883, 277: 887, 281: 991}
QUADRANN_PIN = "111dd611aaeac1fb98c76385706b003ea8ef94be"


def _load(seed, pino_dir, quadrann_dir, resolution):
    pino_path = pino_dir / f"w6_p14_grid64_seed{seed}.pt"
    quad_path = quadrann_dir / f"w6_p21_quadrann_pino{seed}_seed{SEEDS[seed]}.pt"
    for p in (pino_path, quad_path):
        if not p.is_file():
            raise FileNotFoundError(p)
    pkg = torch.load(pino_path, map_location="cpu", weights_only=False)
    if pkg.get("seed") != seed or pkg.get("grid_size") != 64:
        raise ValueError("P14 source identity mismatch")
    pino_sha = hashlib.sha256(pino_path.read_bytes()).hexdigest()
    qpkg = torch.load(quad_path, map_location="cpu", weights_only=False)
    if qpkg.get("pino_seed") != seed or qpkg.get("training_seed") != SEEDS[seed]:
        raise ValueError("P23 seed identity mismatch")
    if qpkg.get("pino_source_checkpoint_sha256") != pino_sha:
        raise ValueError("P23/P14 checkpoint SHA mismatch")
    if qpkg.get("quadrann_upstream") != f"kesmarag/QuadrANN@{QUADRANN_PIN}":
        raise ValueError("QuadrANN source pin mismatch")
    pino = SpinPINO(
        width=8, modes=4, n_layers=4, grid_size=resolution,
        points_per_axis=8, hidden_dim=48, smoothing=.04,
        moment_parameterization="logistic_atom", temperature=.12,
        geometry_adapter="none", use_gradient_checkpoint=True,
    )
    pino.load_state_dict(pkg["state_dict"], strict=True)
    pino.train()  # retain P24's checkpointed density-input gradient mode
    for p in pino.parameters():
        p.requires_grad_(False)
    selected = SelectedPINOCandidates(
        pino, quadrann=True, quadrann_condition_on_material=True,
        quadrann_max_points=128, quadrann_kernel_width=.45,
    )
    selected.quadrann_adapter.model.load_state_dict(
        qpkg["quadrann_state_dict"], strict=True
    )
    gate = float(qpkg["quadrann_gate"])
    with torch.no_grad():
        selected.quadrann_gate.fill_(gate)
    for p in selected.parameters():
        p.requires_grad_(False)
    selected.train()
    selected.quadrann_adapter.model.eval()
    return pino, selected, gate, pino_sha, hashlib.sha256(quad_path.read_bytes()).hexdigest()


def _rel(pred, truth):
    return float((pred-truth).norm() / truth.norm().clamp_min(1e-12))


def _finite_list(x):
    return [float(v) for v in x.detach().cpu().reshape(-1)]


def _run_case(seed, resolution, family, pino_dir, quadrann_dir):
    pino, selected, gate, pino_sha, quad_sha = _load(
        seed, pino_dir, quadrann_dir, resolution
    )
    D, c, truth_r, truth_J, meta = sample_dataset(
        (family,), per_family=1, seed=seed+707,
        grid_size=resolution, queries_per_geometry=1,
    )
    # Match P24 initial density: shell is fixed at 1; design interior starts
    # at sigmoid(4); occupancy remains the full original solid.
    occupancy = D[:, 1:2] > 0
    shell, design = _surface_masks(occupancy, wall_cells=4)
    density = torch.where(
        shell, torch.ones_like(D[:, :1]),
        torch.where(design, torch.full_like(D[:, :1], float(torch.sigmoid(torch.tensor(4.0)))),
                    torch.zeros_like(D[:, :1])),
    )
    geometry = torch.cat((density, occupancy.to(density.dtype),
                          torch.zeros_like(density), torch.zeros_like(density)), dim=1)
    with torch.no_grad():
        base_weights = pino.encode_geometry(geometry)
        q_proposal = selected._quadrann_material_proposal(geometry)
        active_weights = base_weights * torch.exp(
            2.0 * torch.tanh(selected.quadrann_gate) *
            torch.tanh(torch.log(
                (q_proposal / q_proposal.mean(dim=-1, keepdim=True).clamp_min(1e-12))
                .clamp_min(1e-12)
            ))
        )
        base_r = pino.moment_from_weights(base_weights, c)
        base_J = pino.jacobian_from_weights(base_weights, c)
        quad_r = pino.moment_from_weights(active_weights, c)
        quad_J = pino.jacobian_from_weights(active_weights, c)
    qn = q_proposal / q_proposal.sum(dim=-1, keepdim=True).clamp_min(1e-12)
    ess = 1.0 / qn.square().sum(dim=-1)
    component_delta = (quad_r-truth_r).abs() - (base_r-truth_r).abs()
    jac_component_delta = (quad_J-truth_J).abs() - (base_J-truth_J).abs()
    return {
        "seed": seed, "quadrann_training_seed": SEEDS[seed],
        "resolution": resolution, "family": family,
        "geometry_id": meta[0]["geometry_id"],
        "quadrann_gate": gate,
        "pino_source_checkpoint_sha256": pino_sha,
        "quadrann_source_checkpoint_sha256": quad_sha,
        "quadrann_proposal": {
            "node_count": int(q_proposal.shape[-1]),
            "min": float(q_proposal.min()),
            "max": float(q_proposal.max()),
            "mean": float(q_proposal.mean()),
            "std": float(q_proposal.std(unbiased=False)),
            "coefficient_of_variation": float(q_proposal.std(unbiased=False) /
                                               q_proposal.mean().clamp_min(1e-12)),
            "effective_sample_size": float(ess.mean()),
            "normalized_entropy": float((-(qn*qn.clamp_min(1e-12).log()).sum(-1) /
                                          math.log(qn.shape[-1])).mean()),
            "zero_fraction": float((q_proposal <= 1e-12).float().mean()),
        },
        "baseline_pino": {
            "r_relative_l2_to_analytic_p0": _rel(base_r, truth_r),
            "J_relative_l2_to_analytic_p0": _rel(base_J, truth_J),
            "r": _finite_list(base_r), "J": _finite_list(base_J),
        },
        "quadrann_pino": {
            "r_relative_l2_to_analytic_p0": _rel(quad_r, truth_r),
            "J_relative_l2_to_analytic_p0": _rel(quad_J, truth_J),
            "r": _finite_list(quad_r), "J": _finite_list(quad_J),
        },
        "analytic_truth": {"r": _finite_list(truth_r), "J": _finite_list(truth_J)},
        "componentwise_abs_error_delta_r": _finite_list(component_delta),
        "componentwise_abs_error_delta_J": _finite_list(jac_component_delta),
        "quadrann_r_error_delta": _rel(quad_r, truth_r)-_rel(base_r, truth_r),
        "quadrann_J_error_delta": _rel(quad_J, truth_J)-_rel(base_J, truth_J),
        "claims": {"analytic_P0_only": True, "Cherchi": False,
                   "native_Newton": False, "FEM_FEA": False},
    }


def run(seed, pino_dir, quadrann_dir):
    torch.set_num_threads(1)
    cases = []
    # Identical analytic geometry IDs at both resolutions are mandatory.
    for family in ("sphere", "ellipsoid"):
        for resolution in (64, 128):
            cases.append(_run_case(seed, resolution, family, pino_dir, quadrann_dir))
    for family in ("sphere", "ellipsoid"):
        ids = {x["geometry_id"] for x in cases if x["family"] == family}
        if len(ids) != 1:
            raise AssertionError(f"{family} geometry identity changed across resolution")
    return {
        "schema": "W6_P24_5_QUADRANN_DOMAIN_RESOLUTION_DIAGNOSTIC_V1",
        "seed": seed, "quadrann_training_seed": SEEDS[seed],
        "cases": cases,
        "peak_process_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "decision_scope": "diagnostic_only_no_promotion",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pino-checkpoint-dir", type=Path, required=True)
    p.add_argument("--quadrann-checkpoint-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True, choices=(271, 277, 281))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(a.seed, a.pino_checkpoint_dir, a.quadrann_checkpoint_dir)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps([{
        "resolution": c["resolution"], "family": c["family"],
        "base_r": c["baseline_pino"]["r_relative_l2_to_analytic_p0"],
        "quad_r": c["quadrann_pino"]["r_relative_l2_to_analytic_p0"],
        "base_J": c["baseline_pino"]["J_relative_l2_to_analytic_p0"],
        "quad_J": c["quadrann_pino"]["J_relative_l2_to_analytic_p0"],
        "proposal_ess": c["quadrann_proposal"]["effective_sample_size"],
        "proposal_cv": c["quadrann_proposal"]["coefficient_of_variation"],
    } for c in result["cases"]], indent=2))


if __name__ == "__main__":
    main()
