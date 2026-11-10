"""P25.7: repeat geometry-disjoint splits and model seeds to audit UQNO stability."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from .p25_uqno_aggregate_train import run as train_calibrate


def _state_sha(path):
    package = torch.load(path, map_location="cpu", weights_only=False)
    h = hashlib.sha256()
    for key, value in sorted(package["state_dict"].items()):
        h.update(key.encode())
        h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _compact(report, checkpoint_dir):
    result = {}
    for name, key in (
        ("hardcut", "hardcut_error_predictor"),
        ("analytic_p0", "analytic_p0_error_predictor"),
    ):
        m = report[key]
        result[name] = {
            "train_unique_geometries": m["train_unique_geometries"],
            "calibration_unique_geometries": m["calibration_unique_geometries"],
            "test_unique_geometries": m["test_unique_geometries"],
            "query_q90": m["calibration_query_upper_residual_q90"],
            "query_q95": m["calibration_query_upper_residual_q95"],
            "coverage90": m["test_coverage_90_interval"],
            "coverage95": m["test_coverage_95_interval"],
            "geometry_coverage90": m["test_geometry_simultaneous_coverage_90"],
            "geometry_coverage95": m["test_geometry_simultaneous_coverage_95"],
            "median_error_mae": m["test_error_median_mae"],
            "risk_coverage_aurc": m["test_risk_coverage_aurc"],
            "checkpoint_sha256": _state_sha(
                Path(checkpoint_dir) / (
                    "w6_p25_uqno_hardcut.pt" if name == "hardcut"
                    else "w6_p25_uqno_analytic_p0.pt"
                )
            ),
        }
    return result


def run(input_dir, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    configs = [
        {"name": "split0_seed0", "split_salt": 0, "seed_offset": 0},
        {"name": "split1_seed0", "split_salt": 1, "seed_offset": 0},
        {"name": "split2_seed0", "split_salt": 2, "seed_offset": 0},
        {"name": "split0_seed100", "split_salt": 0, "seed_offset": 100},
        {"name": "split0_seed200", "split_salt": 0, "seed_offset": 200},
        {"name": "split0_seed0_repeat", "split_salt": 0, "seed_offset": 0},
    ]
    runs = {}
    for config in configs:
        name = config["name"]
        checkpoint_dir = output_dir / name / "checkpoints"
        report = train_calibrate(
            input_dir,
            checkpoint_dir,
            split_salt=config["split_salt"],
            seed_offset=config["seed_offset"],
        )
        runs[name] = {
            **config,
            "rows": report["rows"],
            "unique_geometries": report["unique_geometry_count"],
            "results": _compact(report, checkpoint_dir),
        }

    baseline = runs["split0_seed0"]["results"]
    repeat = runs["split0_seed0_repeat"]["results"]
    reproducibility = {
        target: {
            "same_hardcut_checkpoint": (
                baseline[target]["checkpoint_sha256"] == repeat[target]["checkpoint_sha256"]
            ),
            "same_test_median_error_mae": (
                baseline[target]["median_error_mae"] == repeat[target]["median_error_mae"]
            ),
        }
        for target in ("hardcut", "analytic_p0")
    }
    return {
        "schema": "W6_P25_7_REPEATED_SPLIT_AND_TRAINING_SEED_AUDIT_V1",
        "purpose": "separate geometry split sensitivity from neural initialization sensitivity",
        "split_policy": "geometry-disjoint SHA-256 salted split; same source P25.1 shards",
        "training_seed_policy": "base seeds 2501/2502 plus seed_offset",
        "runs": runs,
        "same_configuration_reproducibility": reproducibility,
        "decision": "PILOT_ONLY_NO_PRODUCTION_GATE",
        "PINO_remains_primary": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input_dir, args.output_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({
        "same_configuration_reproducibility": result["same_configuration_reproducibility"],
        "runs": {
            name: {
                target: {
                    "q95": values["query_q95"],
                    "coverage95": values["coverage95"],
                    "median_error_mae": values["median_error_mae"],
                }
                for target, values in run["results"].items()
            }
            for name, run in result["runs"].items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
