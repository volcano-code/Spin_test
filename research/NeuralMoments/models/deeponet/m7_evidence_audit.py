"""Conservative cross-framework audit of *previously published* W6 M5 data.

This snapshot is a lossless selection of identified numeric summary fields,
NOT the full upstream JSON file or a fresh execution of 400-step training.
Future use should load the complete W6 M5 summary by SHA from an independent
read-only checkout. No real Cherchi teacher metrics can be inferred.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

W6_M5_SUMMARY_GIT_BLOB = "2e0d186933cf4f8579b1e012e74df714f5ae2bbc"
SNAPSHOT_SCHEMA = "W5_M7_EXTRACTED_W6_M5_PUBLISHED_SNAPSHOT_V1"
FIELDS = ("r_mae", "J_mae", "warm_J_ms")


def _fail_if(condition: bool, reason: str) -> None:
    if condition:
        raise ValueError(reason)


def inspect_snapshot(source: str | Path) -> dict:
    payload = json.loads(Path(source).read_text(encoding="utf-8"))
    _fail_if(not isinstance(payload, dict) or payload.get("schema") != SNAPSHOT_SCHEMA,
             "UNRECOGNIZED_SNAPSHOT")
    origin, data = payload["origin"], payload["data"]
    _fail_if(origin["source_git_blob_sha1"] != W6_M5_SUMMARY_GIT_BLOB or
             origin["source_schema"] != "W6_M5_EVIDENCE_V1", "UNPINNED_W6_EVIDENCE")
    _fail_if(data["kind"] != "ANALYTIC_CONTINUUM_P0_NOT_CHERCHI", "FALSE_ORACLE_STATUS")
    _fail_if(data["representation_parity"] is not False,
             "FALSE_CLAIM_OF_REPRESENTATION_PARITY")
    _fail_if(data["teacher_real_native_runs"] != 0 or data["teacher_real_samples"] != 0,
             "UNVERIFIED_REAL_TEACHER_STATUS")
    _fail_if(data["seeds"] != [19,23,29] or data["max_steps"] != 400 or
             data["training_families"] != ["box", "sphere"] or
             data["heldout_family"] != "ellipsoid" or
             data["validation_only_checkpoint_selection"] is not True,
             "UNMATCHED_PROTOCOL")
    identities = data["dataset_sha256_per_seed"]
    _fail_if(len(identities) != 3 or [i["seed"] for i in identities] != data["seeds"],
             "INVALID_DATASET_MANIFEST")
    train = [x["train"] for x in identities]
    test = [x["heldout"] for x in identities]
    _fail_if(len(set(train + test)) != 6 or
             any(len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h)
                 for h in train+test), "LEAKED_OR_INVALID_DATASET_HASH")
    models = data["models"]
    _fail_if(not isinstance(models, dict) or set(models) != {
        "w5_deeponet", "w5_geometry_mlp", "w6_lite_bottleneck",
        "w6_convex_potential4", "w6_convex_potential6", "w6_convex_potential8"},
        "INVALID_MODEL_SET")
    counts=[]
    for name,m in models.items():
        _fail_if(type(m.get("real_parameters")) is not int or m["real_parameters"] < 1,
                 "INVALID_MODEL_PARAMETER_COUNT")
        counts.append(m["real_parameters"])
        for metric in FIELDS + ("Jq_max_asymmetry", "cold_ms"):
            val = m.get(metric)
            _fail_if(type(val) not in (float,int) or not math.isfinite(val) or val < 0,
                     f"INVALID_METRIC_{name}_{metric}")
    ratio=max(counts)/min(counts)
    _fail_if(ratio>1.05, "CAPACITY_NOT_COMPARABLE")
    # Pareto improvement requires <= across all metrics and < at least one.
    nondominated=[]
    for name, scores in models.items():
        dominated=any(all(other[key] <= scores[key] for key in FIELDS) and
                      any(other[key] < scores[key] for key in FIELDS)
                      for candidate,other in models.items() if candidate!=name)
        if not dominated:
            nondominated.append(name)
    return {
        "schema": "W5_M7_PUBLISHED_W6_AUDIT_V1",
        "status": "ARCHIVED_ANALYTIC_TRAINING_NOT_RERUN_IN_W5_M7",
        "source_git_blob_sha1": W6_M5_SUMMARY_GIT_BLOB,
        "seed_count": 3, "model_count": len(models),
        "capacity_max_over_min": ratio,
        "pareto_metrics": list(FIELDS),
        "pareto_nondominated_models": nondominated,
        "best_r_mae": min(models, key=lambda n: models[n]["r_mae"]),
        "best_J_mae": min(models, key=lambda n: models[n]["J_mae"]),
        "fastest_archived_cached_J": min(models, key=lambda n: models[n]["warm_J_ms"]),
        "fastest_archived_cold_moment": min(models, key=lambda n: models[n]["cold_ms"]),
        "convex6_Jq_asymmetry": models["w6_convex_potential6"]["Jq_max_asymmetry"],
        "deeponet_Jq_asymmetry": models["w5_deeponet"]["Jq_max_asymmetry"],
        "convex6_cached_J_speed_ratio_vs_deeponet":
            models["w5_deeponet"]["warm_J_ms"] / models["w6_convex_potential6"]["warm_J_ms"],
        "representation_parity": False,
        "teacher_real_native_runs": 0,
        "verified_native_CAD_accuracy": False,
        "this_turn_retrained_W6": False,
        "warning": "Aggregated across W6's pre-existing 3-seed CPU 400-step analytic P0 "+
                   "experiment; not a new training run, not fair information parity, "+
                   "not actual native/Cherchi optimization performance."
    }


def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    a=parser.parse_args()
    report=inspect_snapshot(a.snapshot)
    data=json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+"\n"
    if a.output is not None: a.output.write_text(data, encoding="utf-8")
    print(data, end="")


if __name__=="__main__": main()
