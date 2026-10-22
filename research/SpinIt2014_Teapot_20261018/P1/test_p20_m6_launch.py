"""TEST_ONLY: launcher regression fixtures, zero native geometry executions.

Every positive worker/factory response below is a labelled unit-test double.
These temporary reports are never a W0 receipt or an actual M6 success.
"""
from __future__ import annotations

from contextlib import nullcontext
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest
from unittest.mock import patch

import p20_m6_launch as launch


TEST_ONLY = "TEST_ONLY_NO_NATIVE_EXECUTION"


def resources(*, physical=24, effective=24, swap=0):
    return {"physical_memory_bytes": physical * 1024**3,
            "physical_memory_gib": float(physical), "swap_kib": swap,
            "cgroup_memory_limits": [{"version": 2, "path": "/TEST_ONLY/memory.max",
                                      "raw": str(effective * 1024**3), "limit_bytes": effective * 1024**3}],
            "cgroup_effective_memory_bytes": effective * 1024**3,
            "effective_memory_bytes": effective * 1024**3, "effective_memory_gib": float(effective),
            "child_address_space_limit_bytes": min(effective, 24) * 1024**3}


def pins_fixture():
    return {key: hashlib.sha256((TEST_ONLY + key).encode()).hexdigest() for key in launch.PIN_KEYS}


def evidence_fixture(pins):
    """Structural shape only; no native origin, material, or derivative proof."""
    m4 = {"native_execution_observed": True, "native_region_proved": True,
          "mathematical_replay_passed": True, "training_admissible": False,
          "source_geometry_sha256": "a" * 64, "source_quadric_sha256": "b" * 64,
          "TEST_ONLY": TEST_ONLY}
    mapping = {"native_source_sha256": "native_sha256", "native_bridge_sha256": "bridge_sha256",
               "native_adapter_sha256": "adapter_sha256", "frozen_native_c_sha256": "c_sha256",
               "frozen_problem_digest": "problem_input_digest", "frozen_context_sha256": "context_sha256"}
    m4.update({a: pins[b] for a, b in mapping.items()})
    partitions = []
    for i, (label, count) in enumerate((("fixed_plus_design", 2), ("design_cut", 2), ("full_outer", 3))):
        digest = str(i + 1) * 64
        facts = {"completed": True, "complete_partition": True, "union_equals_whole": True,
                 "no_positive_volume_overlap": True, "missing_whole_content": False,
                 "excess_union_content": False, "part_subset_whole": [True] * count,
                 "positive_volume_overlap_pairs": [], "partition_digest": digest, "TEST_ONLY": TEST_ONLY}
        partitions.append({"label": label, "part_count": count, "partition_digest": digest,
                           "native_predicate_facts": facts})
    return {"schema": launch.M6_SCHEMA, "native_full_partition_certified": True,
            "retained_plus_cavity_equals_design_r10_exact": True,
            "fixed_plus_retained_density_weighted_moments_verified": True,
            "training_admissible": False, "smooth_derivative_certified": False,
            "newton_terminal_certified": False, "scope": "EXACT_REPRESENTED_POLYHEDRAL_SETS_AND_R10_ONLY",
            "observed_native_source_calls": 1, "observed_native_boolean_calls": 2,
            "complement_additional_source_calls": 0, "complement_additional_boolean_calls": 1,
            "exact_partition_predicates": partitions,
            "M5_evidence": {"schema": "W0_M5_LIVE_W0_W2_PARITY_V1", "training_admissible": False,
                            "m4_native_evidence": m4}, "TEST_ONLY": TEST_ONLY}


class TemporaryCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w4-p20-TEST_ONLY-")
        self.root = Path(self.temp.name)
        self.pins = pins_fixture()
        self.pin_path = self.root / "pins.json"
        self.pin_path.write_text(json.dumps(self.pins), encoding="ascii")
        self.pin_sha = hashlib.sha256(self.pin_path.read_bytes()).hexdigest()
        self.factory = self.root / "factory.py"
        self.factory.write_text("# TEST_ONLY, never a real native factory\n", encoding="ascii")
        self.factory_sha = hashlib.sha256(self.factory.read_bytes()).hexdigest()
        self.output = self.root / "TEST_ONLY-report.json"
        self.kwargs = {"w0_checkout": self.root / "w0", "factory_file": self.factory,
                       "pins": self.pin_path, "external_pins_sha256": self.pin_sha,
                       "external_factory_sha256": self.factory_sha, "output": self.output}
        self.snapshot = {"TEST_ONLY": TEST_ONLY, "pins_file": launch._read_file(self.pin_path)[1]}

    def tearDown(self):
        self.temp.cleanup()

    def child(self, request, output):
        worker = launch._base_report(launch.WORKER_SCHEMA)
        worker.update(run_nonce=request["run_nonce"], native_full_partition_certified=True,
                      source_files_unchanged=True, source_snapshot_sha256=request["source_snapshot_sha256"],
                      pins_file_sha256=self.pin_sha, m6_evidence=evidence_fixture(self.pins),
                      loaded_w0_source_files={"TEST_ONLY": TEST_ONLY},
                      native_module_files={"TEST_ONLY": TEST_ONLY})
        return {"returncode": 0, "timed_out": False, "worker_report": worker, "TEST_ONLY": TEST_ONLY}

    def mocked_launch(self, *, child=None, snapshot=None):
        with patch.object(launch, "linux_resources", return_value=resources()), \
             patch.object(launch, "snapshot_sources", side_effect=snapshot or (lambda *a, **k: self.snapshot)), \
             patch.object(launch, "_native_lock", side_effect=lambda: nullcontext()), \
             patch.object(launch, "_run_child", side_effect=child or self.child):
            return launch.launch_m6(**self.kwargs)


class ResourceTests(TemporaryCase):
    def test_physical_ram_blocks_before_source_or_factory(self):
        with patch.object(launch, "linux_resources", return_value=resources(physical=10, effective=8)), \
             patch.object(launch, "snapshot_sources", side_effect=AssertionError("MUST_NOT_READ_OR_IMPORT")), \
             patch.object(launch, "_run_child", side_effect=AssertionError("MUST_NOT_LAUNCH_NATIVE")):
            code, report = launch.launch_m6(**self.kwargs)
        self.assertEqual(code, 3)
        self.assertEqual(report["status"], "BLOCKED_INSUFFICIENT_PHYSICAL_RAM")
        self.assertEqual(report["resources"]["cgroup_effective_memory_bytes"], 8 * 1024**3)
        self.assertFalse(report["factory_imported"])
        self.assertEqual(report["native_call_counts_observed"], {"source": 0, "boolean": 0})
        self.assertIsNone(report["m6_evidence"])

    def test_ample_physical_ram_cannot_mask_small_cgroup(self):
        self.assertEqual(launch.resource_admission(resources(physical=64, effective=8)),
                         "BLOCKED_INSUFFICIENT_EFFECTIVE_MEMORY")

    def test_swap_is_veto_even_when_cgroup_has_24gib(self):
        self.assertEqual(launch.resource_admission(resources(swap=1024)), "BLOCKED_NONZERO_SWAP")

    def test_exact_20gib_boundary_admits_resources_only(self):
        self.assertEqual(launch.resource_admission(resources(physical=20, effective=20)),
                         "ADMITTED_RESOURCE_POLICY_ONLY")

    def test_missing_cgroup_observation_is_not_unlimited(self):
        observed = resources()
        observed["cgroup_memory_limits"] = []
        with self.assertRaisesRegex(launch.LaunchRejected, "CGROUP_MEMORY_LIMIT_UNAVAILABLE"):
            launch.resource_admission(observed)

    def test_boolean_or_negative_resource_value_rejected(self):
        for value in (True, -1, float("nan")):
            observed = resources()
            observed["effective_memory_bytes"] = value
            with self.subTest(value=value), self.assertRaises(launch.LaunchRejected):
                launch.resource_admission(observed)

    def test_worker_rechecks_resources_before_factory(self):
        with patch.object(launch, "linux_resources", return_value=resources(physical=64, effective=8)), \
             patch.object(launch, "_apply_worker_limits", side_effect=AssertionError("NO_IMPORT")), \
             patch.object(launch.importlib, "import_module", side_effect=AssertionError("NO_IMPORT")):
            report = launch._worker({"run_nonce": TEST_ONLY})
        self.assertEqual(report["status"], "BLOCKED_INSUFFICIENT_EFFECTIVE_MEMORY")
        self.assertFalse(report["native_audit_invoked"])

    def test_child_hard_limit_is_applied(self):
        with patch.object(launch.resource, "setrlimit") as limits, patch.object(launch.signal, "alarm") as alarm:
            report = launch._apply_worker_limits(resources())
        limits.assert_called_once_with(launch.resource.RLIMIT_AS, (24 * 1024**3, 24 * 1024**3))
        alarm.assert_called_once_with(3600)
        self.assertEqual(report["RLIMIT_AS_hard_bytes"], 24 * 1024**3)

    def test_cgroup_ancestor_limit_is_observed(self):
        mount = self.root / "cgroup"
        leaf = mount / "parent/leaf"
        leaf.mkdir(parents=True)
        (mount / "memory.max").write_text("max")
        (leaf.parent / "memory.max").write_text(str(8 * 1024**3))
        (leaf / "memory.max").write_text(str(24 * 1024**3))
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            if str(path) == "/proc/self/cgroup":
                return "0::/parent/leaf\n"
            if str(path) == "/proc/self/mountinfo":
                return f"1 0 0:24 / {mount} rw - cgroup2 cgroup2 rw\n"
            return original_read(path, *args, **kwargs)
        with patch.object(Path, "read_text", read):
            result = launch._cgroup_memory_limits()
        self.assertEqual(min(row["limit_bytes"] for row in result if row["limit_bytes"] is not None), 8 * 1024**3)
        self.assertEqual(len(result), 3)


class PinsTests(TemporaryCase):
    def test_exact_six_pins_are_bound_to_external_file_sha(self):
        actual, record = launch.read_precommitted_pins(self.pin_path, self.pin_sha)
        self.assertEqual(actual, self.pins)
        self.assertEqual(record["sha256"], self.pin_sha)

    def test_missing_extra_or_bad_pin_rejected(self):
        cases = []
        missing = self.pins.copy(); missing.pop("context_sha256"); cases.append(missing)
        extra = dict(self.pins, training_admissible=True); cases.append(extra)
        bad = dict(self.pins, native_sha256="UNFROZEN"); cases.append(bad)
        for payload in cases:
            with self.subTest(payload=payload):
                self.pin_path.write_text(json.dumps(payload))
                sha = hashlib.sha256(self.pin_path.read_bytes()).hexdigest()
                with self.assertRaises(launch.LaunchRejected):
                    launch.read_precommitted_pins(self.pin_path, sha)

    def test_external_pin_sha_mismatch_rejected_before_worker(self):
        self.kwargs["external_pins_sha256"] = "f" * 64
        with patch.object(launch, "linux_resources", return_value=resources()), \
             patch.object(launch, "_run_child", side_effect=AssertionError("MUST_NOT_RUN")):
            code, report = launch.launch_m6(**self.kwargs)
        self.assertEqual(code, 4)
        self.assertIn("EXTERNAL_PINS_SHA256_MISMATCH", report["reason"])

    def test_duplicate_json_key_is_not_last_value_wins(self):
        self.pin_path.write_text('{"native_sha256":"a","native_sha256":"b"}')
        sha = hashlib.sha256(self.pin_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(launch.LaunchRejected, "DUPLICATE_JSON_KEY"):
            launch.read_precommitted_pins(self.pin_path, sha)

    def test_pin_symlink_rejected(self):
        link = self.root / "pin-link.json"
        link.symlink_to(self.pin_path)
        with self.assertRaisesRegex(launch.LaunchRejected, "SYMLINK"):
            launch.read_precommitted_pins(link, self.pin_sha)


class EnvelopeTests(TemporaryCase):
    def test_original_schema_collision_regression_nested_complete_survives(self):
        # The old W0 worker did report.update(m6), overwriting its RUNTIME
        # schema.  New W4 envelope and nested W0 evidence preserve both names.
        old_runtime = {"schema": "W0_M6_NATIVE_FULL_PARTITION_RUNTIME_V1"}
        old_runtime.update(evidence_fixture(self.pins))
        self.assertNotEqual(old_runtime["schema"], "W0_M6_NATIVE_FULL_PARTITION_RUNTIME_V1")
        code, report = self.mocked_launch()
        self.assertEqual(code, 0)
        self.assertEqual(report["schema"], launch.SCHEMA)
        self.assertEqual(report["m6_evidence"]["schema"], launch.M6_SCHEMA)
        self.assertEqual(report["m6_evidence"]["TEST_ONLY"], TEST_ONLY)
        for key in launch.FALSE_ADMISSION_FLAGS:
            self.assertIs(report[key], False)

    def test_stale_worker_nonce_rejected(self):
        def child(request, output):
            result = self.child(request, output)
            result["worker_report"]["run_nonce"] = "stale-TEST_ONLY"
            return result
        code, report = self.mocked_launch(child=child)
        self.assertEqual(code, 4)
        self.assertFalse(report["native_full_partition_certified"])
        self.assertIsNone(report["m6_evidence"])

    def test_complete_schema_in_outer_worker_is_rejected(self):
        def child(request, output):
            result = self.child(request, output)
            result["worker_report"]["schema"] = launch.M6_SCHEMA
            return result
        code, report = self.mocked_launch(child=child)
        self.assertEqual(code, 4)
        self.assertIn("ENVELOPE", report["reason"])

    def test_worker_admission_claim_rejected(self):
        def child(request, output):
            result = self.child(request, output)
            result["worker_report"]["W0_physical_case_approved"] = True
            return result
        code, report = self.mocked_launch(child=child)
        self.assertEqual(code, 4)
        self.assertFalse(report["W0_physical_case_approved"])

    def test_source_changed_after_worker_rejected(self):
        observations = iter([self.snapshot, dict(self.snapshot, drift=TEST_ONLY)])
        code, report = self.mocked_launch(snapshot=lambda *a: next(observations))
        self.assertEqual(code, 4)
        self.assertIn("SOURCE_CHANGED_BEFORE_PARENT_COLLECTION", report["reason"])
        self.assertFalse(report["native_full_partition_certified"])

    def test_failed_or_unstarted_native_cannot_be_success(self):
        def child(request, output):
            return {"returncode": 4, "timed_out": False, "worker_report": None, "TEST_ONLY": TEST_ONLY}
        code, report = self.mocked_launch(child=child)
        self.assertEqual(code, 4)
        self.assertIsNone(report["native_audit_invoked"])
        self.assertIsNone(report["native_call_counts_observed"])
        self.assertFalse(report["native_full_partition_certified"])

    def test_timeout_preserves_no_admission_and_unknown_calls(self):
        def child(request, output):
            return {"returncode": -9, "timed_out": True, "worker_report": None, "TEST_ONLY": TEST_ONLY}
        code, report = self.mocked_launch(child=child)
        self.assertEqual(code, 5)
        self.assertIsNone(report["native_call_counts_observed"])
        self.assertFalse(report["training_admissible"])

    def test_historical_failure_is_never_overwritten(self):
        self.output.write_text("TEST_ONLY_PRESERVE_EXISTING_FAILURE")
        with self.assertRaisesRegex(launch.LaunchRejected, "NO_OVERWRITE"):
            launch.launch_m6(**self.kwargs)
        self.assertEqual(self.output.read_text(), "TEST_ONLY_PRESERVE_EXISTING_FAILURE")


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pins = pins_fixture()
        self.evidence = evidence_fixture(self.pins)

    def test_structural_fixture_is_explicit_test_only(self):
        result = launch.validate_m6_evidence(self.evidence, self.pins)
        self.assertEqual(result["TEST_ONLY"], TEST_ONLY)

    def test_all_six_receipt_pins_are_enforced(self):
        for key in launch.PIN_KEYS:
            changed = dict(self.pins, **{key: "e" * 64})
            with self.subTest(key=key), self.assertRaisesRegex(launch.LaunchRejected, "RECEIPT_PIN_MISMATCH"):
                launch.validate_m6_evidence(self.evidence, changed)

    def test_same_source_requires_one_source_and_two_booleans(self):
        for key, value in (("observed_native_source_calls", 2), ("observed_native_boolean_calls", 1),
                           ("observed_native_source_calls", True), ("complement_additional_source_calls", 1)):
            bad = dict(self.evidence, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaisesRegex(launch.LaunchRejected, "CALL_COUNT"):
                launch.validate_m6_evidence(bad, self.pins)

    def test_full_native_predicate_facts_cannot_be_replaced_by_flags(self):
        for key, value in (("completed", False), ("missing_whole_content", True),
                           ("excess_union_content", True), ("part_subset_whole", [True, False]),
                           ("positive_volume_overlap_pairs", [[0, 1]])):
            bad = copy.deepcopy(self.evidence)
            bad["exact_partition_predicates"][0]["native_predicate_facts"][key] = value
            with self.subTest(key=key), self.assertRaises(launch.LaunchRejected):
                launch.validate_m6_evidence(bad, self.pins)

    def test_missing_or_reordered_partition_is_rejected(self):
        bad = copy.deepcopy(self.evidence)
        bad["exact_partition_predicates"].reverse()
        with self.assertRaisesRegex(launch.LaunchRejected, "THREE_ORDERED"):
            launch.validate_m6_evidence(bad, self.pins)

    def test_nested_false_admission_cannot_be_upgraded(self):
        bad = copy.deepcopy(self.evidence)
        bad["M5_evidence"]["m4_native_evidence"]["training_admitted"] = True
        with self.assertRaisesRegex(launch.LaunchRejected, "FORBIDDEN_NESTED_ADMISSION"):
            launch.validate_m6_evidence(bad, self.pins)


class SourceIdentityTests(TemporaryCase):
    def setUp(self):
        super().setUp()
        self.checkout = self.root / "w0"
        self.relative = "research/NeuralMoments/contracts/full_partition_m6.py"
        self.source = self.checkout / self.relative
        self.source.parent.mkdir(parents=True)
        self.source.write_text("# TEST_ONLY synthetic source; never imported\n", encoding="ascii")
        data = self.source.read_bytes()
        self.blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        self.tree = f"100644 blob {self.blob}\t{self.relative}\0".encode()

    def fake_git(self, checkout, *args):
        if args == ("rev-parse", "--show-toplevel"):
            return str(self.checkout).encode() + b"\n"
        if args == ("rev-parse", "HEAD"):
            return launch.W0_COMMIT.encode() + b"\n"
        if args == ("rev-parse", "HEAD^{tree}"):
            return b"TEST_ONLY_TREE\n"
        if args == ("ls-tree", "-r", "-z", "--full-tree", "HEAD"):
            return self.tree
        raise AssertionError(args)

    def source_snapshot(self):
        with patch.object(launch, "_git", side_effect=self.fake_git), \
             patch.object(launch, "CRITICAL_BLOBS", {self.relative: self.blob}):
            return launch.snapshot_sources(self.checkout, self.factory, self.factory_sha, self.pin_path)

    def test_every_tracked_source_byte_has_git_blob_and_sha(self):
        report = self.source_snapshot()
        record = report["w0_source_files"][self.relative]
        self.assertEqual(record["git_blob"], self.blob)
        self.assertEqual(record["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertFalse(report["source_to_binary_build_attestation"])

    def test_modified_w0_source_rejected_even_if_git_head_unchanged(self):
        self.source.write_text("# TEST_ONLY mutation\n")
        with self.assertRaisesRegex(launch.LaunchRejected, "SOURCE_BLOB_MISMATCH"):
            self.source_snapshot()

    def test_untracked_python_overlay_rejected(self):
        (self.source.parent / "shadow.py").write_text("# TEST_ONLY overlay\n")
        with self.assertRaisesRegex(launch.LaunchRejected, "UNTRACKED_W0_PYTHON_SOURCE"):
            self.source_snapshot()

    def test_factory_external_sha_mismatch_rejected(self):
        self.factory.write_text("# TEST_ONLY changed factory\n")
        with self.assertRaisesRegex(launch.LaunchRejected, "EXTERNAL_FACTORY_SHA256_MISMATCH"):
            self.source_snapshot()

    def test_source_symlink_is_not_authenticated_by_destination_bytes(self):
        target = self.root / "actual.py"
        self.source.rename(target)
        self.source.symlink_to(target)
        with self.assertRaisesRegex(launch.LaunchRejected, "SYMLINK"):
            self.source_snapshot()

    def test_factory_config_is_in_source_freeze(self):
        config = self.factory.parent / "P20_native_request.json"
        config.write_text('{"scope":"TEST_ONLY"}')
        before = self.source_snapshot()
        config.write_text('{"scope":"TEST_ONLY_CHANGED"}')
        after = self.source_snapshot()
        self.assertNotEqual(launch._digest(before), launch._digest(after))

    def test_registered_material_input_is_frozen_before_and_after(self):
        material = self.root / "TEST_ONLY.obj"
        material.write_text("# TEST_ONLY no geometry\n")
        reference = {"path": material.name, "sha256": hashlib.sha256(material.read_bytes()).hexdigest()}
        config = {"schema": "W4_P20_TEAPOT_NATIVE_REQUEST_V1", "manifest": reference,
                  "canonical_report": reference, "material_inputs": {"M": reference, "F": reference, "D": reference}}
        (self.factory.parent / "P20_native_request.json").write_text(json.dumps(config))
        observed = self.source_snapshot()
        self.assertEqual(observed["factory_registered_input_files"]["D"]["sha256"], reference["sha256"])
        material.write_text("# TEST_ONLY changed input\n")
        with self.assertRaisesRegex(launch.LaunchRejected, "REGISTERED_FACTORY_INPUT_SHA_MISMATCH"):
            self.source_snapshot()

    def test_timestamp_valid_old_bytecode_cannot_replace_checked_source(self):
        name = "p20_TEST_ONLY_cache_poison"
        source = self.root / (name + ".py")
        source.write_text("VALUE='BAD000'\n")
        original = source.stat()
        py_compile.compile(str(source), doraise=True)
        source.write_text("VALUE='GOOD01'\n")
        os.utime(source, ns=(original.st_atime_ns, original.st_mtime_ns))
        old_prefix, old_write, old_path = sys.pycache_prefix, sys.dont_write_bytecode, list(sys.path)
        try:
            with launch._frozen_import_environment(self.root, self.factory, []):
                module = importlib.import_module(name)
                self.assertEqual(module.VALUE, "GOOD01")
            self.assertEqual(sys.pycache_prefix, old_prefix)
            self.assertEqual(sys.dont_write_bytecode, old_write)
            self.assertEqual(sys.path, old_path)
        finally:
            sys.modules.pop(name, None)


if __name__ == "__main__":
    unittest.main()
