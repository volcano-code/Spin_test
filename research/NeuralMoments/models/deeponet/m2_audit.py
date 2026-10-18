"""W5 M2 multi-seed *analytic only* audit and W2 manifest-readiness check.

This deliberately cannot train from W2 pre-W0 mock labels or from another
window's data. Use a genuine contract + independently approved labels and a
real D encoder for native training in a subsequent milestone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import time
from typing import Any

import torch

from .contract_gate import W0_PUBLISHED_HEAD, W0_SOURCE_SHA, W2_PUBLISHED_HEAD, audit_family_split, strict_json
from .smoke import run

_METRICS = ("r_mae", "r_relative_l2", "J_mae", "J_relative_l2",
            "directional_derivative_mae", "step_l2_error", "post_step_true_objective_gap")


def check_w2_readiness(manifest_path: str | Path | None) -> dict[str, Any]:
    if manifest_path is None:
        return {"ready": False, "reason": "W2 manifest not supplied; no real native teacher labels admitted"}
    data = strict_json(manifest_path)
    if not isinstance(data, dict):
        raise ValueError("W2 manifest must be an object")
    if data.get("schema") != "w2-cherchi-teacher-v1-pre-w0":
        raise ValueError("Unrecognized W2 manifest version (fail closed)")
    runs = data.get("native_teacher_runs")
    count = data.get("training_samples")
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 0 or not isinstance(count, int) or isinstance(count,bool) or count < 0:
        raise ValueError("W2 counts malformed")
    # Even a later positive count doesn't license training: published pre-W0
    # format contains NO approved record checksum catalog or W0 frame seal.
    return {"ready": False, "status": data.get("status"), "native_teacher_runs_declared":runs,
            "training_samples_declared":count,
            "reason":"W2 pre-W0 manifest has no approved per-label checksums/W0 contract linkage; training blocked"}


def run_multiseed(*, seeds: tuple[int, ...] = (7, 19, 31), steps: int = 12,
                  per_family: int = 8, repeats: int = 5,
                  w2_manifest: str | Path | None = None) -> dict[str, Any]:
    if not seeds or len(set(seeds)) != len(seeds) or any(x < 0 for x in seeds):
        raise ValueError("unique nonnegative seeds required")
    if steps < 0 or per_family < 1 or repeats < 1:
        raise ValueError("steps nonnegative, per-family/repeats positive")
    started = time.perf_counter()
    readiness = check_w2_readiness(w2_manifest)
    torch.set_num_threads(1)
    audits = [run(seed=seed, steps=steps, per_family=per_family, repeats=repeats) for seed in seeds]
    for report in audits:
        if report["status"] != "synthetic_architecture_smoke_only" or not report["no_real_spin_label_or_W0_contract"]:
            raise ValueError("Unexpected truth provenance; abort")
        if set(report["train_geometry_families"]) & set(report["test_geometry_families"]):
            raise ValueError("Synthetic family leakage")
    aggregate: dict[str, Any] = {}
    for architecture in ("deeponet", "geometry_mlp"):
        aggregate[architecture] = {}
        for variant in ("residual_only", "derivative_enhanced"):
            entries = [r["model_results"][architecture][variant] for r in audits]
            score = {}
            for name in _METRICS:
                values = [float(x["heldout_metrics"][name]) for x in entries]
                score[name] = {"mean":statistics.fmean(values),
                               "sample_std":statistics.stdev(values) if len(values)>1 else None,
                               "per_seed": dict(zip(map(str,seeds), values))}
            curves = {}
            for k in (0, 1, 2, 4, 8):
                values = [float(x["adaptation"][str(k)]["r_mae"]) for x in entries]
                curves[str(k)] = {"r_mae_mean":statistics.fmean(values), "per_seed":dict(zip(map(str,seeds),values))}
            aggregate[architecture][variant] = {"heldout":score,"oracle_adaptation":curves,
                "parameters":entries[0]["performance"]["parameters"],
                "estimated_linear_macs_cold":entries[0]["performance"]["cold_query_macs"],
                "estimated_linear_macs_warm":entries[0]["performance"]["warm_query_macs"],
                "cpu_train_seconds_sum":sum(x["training"]["cpu_train_seconds"] for x in entries),
                "gpu_seconds_sum":0.0,
                "benchmarks_per_seed_ms":{str(seed):{
                    "cold_encode_plus_query":x["performance"]["cold_encode_plus_query_ms"],
                    "warm_cached_query":x["performance"]["warm_cached_query_ms"],
                    "cached_jacrev_10x10":x["performance"]["cached_jacrev_10x10_ms"]}
                    for seed,x in zip(seeds,entries)}}
    return {"schema":"W5-M2-analytic-only-v1", "status":"MULTISEED_ANALYTIC_ONLY_NATIVE_TRAINING_BLOCKED",
            "frozen_source_sha":W0_SOURCE_SHA,
            "external_dependency_heads_read_only":{"W0":W0_PUBLISHED_HEAD,"W2":W2_PUBLISHED_HEAD},
            "w2_admission":readiness, "no_native_training_or_speedup_claim":True,
            "teacher":"fixed-volume synthetic polynomial density closed form, NOT W0/W2 Spin c",
            "synthetic_train_families":["box","sphere"],"synthetic_test_families":["ellipsoid"],
            "analytic_truth_is_independent":True,"seed_list":list(seeds),
            "hyperparameters":{"steps":steps,"per_family_per_split":per_family,
               "queries_per_geometry":2,"learning_rate":0.003,"batch_size":8,
               "derivative_jacobian_mse_weight":0.5,
               "synthetic_adapter_budgets":[0,1,2,4,8]},
            "cpu_threads":torch.get_num_threads(),"device":"cpu","torch_version":torch.__version__,
            "python_version":platform.python_version(),"gpu_seconds":0.0,
            "wall_seconds":time.perf_counter()-started,"models":aggregate}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds",default="7,19,31")
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--per-family",type=int,default=8)
    p.add_argument("--repeats",type=int,default=5)
    p.add_argument("--w2-manifest",type=Path)
    args = p.parse_args()
    seeds = tuple(int(s.strip()) for s in args.seeds.split(","))
    print(json.dumps(run_multiseed(seeds=seeds,steps=args.steps,
                  per_family=args.per_family,repeats=args.repeats,
                  w2_manifest=args.w2_manifest),indent=2,sort_keys=True,allow_nan=False))


if __name__ == "__main__":
    main()
