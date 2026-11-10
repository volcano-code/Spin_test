"""P25.4: compare calibrated UQNO risk estimates with train-only baselines.

The evaluator consumes the frozen P25.3 report. Baselines are fitted only on
training geometries; calibration and test geometries are never used to fit
their coefficients. UQNO remains an uncertainty/risk head, not the PINO
moment backbone.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch

from .p25_uqno_gate import CalibratedUQNO


TARGETS = {
    "hardcut": "hardcut_error",
    "analytic_p0": "analytic_p0_error",
}


def _rank(values):
    order = torch.argsort(values, stable=True)
    ranks = torch.empty_like(order, dtype=torch.float64)
    ranks[order] = torch.arange(len(values), dtype=torch.float64)
    return ranks


def _spearman(a, b):
    ra, rb = _rank(a), _rank(b)
    ra = ra - ra.mean()
    rb = rb - rb.mean()
    denom = ra.norm() * rb.norm()
    if float(denom) <= 1e-12:
        return 0.0
    return float((ra * rb).sum() / denom)


def _aurc(errors, risk):
    order = torch.argsort(risk, stable=True)
    sorted_errors = errors[order]
    cumulative = torch.cumsum(sorted_errors, 0) / torch.arange(
        1, len(sorted_errors) + 1, dtype=sorted_errors.dtype
    )
    coverage = torch.arange(1, len(sorted_errors) + 1, dtype=sorted_errors.dtype) / len(sorted_errors)
    return float(torch.trapz(cumulative, coverage))


def _ridge_fit_predict(train_x, train_y, test_x, ridge=1e-2):
    mean = train_x.mean(0)
    scale = train_x.std(0, unbiased=False).clamp_min(1e-5)
    xtr = ((train_x - mean) / scale).clamp(-10, 10)
    xte = ((test_x - mean) / scale).clamp(-10, 10)
    # Add an unregularized intercept; regularize feature coefficients only.
    xtr = torch.cat((torch.ones(len(xtr), 1), xtr), dim=1)
    xte = torch.cat((torch.ones(len(xte), 1), xte), dim=1)
    penalty = torch.eye(xtr.shape[1], dtype=xtr.dtype)
    penalty[0, 0] = 0.0
    beta = torch.linalg.solve(xtr.T @ xtr + ridge * penalty, xtr.T @ train_y)
    return xte @ beta


def _metrics(y, median_prediction, risk_score):
    ylog = torch.log(y.clamp_min(1e-6))
    predlog = torch.log(median_prediction.clamp_min(1e-6))
    return {
        "log_mae": float((predlog - ylog).abs().mean()),
        "log_rmse": float(torch.sqrt(((predlog - ylog) ** 2).mean())),
        "absolute_error_mae": float((median_prediction - y).abs().mean()),
        "risk_spearman": _spearman(risk_score, y),
        "risk_coverage_aurc": _aurc(y, risk_score),
    }


def _evaluate_target(report, checkpoint_dir, target):
    label = TARGETS[target]
    cases = report.get("all_cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("P25.3 report must include all_cases for baseline audit")
    train = [r for r in cases if r["split"] == "train"]
    test = [r for r in cases if r["split"] == "test"]
    if len(train) < 32 or len(test) < 16:
        raise ValueError("insufficient train/test rows")
    x_train = torch.tensor([r["features"] for r in train], dtype=torch.float32)
    x_test = torch.tensor([r["features"] for r in test], dtype=torch.float32)
    y_train = torch.tensor([r[label] for r in train], dtype=torch.float32)
    y_test = torch.tensor([r[label] for r in test], dtype=torch.float32)
    if not (torch.isfinite(x_train).all() and torch.isfinite(x_test).all()
            and torch.isfinite(y_train).all() and torch.isfinite(y_test).all()):
        raise ValueError("nonfinite data in P25.3 report")

    checkpoint = Path(checkpoint_dir) / (
        "w6_p25_uqno_hardcut.pt" if target == "hardcut"
        else "w6_p25_uqno_analytic_p0.pt"
    )
    gate = CalibratedUQNO(checkpoint, target=target)
    intervals = gate.predict_interval(x_test, confidence=.95)
    uqno_median = intervals["median"].reshape(-1).double()
    uqno_upper = intervals["upper"].reshape(-1).double()

    # A constant median and ridge regression are train-only reference models.
    constant = torch.full_like(y_test, float(torch.median(y_train))).double()
    ridge_log = _ridge_fit_predict(
        x_train.double(), torch.log(y_train.double().clamp_min(1e-6)),
        x_test.double(),
    )
    ridge_median = torch.exp(ridge_log)
    return {
        "target": target,
        "train_rows": len(train),
        "test_rows": len(test),
        "train_unique_geometries": len({r["geometry_id"] for r in train}),
        "test_unique_geometries": len({r["geometry_id"] for r in test}),
        "models": {
            "constant_train_median": _metrics(y_test.double(), constant, constant),
            "ridge_log_error": _metrics(y_test.double(), ridge_median, ridge_median),
            "uqno_calibrated_95_upper": {
                **_metrics(y_test.double(), uqno_median, uqno_upper),
                "mean_95_upper_bound": float(uqno_upper.mean()),
                "median_95_upper_bound": float(uqno_upper.median()),
                "fallback_fraction": float((uqno_upper > 0.10).double().mean()),
            },
        },
        "by_geometry_family": {
            family: _metrics(
                y_test.double()[torch.tensor([row["family"] == family for row in test])],
                uqno_median[torch.tensor([row["family"] == family for row in test])],
                uqno_upper[torch.tensor([row["family"] == family for row in test])],
            )
            for family in sorted({row["family"] for row in test})
        },
    }


def run(report_path, checkpoint_dir):
    report = json.loads(Path(report_path).read_text())
    output = {}
    for target in TARGETS:
        output[target] = _evaluate_target(report, checkpoint_dir, target)
    return {
        "schema": "W6_P25_4_UQNO_BASELINE_COMPARISON_V1",
        "split_policy": "reuse frozen geometry-disjoint P25.3 train/test split",
        "ridge": "closed-form ridge regression on train-only standardized features; lambda=1e-2",
        "decision": "PILOT_ONLY_NO_PRODUCTION_GATE",
        "PINO_remains_primary": True,
        "results": output,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.report, args.checkpoint_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\\n")
    print(json.dumps(result["results"], indent=2))


if __name__ == "__main__":
    main()
