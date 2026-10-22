"""W4 P20 launcher for the unchanged, pinned W0 public M6 audit.

This module performs no native work at import time.  Its runtime envelope is
distinct from the W0 COMPLETE material evidence nested inside it.  A complete
M6 geometry result never grants W0 owner/physical, derivative, Newton, or
training admission.  A fresh trusted factory must return (evaluator, problem,
native_c); the unchanged W0 audit enforces their genuine native types.

The two external SHA arguments are supplied by an independent pre-run lock.
Checking them establishes byte binding, not cryptographic runtime attestation
or independent proof of when the reviewer registered the lock.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid


W0_COMMIT = "51cbfd33d08063404d7e0c40e4256dd0e38efa1a"
W0_BASELINE = "0bcc187b3005478baa586a6d6f450e73811ca342"
SCHEMA = "W4_P20_M6_RUNTIME_V1"
WORKER_SCHEMA = "W4_P20_M6_WORKER_V1"
M6_SCHEMA = "W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1"
RESULT_PREFIX = "W4_P20_M6_RESULT_JSON:"
MINIMUM_BYTES = 20 * 1024**3
CHILD_MAXIMUM_ADDRESS_BYTES = 24 * 1024**3
MAX_RUNTIME_SECONDS = 3600
LOCK_PATH = Path("/tmp/spin_test_w0_m5_cherchi_job.lock")
PIN_KEYS = frozenset({"native_sha256", "bridge_sha256", "adapter_sha256",
                      "c_sha256", "problem_input_digest", "context_sha256"})
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_SUFFIXES = frozenset({".py", ".pyi", ".cpp", ".cc", ".c", ".h",
                              ".hpp", ".hxx", ".cmake", ".inl", ".ipp"})
# These are independently read Git blobs at W0_COMMIT, not local calculated
# values promoted into expected identities.  All other W0 tracked source files
# are also byte-verified against the actual immutable commit tree below.
CRITICAL_BLOBS = {
    "research/NeuralMoments/contracts/full_partition_m6.py": "a226f61c19a465bd3421ea1ec7e56ce7f381b633",
    "research/NeuralMoments/contracts/native_teacher_replay.py": "ff53709e38bdba360ad2c7aba499a675ee83dd93",
    "research/NeuralMoments/contracts/native_m5_bridge.py": "247c728d3442048a64c2e9c68655cc740365fd88",
    "research/NeuralMoments/contracts/cross_oracle_gate.py": "bcd546f462c793eb8c531885ee9e416eaec9c25a",
    "research/NeuralMoments/contracts/w2_reference_snapshot.py": "d734398292e1fdaf839db3413c537de2474df3e1",
    "python/make_it_stand/verification/cherchi_inprocess.py": "f9fa539f699df8baf8b8d30729048269a26ecb3c",
    "python/make_it_stand/verification/spin_problem.py": "1d5ab0dc0ea3e07bea68874244e727dcd35c26a8",
    "python/make_it_stand/verification/spin_common.py": "56c908c138c24fd5b90444bfc508904dead71c61",
    "python/make_it_stand/verification/faster_material.py": "a3c56a395e98e5c19d5924d1568b4e800e94b4d9",
    "python/make_it_stand/spin.py": "1adaacbb89e45bf9a546594cfa684da7ae0f1cf2",
    "bindings/pybind_module.cpp": "cbb08610947880b8a3d1a06fd52343d784c8ff8d",
}
FALSE_ADMISSION_FLAGS = {
    "W0_owner_adoption": False, "W0_physical_case_approved": False,
    "W2_teacher_training_allowed": False, "training_admissible": False,
    "smooth_neighborhood_certified": False, "newton_terminal_certified": False,
}


class LaunchRejected(ValueError):
    """A required precondition or immutable runtime binding failed."""


def _need(condition, reason):
    if not condition:
        raise LaunchRejected(reason)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("ascii")).hexdigest()


def _json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            _need(key not in out, "DUPLICATE_JSON_KEY:" + key)
            out[key] = value
        return out
    def nonfinite(value):
        raise LaunchRejected("NONFINITE_JSON:" + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)


def _sha(value, label):
    _need(type(value) is str and SHA256.fullmatch(value), "INVALID_SHA256:" + label)
    return value


def _path(value):
    """Check the lexical path before resolving, so a symlink is never hidden."""
    p = Path(os.path.abspath(os.fspath(value)))
    for part in (p, *p.parents):
        _need(not part.is_symlink(), "SYMLINK_SOURCE_OR_OUTPUT_PATH:" + str(part))
    return p


def _stat_identity(s):
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode]


def _read_file(path, *, maximum=None):
    p = _path(path)
    descriptor = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        _need(stat.S_ISREG(before.st_mode), "ORDINARY_FILE_REQUIRED:" + str(p))
        _need(maximum is None or before.st_size <= maximum, "INPUT_TOO_LARGE:" + str(p))
        data = stream.read()
        after = os.fstat(stream.fileno())
    _need(_stat_identity(before) == _stat_identity(after) == _stat_identity(p.stat()),
          "FILE_CHANGED_DURING_READ:" + str(p))
    return data, {"path": str(p), "sha256": hashlib.sha256(data).hexdigest(),
                  "bytes": len(data), "stat_identity": _stat_identity(after)}


def read_precommitted_pins(path, expected_sha256):
    """Read the external six-pin lock. Never synthesize any missing identity."""
    _sha(expected_sha256, "external_pins_sha256")
    data, record = _read_file(path, maximum=65536)
    _need(record["sha256"] == expected_sha256, "EXTERNAL_PINS_SHA256_MISMATCH")
    pins = _json(data)
    _need(type(pins) is dict and set(pins) == PIN_KEYS, "EXACT_PRECOMMITTED_SIX_PIN_SET_REQUIRED")
    for key, value in pins.items():
        _sha(value, key)
    return pins, record


def _mount_unescape(value):
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), value)


def _cgroup_memory_limits():
    """Read every visible ancestor limit; unknown cgroup layout fails closed."""
    groups = Path("/proc/self/cgroup").read_text(encoding="ascii").splitlines()
    mounts = Path("/proc/self/mountinfo").read_text(encoding="ascii").splitlines()
    choices = []
    for line in groups:
        hierarchy, controllers, member = line.split(":", 2)
        version = 2 if hierarchy == "0" and not controllers else 1
        if version == 1 and "memory" not in controllers.split(","):
            continue
        for mount in mounts:
            left, right = mount.split(" - ", 1)
            fields, extra = left.split(), right.split()
            if extra[0] != ("cgroup2" if version == 2 else "cgroup"):
                continue
            if version == 1 and "memory" not in extra[-1].split(","):
                continue
            mount_root = _mount_unescape(fields[3])
            mount_point = Path(_mount_unescape(fields[4]))
            if mount_root == "/":
                relative = member.lstrip("/")
            elif member == mount_root:
                relative = ""
            elif member.startswith(mount_root.rstrip("/") + "/"):
                relative = member[len(mount_root):].lstrip("/")
            else:
                continue
            current = mount_point / relative
            _need(".." not in current.parts, "INVALID_CGROUP_MEMBERSHIP_PATH")
            choices.append((version, mount_point, current))
    _need(choices, "CGROUP_MEMORY_HIERARCHY_UNAVAILABLE")
    records, seen = [], set()
    for version, mount_point, current in choices:
        while True:
            limit = current / ("memory.max" if version == 2 else "memory.limit_in_bytes")
            if str(limit) not in seen and limit.is_file():
                text = limit.read_text(encoding="ascii").strip()
                _need(text == "max" or text.isdecimal(), "INVALID_CGROUP_MEMORY_LIMIT")
                value = None if text == "max" else int(text)
                if version == 1 and value is not None and value >= 2**60:
                    value = None
                _need(value is None or value > 0, "INVALID_CGROUP_MEMORY_LIMIT")
                record = {"version": version, "path": str(limit), "raw": text,
                          "limit_bytes": value}
                swap = current / ("memory.swap.max" if version == 2 else "memory.memsw.limit_in_bytes")
                if swap.is_file():
                    record["swap_limit_raw"] = swap.read_text(encoding="ascii").strip()
                records.append(record)
                seen.add(str(limit))
            if current == mount_point:
                break
            _need(mount_point in current.parents, "CGROUP_PATH_OUTSIDE_MOUNT")
            current = current.parent
    _need(records, "CGROUP_MEMORY_LIMIT_UNAVAILABLE")
    return records


def linux_resources():
    values = {}
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[1].isdecimal() and fields[2] == "kB":
            values[fields[0].rstrip(":")] = int(fields[1])
    _need("MemTotal" in values and "SwapTotal" in values, "HOST_RESOURCE_INFORMATION_UNAVAILABLE")
    physical = values["MemTotal"] * 1024
    limits = _cgroup_memory_limits()
    finite = [r["limit_bytes"] for r in limits if r["limit_bytes"] is not None]
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    address_limits = [x for x in (soft, hard) if x != resource.RLIM_INFINITY]
    effective = min([physical, *finite, *address_limits])
    return {"physical_memory_bytes": physical, "physical_memory_gib": physical / 1024**3,
            "swap_kib": values["SwapTotal"], "cgroup_memory_limits": limits,
            "cgroup_effective_memory_bytes": min(finite) if finite else None,
            "process_address_space_soft_bytes": None if soft == resource.RLIM_INFINITY else soft,
            "process_address_space_hard_bytes": None if hard == resource.RLIM_INFINITY else hard,
            "effective_memory_bytes": effective, "effective_memory_gib": effective / 1024**3,
            "minimum_required_bytes": MINIMUM_BYTES,
            "child_address_space_limit_bytes": min(effective, CHILD_MAXIMUM_ADDRESS_BYTES)}


def resource_admission(resources):
    for key in ("physical_memory_bytes", "effective_memory_bytes", "swap_kib"):
        _need(type(resources.get(key)) is int and resources[key] >= 0, "INVALID_RESOURCE_OBSERVATION:" + key)
    _need(type(resources.get("cgroup_memory_limits")) is list and resources["cgroup_memory_limits"],
          "CGROUP_MEMORY_LIMIT_UNAVAILABLE")
    if resources["physical_memory_bytes"] < MINIMUM_BYTES:
        return "BLOCKED_INSUFFICIENT_PHYSICAL_RAM"
    if resources["effective_memory_bytes"] < MINIMUM_BYTES:
        return "BLOCKED_INSUFFICIENT_EFFECTIVE_MEMORY"
    if resources["swap_kib"] != 0:
        return "BLOCKED_NONZERO_SWAP"
    return "ADMITTED_RESOURCE_POLICY_ONLY"


def _git(checkout, *arguments):
    result = subprocess.run(["git", "-C", str(checkout), *arguments],
                            capture_output=True, timeout=120, check=False)
    _need(result.returncode == 0, "W0_GIT_IDENTITY_UNAVAILABLE:" + " ".join(arguments))
    return result.stdout


def _is_source(path):
    p = Path(path)
    return p.suffix in SOURCE_SUFFIXES or p.name == "CMakeLists.txt"


def snapshot_sources(w0_checkout, factory_file, expected_factory_sha256, pins_file, python_paths=()):
    """Freeze all tracked W0 code, factory peers/config, pins, native search dirs.

    Immutable Git object blobs provide the expected source bytes.  Generated
    native binaries have independent external pins and are checked again from
    the actual loaded modules.  Build-to-binary attestation remains separate.
    """
    root, factory = _path(w0_checkout), _path(factory_file)
    _need(root.is_dir(), "W0_CHECKOUT_MISSING")
    _need(Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel")).strip()).resolve() == root,
          "W0_CHECKOUT_ROOT_REQUIRED")
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    _need(head == W0_COMMIT, "W0_HEAD_MISMATCH")
    entries = _git(root, "ls-tree", "-r", "-z", "--full-tree", "HEAD").split(b"\0")
    records, tree_paths = {}, set()
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, blob = metadata.decode("ascii").split()
        relative = os.fsdecode(raw_path)
        if kind != "blob" or not _is_source(relative):
            continue
        _need(mode in ("100644", "100755"), "NONREGULAR_W0_SOURCE:" + relative)
        data, record = _read_file(root / relative)
        calculated = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        _need(calculated == blob, "W0_SOURCE_BLOB_MISMATCH:" + relative)
        record.update(git_blob=blob, git_mode=mode)
        records[relative] = record
        tree_paths.add(relative)
    for path, blob in CRITICAL_BLOBS.items():
        _need(path in records and records[path]["git_blob"] == blob, "W0_CRITICAL_SOURCE_PIN_MISMATCH:" + path)
    # Reject Python source overlays, including ignored files, in importable W0
    # package trees.  Such a file cannot be authenticated by the pinned tree.
    possible = list(root.glob("*.py"))
    for directory in (root / "python", root / "research/NeuralMoments/contracts"):
        if directory.is_dir():
            possible.extend(directory.rglob("*.py"))
    for p in possible:
        _need(p.relative_to(root).as_posix() in tree_paths, "UNTRACKED_W0_PYTHON_SOURCE:" + str(p))
    _sha(expected_factory_sha256, "external_factory_sha256")
    _, factory_record = _read_file(factory)
    _need(factory.suffix == ".py" and factory_record["sha256"] == expected_factory_sha256,
          "EXTERNAL_FACTORY_SHA256_MISMATCH")
    peers = {}
    for p in sorted(factory.parent.glob("*.py")):
        peers[p.name] = _read_file(p)[1]
    config = factory.parent / "P20_native_request.json"
    registered_inputs = {}
    if config.exists():
        config_bytes, peers[config.name] = _read_file(config)
        registered = _json(config_bytes)
        if type(registered) is dict and registered.get("schema") == "W4_P20_TEAPOT_NATIVE_REQUEST_V1":
            references = {"manifest": registered["manifest"], "canonical_report": registered["canonical_report"],
                          **registered["material_inputs"]}
            for label, reference in references.items():
                relative = Path(reference["path"])
                _need(not relative.is_absolute() and ".." not in relative.parts, "REGISTERED_INPUT_PATH_ESCAPE")
                _sha(reference["sha256"], "registered_input_" + label)
                record = _read_file(factory.parent / relative)[1]
                _need(record["sha256"] == reference["sha256"], "REGISTERED_FACTORY_INPUT_SHA_MISMATCH:" + label)
                registered_inputs[label] = record
    paths = []
    for value in python_paths:
        directory = _path(value)
        _need(directory.is_dir(), "NATIVE_PYTHON_PATH_MISSING")
        _need(not list(directory.glob("*.py")) and not list(directory.glob("*.pyc")),
              "NATIVE_SEARCH_DIRECTORY_CONTAINS_PYTHON_SOURCE")
        binaries = [_read_file(p)[1] for p in sorted(directory.iterdir())
                    if p.is_file() and (".so" in p.name or p.suffix in (".dll", ".dylib", ".pyd"))]
        paths.append({"path": str(directory), "binary_files": binaries})
    observation = {"w0_commit": head, "w0_root": str(root),
                   "w0_tree": _git(root, "rev-parse", "HEAD^{tree}").decode("ascii").strip(),
                   "w0_source_files": records, "factory_file": factory_record,
                   "factory_peer_sources_and_config": peers,
                   "factory_registered_input_files": registered_inputs,
                   "pins_file": _read_file(pins_file, maximum=65536)[1],
                   "native_python_paths": paths, "launcher_file": _read_file(__file__)[1],
                   "scope": "ALL_TRACKED_W0_SOURCE_BYTES_AND_FACTORY_PEERS_CONFIG_PINS_NATIVE_SEARCH_FILES",
                   "source_to_binary_build_attestation": False}
    return observation


def _loaded_w0_sources(snapshot):
    root = Path(snapshot["w0_root"])
    records, loaded = snapshot["w0_source_files"], {}
    for name, module in tuple(sys.modules.items()):
        if not (name == "make_it_stand" or name.startswith("make_it_stand.") or
                name.startswith("research.NeuralMoments.contracts")):
            continue
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        p = _path(filename)
        _need(root in p.parents, "LOADED_W0_MODULE_OUTSIDE_PINNED_CHECKOUT:" + name)
        relative = p.relative_to(root).as_posix()
        _need(relative in records, "LOADED_W0_SOURCE_NOT_FROZEN:" + name)
        record = _read_file(p)[1]
        _need(record == {k: v for k, v in records[relative].items() if k not in ("git_blob", "git_mode")},
              "LOADED_W0_SOURCE_CHANGED:" + name)
        loaded[name] = record
    return loaded


def _native_files(evaluator, pins):
    adapter = sys.modules.get(type(evaluator).__module__)
    sources = {"native_sha256": getattr(evaluator.native, "__file__", None),
               "bridge_sha256": getattr(evaluator.bridge, "__file__", None),
               "adapter_sha256": getattr(adapter, "__file__", None)}
    records = {}
    for key, filename in sources.items():
        _need(filename is not None, "ACTUAL_NATIVE_MODULE_PATH_MISSING:" + key)
        record = _read_file(filename)[1]
        _need(record["sha256"] == pins[key], "ACTUAL_NATIVE_MODULE_PIN_MISMATCH:" + key)
        records[key] = record
    arithmetic = getattr(evaluator, "arithmetic", None)
    if arithmetic is not None:
        records["optional_arithmetic_module"] = _read_file(arithmetic.__file__)[1]
    return records


def validate_m6_evidence(evidence, pins):
    """Structural defense after the real public audit, never an origin proof."""
    _need(type(evidence) is dict and evidence.get("schema") == M6_SCHEMA, "M6_COMPLETE_SCHEMA_REQUIRED")
    forbidden = set(FALSE_ADMISSION_FLAGS) | {"training_admitted", "newton_admitted", "newton_converged",
        "smooth_derivative_proved", "certified_smooth_neighborhood", "smooth_neighborhood_proven"}
    def check_nonrelease(value):
        if type(value) is dict:
            for key, item in value.items():
                if key in forbidden:
                    _need(item is False, "FORBIDDEN_NESTED_ADMISSION:" + key)
                check_nonrelease(item)
        elif type(value) in (list, tuple):
            for item in value:
                check_nonrelease(item)
    check_nonrelease(evidence)
    for key in ("native_full_partition_certified", "retained_plus_cavity_equals_design_r10_exact",
                "fixed_plus_retained_density_weighted_moments_verified"):
        _need(evidence.get(key) is True, "M6_REQUIRED_FACT_MISSING:" + key)
    for key in ("training_admissible", "smooth_derivative_certified", "newton_terminal_certified"):
        _need(evidence.get(key) is False, "M6_FORBIDDEN_OR_AMBIGUOUS_ADMISSION:" + key)
    _need(evidence.get("scope") == "EXACT_REPRESENTED_POLYHEDRAL_SETS_AND_R10_ONLY", "M6_SCOPE_CHANGED")
    for key, expected in (("observed_native_source_calls", 1), ("observed_native_boolean_calls", 2),
                          ("complement_additional_source_calls", 0), ("complement_additional_boolean_calls", 1)):
        _need(type(evidence.get(key)) is int and evidence[key] == expected, "M6_SAME_SOURCE_CALL_COUNT_MISMATCH:" + key)
    partitions = evidence.get("exact_partition_predicates")
    _need(type(partitions) is list and [p.get("label") for p in partitions] ==
          ["fixed_plus_design", "design_cut", "full_outer"], "THREE_ORDERED_NATIVE_PARTITIONS_REQUIRED")
    for row in partitions:
        facts = row.get("native_predicate_facts")
        _need(type(facts) is dict, "COMPLETE_NATIVE_PARTITION_FACTS_REQUIRED")
        for key in ("completed", "complete_partition", "union_equals_whole", "no_positive_volume_overlap"):
            _need(facts.get(key) is True, "NATIVE_PARTITION_FAILED:" + key)
        for key in ("missing_whole_content", "excess_union_content"):
            _need(facts.get(key) is False, "NATIVE_PARTITION_CONTENT_MISMATCH:" + key)
        count, subsets = row.get("part_count"), facts.get("part_subset_whole")
        _need(type(count) is int and count > 0 and type(subsets) in (list, tuple) and
              len(subsets) == count and all(x is True for x in subsets), "NATIVE_PART_SUBSET_FAILED")
        _need(facts.get("positive_volume_overlap_pairs") == [], "NATIVE_POSITIVE_OVERLAP")
        _sha(facts.get("partition_digest"), "native_partition_digest")
        _need(row.get("partition_digest") == facts["partition_digest"], "PARTITION_DIGEST_MISMATCH")
    m5 = evidence.get("M5_evidence")
    _need(type(m5) is dict and m5.get("schema") == "W0_M5_LIVE_W0_W2_PARITY_V1" and
          m5.get("training_admissible") is False, "REAL_M5_PARITY_EVIDENCE_REQUIRED")
    m4 = m5.get("m4_native_evidence")
    _need(type(m4) is dict and m4.get("native_execution_observed") is True and
          m4.get("native_region_proved") is True and m4.get("mathematical_replay_passed") is True and
          m4.get("training_admissible") is False, "REAL_M4_SAME_CALL_EVIDENCE_REQUIRED")
    mapping = {"native_source_sha256": "native_sha256", "native_bridge_sha256": "bridge_sha256",
               "native_adapter_sha256": "adapter_sha256", "frozen_native_c_sha256": "c_sha256",
               "frozen_problem_digest": "problem_input_digest", "frozen_context_sha256": "context_sha256"}
    for observed, pin in mapping.items():
        _need(m4.get(observed) == pins[pin], "M4_RECEIPT_PIN_MISMATCH:" + pin)
    for key in ("source_geometry_sha256", "source_quadric_sha256"):
        _sha(m4.get(key), key)
    return evidence


def _base_report(schema=SCHEMA):
    return {"schema": schema, "w0_commit": W0_COMMIT, "w0_production_baseline": W0_BASELINE,
            **FALSE_ADMISSION_FLAGS, "native_full_partition_certified": False,
            "native_audit_invoked": False, "factory_imported": False, "worker_started": False,
            "native_call_counts_observed": {"source": 0, "boolean": 0}, "m6_evidence": None,
            "byte_binding_is_independent_runtime_attestation": False}


def _apply_worker_limits(resources):
    limit = resources["child_address_space_limit_bytes"]
    _need(type(limit) is int and MINIMUM_BYTES <= limit <= CHILD_MAXIMUM_ADDRESS_BYTES,
          "INVALID_CHILD_ADDRESS_SPACE_LIMIT")
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    signal.alarm(MAX_RUNTIME_SECONDS)
    return {"RLIMIT_AS_soft_bytes": limit, "RLIMIT_AS_hard_bytes": limit,
            "wall_alarm_seconds": MAX_RUNTIME_SECONDS}


@contextmanager
def _frozen_import_environment(root, factory, python_paths):
    """Read checked source instead of a pre-existing timestamp-valid .pyc."""
    old_path, old_prefix, old_write = list(sys.path), sys.pycache_prefix, sys.dont_write_bytecode
    with tempfile.TemporaryDirectory(prefix="w4-p20-frozen-source-import-") as cache:
        sys.pycache_prefix = cache
        sys.dont_write_bytecode = True
        sys.path[:0] = [str(Path(root) / "python"), str(root), str(Path(factory).parent), *python_paths]
        try:
            yield
        finally:
            sys.path[:] = old_path
            sys.pycache_prefix, sys.dont_write_bytecode = old_prefix, old_write


def _worker(request):
    report = _base_report(WORKER_SCHEMA)
    report.update(run_nonce=request["run_nonce"], worker_started=True,
                  native_call_counts_observed=None)
    resources = linux_resources()
    report["resources"] = resources
    state = resource_admission(resources)
    if state != "ADMITTED_RESOURCE_POLICY_ONLY":
        report.update(status=state, native_call_counts_observed={"source": 0, "boolean": 0})
        return report
    report["child_limits"] = _apply_worker_limits(resources)
    pins, pin_record = read_precommitted_pins(request["pins"], request["external_pins_sha256"])
    before = snapshot_sources(request["w0_checkout"], request["factory_file"],
                              request["external_factory_sha256"], request["pins"], request["python_paths"])
    _need(_digest(before) == request["source_snapshot_sha256"], "PARENT_WORKER_SOURCE_SNAPSHOT_MISMATCH")
    _need(pin_record == before["pins_file"], "PINS_CHANGED_BETWEEN_PREFLIGHTS")
    root, factory = Path(before["w0_root"]), Path(request["factory_file"])
    with _frozen_import_environment(root, factory, request["python_paths"]):
        return _audit_in_worker(request, report, pins, pin_record, before)


def _audit_in_worker(request, report, pins, pin_record, before):
    factory = Path(request["factory_file"])
    audit_module = importlib.import_module("research.NeuralMoments.contracts.full_partition_m6")
    _loaded_w0_sources(before)
    spec = importlib.util.spec_from_file_location("_w4_p20_frozen_factory_" + request["external_factory_sha256"], factory)
    _need(spec is not None and spec.loader is not None, "FACTORY_SPEC_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    report["factory_imported"] = True
    prepare = getattr(module, request["factory_function"], None)
    _need(callable(prepare), "TRUSTED_FACTORY_FUNCTION_MISSING")
    prepared = prepare()
    _need(type(prepared) is tuple and len(prepared) == 3, "FACTORY_MUST_RETURN_EVALUATOR_PROBLEM_C")
    evaluator, problem, coefficients = prepared
    native_before = _native_files(evaluator, pins)
    _loaded_w0_sources(before)
    _need(_digest(snapshot_sources(request["w0_checkout"], request["factory_file"],
          request["external_factory_sha256"], request["pins"], request["python_paths"])) == _digest(before),
          "SOURCE_CHANGED_DURING_FACTORY")
    report["native_audit_invoked"] = True
    evidence = audit_module.audit_native_full_partition_once(
        evaluator=evaluator, problem=problem, c=coefficients, pins=pins)
    validate_m6_evidence(evidence, pins)
    native_after = _native_files(evaluator, pins)
    _need(native_after == native_before, "NATIVE_MODULE_BYTES_CHANGED_DURING_AUDIT")
    after = snapshot_sources(request["w0_checkout"], request["factory_file"],
                             request["external_factory_sha256"], request["pins"], request["python_paths"])
    _need(after == before, "SOURCE_CHANGED_DURING_AUDIT")
    report.update(status="REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE",
                  m6_evidence=evidence, native_full_partition_certified=True,
                  native_call_counts_observed={"source": 1, "boolean": 2},
                  source_snapshot_sha256=_digest(before), source_files_unchanged=True,
                  pins_file_sha256=pin_record["sha256"], native_module_files=native_after,
                  loaded_w0_source_files=_loaded_w0_sources(after))
    return report


@contextmanager
def _native_lock():
    descriptor = os.open(LOCK_PATH, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        _need(stat.S_ISREG(os.fstat(descriptor).st_mode), "NATIVE_LOCK_NOT_REGULAR")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise LaunchRejected("BLOCKED_OTHER_W0_M5_M6_NATIVE_JOB_ACTIVE") from exc
        yield
    finally:
        os.close(descriptor)


def _run_child(request, output_path):
    """No shell; full child logs are exclusive files beside the new report."""
    output = _path(output_path)
    stdout_path = output.with_name(output.name + ".worker.stdout.log")
    stderr_path = output.with_name(output.name + ".worker.stderr.log")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    started = time.monotonic()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        process = subprocess.Popen([sys.executable, str(_path(__file__)), "--_worker"],
            stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, env=env,
            cwd=request["w0_checkout"], start_new_session=True)
        timed_out = False
        try:
            process.communicate(_canonical(request).encode("ascii"), timeout=MAX_RUNTIME_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
    stdout_data, stdout_record = _read_file(stdout_path, maximum=64 * 1024**2)
    _, stderr_record = _read_file(stderr_path, maximum=64 * 1024**2)
    lines = stdout_data.decode("utf-8", errors="replace").splitlines()
    markers = [line[len(RESULT_PREFIX):] for line in lines if line.startswith(RESULT_PREFIX)]
    child = _json(markers[0]) if len(markers) == 1 else None
    return {"returncode": process.returncode, "timed_out": timed_out,
            "wall_seconds": time.monotonic() - started, "stdout_log": stdout_record,
            "stderr_log": stderr_record, "worker_report": child}


def _write_report(output_path, report):
    output = _path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")


def launch_m6(*, w0_checkout, factory_file, pins, external_pins_sha256,
              external_factory_sha256, output, factory_function="prepare_one", python_paths=()):
    """Return (exit_code, report); create a new report, never modify W0 files.

    0 = real public M6 geometry audit returned and all byte bindings held;
    3 = resource/serialization blocked; 4 = missing, changed or failed proof;
    5 = child wall timeout.  Every exit keeps all scientific admission false.
    """
    report, code = _base_report(), 4
    destination = _path(output)
    _need(not destination.exists(), "EVIDENCE_FILE_EXISTS_NO_OVERWRITE")
    try:
        observed = linux_resources()
        report["resources"] = observed
        state = resource_admission(observed)
        if state != "ADMITTED_RESOURCE_POLICY_ONLY":
            report["status"], code = state, 3
        else:
            _need(type(factory_function) is str and factory_function.isidentifier(), "INVALID_FACTORY_FUNCTION")
            frozen_pins, pin_record = read_precommitted_pins(pins, external_pins_sha256)
            before = snapshot_sources(w0_checkout, factory_file, external_factory_sha256, pins, python_paths)
            _need(before["pins_file"] == pin_record, "PINS_CHANGED_DURING_PREFLIGHT")
            report.update(source_snapshot=before, source_snapshot_sha256=_digest(before),
                          pins_file_sha256=pin_record["sha256"], external_pins_sha256=external_pins_sha256,
                          external_factory_sha256=external_factory_sha256)
            request = {"w0_checkout": str(_path(w0_checkout)), "factory_file": str(_path(factory_file)),
                       "factory_function": factory_function, "pins": str(_path(pins)),
                       "external_pins_sha256": external_pins_sha256,
                       "external_factory_sha256": external_factory_sha256,
                       "python_paths": [str(_path(p)) for p in python_paths],
                       "source_snapshot_sha256": _digest(before), "run_nonce": uuid.uuid4().hex}
            destination.parent.mkdir(parents=True, exist_ok=True)
            with _native_lock():
                report.update(worker_started=True, native_call_counts_observed=None,
                              native_audit_invoked=None, factory_imported=None)
                child = _run_child(request, destination)
            report["child_process"] = child
            if child["timed_out"]:
                report["status"], code = "BLOCKED_NATIVE_RUNTIME_EXCEEDED_3600_SECONDS", 5
            else:
                _need(child["returncode"] == 0, "NATIVE_WORKER_FAILED")
                worker = child["worker_report"]
                _need(type(worker) is dict and worker.get("schema") == WORKER_SCHEMA and
                      worker.get("run_nonce") == request["run_nonce"], "FRESH_W4_WORKER_ENVELOPE_REQUIRED")
                for key in FALSE_ADMISSION_FLAGS:
                    _need(worker.get(key) is False, "WORKER_FORBIDDEN_ADMISSION:" + key)
                _need(worker.get("native_full_partition_certified") is True and
                      worker.get("source_files_unchanged") is True and
                      worker.get("source_snapshot_sha256") == _digest(before) and
                      worker.get("pins_file_sha256") == external_pins_sha256,
                      "WORKER_IMMUTABLE_NATIVE_BINDING_MISSING")
                evidence = validate_m6_evidence(worker.get("m6_evidence"), frozen_pins)
                after = snapshot_sources(w0_checkout, factory_file, external_factory_sha256, pins, python_paths)
                _need(after == before, "SOURCE_CHANGED_BEFORE_PARENT_COLLECTION")
                report.update(status="REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE",
                    native_audit_invoked=True, factory_imported=True, native_full_partition_certified=True,
                    native_call_counts_observed={"source": 1, "boolean": 2}, m6_evidence=evidence,
                    source_files_unchanged=True, loaded_w0_source_files=worker.get("loaded_w0_source_files"),
                    native_module_files=worker.get("native_module_files"))
                code = 0
    except (LaunchRejected, OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        report.update(status="FAILED_CLOSED", reason=f"{type(exc).__name__}: {exc}")
        if "BLOCKED_OTHER_W0_M5_M6_NATIVE_JOB_ACTIVE" in str(exc):
            report["status"], code = "BLOCKED_OTHER_W0_M5_M6_NATIVE_JOB_ACTIVE", 3
    _write_report(destination, report)
    return code, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w0-checkout")
    parser.add_argument("--factory-file")
    parser.add_argument("--factory-function", default="prepare_one")
    parser.add_argument("--pins")
    parser.add_argument("--external-pins-sha256")
    parser.add_argument("--external-factory-sha256")
    parser.add_argument("--python-path", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        request = None
        try:
            request = _json(sys.stdin.buffer.read(1024 * 1024))
            report = _worker(request)
            code = 0 if report["native_full_partition_certified"] else 3
        except BaseException as exc:
            report = _base_report(WORKER_SCHEMA)
            report.update(status="FAILED_CLOSED", worker_started=True,
                          native_call_counts_observed=None, native_audit_invoked=None, factory_imported=None,
                          run_nonce=request.get("run_nonce") if type(request) is dict else None,
                          reason=f"{type(exc).__name__}: {exc}")
            code = 4
        print(RESULT_PREFIX + _canonical(report), flush=True)
        return code
    required = ("w0_checkout", "factory_file", "pins", "external_pins_sha256", "external_factory_sha256", "output")
    if any(getattr(args, name) is None for name in required):
        parser.error("required: --w0-checkout --factory-file --pins --external-pins-sha256 --external-factory-sha256 --output")
    try:
        code, report = launch_m6(w0_checkout=args.w0_checkout, factory_file=args.factory_file,
            factory_function=args.factory_function, pins=args.pins,
            external_pins_sha256=args.external_pins_sha256,
            external_factory_sha256=args.external_factory_sha256,
            output=args.output, python_paths=args.python_path)
    except (LaunchRejected, OSError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 4
    print(_canonical(report))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
