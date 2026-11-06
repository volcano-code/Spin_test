#!/usr/bin/env python3
"""W4 P25: rerun the historical P22 capacity probe against fixed W0.

This is a bounded TEST_ONLY call to the unchanged W0 native M6 audit function.
It deliberately does not use the formal P20 launcher or grant formal M6,
owner, teacher, derivative, Newton, training, or scientific admission.
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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, timeout=30,
    ).stdout.strip()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def cgroup_snapshot():
    root = Path("/sys/fs/cgroup")
    result = {}
    for name in ("memory.current", "memory.peak", "memory.max",
                 "memory.swap.current", "memory.swap.max", "memory.events"):
        path = root / name
        if path.is_file():
            result[name] = path.read_text(encoding="ascii").strip()
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w0-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--w4-root", type=Path, required=True)
    parser.add_argument("--p1", type=Path, required=True)
    parser.add_argument("--native-build", type=Path, required=True)
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--preparation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    started = time.monotonic()
    out = args.output.resolve()
    result = {
        "schema": "W4_P25_P22_FIXED_W0_CAPACITY_RERUN_V1",
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
        "P24_acceptance_run": P24_RUN_URL,
        "expected_w0_commit": W0_COMMIT,
        "expected_core_commit": CORE_COMMIT,
        "w4_commit": os.environ.get("P25_W4_COMMIT"),
        "stages": [],
        "started_monotonic_seconds": started,
        "cgroup_before": cgroup_snapshot(),
    }
    evaluator = None
    try:
        w0_root = args.w0_root.resolve(strict=True)
        core_root = args.core_root.resolve(strict=True)
        w4_root = args.w4_root.resolve(strict=True)
        p1 = args.p1.resolve(strict=True)
        native_build = args.native_build.resolve(strict=True)
        pins_path = args.pins.resolve(strict=True)
        preparation_path = args.preparation.resolve(strict=True)
        out.mkdir(parents=True, exist_ok=False)

        observed_w0 = git_head(w0_root)
        observed_core = git_head(core_root)
        if observed_w0 != W0_COMMIT:
            raise RuntimeError("W0_COMMIT_MISMATCH:" + observed_w0)
        if observed_core != CORE_COMMIT:
            raise RuntimeError("CORE_COMMIT_MISMATCH:" + observed_core)
        result.update(w0_commit=observed_w0, core_commit=observed_core)

        preparation = read_json(preparation_path)
        if preparation.get("completed") is not True:
            raise RuntimeError("P20_OWNED_MATERIAL_PREPARATION_NOT_COMPLETE")
        pins = read_json(pins_path)
        required_pins = {
            "native_sha256", "bridge_sha256", "adapter_sha256",
            "c_sha256", "problem_input_digest", "context_sha256",
        }
        if type(pins) is not dict or set(pins) != required_pins:
            raise RuntimeError("EXACT_SIX_NATIVE_PINS_REQUIRED")
        if preparation.get("result", {}).get("observed_six_pins") != pins:
            raise RuntimeError("P20_PREPARATION_PINS_REPORT_MISMATCH")
        result["pins_sha256"] = sha(pins_path)
        result["pins"] = pins

        build_report_path = native_build / "P20_NATIVE_BUILD_REPORT.json"
        build_report = read_json(build_report_path)
        if build_report.get("status") != "BUILT_AND_IMPORT_VERIFIED_NO_GEOMETRY":
            raise RuntimeError("P20_NATIVE_BUILD_NOT_VERIFIED")
        result["native_build_report_sha256"] = sha(build_report_path)

        # This material request is the frozen P19 one-point design input. Its
        # source_w0_commit records the original registration context; the
        # actual W0 runtime checkout used by this rerun is independently pinned
        # above to the post-fix commit.
        request_path = p1 / "P20_native_request.json"
        request = read_json(request_path)
        result["material_request_sha256"] = sha(request_path)
        result["material_request_registered_w0_commit"] = request.get("source_w0_commit")

        module_specs = (
            ("_make_it_stand", native_build / "core" / "python", "native_sha256"),
            ("_cherchi_core_boolean", native_build / "cherchi" / "python", "bridge_sha256"),
        )
        module_files = {}
        for module_name, directory, key in module_specs:
            matches = sorted(directory.glob(module_name + "*.so"))
            if len(matches) != 1 or sha(matches[0]) != pins[key]:
                raise RuntimeError("NATIVE_MODULE_PIN_MISMATCH:" + key)
            module_files[module_name] = {"path": str(matches[0]), "sha256": sha(matches[0])}
        arithmetic_dir = native_build / "cherchi" / "python"
        arithmetic_matches = sorted(arithmetic_dir.glob("_cherchi_rational_moments*.so"))
        if len(arithmetic_matches) != 1:
            raise RuntimeError("ONE_RATIONAL_ARITHMETIC_MODULE_REQUIRED")
        module_files["_cherchi_rational_moments"] = {
            "path": str(arithmetic_matches[0]), "sha256": sha(arithmetic_matches[0])}
        result["native_module_files"] = module_files

        sys.path[:0] = [
            str(w0_root / "python"), str(w0_root), str(p1),
            str(native_build / "core" / "python"),
            str(native_build / "cherchi" / "python"),
        ]
        os.environ["PYTHONNOUSERSITE"] = "1"
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        import p20_native_factory
        from research.NeuralMoments.contracts.full_partition_m6 import (
            audit_native_full_partition_once,
        )
        from research.NeuralMoments.contracts.native_teacher_replay import (
            canonical_mesh_rational_rows,
        )

        if not callable(canonical_mesh_rational_rows):
            raise RuntimeError("FIXED_W0_CANONICAL_RATIONAL_HELPER_MISSING")
        bundle = p20_native_factory.prepare_context()
        observed_pins = p20_native_factory.observed_pins(bundle)
        if observed_pins != pins:
            raise RuntimeError("FRESH_FACTORY_OBSERVED_PINS_MISMATCH")
        evaluator = bundle["evaluator"]
        result["stages"].append({
            "stage": "genuine_cherchi_factory",
            "status": "PASS",
            "fresh_factory_call_counts": dict(evaluator.call_counts),
        })
        if evaluator.call_counts != {
            "source": 0, "boolean": 0, "integration": 0, "derivative": 0,
        }:
            raise RuntimeError("FACTORY_MUST_BE_FRESH_AND_UNEVALUATED")

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
            result["status"] = "TEST_ONLY_NATIVE_AUDIT_RETURNED_NOT_FORMAL"
        except BaseException as error:
            result["status"] = "TEST_ONLY_FAILED"
            result["audit_error"] = type(error).__name__ + ": " + str(error)
            (out / "traceback.log").write_text(traceback.format_exc(), encoding="utf-8")
        result["native_audit_wall_seconds"] = time.monotonic() - audit_started
        result["native_call_counts_after_audit"] = dict(evaluator.call_counts)
        result["stages"].append({
            "stage": "unchanged_W0_native_M6_audit_function",
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
        result["cgroup_after"] = cgroup_snapshot()
        result["maxrss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["wall_seconds"] = time.monotonic() - started
        write_json(out / "P25_P22_RERUN_RESULT.json", result)
        print(json.dumps({
            "status": result["status"],
            "diagnostic_captured": result.get("diagnostic_captured", False),
            "native_audit_returned": result.get("native_audit_returned", False),
            "native_call_counts": result.get("native_call_counts_final"),
            "wall_seconds": result["wall_seconds"],
        }, ensure_ascii=False, sort_keys=True), flush=True)

    return 0 if result.get("diagnostic_captured") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
