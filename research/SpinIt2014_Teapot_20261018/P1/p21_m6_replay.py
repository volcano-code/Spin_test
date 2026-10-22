"""W4 P21: pre-register, execute and archive the unchanged P20 M6 launcher.

Registration reads bytes only. Execution retains the original physical/effective
20 GiB, zero-swap, single-job and 3600-second native limits. A caller must supply
the digest of a separately created pre-run lock; a self-created digest is byte
binding, never independent attestation or owner/teacher approval.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time


BASE = Path(__file__).resolve().parent
W4_BASELINE = "c85c7f3b8b985ad68e5db58975123654c57132dd"
W0_COMMIT = "51cbfd33d08063404d7e0c40e4256dd0e38efa1a"
P20_LAUNCHER_SHA256 = "3f2f9164f73754479bfe923ddb09e022b152985d8e7fc04cf41832ccf4a07e03"
P20_FACTORY_SHA256 = "34c401592747d6397e958eaff85fed90561d1adc3b06d2561eec2f54bbebd06f"
REQUEST_SHA256 = "74d9cfa64417dd2c82d196ab27094651976954742a4c692667a1b19b1032de62"
LOCK_SCHEMA = "W4_P21_M6_PRERUN_LOCK_V1"
BUNDLE_SCHEMA = "W4_P21_REPLAY_BUNDLE_V1"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SAFE_ENV = ("LD_LIBRARY_PATH", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
SCIENCE = {
    "W0_owner_adoption": False, "W0_physical_case_approved": False,
    "W2_teacher_training_allowed": False, "training_admissible": False,
    "smooth_neighborhood_certified": False, "newton_terminal_certified": False,
    "Faster_optimization_executed": False,
    "MuJoCo_optimized_before_after_executed": False,
    "physical_validation_passed": False,
}


class ReplayRunRejected(ValueError):
    pass


def need(test, reason):
    if not test:
        raise ReplayRunRejected(reason)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, "DUPLICATE_JSON_KEY:" + key)
            out[key] = value
        return out
    def nonfinite(value):
        raise ReplayRunRejected("NONFINITE_JSON:" + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def path(value):
    p = Path(os.path.abspath(os.fspath(value)))
    for part in (p, *p.parents):
        need(not part.is_symlink(), "SYMLINK_PATH_REJECTED:" + str(part))
    return p


def read_bytes(value):
    p = path(value)
    descriptor = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode), "REGULAR_FILE_REQUIRED:" + str(p))
        data = stream.read()
        after = os.fstat(stream.fileno())
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    need(not p.is_symlink() and identity(before) == identity(after) == identity(p.stat()),
         "FILE_CHANGED_DURING_READ:" + str(p))
    return data


def new_bytes(value, data):
    p = path(value)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def new_json(value, data):
    new_bytes(value, (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True,
                                 allow_nan=False) + "\n").encode("ascii"))


def load_p20():
    """Compile authenticated source bytes, never a timestamp-valid old .pyc."""
    source = BASE / "p20_m6_launch.py"
    data = read_bytes(source)
    need(sha(data) == P20_LAUNCHER_SHA256, "FROZEN_P20_LAUNCHER_CHANGED")
    name = "_w4_p21_frozen_p20_launch"
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(source))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(source)
    sys.modules[name] = module
    exec(compile(data, str(source), "exec"), module.__dict__)
    return module


def check_static_inputs():
    for filename, expected in (("p20_m6_launch.py", P20_LAUNCHER_SHA256),
                               ("p20_native_factory.py", P20_FACTORY_SHA256),
                               ("P20_native_request.json", REQUEST_SHA256)):
        need(sha(read_bytes(BASE / filename)) == expected, "FROZEN_INPUT_CHANGED:" + filename)
    for filename in ("p21_native_factory.py", "p21_same_call_capture.py", "p21_replay_verify.py"):
        read_bytes(BASE / filename)


def resource_report(launch):
    observed = launch.linux_resources()
    state = launch.resource_admission(observed)
    return {"schema": "W4_P21_ACTUAL_RESOURCE_PREFLIGHT_V1", "observed_utc": now(),
            "status": state, "resources": observed,
            "scope": "RESOURCE_OBSERVATION_ONLY; EXECUTION_FLAGS_DESCRIBE_THIS_PROBE",
            "formal_M6_executed": False, "factory_imported": False,
            "native_worker_started": False, "admission": dict(SCIENCE)}


def preflight(output):
    report = resource_report(load_p20())
    new_json(output, report)
    return (0 if report["status"] == "ADMITTED_RESOURCE_POLICY_ONLY" else 3), report


def _bind_binary_pins(snapshot, pins):
    files = [item for directory in snapshot["native_python_paths"]
             for item in directory["binary_files"]]
    for prefix, key in (("_make_it_stand.", "native_sha256"),
                        ("_cherchi_core_boolean.", "bridge_sha256")):
        hits = [item for item in files if Path(item["path"]).name.startswith(prefix)]
        need(len(hits) == 1 and hits[0]["sha256"] == pins[key],
             "ACTUAL_NATIVE_SEARCH_FILE_PIN_MISMATCH:" + key)
    arithmetic = [item for item in files if Path(item["path"]).name.startswith("_cherchi_rational_moments.")]
    need(len(arithmetic) == 1, "ONE_ACTUAL_RATIONAL_ARITHMETIC_MODULE_REQUIRED")
    adapter = snapshot["w0_source_files"]["python/make_it_stand/verification/cherchi_inprocess.py"]
    need(adapter["sha256"] == pins["adapter_sha256"], "PINNED_W0_ADAPTER_SHA_MISMATCH")


def register(*, w0_checkout, pins_file, python_paths, output):
    """Read-only preparation of a lock for already built, actually prepared inputs."""
    check_static_inputs()
    launch = load_p20()
    need(python_paths, "ACTUAL_NATIVE_PYTHON_DIRECTORIES_REQUIRED")
    pins_path = path(pins_file)
    pin_sha = sha(read_bytes(pins_path))
    pins, _ = launch.read_precommitted_pins(pins_path, pin_sha)
    factory = BASE / "p21_native_factory.py"
    factory_sha = sha(read_bytes(factory))
    snapshot = launch.snapshot_sources(w0_checkout, factory, factory_sha, pins_path, python_paths)
    _bind_binary_pins(snapshot, pins)
    observation = resource_report(launch)
    lock = {"schema": LOCK_SCHEMA, "created_utc": now(), "test_only": False,
            "source_w4_baseline_commit": W4_BASELINE, "w0_commit": W0_COMMIT,
            "paths": {"w0_checkout": str(path(w0_checkout)), "factory_file": str(factory),
                      "pins_file": str(pins_path), "launcher_file": str(BASE / "p20_m6_launch.py"),
                      "python_paths": [str(path(p)) for p in python_paths]},
            "pins": pins, "pins_sha256": pin_sha, "factory_sha256": factory_sha,
            "launcher_sha256": P20_LAUNCHER_SHA256, "request_sha256": REQUEST_SHA256,
            "source_snapshot": snapshot, "source_snapshot_sha256": launch._digest(snapshot),
            "resource_observation_at_registration": observation,
            "runtime_environment_allowlist": {key: os.environ.get(key) for key in SAFE_ENV},
            "python_executable": str(Path(sys.executable).resolve()),
            "python_version": sys.version,
            "registration_is_read_only": True, "factory_imported": False,
            "registration_is_independent_attestation": False,
            "registration_grants_scientific_admission": False,
            "admission": dict(SCIENCE)}
    new_json(output, lock)
    return lock


def read_lock(lock_path, expected_sha256):
    need(type(expected_sha256) is str and SHA256.fullmatch(expected_sha256), "EXTERNAL_LOCK_SHA256_REQUIRED")
    data = read_bytes(lock_path)
    need(sha(data) == expected_sha256, "PRERUN_LOCK_SHA256_MISMATCH")
    lock = strict_json(data)
    need(type(lock) is dict and lock.get("schema") == LOCK_SCHEMA, "PRERUN_LOCK_SCHEMA_MISMATCH")
    need(lock.get("test_only") is False, "TEST_ONLY_LOCK_FORBIDDEN")
    need(lock.get("source_w4_baseline_commit") == W4_BASELINE and lock.get("w0_commit") == W0_COMMIT,
         "FROZEN_SOURCE_COMMITS_MISMATCH")
    need(lock.get("registration_is_independent_attestation") is False and
         lock.get("registration_grants_scientific_admission") is False,
         "LOCK_CANNOT_GRANT_SCIENTIFIC_ADMISSION")
    need(lock.get("admission") == SCIENCE, "LOCK_ADMISSION_CHANGED")
    return lock, data


def _raw_resource_files(destination, label):
    for name, source in (("meminfo", "/proc/meminfo"), ("swaps", "/proc/swaps"),
                         ("cgroup", "/proc/self/cgroup"), ("mountinfo", "/proc/self/mountinfo")):
        new_bytes(destination / (label + "-" + name + ".txt"), Path(source).read_bytes())


def _copy_input(source, destination, expected=None):
    data = read_bytes(source)
    if expected is not None:
        need(sha(data) == expected, "ARCHIVED_INPUT_DIGEST_MISMATCH:" + str(source))
    new_bytes(destination, data)


def _write_bundle_manifest(destination, execution, formal_report, collection_errors=()):
    roles = {"formal-report.json": "formal_report", "inputs/pins.json": "pins",
             "capture/manifest.json": "capture_manifest", "capture/context.json": "capture_context",
             "capture/events.jsonl": "capture_events", "inputs/M.obj": "material_M",
             "inputs/F.obj": "material_F", "inputs/D.obj": "material_D",
             "inputs/P20_native_request.json": "request", "formal.stdout.log": "formal_stdout",
             "formal.stderr.log": "formal_stderr", "prerun-lock.json": "prerun_lock",
             "formal-report.json.worker.stdout.log": "worker_stdout",
             "formal-report.json.worker.stderr.log": "worker_stderr"}
    files = []
    for p in sorted(destination.rglob("*")):
        need(not p.is_symlink(), "SYMLINK_IN_BUNDLE")
        if p.is_dir():
            continue
        relative = p.relative_to(destination).as_posix()
        need(relative != "manifest.json", "BUNDLE_MANIFEST_ALREADY_EXISTS")
        data = read_bytes(p)
        files.append({"path": relative, "sha256": sha(data), "bytes": len(data),
                      "role": roles.get(relative, "capture_artifact" if relative.startswith("capture/") else "execution_evidence")})
    executed = formal_report.get("native_audit_invoked") if type(formal_report) is dict else None
    need(executed is None or type(executed) is bool, "INVALID_FORMAL_EXECUTION_STATE")
    manifest = {"schema": BUNDLE_SCHEMA, "created_utc": now(), "test_only": False,
                "source_w4_baseline_commit": W4_BASELINE, "w0_commit": W0_COMMIT,
                "formal_exit_code": execution.get("returncode"), "formal_executed": executed,
                "collection_errors": list(collection_errors),
                "collection_completed": not collection_errors,
                "prerun_lock_sha256": execution["prerun_lock_sha256"], "files": files,
                "admission": dict(SCIENCE), "native_execution_independently_proved": False,
                "scope": "SAME_EXECUTION_ARCHIVE; OFFLINE_ARITHMETIC_REPLAY_NOT_EXTERNAL_NATIVE_ATTESTATION"}
    new_json(destination / "manifest.json", manifest)
    return manifest


def execute(*, lock_path, expected_lock_sha256, output_directory):
    """Run the original launcher as a subprocess, retain all actual failure data."""
    check_static_inputs()
    launch = load_p20()
    lock, lock_data = read_lock(lock_path, expected_lock_sha256)
    locations = lock["paths"]
    need(path(locations["factory_file"]) == BASE / "p21_native_factory.py", "P21_FACTORY_LOCATION_MISMATCH")
    need(path(locations["launcher_file"]) == BASE / "p20_m6_launch.py", "P20_LAUNCHER_LOCATION_MISMATCH")
    need(sha(read_bytes(locations["factory_file"])) == lock["factory_sha256"], "P21_FACTORY_CHANGED_AFTER_LOCK")
    need(sha(read_bytes(locations["pins_file"])) == lock["pins_sha256"], "PINS_CHANGED_AFTER_LOCK")
    need(str(Path(sys.executable).resolve()) == lock["python_executable"] and sys.version == lock["python_version"],
         "PYTHON_RUNTIME_CHANGED_AFTER_LOCK")
    need({key: os.environ.get(key) for key in SAFE_ENV} == lock["runtime_environment_allowlist"],
         "RUNTIME_LIBRARY_OR_THREAD_ENVIRONMENT_CHANGED_AFTER_LOCK")
    before = resource_report(launch)
    # Byte verification performs no native work. Always bind it to the prior
    # lock: resources may change between this observation and P20's own guard.
    snapshot = launch.snapshot_sources(locations["w0_checkout"], locations["factory_file"],
        lock["factory_sha256"], locations["pins_file"], locations["python_paths"])
    need(snapshot == lock["source_snapshot"] and launch._digest(snapshot) == lock["source_snapshot_sha256"],
         "INPUTS_CHANGED_AFTER_PRERUN_REGISTRATION")
    _bind_binary_pins(snapshot, lock["pins"])
    destination = path(output_directory)
    destination.mkdir(parents=True, exist_ok=False)
    new_bytes(destination / "prerun-lock.json", lock_data)
    new_json(destination / "resource-before.json", before)
    _raw_resource_files(destination, "before")
    config = strict_json(read_bytes(BASE / "P20_native_request.json"))
    _copy_input(BASE / "P20_native_request.json", destination / "inputs/P20_native_request.json", REQUEST_SHA256)
    _copy_input(locations["pins_file"], destination / "inputs/pins.json", lock["pins_sha256"])
    for name in ("M", "F", "D"):
        row = config["material_inputs"][name]
        _copy_input(BASE / row["path"], destination / ("inputs/" + name + ".obj"), row["sha256"])
    command = [sys.executable, "-B", str(BASE / "p20_m6_launch.py"),
               "--w0-checkout", locations["w0_checkout"],
               "--factory-file", locations["factory_file"], "--factory-function", "prepare_one",
               "--pins", locations["pins_file"], "--external-pins-sha256", lock["pins_sha256"],
               "--external-factory-sha256", lock["factory_sha256"],
               "--output", str(destination / "formal-report.json")]
    for directory in locations["python_paths"]:
        command.extend(("--python-path", directory))
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["W4_P21_CAPTURE_DIRECTORY"] = str(destination / "capture")
    started = time.monotonic()
    execution = {"schema": "W4_P21_REAL_LAUNCHER_EXECUTION_V1", "started_utc": now(),
                 "command": command, "returncode": None, "completed": False,
                 "prerun_lock_sha256": expected_lock_sha256,
                 "runtime_environment_allowlist": lock["runtime_environment_allowlist"],
                 "timeout_owner": "FROZEN_P20_PARENT_AND_WORKER_3600_SECONDS",
                 "admission": dict(SCIENCE)}
    new_json(destination / "execution-start.json", execution)
    try:
        with (destination / "formal.stdout.log").open("xb") as stdout, (destination / "formal.stderr.log").open("xb") as stderr:
            process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     env=environment, cwd=str(BASE), check=False)
        execution.update(returncode=process.returncode, completed=True)
    except (OSError, subprocess.SubprocessError) as error:
        execution["error"] = f"{type(error).__name__}: {error}"
    execution.update(finished_utc=now(), wall_seconds=time.monotonic()-started)
    new_json(destination / "execution.json", execution)
    collection_errors = []
    try:
        after = resource_report(launch)
        new_json(destination / "resource-after.json", after)
    except (OSError, ValueError, KeyError, TypeError) as error:
        collection_errors.append("POSTRUN_RESOURCE_OBSERVATION_FAILED:" + f"{type(error).__name__}: {error}")
    try:
        _raw_resource_files(destination, "after")
    except (OSError, ValueError) as error:
        collection_errors.append("POSTRUN_RAW_RESOURCE_CAPTURE_FAILED:" + f"{type(error).__name__}: {error}")
    formal_path = destination / "formal-report.json"
    formal_report = None
    try:
        if formal_path.is_file():
            formal_report = strict_json(read_bytes(formal_path))
            need(type(formal_report) is dict, "FORMAL_REPORT_OBJECT_REQUIRED")
    except (OSError, ValueError, TypeError) as error:
        formal_report = None
        collection_errors.append("FORMAL_REPORT_PARSE_FAILED:" + f"{type(error).__name__}: {error}")
    new_json(destination / "collection.json", {"schema": "W4_P21_COLLECTION_V1",
        "completed": not collection_errors, "errors": collection_errors, "admission": dict(SCIENCE)})
    manifest = _write_bundle_manifest(destination, execution, formal_report, collection_errors)
    report = {"schema": "W4_P21_EXECUTION_COLLECTION_RESULT_V1", "bundle": str(destination),
              "manifest_sha256": sha(read_bytes(destination / "manifest.json")),
              "formal_exit_code": execution["returncode"], "formal_executed": manifest["formal_executed"],
              "formal_status": formal_report.get("status") if type(formal_report) is dict else "NO_FORMAL_REPORT",
              "collection_errors": collection_errors,
              "admission": dict(SCIENCE)}
    code = execution["returncode"] if type(execution["returncode"]) is int and 0 <= execution["returncode"] <= 125 else 4
    if collection_errors:
        code = 4
    return code, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight", help="Read actual Linux resources; no native imports or builds")
    p.add_argument("--output", required=True)
    p = sub.add_parser("register", help="Freeze existing actual build/pins/input identities without evaluating")
    p.add_argument("--w0-checkout", required=True)
    p.add_argument("--pins", required=True)
    p.add_argument("--python-path", action="append", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("execute", help="Call frozen P20 launcher using a separately registered lock digest")
    p.add_argument("--lock", required=True)
    p.add_argument("--lock-sha256", required=True)
    p.add_argument("--output-directory", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            code, report = preflight(args.output)
        elif args.command == "register":
            register(w0_checkout=args.w0_checkout, pins_file=args.pins,
                     python_paths=args.python_path, output=args.output)
            code, report = 0, {"status": "PRERUN_BYTE_LOCK_CREATED_NO_NATIVE_EXECUTION",
                               "lock": str(path(args.output)), "lock_sha256": sha(read_bytes(args.output)),
                               "scientific_admission": False}
        else:
            code, report = execute(lock_path=args.lock, expected_lock_sha256=args.lock_sha256,
                                   output_directory=args.output_directory)
    except (ReplayRunRejected, ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "FAILED_CLOSED", "reason": f"{type(error).__name__}: {error}",
                          "admission": SCIENCE}, sort_keys=True), file=sys.stderr)
        return 4
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
