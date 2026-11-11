#!/usr/bin/env python3
"""Execute the pinned historical builder with an explicit SYNTHETIC common shim.

This is a control-flow/cache experiment, NOT a Boolean geometry experiment.
No CGAL or Cherchi executable is invoked; no native solid or label is produced.
The historical script itself is unmodified. Fixture operands and source audit
are synthetic and must never enter a production evidence ledger.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import types
from unittest.mock import patch

SNAPSHOT_SHA = "f7cf4c2efbd32b9c19d33359471f0671aa2efae104d3aa912500157052f39980"
BUILDER_BLOB = "0c02cd8f4e7554ab6f3cbde497877253ce5bddec"
SOURCE_MANIFEST_SHA = "67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a"
FINAL_NAMES = ("fixed", "envelope", "design", "initial", "fixed-inside-envelope", "fixed-outside-envelope")


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha(path):
    return sha_bytes(Path(path).read_bytes())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")


def load_json(path):
    return json.loads(Path(path).read_text())


def packet(tag):
    return {"vertices": [["0", "0", "0"], ["1", "0", "0"],
                         ["0", "1", "0"], ["0", "0", "1"]],
            "faces": [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]],
            "SYNTHETIC_NOT_BOOLEAN_RESULT": tag}


def prepare_fixture(root, frozen_manifest):
    """Preserve recipe names/order, but NOT the real V7 coordinates/audit."""
    source = root / "source"; source.mkdir(parents=True)
    manifest = {"spec": {"schema": "noodles-paper-photo-hypothesis-v7", "model_unit_m": 1},
                "parts": {}, "construction": copy.deepcopy(frozen_manifest["construction"])}
    audit = {"full_source_parts_passed": True, "parts_completed": 94,
             "SYNTHETIC_FIXTURE_NOT_NATIVE_AUDIT": True, "results": []}
    for name in frozen_manifest["parts"]:
        obj = source / (name + "-model.obj")
        obj.write_text("# SYNTHETIC FIXTURE " + name + "\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
        manifest["parts"][name] = {"model_obj": obj.name, "sha256_model": sha(obj)}
        audit["results"].append({"part": obj.name, "sha256": sha(obj)})
    write_json(source / "manifest.json", manifest)
    write_json(root / "source-v7c-native-audit.json", audit)


def execute(builder, root, backend_identity="a" * 64):
    operations = []
    shim = types.ModuleType("common")

    class SyntheticBuilder:
        def __init__(self, executable, workdir, timeout):
            self.index = 0; self.exe_sha = backend_identity

        def boolean(self, left, right, operation):
            self.index += 1; operations.append(operation)
            expression = json.dumps([left, right, operation], sort_keys=True).encode()
            return packet(sha_bytes(expression))

    def obj_packet(path):
        return packet("fixture-input-bytes:" + sha(path))

    def no_geometry_export(path, value, scale, label):
        Path(path).write_text("# SYNTHETIC CONTROL-FLOW PROBE; NOT A GEOMETRY EXPORT\n")

    shim.ExactBuilder = SyntheticBuilder
    shim.obj_packet = obj_packet
    shim.packet_arrays = lambda value: (value["vertices"], value["faces"])
    shim.sha = sha; shim.write_json = write_json; shim.load_json = load_json
    shim.export_obj = no_geometry_export
    stdout = io.StringIO(); error = None
    argv = [str(builder), "--source", str(root / "source"), "--out", str(root / "out"),
            "--boolean", "SYNTHETIC_NOT_AN_EXECUTABLE"]
    with patch.dict(sys.modules, {"common": shim}), patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout):
        try:
            runpy.run_path(str(builder), run_name="__main__")
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)
    return {"script_completed": error is None, "error": error,
            "synthetic_boolean_calls": len(operations), "operation_counts": dict(Counter(operations)),
            "current_synthetic_backend_sha256": backend_identity,
            "stdout": "SYNTHETIC PROBE ONLY: historical print labels below do not describe native work.\n" + stdout.getvalue()}


def probe(snapshot_path):
    raw = Path(snapshot_path).read_bytes()
    if sha_bytes(raw) != SNAPSHOT_SHA:
        raise ValueError("FROZEN_SOURCE_SNAPSHOT_SHA_MISMATCH")
    snapshot = json.loads(raw)
    code = snapshot["source/build_exact_v7.py"].encode()
    blob = hashlib.sha1(b"blob " + str(len(code)).encode() + b"\0" + code).hexdigest()
    if blob != BUILDER_BLOB:
        raise ValueError("FROZEN_BUILD_SCRIPT_BLOB_MISMATCH")
    manifest_raw = snapshot["frozen-parts-v7c/manifest.json"].encode()
    if sha_bytes(manifest_raw) != SOURCE_MANIFEST_SHA:
        raise ValueError("FROZEN_MANIFEST_SHA_MISMATCH")
    manifest = json.loads(manifest_raw)
    cases = {}
    with tempfile.TemporaryDirectory(prefix="w2-synthetic-cache-probe-") as temp:
        base = Path(temp); script = base / "historical_build_exact_v7.py"; script.write_bytes(code)
        clean = base / "clean"; prepare_fixture(clean, manifest)
        cases["fresh"] = execute(script, clean)
        cases["unchanged_resume"] = execute(script, clean)

        def clone(name):
            dest = base / name; shutil.copytree(clean, dest); return dest

        altered = clone("altered-final")
        before = {}
        for name in FINAL_NAMES:
            path = altered / "out" / (name + "-rational.json")
            value = load_json(path); value["vertices"][0][0] = "999"
            value["SYNTHETIC_FOREIGN_CACHE_MARKER"] = name
            write_json(path, value); before[name] = sha(path)
        cases["altered_all_six_final_outputs"] = execute(script, altered)
        cases["altered_all_six_final_outputs"]["altered_bytes_reused_unchanged"] = all(
            sha(altered / "out" / (name + "-rational.json")) == before[name] for name in FINAL_NAMES)

        changed = clone("backend-change")
        cases["changed_current_backend"] = execute(script, changed, "b" * 64)

        changed = clone("receipt-backend-change")
        receipt = changed / "out/fixed-union-level00-pair000.json.receipt"
        value = load_json(receipt); value["backend_sha"] = "c" * 64; write_json(receipt, value)
        cases["changed_cached_receipt_backend"] = execute(script, changed)

        changed = clone("source-change")
        obj = changed / "source/hub-fixed-model.obj"
        obj.write_text(obj.read_text().replace("v 0 0 0", "v 2 0 0"))
        mf = load_json(changed / "source/manifest.json")
        mf["parts"]["hub-fixed"]["sha256_model"] = sha(obj)
        write_json(changed / "source/manifest.json", mf)
        au = load_json(changed / "source-v7c-native-audit.json")
        for row in au["results"]:
            if row["part"] == obj.name: row["sha256"] = sha(obj)
        write_json(changed / "source-v7c-native-audit.json", au)
        cases["changed_source_with_consistent_synthetic_manifest"] = execute(script, changed)

        rejected = clone("damaged-union")
        p = rejected / "out/fixed-union-level00-pair000.json"
        value = load_json(p); value["vertices"][0][0] = "321"; write_json(p, value)
        cases["negative_control_union_result_sha_mismatch"] = execute(script, rejected)

    if cases["fresh"]["synthetic_boolean_calls"] != 96 or not cases["fresh"]["script_completed"]:
        raise AssertionError("FRESH_CONTROL_FLOW_UNEXPECTED")
    for key in ("unchanged_resume", "altered_all_six_final_outputs", "changed_current_backend",
                "changed_cached_receipt_backend", "changed_source_with_consistent_synthetic_manifest"):
        if not cases[key]["script_completed"] or cases[key]["synthetic_boolean_calls"] != 0:
            raise AssertionError("EXPECTED_LEGACY_REUSE_NOT_REPRODUCED:" + key)
    if not cases["altered_all_six_final_outputs"]["altered_bytes_reused_unchanged"]:
        raise AssertionError("FOREIGN_FINAL_BYTES_NOT_REUSED")
    if cases["negative_control_union_result_sha_mismatch"]["script_completed"]:
        raise AssertionError("UNION_NEGATIVE_CONTROL_NOT_REJECTED")
    return {"schema": "W2_HISTORICAL_CACHE_CONTROL_FLOW_PROBE_V1",
            "status": "LEGACY_CACHE_GAPS_REPRODUCED_SYNTHETIC_ONLY",
            "snapshot_sha256": SNAPSHOT_SHA, "build_script_git_blob_sha1": blob,
            "build_script_sha256": sha_bytes(code), "frozen_manifest_sha256": SOURCE_MANIFEST_SHA,
            "original_script_modified": False, "fixtures": "94 SYNTHETIC INPUTS; common SHIM; NO NATIVE GEOMETRY",
            "external_readiness_gate_executed": False,
            "native_calls": 0, "historical_common_recovered": False, "J_D": None,
            "training_admitted": False, "training_samples": 0, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error("REFUSE_OVERWRITE")
    result = probe(args.snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False); stream.write("\n")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "native_calls": 0, "training_admitted": False}, sort_keys=True))


if __name__ == "__main__":
    main()
