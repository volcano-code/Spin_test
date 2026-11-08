"""P24.7: multi-geometry, multi-family QuadrANN generalization benchmark.

Matched P14/P23 seeds; 3 independent geometries per family (box, sphere,
ellipsoid); same analytic geometry IDs at 64^3 and 128^3; vertical cuts only
because analytic_cut currently certifies that coefficient-plane family.
Reports analytic P0 moments/J, independent cell-centered hard-cut moments,
proposal concentration, and per-geometry deltas. Diagnostic only: no material
design updates, no Cherchi certification, no production promotion.
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
from .p13b_highres import exact_discrete_cut_moments
from .p17_trained_pino import _surface_masks
from .p24_5_diagnostic import SEEDS, _load


FAMILIES = ("box", "sphere", "ellipsoid")
RESOLUTIONS = (64, 128)
GEOMETRIES_PER_FAMILY = 3


def _rel(a, b):
    return float((a-b).norm()/b.norm().clamp_min(1e-12))


def _list(x):
    return [float(v) for v in x.detach().cpu().reshape(-1)]


def _case(seed, resolution, family, pino_dir, quad_dir):
    pino, selected, gate, pino_sha, quad_sha = _load(
        seed, pino_dir, quad_dir, resolution
    )
    D, c, truth_r, truth_J, metadata = sample_dataset(
        (family,), per_family=GEOMETRIES_PER_FAMILY,
        seed=seed+707, grid_size=resolution, queries_per_geometry=1,
    )
    if tuple(D.shape[-3:]) != (resolution,)*3:
        raise AssertionError("geometry input resolution mismatch")
    shell, design = _surface_masks(D[:, 1:2] > 0, wall_cells=4)
    density = torch.where(
        shell, torch.ones_like(D[:, :1]),
        torch.where(
            design,
            torch.full_like(D[:, :1], float(torch.sigmoid(torch.tensor(4.0)))),
            torch.zeros_like(D[:, :1]),
        ),
    )
    occupancy = D[:, 1:2] > 0
    geometry = torch.cat((
        density, occupancy.to(density.dtype),
        torch.zeros_like(density), torch.zeros_like(density),
    ), dim=1)

    with torch.no_grad():
        base_weights = pino.encode_geometry(geometry)
        proposal = selected._quadrann_material_proposal(geometry)
        active_weights = base_weights * torch.exp(
            2.0 * torch.tanh(selected.quadrann_gate) *
            torch.tanh(torch.log(
                (proposal/proposal.mean(dim=-1, keepdim=True).clamp_min(1e-12))
                .clamp_min(1e-12)
            ))
        )
        base_r = pino.moment_from_weights(base_weights, c)
        base_J = pino.jacobian_from_weights(base_weights, c)
        quad_r = pino.moment_from_weights(active_weights, c)
        quad_J = pino.jacobian_from_weights(active_weights, c)
        hardcut = exact_discrete_cut_moments(density, c)

    normalized = proposal/proposal.sum(-1, keepdim=True).clamp_min(1e-12)
    ess = 1.0/normalized.square().sum(-1)
    entropy = -(normalized*normalized.clamp_min(1e-12).log()).sum(-1)/math.log(normalized.shape[-1])
    rows = []
    for i, meta in enumerate(metadata):
        rows.append({
            "geometry_index": i,
            "geometry_id": meta["geometry_id"],
            "family": meta["family"],
            "base_r_analytic_rel": _rel(base_r[i:i+1], truth_r[i:i+1]),
            "quad_r_analytic_rel": _rel(quad_r[i:i+1], truth_r[i:i+1]),
            "base_J_analytic_rel": _rel(base_J[i:i+1], truth_J[i:i+1]),
            "quad_J_analytic_rel": _rel(quad_J[i:i+1], truth_J[i:i+1]),
            "base_r_hardcut_rel": _rel(base_r[i:i+1], hardcut[i:i+1]),
            "quad_r_hardcut_rel": _rel(quad_r[i:i+1], hardcut[i:i+1]),
            "base_r": _list(base_r[i:i+1]),
            "quad_r": _list(quad_r[i:i+1]),
            "hardcut_r": _list(hardcut[i:i+1]),
            "truth_r": _list(truth_r[i:i+1]),
            "truth_J": _list(truth_J[i:i+1]),
            "proposal_ess": float(ess[i]),
            "proposal_entropy": float(entropy[i]),
        })
    return {
        "seed": seed, "quadrann_training_seed": SEEDS[seed],
        "resolution": resolution, "family": family,
        "quadrann_gate": gate,
        "pino_checkpoint_sha256": pino_sha,
        "quadrann_checkpoint_sha256": quad_sha,
        "geometry_count": len(rows),
        "protected_shell_cells": int(shell.sum()),
        "design_cells": int(design.sum()),
        "proposal": {
            "node_count": int(proposal.shape[-1]),
            "min": float(proposal.min()), "max": float(proposal.max()),
            "mean": float(proposal.mean()), "std": float(proposal.std(unbiased=False)),
            "cv": float(proposal.std(unbiased=False)/proposal.mean().clamp_min(1e-12)),
            "effective_sample_size_mean": float(ess.mean()),
            "normalized_entropy_mean": float(entropy.mean()),
            "zero_fraction": float((proposal <= 1e-12).float().mean()),
        },
        "geometries": rows,
        "claims": {
            "analytic_P0_vertical_cut_only": True,
            "independent_voxel_hardcut": True,
            "Cherchi": False, "native_Newton": False,
            "material_design_optimization": False,
            "512_cube": False,
        },
    }


def run(seed, pino_dir, quad_dir):
    torch.set_num_threads(1)
    cases = []
    for family in FAMILIES:
        for resolution in RESOLUTIONS:
            cases.append(_case(seed, resolution, family, pino_dir, quad_dir))
    for family in FAMILIES:
        low = next(x for x in cases if x["family"] == family and x["resolution"] == 64)
        high = next(x for x in cases if x["family"] == family and x["resolution"] == 128)
        ids_low = [x["geometry_id"] for x in low["geometries"]]
        ids_high = [x["geometry_id"] for x in high["geometries"]]
        if ids_low != ids_high:
            raise AssertionError(f"{family}: geometry identities differ across resolutions")
    return {
        "schema": "W6_P24_7_MULTI_GEOMETRY_GENERALIZATION_V1",
        "seed": seed, "quadrann_training_seed": SEEDS[seed],
        "families": list(FAMILIES),
        "resolutions": list(RESOLUTIONS),
        "geometries_per_family": GEOMETRIES_PER_FAMILY,
        "total_geometry_resolution_cases": len(FAMILIES)*GEOMETRIES_PER_FAMILY*len(RESOLUTIONS),
        "cases": cases,
        "peak_process_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "decision_scope": "generalization_diagnostic_only_no_promotion",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pino-checkpoint-dir", type=Path, required=True)
    p.add_argument("--quadrann-checkpoint-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True, choices=(271,277,281))
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(a.seed, a.pino_checkpoint_dir, a.quadrann_checkpoint_dir)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({
        "seed": a.seed,
        "cases": [{
            "family": c["family"], "resolution": c["resolution"],
            "base_r": sum(x["base_r_analytic_rel"] for x in c["geometries"])/len(c["geometries"]),
            "quad_r": sum(x["quad_r_analytic_rel"] for x in c["geometries"])/len(c["geometries"]),
            "base_J": sum(x["base_J_analytic_rel"] for x in c["geometries"])/len(c["geometries"]),
            "quad_J": sum(x["quad_J_analytic_rel"] for x in c["geometries"])/len(c["geometries"]),
        } for c in result["cases"]]
    }, indent=2))


if __name__ == "__main__":
    main()
