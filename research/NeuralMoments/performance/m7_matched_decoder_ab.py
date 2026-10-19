"""W1 M7: real archived Cherchi 25-point material, matched JSON-decode A/B.

ONE optimization dimension (parsing JSON bytes via optional orjson) and ZERO
changes to Cherchi, GMP, accepted materials, or the previous geometric gates.
Full Newton/Boolean speedups cannot be inferred from this archival replay.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import resource
import signal
from statistics import median
import sys
import time

from m6_archived_validation_replay import (ARCHIVE_SHA, run, decoder_for, sha)

SCHEMA = "w1-m7-matched-archived-h8-json-decode-ab-v1"
STANDARD_ORDER = ("stdlib", "orjson", "orjson", "stdlib")
TWO_ORDER = ("stdlib", "orjson")


def _load_points(path, count):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    if len(rows) != count or [row["index"] for row in rows] != list(range(count)):
        raise ValueError("M7_INCOMPLETE_POINT_REPLAY")
    for row in rows:
        if not row["stage_timing"]["all_passed"] or not row.get("m7_scientific_fingerprint"):
            raise ValueError("M7_MISSING_SCIENTIFIC_PROOF")
        if len(row.get("moments", [])) != 10 or len(row.get("q", [])) != 10:
            raise ValueError("M7_INVALID_POINT_VECTORS")
    return rows


def _scientific_receipt(rows, baseline):
    """Use values from independently re-integrated GMP and archived ten/J."""
    canon = [{
        "index": row["index"],
        "material_sha256": row["archive_material_sha256"],
        "material_identity": row["topology_hash"],
        "q": row["q"],
        "ten": row["moments"],
        "scientific_fingerprint": row["m7_scientific_fingerprint"],
    } for row in rows]
    # The only allowed numeric finite-difference status is the original one.
    fd = baseline["independent_fd"]
    if len(rows) == 25:
        if (fd["status"] != "NUMERICAL_FD_ONLY_NO_SMOOTH_NEIGHBORHOOD_PROOF"
                or fd["numeric_stencils"] != 9
                or fd["originally_changed_feature_hash_points"] != 8):
            raise ValueError("M7_H8E_ORIGINAL_FAILURE_STATUS_CHANGED")
    else:
        if fd["status"] != "INCOMPLETE_NO_FD":
            raise ValueError("M7_PARTIAL_REPLAY_FALSE_FD_ADMISSION")
    if (baseline.get("full_newton_solver_measured") is not False
            or baseline.get("fresh_cherchi_boolean_calls") != 0
            or baseline.get("new_independent_self_intersection_audits") != 0
            or baseline.get("paper_speed_qualified") is not False):
        raise ValueError("M7_FORBIDDEN_FRESH_SOLVER_CLAIM")
    return sha256(json.dumps(canon, sort_keys=True, separators=(",",":"),
                             allow_nan=False).encode()).hexdigest()


def _stage_ms(report, stage):
    return report["stage_exclusive_ns"][stage]/1e6


def summarize_pair(runs, count, order):
    if len(runs) != len(order) or [r["backend"] for r in runs] != list(order):
        raise ValueError("M7_MISMATCHED_REPLAY_SEQUENCE")
    if count != runs[0]["point_count"] or any(r["point_count"] != count for r in runs):
        raise ValueError("M7_NOT_ALL_POINTS_REPLAYED")
    if len({r["science_receipt_sha256"] for r in runs}) != 1:
        raise ValueError("M7_OLD_NEW_SCIENTIFIC_BITWISE_DRIFT")
    if len({r["native_binary_sha256"] for r in runs}) != 1:
        raise ValueError("M7_CHANGED_NATIVE_GMP_BINARY")
    values = {}
    for backend in ("stdlib", "orjson"):
        cases=[r for r in runs if r["backend"]==backend]
        if len(cases) != len(order)//2:
            raise ValueError("M7_UNBALANCED_BACKEND_SAMPLES")
        values[backend] = dict(
            samples=len(cases),
            end_to_end_median_seconds=median(r["wall_seconds"] for r in cases),
            parse_json_median_seconds=median(r["parse_json_seconds"] for r in cases),
            independent_native_gmp_median_seconds=median(r["native_gmp_seconds"] for r in cases),
            end_to_end_range_seconds=[min(r["wall_seconds"] for r in cases),
                                      max(r["wall_seconds"] for r in cases)],
        )
    old,new=values["stdlib"],values["orjson"]
    return dict(
        count_per_run=count,
        order=list(order),
        complete_25_point_scientific_parity=(count==25),
        identical_scientific_receipt_sha256=runs[0]["science_receipt_sha256"],
        backends=values,
        paired_end_to_end_archived_validator_ratio_old_over_new=(
            old["end_to_end_median_seconds"]/new["end_to_end_median_seconds"]),
        paired_parse_only_ratio_old_over_new=(
            old["parse_json_median_seconds"]/new["parse_json_median_seconds"]),
        **{
            "fresh_cherchi_boolean_calls":0,
            "production_full_solver_speedup":None,
            "new_full_geometry_self_intersection_checks":0,
            "archived_analytic_jacobian_not_regenerated":True,
            "original_h8e_ci_failure_preserved":True,
            "paper_speed_qualified":False,
        },
    )


def run_ab(archive, binary, output, *, points=25, order=STANDARD_ORDER):
    archive,binary,output = Path(archive),Path(binary),Path(output)
    if type(points) is not int or not 1<=points<=25:
        raise ValueError("M7_INVALID_POINT_COUNT")
    if tuple(order) not in (STANDARD_ORDER,TWO_ORDER):
        raise ValueError("M7_INVALID_AB_SEQUENCE")
    output.mkdir(parents=True,exist_ok=False)
    runs=[]
    total_start=time.monotonic_ns()
    try:
        if len(Path("/proc/swaps").read_text().splitlines())!=1:
            raise RuntimeError("M7_SWAP_MUST_BE_ZERO")
        if not archive.is_file() or not binary.is_file():
            raise FileNotFoundError("M7_PINNED_ARCHIVE_AND_COMPILED_GMP_REQUIRED")
        if sha(archive.read_bytes())!=ARCHIVE_SHA:
            raise ValueError("M7_SOURCE_ARCHIVE_HASH_DRIFT")
        decoder_for("orjson")  # no claim of optimized run without actual dependency
        import orjson
        if not orjson.__version__:
            raise ValueError("M7_INVALID_ORJSON_VERSION")
        signal.alarm(3600)
        for idx,backend in enumerate(order):
            sub=output/f"sample-{idx:02d}-{backend}"
            print(f"M7_AB_STARTED {idx+1}/{len(order)} {backend} {points} points",flush=True)
            report=run(archive,binary,sub,count=points,reference_indices=(),json_backend=backend)
            rows=_load_points(sub/"points.jsonl", points)
            receipt=_scientific_receipt(rows,report)
            run_row=dict(
                sample=idx,
                backend=backend,
                point_count=points,
                wall_seconds=report["end_to_end_wall_ns"]/1e9,
                parse_json_seconds=_stage_ms(report,"parse_packet")/1e3,
                native_gmp_seconds=_stage_ms(report,"native_exact_tetra")/1e3,
                science_receipt_sha256=receipt,
                native_binary_sha256=report["native_binary_sha256"],
                completed_without_shortcut=(
                    report["point_count"]==points
                    and report["all_points_parity_passed"] is True
                    and report["ten_component_historical_parity_count"]==10*points
                    and report["all_timed_point_stages_closed"] is True
                    and report["original_h8e_ci_failure_preserved"] is True),
            )
            if not run_row["completed_without_shortcut"]:
                raise ValueError("M7_INCOMPLETE_STRICT_EVALUATION")
            runs.append(run_row)
            print(f"M7_AB_COMPLETED {idx+1}/{len(order)} ",
                  f"wall={run_row['wall_seconds']:.3f}s parse={run_row['parse_json_seconds']:.3f}s",flush=True)
        paired=summarize_pair(runs,points,order)
        limits={
            "archived_input_sha256":ARCHIVE_SHA,
            "native_binary_sha256":runs[0]["native_binary_sha256"],
            "host_platform":platform.platform(),
            "python_version":platform.python_version(),
            "orjson_version":orjson.__version__,
            "cpu_count":os.cpu_count(),
            "rss_parent_peak_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "rss_child_peak_kib":resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            "swap_entries":0,
            "max_memory_gib":24,
            "max_single_run_seconds":3600,
            "compile_parallelism":1,
        }
        pair=dict(schema=SCHEMA,scope="ACTUAL_ARCHIVED_CHERCHI_H8E_25POINT_OLD_NEW_JSON_DECODER_ONLY",
                  all_checks_passed=True, experiment_type="ISOLATED_VALIDATOR_OPTIMIZATION_NOT_SOLVER",
                  resource_contract=limits, matched_pair=paired,
                  executions=runs, measured_total_wall_seconds=(time.monotonic_ns()-total_start)/1e9,
                  not_author_cad=True)
        (output/"baseline-performance.json").write_text(json.dumps(pair,indent=2,sort_keys=True,allow_nan=False)+"\n")
        after=dict(schema="w1-m7-before-after-v1",scope="PAIRED_OLD_NEW_ARCHIVED_25POINT_VALIDATOR_ONLY",
                   before=paired["backends"]["stdlib"],after=paired["backends"]["orjson"],
                   paired_results=paired,strict_scientific_parity=True,
                   production_optimization_applied=False,
                   original_25point_ci_failed=True,
                   fresh_boolean_or_newton_calls=0,
                   full_solver_end_to_end_speedup=None,paper_speed_qualified=False)
        (output/"before_after.json").write_text(json.dumps(after,indent=2,sort_keys=True,allow_nan=False)+"\n")
        return pair
    except BaseException as e:
        (output/"failure.json").write_text(json.dumps(dict(
            schema="w1-m7-failure-v1",status="FAILED_CLOSED",
            reason=f"{type(e).__name__}: {e}",completed_paired_runs=len(runs),
            production_speedup=None,paper_speed_qualified=False,
            original_h8e_ci_failure_preserved=True),indent=2,allow_nan=False)+"\n")
        raise
    finally:
        signal.alarm(0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True,type=Path)
    p.add_argument('--binary',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--points',type=int,default=25)
    p.add_argument('--two-run-smoke',action='store_true',help='Only two AB runs; not balanced ABBA')
    a=p.parse_args()
    order=TWO_ORDER if a.two_run_smoke else STANDARD_ORDER
    data=run_ab(a.archive,a.binary,a.output,points=a.points,order=order)
    print('M7_DONE',json.dumps({"points":a.points,"matched_pair":data["matched_pair"][
        "paired_end_to_end_archived_validator_ratio_old_over_new"]},sort_keys=True),flush=True)

if __name__=='__main__':
    main()
