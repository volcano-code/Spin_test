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


def _fit_calibrate(X, y, split, seed):
    train = torch.tensor([s == "train" for s in split])
    cal = torch.tensor([s == "calibration" for s in split])
    test = torch.tensor([s == "test" for s in split])
    if min(int(train.sum()), int(cal.sum()), int(test.sum())) < 8:
        raise ValueError("insufficient geometry-disjoint rows per split")
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
        q90 = float(torch.quantile(cal_z, .90))
        q95 = float(torch.quantile(cal_z, .95))
        lower90 = torch.exp(mu[test]-q90*sigma[test])
        upper90 = torch.exp(mu[test]+q90*sigma[test])
        lower95 = torch.exp(mu[test]-q95*sigma[test])
        upper95 = torch.exp(mu[test]+q95*sigma[test])
        coverage90 = float(((y[test] >= lower90) & (y[test] <= upper90)).float().mean())
        coverage95 = float(((y[test] >= lower95) & (y[test] <= upper95)).float().mean())
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


def run(input_dir):
    torch.set_num_threads(1)
    root = Path(input_dir)
    reports = []
    for seed in SEEDS:
        p = root/f"w6_p25_1_seed{seed}.json"
        if not p.is_file():
            raise FileNotFoundError(p)
        d = json.loads(p.read_text())
        if d.get("seed") != seed or len(d.get("rows", [])) != 288:
            raise ValueError(f"invalid P25.1 collection: {p}")
        reports.append(d)

    grouped = {}
    for report in reports:
        for row in report["rows"]:
            key = (row["geometry_id"], row["query_index"], row["resolution"])
            grouped.setdefault(key, {"rows": []})["rows"].append(row)
    if len(grouped) != 288:
        raise ValueError(f"expected 288 geometry-query-resolution groups, got {len(grouped)}")

    X, hard_y, analytic_y, splits, metadata = [], [], [], [], []
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
    hard_model, hm, hs, hym, hys, hard_metrics = _fit_calibrate(X, hard_y, splits, 2501)
    analytic_model, am, ass, aym, ays, analytic_metrics = _fit_calibrate(X, analytic_y, splits, 2502)

    return {
        "schema": "W6_P25_1_UQNO_PILOT_CALIBRATION_V1",
        "geometry_split": "sha256(geometry_id) mod 10; train<6, calibration<8, test>=8",
        "unique_geometry_count": len({m["geometry_id"] for m in metadata}),
        "rows": len(metadata), "feature_dim": int(X.shape[1]),
        "hardcut_error_predictor": hard_metrics,
        "analytic_p0_error_predictor": analytic_metrics,
        "metadata": metadata,
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
    a = p.parse_args()
    result = run(a.input_dir)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({
        "hardcut": result["hardcut_error_predictor"],
        "analytic": result["analytic_p0_error_predictor"],
    }, indent=2))


if __name__ == "__main__":
    main()
