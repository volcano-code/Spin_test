"""W1: immutable historical evidence audit and exclusive-stage profiler.

This instrument does not optimize geometry, modify ABI or certify paper speed.
"""
from __future__ import annotations
import argparse
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import platform
import resource
import time

FROZEN = "0bcc187b3005478baa586a6d6f450e73811ca342"
HISTORY = {
    "noodles": "3b5d66927742d6a369f9f700c5035c988fc92016",
    "heart": "9eb5269b12e8c33d22b35b7107c03330617be602",
}
HISTORY_DIR = "experiments/faster_core_repair_20261012"
EXCLUSIVE = ("source", "boolean", "derivative", "integration")
STAGES = EXCLUSIVE + ("construction_motion", "fraction_conversion",
                     "gmp_moments", "snapshot", "same_call_validation",
                     "native_boundary_audit", "independent_moments")


def digest(data):
    return sha256(data).hexdigest()


def blob_sha(data):
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class StageClock:
    """Sequential, nonoverlapping stages with visible unattributed time."""
    def __init__(self):
        self.start = time.perf_counter_ns()
        self.entries = []
        self.active = None

    def measure(self, label, work):
        if label not in STAGES or self.active is not None:
            raise ValueError("W1_INVALID_OR_OVERLAPPING_STAGE")
        self.active = label
        started = time.perf_counter_ns()
        status = "returned"
        try:
            return work()
        except BaseException:
            status = "failed"
            raise
        finally:
            self.entries.append(dict(stage=label,
                                     ns=time.perf_counter_ns() - started,
                                     status=status))
            self.active = None

    def snapshot(self):
        if self.active is not None:
            raise ValueError("W1_ACTIVE_STAGE")
        wall = time.perf_counter_ns() - self.start
        summed = sum(row["ns"] for row in self.entries)
        if summed > wall:
            raise ValueError("W1_OVERLAPPING_TIMES")
        return dict(wall_ns=wall, stages=self.entries,
                    unattributed_ns=wall - summed,
                    all_returned=all(x["status"] == "returned"
                                     for x in self.entries))


def verify_history(record):
    if record.get("schema") != "faster-exclusive-solver-timing-v1":
        raise ValueError("W1_BAD_HISTORY_SCHEMA")
    stages = record["exclusive_stage_ns"]
    if not stages or any(type(v) is not int or v < 0 for v in stages.values()):
        raise ValueError("W1_BAD_HISTORY_TIMES")
    algorithm = sum(stages.get(name, 0) for name in EXCLUSIVE)
    validation = sum(v for name, v in stages.items() if name.startswith("map_"))
    remaining = sum(v for name, v in stages.items()
                    if name not in EXCLUSIVE and not name.startswith("map_"))
    if algorithm != record["measured_algorithm_ns"] or validation != record["validation_ns"]:
        raise ValueError("W1_HISTORY_STAGE_SUM_MISMATCH")
    if record["solver_completed"]:
        if record["solver_wall_ns"] != sum(stages.values()):
            raise ValueError("W1_HISTORY_WALL_MISMATCH")
        if record["unclassified_ns"] != remaining:
            raise ValueError("W1_HISTORY_UNCLASSIFIED_MISMATCH")
    elif record["solver_wall_ns"] is not None or record["unclassified_ns"] is not None:
        raise ValueError("W1_INCOMPLETE_SOLVER_CANNOT_HAVE_WALL")
    return dict(solver_completed=record["solver_completed"],
                solver_wall_ns=record["solver_wall_ns"],
                measured_algorithm_ns=algorithm, validation_ns=validation,
                unclassified_ns=record["unclassified_ns"],
                unfinished_stages=record["unfinished_stages"],
                paper_comparable_seconds=None)


def audit(root):
    historical = {}
    for name, expected in HISTORY.items():
        path = root / HISTORY_DIR / (name + "-historical-timing-scope-01.json")
        if not path.is_file():
            historical[name] = dict(status="ABSENT", expected_blob_sha=expected)
            continue
        raw = path.read_bytes()
        if blob_sha(raw) != expected:
            raise ValueError("W1_HISTORICAL_SOURCE_DRIFT:" + name)
        historical[name] = dict(status="FROZEN_HISTORY_VERIFIED",
                                blob_sha=expected, sha256=digest(raw),
                                source=verify_history(json.loads(raw)))
    inputs = {}
    for key, relative in {
        "noodles_v7": "research/Noodles_v7_20261017/V7_STAGE_STATUS.json",
        "h8_request": "research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/artifacts/h8-request/prepared-request.json"
    }.items():
        path = root / relative
        inputs[key] = dict(path=relative, available=path.is_file(),
                           sha256=digest(path.read_bytes()) if path.is_file() else None)
    return dict(schema="w1-baseline-performance-v1",
                scope="CHECKOUT_AUDIT_ONLY_NO_NEW_NATIVE_BENCHMARK",
                freeze_sha=FROZEN,
                inputs=inputs, historical_evidence=historical,
                hardware=dict(platform=platform.platform(), python=platform.python_version(),
                              cpu_count=os.cpu_count(),
                              peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
                native_binary_sha256=None, cherchi_binary_sha256=None,
                arithmetic_binary_sha256=None,
                native_samples=[], end_to_end_solver_seconds=None,
                resources=dict(max_ram_gib=24, swap_required=0,
                               max_job_seconds=3600, max_compile_parallelism=4),
                status="BLOCKED_NATIVE_INPUT_OR_RUNTIME_UNAVAILABLE",
                paper_speed_qualified=False)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    baseline = audit(args.root)
    before_after = dict(schema="w1-before-after-v1",
                        before=None, after=None, old_new_parity=None,
                        end_to_end_speedup=None, production_optimization_applied=False,
                        finished=False, paper_speed_qualified=False,
                        reason="No matching old/new native performance and W0/W2 contract yet")
    for filename, data in (("baseline-performance.json", baseline),
                           ("before_after.json", before_after)):
        (args.output / filename).write_text(
            json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": baseline["status"],
                      "historical": {k: v["status"] for k, v
                                      in baseline["historical_evidence"].items()}}))


if __name__ == "__main__":
    main()
