"""P25.1: train and geometry-disjoint conformal-calibrate a pilot UQNO.

Input is the three-seed P25.1 collection. All rows for one geometry_id,
across queries and resolutions, are assigned to exactly one split.
Two targets are trained separately: ensemble PINO+QuadrANN error to the
independent voxel hard-cut reference, and error to analytic continuum P0.
The latter and former are never conflated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import torch
from torch import nn

SEEDS = (271, 277, 281)
FAMILIES = ("box", "sphere", "ellipsoid")


def _rel(a, b):
    aa = torch.tensor(a, dtype=torch.float64)
    bb = torch.tensor(b, dtype=torch.float64)
    return float((aa-bb).norm()/bb.norm().clamp_min(1e-12))


def _split(geometry_id):
    h = int(hashlib.sha256(geometry_id.encode()).hexdigest()[:8], 16) % 10
    return "train" if h < 6 else ("calibration" if h < 8 else "test")


def _feature(group):
    rows = group["rows"]
    def matrix(key):
        return torch.tensor([r[key] for r in rows], dtype=torch.float64)
    base_r, quad_r = matrix("base_r"), matrix("quad_r")
    base_J, quad_J = matrix("base_J"), matrix("quad_J")
    proposal = torch.tensor([[
        r["proposal_cv"], r["proposal_ess"]/512.0,
        r["proposal_entropy"], r["proposal_zero_fraction"],
        r["proposal_min"], r["proposal_max"],
    ] for r in rows], dtype=torch.float64)
    geometry = rows[0]
    family = [1.0 if geometry["family"] == f else 0.0 for f in FAMILIES]
    geom = torch.tensor(
        [geometry["occupancy_fraction"], *geometry["bbox_extent"],
         *geometry["bbox_center"], *family,
         geometry["resolution"]/128.0],
        dtype=torch.float64,
    )
    gates = torch.tensor([r["quadrann_gate"] for r in rows], dtype=torch.float64)
    mean = lambda x: x.mean(0)
    std = lambda x: x.std(0, unbiased=False)
    features = torch.cat((
        mean(quad_r), std(quad_r),
        mean(quad_J), std(quad_J),
        mean((quad_r-base_r).abs()),
        mean((quad_J-base_J).abs()),
        mean(proposal), geom,
        torch.stack((gates.mean(), gates.std(unbiased=False))),
    ))
    # The ensemble mean is used as the prediction whose error UQNO forecasts.
    pred_r = mean(quad_r)
    truth_r = torch.tensor(geometry["analytic_r"], dtype=torch.float64)
    hardcut_r = torch.tensor(geometry["hardcut_r"], dtype=torch.float64)
    return features.float(), pred_r, truth_r, hardcut_r


class _UQNO(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 96), nn.GELU(),
            nn.Linear(96, 48), nn.GELU(),
            nn.Linear(48, 2),
        )

    def forward(self, x):
        out = self.net(x)
        mu = out[:, 0]
        logvar = out[:, 1].clamp(-8.0, 4.0)
        return mu, logvar


def _group_max_scores(scores, selected_mask, geometry_ids):
    """Max score per geometry; scores are already subset to selected_mask."""
    selected_indices = torch.nonzero(selected_mask, as_tuple=False).reshape(-1).tolist()
    selected_geometry_ids = [geometry_ids[i] for i in selected_indices]
    if len(scores) != len(selected_geometry_ids):
        raise ValueError("score/selected geometry count mismatch")
    grouped = []
    for gid in sorted(set(selected_geometry_ids)):
        local = torch.tensor([g == gid for g in selected_geometry_ids], dtype=torch.bool)
        grouped.append(scores[local].max())
    if not grouped:
        raise ValueError("empty geometry group calibration set")
    return torch.stack(grouped)


def _fit_calibrate(X, y, split, geometry_ids, seed):
    train = torch.tensor([s == "train" for s in split])
    cal = torch.tensor([s == "calibration" for s in split])
    test = torch.tensor([s == "test" for s in split])
    train_gids = sorted({geometry_ids[i] for i, flag in enumerate(train.tolist()) if flag})
    cal_gids = sorted({geometry_ids[i] for i, flag in enumerate(cal.tolist()) if flag})
    test_gids = sorted({geometry_ids[i] for i, flag in enumerate(test.tolist()) if flag})
    if min(len(train_gids), len(cal_gids), len(test_gids)) < 8:
        raise ValueError("insufficient unique geometries per split")
    mean = X[train].mean(0)
    scale = X[train].std(0, unbiased=False).clamp_min(1e-5)
    Xn = ((X-mean)/scale).clamp(-10, 10)
    ylog = torch.log(y.clamp_min(1e-6))
    ymean = ylog[train].mean()
    yscale = ylog[train].std(unbiased=False).clamp_min(1e-4)
    yn = (ylog-ymean)/yscale

    torch.manual_seed(seed)
    model = _UQNO(X.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    history = []
    for epoch in range(1, 401):
        model.train()
        mu, logvar = model(Xn[train])
        loss = 0.5*(logvar+(yn[train]-mu).square()*torch.exp(-logvar)).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        optimizer.step()
        if epoch in (1, 50, 100, 200, 300, 400):
            history.append({"epoch": epoch, "train_nll": float(loss.detach())})

    model.eval()
    with torch.no_grad():
        mu, logvar = model(Xn)
        mu = mu*yscale+ymean
        sigma = torch.exp(0.5*logvar)*yscale
        cal_z = ((ylog[cal]-mu[cal]).abs()/sigma[cal].clamp_min(1e-6))
        # Geometry-level simultaneous calibration: all coefficient queries
        # and both resolutions for a geometry contribute to one max score.
        cal_group_scores = _group_max_scores(cal_z, cal, geometry_ids)
        def conformal_quantile(scores, alpha):
            k = min(len(scores), max(1, math.ceil((len(scores)+1)*(1-alpha))))
            return float(torch.kthvalue(scores, k).values)
        q90 = conformal_quantile(cal_group_scores, .10)
        q95 = conformal_quantile(cal_group_scores, .05)
        lower90 = torch.exp(mu[test]-q90*sigma[test])
        upper90 = torch.exp(mu[test]+q90*sigma[test])
        lower95 = torch.exp(mu[test]-q95*sigma[test])
        upper95 = torch.exp(mu[test]+q95*sigma[test])
        coverage90 = float(((y[test] >= lower90) & (y[test] <= upper90)).float().mean())
        coverage95 = float(((y[test] >= lower95) & (y[test] <= upper95)).float().mean())
        test_indices = torch.nonzero(test, as_tuple=False).reshape(-1).tolist()
        test_geometry_ids = [geometry_ids[i] for i in test_indices]
        geometry_coverage90 = []
        geometry_coverage95 = []
        for gid in test_gids:
            local = torch.tensor([g == gid for g in test_geometry_ids], dtype=torch.bool)
            geometry_coverage90.append(bool(((y[test][local] >= lower90[local]) & (y[test][local] <= upper90[local])).all()))
            geometry_coverage95.append(bool(((y[test][local] >= lower95[local]) & (y[test][local] <= upper95[local])).all()))
        pred_median = torch.exp(mu[test])
        mae_log = float((mu[test]-ylog[test]).abs().mean())
        # Risk-coverage: sort by predicted 90% upper bound, accept lowest risk first.
        order = torch.argsort(upper90)
        sorted_error = y[test][order]
        cumulative = torch.cumsum(sorted_error, 0)/torch.arange(
            1, len(sorted_error)+1, dtype=sorted_error.dtype
        )
        coverage = torch.arange(1, len(sorted_error)+1, dtype=sorted_error.dtype)/len(sorted_error)
        aurc = float(torch.trapz(cumulative, coverage))
        result = {
            "train_rows": int(train.sum()), "calibration_rows": int(cal.sum()),
            "test_rows": int(test.sum()), "feature_dim": int(X.shape[1]),
            "training_feature_q01": [float(v) for v in torch.quantile(X[train], .01, dim=0)],
            "training_feature_q99": [float(v) for v in torch.quantile(X[train], .99, dim=0)],
            "train_unique_geometries": len(train_gids),
            "calibration_unique_geometries": len(cal_gids),
            "test_unique_geometries": len(test_gids),
            "calibration_unit": "maximum standardized residual per geometry across all queries and resolutions",
            "calibration_geometry_scores": len(cal_group_scores),
            "test_geometry_simultaneous_coverage_90": sum(geometry_coverage90)/len(geometry_coverage90),
            "test_geometry_simultaneous_coverage_95": sum(geometry_coverage95)/len(geometry_coverage95),
            "epochs": 400, "training_history": history,
            "calibration_standardized_residual_q90": q90,
            "calibration_standardized_residual_q95": q95,
            "test_coverage_90_interval": coverage90,
            "test_coverage_95_interval": coverage95,
            "test_log_error_mae": mae_log,
            "test_error_median_mae": float((pred_median-y[test]).abs().mean()),
            "test_risk_coverage_aurc": aurc,
            "test_error_mean": float(y[test].mean()),
            "test_error_p90": float(torch.quantile(y[test], .90)),
        }
    return model, mean, scale, ymean, yscale, result


def run(input_dir, checkpoint_dir):
    torch.set_num_threads(1)
    root = Path(input_dir)
    reports = []
    for seed in SEEDS:
        p = root/f"w6_p25_1_seed{seed}.json"
        if not p.is_file():
            raise FileNotFoundError(p)
        d = json.loads(p.read_text())
        if d.get("seed") != seed or len(d.get("rows", [])) != 960:
            raise ValueError(f"invalid P25.1 collection: {p}")
        reports.append(d)

    grouped = {}
    for report in reports:
        for row in report["rows"]:
            key = (row["geometry_id"], row["query_index"], row["resolution"])
            grouped.setdefault(key, {"rows": []})["rows"].append(row)
    if len(grouped) != 960:
        raise ValueError(f"expected 960 geometry-query-resolution groups, got {len(grouped)}")

    X, hard_y, analytic_y, splits, geometry_ids, metadata = [], [], [], [], [], []
    for (gid, query, resolution), group in sorted(grouped.items()):
        if len(group["rows"]) != 3 or {r["seed"] for r in group["rows"]} != set(SEEDS):
            raise ValueError("ensemble seed coverage mismatch")
        rows = group["rows"]
        if len({r["family"] for r in rows}) != 1 or len({r["resolution"] for r in rows}) != 1:
            raise ValueError("geometry metadata mismatch")
        features, pred_r, truth_r, hardcut_r = _feature(group)
        X.append(features)
        hard_y.append(max(_rel(pred_r.tolist(), hardcut_r.tolist()), 1e-6))
        analytic_y.append(max(_rel(pred_r.tolist(), truth_r.tolist()), 1e-6))
        split = _split(gid)
        splits.append(split)
        geometry_ids.append(gid)
        metadata.append({
            "geometry_id": gid, "query_index": query,
            "resolution": resolution, "family": rows[0]["family"],
            "split": split,
            "seed_predictions": [{
                "seed": r["seed"], "quadrann_gate": r["quadrann_gate"],
                "proposal_ess": r["proposal_ess"],
                "proposal_entropy": r["proposal_entropy"],
            } for r in rows],
        })
    X = torch.stack(X)
    hard_y = torch.tensor(hard_y, dtype=torch.float32)
    analytic_y = torch.tensor(analytic_y, dtype=torch.float32)
    hard_model, hm, hs, hym, hys, hard_metrics = _fit_calibrate(X, hard_y, splits, geometry_ids, 2501)
    analytic_model, am, ass, aym, ays, analytic_metrics = _fit_calibrate(X, analytic_y, splits, geometry_ids, 2502)
    test_cases = [{
        **metadata[i],
        "features": [float(v) for v in X[i].tolist()],
        "hardcut_error": float(hard_y[i]),
        "analytic_p0_error": float(analytic_y[i]),
    } for i in range(len(metadata)) if splits[i] == "test"]
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    hard_path = checkpoint_dir / "w6_p25_uqno_hardcut.pt"
    analytic_path = checkpoint_dir / "w6_p25_uqno_analytic_p0.pt"
    torch.save({
        "schema": "W6_P25_UQNO_HARDCUT_PREDICTOR_V1",
        "state_dict": hard_model.state_dict(), "input_mean": hm,
        "input_scale": hs, "target_log_mean": hym, "target_log_scale": hys,
        "feature_dim": int(X.shape[1]), "metrics": hard_metrics,
    }, hard_path)
    torch.save({
        "schema": "W6_P25_UQNO_ANALYTIC_P0_PREDICTOR_V1",
        "state_dict": analytic_model.state_dict(), "input_mean": am,
        "input_scale": ass, "target_log_mean": aym, "target_log_scale": ays,
        "feature_dim": int(X.shape[1]), "metrics": analytic_metrics,
    }, analytic_path)

    return {
        "schema": "W6_P25_1_UQNO_PILOT_CALIBRATION_V1",
        "geometry_split": "sha256(geometry_id) mod 10; train<6, calibration<8, test>=8",
        "unique_geometry_count": len({m["geometry_id"] for m in metadata}),
        "rows": len(metadata), "feature_dim": int(X.shape[1]),
        "hardcut_error_predictor": hard_metrics,
        "analytic_p0_error_predictor": analytic_metrics,
        "metadata": metadata,
        "test_cases": test_cases,
        "checkpoints": {
            "hardcut": str(hard_path), "analytic_p0": str(analytic_path),
        },
        "decision": "PILOT_ONLY_REQUIRES_EXTERNAL_VALIDATION",
        "claims": {
            "PINO_remains_primary": True,
            "UQNO_is_uncertainty_calibrator_not_moment_backbone": True,
            "geometry_disjoint_splits": True,
            "Cherchi": False, "native_Newton": False,
            "FEM_FEA": False, "512_cube": False,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--checkpoint-dir", type=Path, required=True)
    a = p.parse_args()
    result = run(a.input_dir, a.checkpoint_dir)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({
        "hardcut": result["hardcut_error_predictor"],
        "analytic": result["analytic_p0_error_predictor"],
    }, indent=2))


if __name__ == "__main__":
    main()
