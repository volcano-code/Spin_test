"""P25.1: collect geometry-disjoint multi-seed signals for UQNO calibration.

Each seed job evaluates its matched frozen P14 PINO and P23 QuadrANN pair on
the same deterministic 72-geometry set, two coefficient queries per geometry,
at 64^3 and 128^3. Aggregation joins rows by geometry_id/query/resolution and
forms ensemble disagreement features. Labels remain analytic P0 and
independent voxel hard-cut errors, kept separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
from pathlib import Path

import torch

from ..analytic_cut import sample_dataset
from .p13b_highres import exact_discrete_cut_moments
from .p24_5_diagnostic import SEEDS, _load

DATA_SEED = 20261108
FAMILIES = ("box", "sphere", "ellipsoid")
RESOLUTIONS = (64, 128)
GEOMETRIES_PER_FAMILY = 80
QUERIES_PER_GEOMETRY = 2


def _flat(x):
    return [float(v) for v in x.detach().cpu().reshape(-1)]


def _stats(w):
    wn = w / w.sum(-1, keepdim=True).clamp_min(1e-12)
    entropy = -(wn * wn.clamp_min(1e-12).log()).sum(-1)
    entropy = entropy / torch.log(torch.tensor(float(wn.shape[-1]), device=wn.device))
    ess = 1.0 / wn.square().sum(-1).clamp_min(1e-12)
    return {
        "proposal_min": float(w.min()),
        "proposal_max": float(w.max()),
        "proposal_mean": float(w.mean()),
        "proposal_cv": float(w.std(unbiased=False) / w.mean().clamp_min(1e-12)),
        "proposal_ess": float(ess.mean()),
        "proposal_entropy": float(entropy.mean()),
        "proposal_zero_fraction": float((w <= 1e-12).float().mean()),
    }


def _evaluate_seed(seed, resolution, pino_dir, quad_dir, families=FAMILIES):
    pino, selected, gate, pino_sha, quad_sha = _load(
        seed, pino_dir, quad_dir, resolution
    )
    pino.eval()
    selected.eval()
    data = sample_dataset(
        families, per_family=GEOMETRIES_PER_FAMILY,
        seed=DATA_SEED, grid_size=resolution,
        queries_per_geometry=QUERIES_PER_GEOMETRY,
    )
    D, c, truth_r, truth_J, metadata = data
    if tuple(D.shape[-3:]) != (resolution,)*3:
        raise AssertionError("unexpected input resolution")
    rows = []
    with torch.no_grad():
        for i in range(len(D)):
            geometry = D[i:i+1]
            coeff = c[i:i+1]
            base_weights = pino.encode_geometry(geometry)
            proposal = selected._quadrann_material_proposal(geometry)
            active_weights = base_weights * torch.exp(
                2.0 * torch.tanh(selected.quadrann_gate) *
                torch.tanh(torch.log(
                    (proposal / proposal.mean(-1, keepdim=True).clamp_min(1e-12))
                    .clamp_min(1e-12)
                ))
            )
            base_r = pino.moment_from_weights(base_weights, coeff)
            base_J = pino.jacobian_from_weights(base_weights, coeff)
            quad_r = pino.moment_from_weights(active_weights, coeff)
            quad_J = pino.jacobian_from_weights(active_weights, coeff)
            hardcut_r = exact_discrete_cut_moments(geometry[:, 0:1], coeff)
            occ = geometry[:, 1:2] > 0
            coords = torch.nonzero(occ[0, 0], as_tuple=False).float()
            if coords.numel():
                extent = (coords.max(0).values-coords.min(0).values+1)/resolution
                center = (coords.max(0).values+coords.min(0).values)/(2*(resolution-1))
            else:
                extent = torch.zeros(3)
                center = torch.zeros(3)
            meta = metadata[i]
            rows.append({
                "seed": seed,
                "quadrann_training_seed": SEEDS[seed],
                "resolution": resolution,
                "family": meta["family"],
                "geometry_id": meta["geometry_id"],
                "query_index": meta["query_index"],
                "pino_checkpoint_sha256": pino_sha,
                "quadrann_checkpoint_sha256": quad_sha,
                "quadrann_gate": gate,
                "occupancy_fraction": float(occ.float().mean()),
                "bbox_extent": _flat(extent),
                "bbox_center": _flat(center),
                "base_r": _flat(base_r),
                "quad_r": _flat(quad_r),
                "base_J": _flat(base_J),
                "quad_J": _flat(quad_J),
                "analytic_r": _flat(truth_r[i:i+1]),
                "analytic_J": _flat(truth_J[i:i+1]),
                "hardcut_r": _flat(hardcut_r),
                **_stats(proposal),
            })
    return rows


def run(seed, pino_dir, quad_dir, families=FAMILIES):
    torch.set_num_threads(1)
    if seed not in SEEDS:
        raise ValueError("unsupported P25 matched seed")
    families = tuple(families)
    if not families or any(f not in FAMILIES for f in families):
        raise ValueError("families must be a nonempty subset of the registered families")
    rows = []
    for resolution in RESOLUTIONS:
        rows.extend(_evaluate_seed(seed, resolution, pino_dir, quad_dir, families))
    expected = (len(families)*GEOMETRIES_PER_FAMILY*
                QUERIES_PER_GEOMETRY*len(RESOLUTIONS))
    if len(rows) != expected:
        raise AssertionError(f"expected {expected} rows, got {len(rows)}")
    return {
        "schema": "W6_P25_1_UQNO_SIGNAL_COLLECTION_V1",
        "seed": seed, "data_seed": DATA_SEED,
        "families": list(families), "resolutions": list(RESOLUTIONS),
        "geometries_per_family": GEOMETRIES_PER_FAMILY,
        "queries_per_geometry": QUERIES_PER_GEOMETRY,
        "rows": rows,
        "geometry_id_sha256": hashlib.sha256(
            "\n".join(sorted({x["geometry_id"] for x in rows})).encode()
        ).hexdigest(),
        "peak_process_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "labels": {
            "analytic_P0": "continuum vertical-cut moment/Jacobian",
            "independent_hardcut": "cell-centered voxel hard-cut moments",
        },
        "claims": {
            "PINO_remains_primary": True,
            "QuadrANN_optional": True,
            "Cherchi": False, "native_Newton": False,
            "FEM_FEA": False, "512_cube": False,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pino-checkpoint-dir", type=Path, required=True)
    p.add_argument("--quadrann-checkpoint-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, required=True, choices=(271,277,281))
    p.add_argument("--family", action="append", choices=FAMILIES)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = run(a.seed, a.pino_checkpoint_dir, a.quadrann_checkpoint_dir,
                 families=tuple(a.family) if a.family else FAMILIES)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({
        "seed": a.seed, "rows": len(result["rows"]),
        "unique_geometries": len({x["geometry_id"] for x in result["rows"]}),
    }, indent=2))


if __name__ == "__main__":
    main()
