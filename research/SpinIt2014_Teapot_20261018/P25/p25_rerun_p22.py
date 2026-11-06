#!/usr/bin/env python3
"""W4 P25: bounded TEST_ONLY replay of the unchanged W0 native M6 audit.

P25 runs inside an 8 GiB, zero-swap cgroup. It deliberately bypasses the
formal P20 host-resource admission wrapper because the shared GitHub runner
host itself has nonzero swap and less than 20 GiB physical RAM. It does NOT
weaken or impersonate the formal M6 admission policy. The genuine frozen
P20 factory prepares the exact P19 inputs and a fresh evaluator; then the
unchanged W0 audit function is invoked once for diagnostic evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

W0_COMMIT = "5bab2eb2616df306906a6887a273f68acfa49320"
CORE_COMMIT = "58fd12c1306c1c01679a19172e276eef0cb30542"
P24_RUN_URL = "https://github.com/volcano-code/Spin_test/actions/runs/42170336386"
EXPECTED_W0_BLOBS = {
    "research/NeuralMoments/contracts/full_partition_m6.py":
        "7f18bafa1094ae38eadc0fa13cde7730c35cfe32",
    "research/NeuralMoments/contracts/native_teacher_replay.py":
        "4ddd0250ad4a9803139fdd1948c8d4b4e31abf5f",
    "research/NeuralMoments/contracts/native_m5_bridge.py":
        "247c728d3442048a64c2e9c68655cc740365fd88",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, capture_output=True, text=True, timeout=60,
    ).stdout.strip()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def host_snapshot():
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        fields = line.split()
        key = fields[0].rstrip(":")
        if key in wanted and len(fields) >= 2 and fields[1].isdecimal():
            values[key + "_bytes"] = int(fields[1]) * 1024
    return values


def cgroup_snapshot():
    root = Path("/sys/fs/cgroup")
    result = {}
    for name in ("memory.current", "memory.peak", "memory.max",
                 "memory.swap.current", "memory.swap.max", "memory.events"):
        path = root / name
        if path.is_file():
            result[name] = path.read_text(encoding="ascii").strip()
    return result


def native_module_record(directory: Path, prefix: str):
    matches = sorted(directory.glob(prefix + "*.so"))
    if len(matches) != 1:
        raise RuntimeError("ONE_NATIVE_ELF_REQUIRED:" + prefix)
    return {"path": str(matches[0].resolve()), "sha256": sha(matches[0]),
            "size_bytes": matches[0].stat().st_size}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w0-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--w4-root", type=Path, required=True)
    parser.add_argument("--p1", type=Path, required=True)
    parser.add_argument("--native-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    started = time.monotonic()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = {
        "schema": "W4_P25_P22_FIXED_W0_CAPACITY_RERUN_V2",
        "status": "STARTED",
        "test_only": True,
        "formal_M6_executed": False,
        "formal_M6_passed": False,
        "scientific_release": False,
        "W0_owner_admitted": False,
        "W0_physical_case_approved": False,
        "W2_teacher_training_allowed": False,
        "derivative_neighborhood_certified": False,
        "newton_terminal_certified": False,
        "training_admissible": False,
        "native_audit_invoked": False,
        "native_audit_returned": False,
        "formal_resource_admission": False,
        "resource_policy_note": (
            "TEST_ONLY cgroup diagnostic; host physical RAM and host swap are recorded, "
            "not used to override the formal P20 >=20 GiB and host swap-zero gate"
        ),
        "P24_acceptance_run": P24_RUN_URL,
        "expected_w0_commit": W0_COMMIT,
        "expected_core_commit": CORE_COMMIT,
        "w4_commit": os.environ.get("P25_W4_COMMIT"),
        "host_before": host_snapshot(),
        "cgroup_before": cgroup_snapshot(),
        "stages": [],
        "started_monotonic_seconds": started,
    }
    evaluator = None
    bundle = None
    try:
        w0_root = args.w0_root.resolve(strict=True)
        core_root = args.core_root.resolve(strict=True)
        w4_root = args.w4_root.resolve(strict=True)
        p1 = args.p1.resolve(strict=True)
        native_build = args.native_build.resolve(strict=True)

        observed_w0 = git(w0_root, "rev-parse", "HEAD")
        observed_core = git(core_root, "rev-parse", "HEAD")
        observed_w4 = git(w4_root, "rev-parse", "HEAD")
        if observed_w0 != W0_COMMIT:
            raise RuntimeError("W0_COMMIT_MISMATCH:" + observed_w0)
        if observed_core != CORE_COMMIT:
            raise RuntimeError("CORE_COMMIT_MISMATCH:" + observed_core)
        if result["w4_commit"] and observed_w4 != result["w4_commit"]:
            raise RuntimeError("W4_COMMIT_MISMATCH:" + observed_w4)
        result.update(w0_commit=observed_w0, core_commit=observed_core,
                      observed_w4_commit=observed_w4)
        for relative, expected in EXPECTED_W0_BLOBS.items():
            actual = git(w0_root, "rev-parse", "HEAD:" + relative)
            if actual != expected:
                raise RuntimeError("W0_CRITICAL_BLOB_MISMATCH:" + relative)
        result["w0_critical_blobs"] = EXPECTED_W0_BLOBS

        build_report_path = native_build / "P20_NATIVE_BUILD_REPORT.json"
        build_report = read_json(build_report_path)
        if build_report.get("status") != "BUILT_AND_IMPORT_VERIFIED_NO_GEOMETRY":
            raise RuntimeError("P20_NATIVE_BUILD_NOT_VERIFIED")
        result["native_build_report_sha256"] = sha(build_report_path)
        result["native_build_wall_seconds"] = build_report.get("wall_seconds")
        build_modules = build_report.get("native_modules", {})
        module_specs = (
            ("_make_it_stand", native_build / "core" / "python", "native_sha256"),
            ("_cherchi_core_boolean", native_build / "cherchi" / "python", "bridge_sha256"),
            ("_cherchi_rational_moments", native_build / "cherchi" / "python", None),
        )
        module_files = {}
        for module_name, directory, pin_key in module_specs:
            actual = native_module_record(directory, module_name)
            expected = build_modules.get(module_name)
            if type(expected) is not dict or actual["sha256"] != expected.get("sha256"):
                raise RuntimeError("NATIVE_BUILD_REPORT_MODULE_MISMATCH:" + module_name)
            if pin_key:
                result.setdefault("built_module_hashes", {})[pin_key] = actual["sha256"]
            module_files[module_name] = actual
        result["native_module_files"] = module_files

        request_path = p1 / "P20_native_request.json"
        request = read_json(request_path)
        result["material_request_sha256"] = sha(request_path)
        result["material_request_registered_w0_commit"] = request.get("source_w0_commit")
        result["material_request_is_historical_registration"] = (
            request.get("source_w0_commit") != observed_w0
        )

        # P20's Python facade is imported from the independently frozen Core
        # source tree; W0's research package is imported from the fixed W0 tree.
        sys.path[:0] = [
            str(w0_root),
            str(core_root / "python"),
            str(p1),
            str(native_build / "core" / "python"),
            str(native_build / "cherchi" / "python"),
        ]
        os.environ["PYTHONNOUSERSITE"] = "1"
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ["OMP_NUM_THREADS"] = "1"
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
        os.environ["MKL_NUM_THREADS"] = "1"

        # Match the bounded P20 preparation worker's address-space ceiling,
        # without pretending this diagnostic satisfies the host resource gate.
        limit = 6 * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        result["worker_address_space_limit_bytes"] = limit

        import p20_native_factory
        from research.NeuralMoments.contracts.full_partition_m6 import (
            audit_native_full_partition_once,
        )
        from research.NeuralMoments.contracts.native_teacher_replay import (
            canonical_mesh_rational_rows,
        )
        if not callable(canonical_mesh_rational_rows):
            raise RuntimeError("FIXED_W0_CANONICAL_RATIONAL_HELPER_MISSING")

        preparation_started = time.monotonic()
        bundle = p20_native_factory.prepare_context()
        evaluator = bundle["evaluator"]
        pins = p20_native_factory.observed_pins(bundle)
        if pins["native_sha256"] != module_files["_make_it_stand"]["sha256"]:
            raise RuntimeError("FACTORY_NATIVE_MODULE_PIN_MISMATCH")
        if pins["bridge_sha256"] != module_files["_cherchi_core_boolean"]["sha256"]:
            raise RuntimeError("FACTORY_CHERCHI_MODULE_PIN_MISMATCH")
        if evaluator.call_counts != {
            "source": 0, "boolean": 0, "integration": 0, "derivative": 0,
        }:
            raise RuntimeError("FACTORY_MUST_BE_FRESH_AND_UNEVALUATED")
        preparation = {
            "schema": "W4_P25_FRESH_FACTORY_PREPARATION_V1",
            "status": "P25_FACTORY_PREPARED_TEST_ONLY_NO_CHERCHI_EVALUATION",
            "test_only": True,
            "w0_commit": observed_w0,
            "core_commit": observed_core,
            "w4_commit": observed_w4,
            "pins": pins,
            "pins_are_self_observed_not_independently_preregistered": True,
            "factory_timings": bundle["timings"],
            "problem_identity": bundle["problem"].identity,
            "input_identity": bundle["input_identity"],
            "native_call_counts_before_audit": dict(evaluator.call_counts),
            "formal_M6_executed": False,
            "scientific_admission": False,
            "wall_seconds": time.monotonic() - preparation_started,
        }
        write_json(out / "P25_FACTORY_PREPARATION.json", preparation)
        write_json(out / "P25_OBSERVED_SIX_PINS_TEST_ONLY.json", pins)
        result["observed_six_pins"] = pins
        result["stages"].append({
            "stage": "genuine_frozen_P20_factory_prepare_context",
            "status": "PASS",
            "seconds": preparation["wall_seconds"],
            "native_call_counts": dict(evaluator.call_counts),
        })

        result["native_audit_invoked"] = True
        audit_started = time.monotonic()
        try:
            evidence = audit_native_full_partition_once(
                evaluator=evaluator,
                problem=bundle["problem"],
                c=bundle["coefficients"],
                pins=pins,
            )
            write_json(out / "native-evidence.json", evidence)
            result["native_audit_returned"] = True
            result["native_evidence_schema"] = evidence.get("schema") if type(evidence) is dict else None
            result["native_evidence_status"] = evidence.get("status") if type(evidence) is dict else None
            result["native_full_partition_certified_test_only"] = (
                evidence.get("native_full_partition_certified") is True
                if type(evidence) is dict else False
            )
            result["status"] = "TEST_ONLY_NATIVE_AUDIT_RETURNED_NOT_FORMAL"
        except BaseException as error:
            result["status"] = "TEST_ONLY_NATIVE_AUDIT_RAISED"
            result["audit_error"] = type(error).__name__ + ": " + str(error)
            (out / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
        result["native_audit_wall_seconds"] = time.monotonic() - audit_started
        result["native_call_counts_after_audit"] = dict(evaluator.call_counts)
        result["stages"].append({
            "stage": "unchanged_W0_native_M6_audit_function_TEST_ONLY",
            "status": "RETURNED" if result["native_audit_returned"] else "RAISED",
            "seconds": result["native_audit_wall_seconds"],
        })
        result["diagnostic_captured"] = True
    except BaseException as error:
        result["status"] = "TEST_ONLY_SETUP_FAILED"
        result["setup_error"] = type(error).__name__ + ": " + str(error)
        (out / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
        result["diagnostic_captured"] = False
    finally:
        if evaluator is not None:
            result["native_call_counts_final"] = dict(evaluator.call_counts)
        result["host_after"] = host_snapshot()
        result["cgroup_after"] = cgroup_snapshot()
        result["maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["wall_seconds"] = time.monotonic() - started
        result["result_file_sha256_excluded"] = True
        write_json(out / "P25_P22_RERUN_RESULT.json", result)
        print(json.dumps({
            "status": result["status"],
            "diagnostic_captured": result.get("diagnostic_captured", False),
            "native_audit_returned": result.get("native_audit_returned", False),
            "native_full_partition_certified_test_only": result.get("native_full_partition_certified_test_only", False),
            "native_call_counts": result.get("native_call_counts_final"),
            "host_swap_total_bytes": result.get("host_after", {}).get("SwapTotal_bytes"),
            "cgroup_memory_peak": result.get("cgroup_after", {}).get("memory.peak"),
            "wall_seconds": result["wall_seconds"],
        }, ensure_ascii=False, sort_keys=True), flush=True)

    return 0 if result.get("diagnostic_captured") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
