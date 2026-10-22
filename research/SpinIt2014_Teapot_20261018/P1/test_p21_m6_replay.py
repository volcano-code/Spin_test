"""TEST_ONLY control-plane cases; fixtures never establish native execution.

Subprocess and qualified-resource positive paths are explicit test doubles.
Actual resource observations and actual frozen MFD replay are recorded separately.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import p21_m6_replay as run


TEST_ONLY = "TEST_ONLY_CONTROL_PLANE_NO_NATIVE_EXECUTION"


class RunCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="w4-p21-TEST_ONLY-")
        self.root = Path(self.temp.name)
        self.pins_path = self.root / "TEST_ONLY-pins.json"
        self.pins = {key: hashlib.sha256((TEST_ONLY+key).encode()).hexdigest()
                     for key in ("native_sha256", "bridge_sha256", "adapter_sha256",
                                 "c_sha256", "problem_input_digest", "context_sha256")}
        run.new_json(self.pins_path, self.pins)
        self.lock_path = self.root / "TEST_ONLY-lock.json"
        self.lock = {
            "schema": run.LOCK_SCHEMA, "test_only": False, "TEST_ONLY": TEST_ONLY,
            "source_w4_baseline_commit": run.W4_BASELINE, "w0_commit": run.W0_COMMIT,
            "registration_is_independent_attestation": False,
            "registration_grants_scientific_admission": False, "admission": dict(run.SCIENCE),
            "paths": {"w0_checkout": str(self.root / "TEST_ONLY-w0"),
                      "factory_file": str(run.BASE / "p21_native_factory.py"),
                      "launcher_file": str(run.BASE / "p20_m6_launch.py"),
                      "pins_file": str(self.pins_path), "python_paths": [str(self.root / "TEST_ONLY-native")]},
            "pins_sha256": run.sha(self.pins_path.read_bytes()), "pins": self.pins,
            "factory_sha256": run.sha((run.BASE / "p21_native_factory.py").read_bytes()),
            "python_executable": str(Path(sys.executable).resolve()), "python_version": sys.version,
            "runtime_environment_allowlist": {key: os.environ.get(key) for key in run.SAFE_ENV},
            "source_snapshot": {"TEST_ONLY": TEST_ONLY}, "source_snapshot_sha256": "a"*64,
        }
        self.fake_launch = SimpleNamespace(
            linux_resources=Mock(return_value={"physical_memory_bytes": 8*1024**3,
                                              "effective_memory_bytes": 8*1024**3,
                                              "swap_kib": 0, "TEST_ONLY": TEST_ONLY}),
            resource_admission=Mock(return_value="BLOCKED_PHYSICAL_MEMORY_BELOW_20_GIB"),
            snapshot_sources=Mock(return_value={"TEST_ONLY": TEST_ONLY}),
            _digest=Mock(return_value="a"*64))

    def tearDown(self):
        self.temp.cleanup()

    def save_lock(self):
        run.new_json(self.lock_path, self.lock)
        return run.sha(self.lock_path.read_bytes())

    def execute(self, *, fake_process=None):
        digest = self.save_lock()
        with patch.object(run, "load_p20", return_value=self.fake_launch), \
             patch.object(run, "_bind_binary_pins", return_value=None), \
             patch.object(run.subprocess, "run", side_effect=fake_process) as process:
            result = run.execute(lock_path=self.lock_path, expected_lock_sha256=digest,
                                 output_directory=self.root / "TEST_ONLY-bundle")
        return result, process

    @staticmethod
    def blocked_process(command, **kwargs):
        output = Path(command[command.index("--output")+1])
        run.new_json(output, {"schema": "W4_P20_M6_RUNTIME_V1", "TEST_ONLY": TEST_ONLY,
                             "status": "BLOCKED_PHYSICAL_MEMORY_BELOW_20_GIB",
                             "native_audit_invoked": False, "worker_started": False,
                             "factory_imported": False})
        return subprocess.CompletedProcess(command, 3)


class InputContractTests(RunCase):
    def test_duplicate_and_nonfinite_json_rejected(self):
        for data in (b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.subTest(data=data), self.assertRaises(run.ReplayRunRejected):
                run.strict_json(data)

    def test_lock_must_match_explicit_prior_digest(self):
        self.save_lock()
        with self.assertRaisesRegex(run.ReplayRunRejected, "PRERUN_LOCK_SHA256_MISMATCH"):
            run.read_lock(self.lock_path, "0"*64)

    def test_lock_requires_explicit_digest(self):
        for value in (None, "", True, "ABC", "A"*64):
            with self.subTest(value=value), self.assertRaisesRegex(run.ReplayRunRejected, "EXTERNAL_LOCK_SHA256_REQUIRED"):
                run.read_lock(self.lock_path, value)

    def test_test_only_lock_cannot_enter_production(self):
        self.lock["test_only"] = True
        digest = self.save_lock()
        with self.assertRaisesRegex(run.ReplayRunRejected, "TEST_ONLY_LOCK_FORBIDDEN"):
            run.read_lock(self.lock_path, digest)

    def test_lock_cannot_claim_owner_or_training_admission(self):
        self.lock["admission"]["W2_teacher_training_allowed"] = True
        digest = self.save_lock()
        with self.assertRaisesRegex(run.ReplayRunRejected, "LOCK_ADMISSION_CHANGED"):
            run.read_lock(self.lock_path, digest)

    def test_prior_failures_are_never_overwritten(self):
        target = self.root / "prior-failure.json"
        target.write_bytes(b"TEST_ONLY_PRESERVED_FAILURE")
        with self.assertRaises(FileExistsError):
            run.new_json(target, {"new": True})
        self.assertEqual(target.read_bytes(), b"TEST_ONLY_PRESERVED_FAILURE")

    def test_symlink_is_rejected_before_read(self):
        target = self.root / "pins-link.json"
        target.symlink_to(self.pins_path)
        with self.assertRaisesRegex(run.ReplayRunRejected, "SYMLINK_PATH_REJECTED"):
            run.read_bytes(target)

    def test_authenticated_launcher_source_cannot_be_substituted(self):
        (self.root / "p20_m6_launch.py").write_text("raise RuntimeError('TEST_ONLY must never execute')\n")
        with patch.object(run, "BASE", self.root), self.assertRaisesRegex(run.ReplayRunRejected, "FROZEN_P20_LAUNCHER_CHANGED"):
            run.load_p20()


class ResourceAndExecutionTests(RunCase):
    def test_preflight_refuses_without_source_snapshot_or_process(self):
        with patch.object(run, "load_p20", return_value=self.fake_launch), \
             patch.object(run.subprocess, "run", side_effect=AssertionError("no process")):
            code, report = run.preflight(self.root / "TEST_ONLY-preflight.json")
        self.assertEqual(code, 3)
        self.assertIs(report["formal_M6_executed"], False)
        self.assertIs(report["factory_imported"], False)
        self.fake_launch.snapshot_sources.assert_not_called()

    def test_resource_admission_alone_does_not_execute_native(self):
        self.fake_launch.resource_admission.return_value = "ADMITTED_RESOURCE_POLICY_ONLY"
        with patch.object(run, "load_p20", return_value=self.fake_launch), \
             patch.object(run.subprocess, "run", side_effect=AssertionError("no process")):
            code, report = run.preflight(self.root / "TEST_ONLY-qualified.json")
        self.assertEqual(code, 0)
        self.assertIs(report["native_worker_started"], False)

    def test_changed_factory_stops_before_process(self):
        self.lock["factory_sha256"] = "0"*64
        with self.assertRaisesRegex(run.ReplayRunRejected, "P21_FACTORY_CHANGED_AFTER_LOCK"):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))

    def test_changed_pins_stops_before_process(self):
        self.lock["pins_sha256"] = "0"*64
        with self.assertRaisesRegex(run.ReplayRunRejected, "PINS_CHANGED_AFTER_LOCK"):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))

    def test_changed_library_environment_stops_before_process(self):
        self.lock["runtime_environment_allowlist"]["LD_LIBRARY_PATH"] = "TEST_ONLY_DIFFERENT_LIBRARY_PATH"
        with self.assertRaisesRegex(run.ReplayRunRejected, "RUNTIME_LIBRARY_OR_THREAD_ENVIRONMENT_CHANGED_AFTER_LOCK"):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))

    def test_changed_python_stops_before_process(self):
        self.lock["python_version"] = "TEST_ONLY_WRONG_PYTHON"
        with self.assertRaisesRegex(run.ReplayRunRejected, "PYTHON_RUNTIME_CHANGED_AFTER_LOCK"):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))

    def test_admitted_route_rechecks_complete_snapshot(self):
        self.fake_launch.resource_admission.return_value = "ADMITTED_RESOURCE_POLICY_ONLY"
        self.fake_launch.snapshot_sources.side_effect = None
        self.fake_launch.snapshot_sources.return_value = {"TEST_ONLY": "changed"}
        with self.assertRaisesRegex(run.ReplayRunRejected, "INPUTS_CHANGED_AFTER_PRERUN_REGISTRATION"):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))

    def test_blocked_observation_still_rechecks_prerun_snapshot_before_delegation(self):
        self.fake_launch.snapshot_sources.return_value = {"TEST_ONLY": "changed while resources could recover"}
        with self.assertRaisesRegex(run.ReplayRunRejected, "INPUTS_CHANGED_AFTER_PRERUN_REGISTRATION"):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))

    def test_blocked_route_preserves_actual_returncode_and_does_not_claim_m6(self):
        (code, report), process = self.execute(fake_process=self.blocked_process)
        self.assertEqual(code, 3)
        self.assertIs(report["formal_executed"], False)
        process.assert_called_once()
        self.fake_launch.snapshot_sources.assert_called_once()
        output = self.root / "TEST_ONLY-bundle"
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(manifest["formal_exit_code"], 3)
        self.assertIs(manifest["formal_executed"], False)
        self.assertFalse((output / "capture").exists())
        roles = {row["role"] for row in manifest["files"]}
        self.assertTrue({"formal_report", "material_M", "material_F", "material_D", "request", "pins"} <= roles)
        for row in manifest["files"]:
            data = (output / row["path"]).read_bytes()
            self.assertEqual(run.sha(data), row["sha256"])
            self.assertEqual(len(data), row["bytes"])

    def test_capture_directory_is_new_and_pythonpath_removed(self):
        observed = {}
        def process(command, **kwargs):
            observed.update(kwargs)
            return self.blocked_process(command, **kwargs)
        with patch.dict(os.environ, {"PYTHONPATH": "TEST_ONLY_UNTRUSTED_OVERLAY"}):
            self.execute(fake_process=process)
        self.assertNotIn("PYTHONPATH", observed["env"])
        self.assertEqual(observed["env"]["PYTHONNOUSERSITE"], "1")
        self.assertEqual(observed["env"]["W4_P21_CAPTURE_DIRECTORY"], str(self.root / "TEST_ONLY-bundle/capture"))

    def test_process_spawn_failure_retains_unknown_execution_state(self):
        def fail(*args, **kwargs):
            raise OSError("TEST_ONLY_SPAWN_FAILED")
        (code, report), _ = self.execute(fake_process=fail)
        self.assertEqual(code, 4)
        self.assertIsNone(report["formal_executed"])
        self.assertIsNone(report["formal_exit_code"])
        record = json.loads((self.root / "TEST_ONLY-bundle/execution.json").read_text())
        self.assertIn("TEST_ONLY_SPAWN_FAILED", record["error"])

    def test_bad_formal_json_preserves_raw_bytes_and_manifest(self):
        def process(command, **kwargs):
            output = Path(command[command.index("--output")+1])
            output.write_bytes(b"TEST_ONLY_TRUNCATED_JSON{")
            return subprocess.CompletedProcess(command, 4)
        (code, report), _ = self.execute(fake_process=process)
        self.assertEqual(code, 4)
        self.assertIsNone(report["formal_executed"])
        self.assertTrue(any("FORMAL_REPORT_PARSE_FAILED" in error for error in report["collection_errors"]))
        output = self.root / "TEST_ONLY-bundle"
        self.assertEqual((output / "formal-report.json").read_bytes(), b"TEST_ONLY_TRUNCATED_JSON{")
        self.assertIs(json.loads((output / "manifest.json").read_text())["collection_completed"], False)

    def test_postrun_resource_failure_still_archives_failed_run(self):
        self.fake_launch.linux_resources.side_effect = [
            {"physical_memory_bytes": 8*1024**3, "effective_memory_bytes": 8*1024**3, "swap_kib": 0},
            ValueError("TEST_ONLY_POSTRUN_RESOURCE_UNAVAILABLE")]
        (code, report), _ = self.execute(fake_process=self.blocked_process)
        self.assertEqual(code, 4)
        self.assertEqual(report["formal_exit_code"], 3)
        self.assertTrue(any("POSTRUN_RESOURCE_OBSERVATION_FAILED" in error for error in report["collection_errors"]))
        self.assertTrue((self.root / "TEST_ONLY-bundle/manifest.json").is_file())

    def test_existing_bundle_is_not_overwritten(self):
        output = self.root / "TEST_ONLY-bundle"
        output.mkdir()
        (output / "sentinel").write_text(TEST_ONLY)
        with self.assertRaises(FileExistsError):
            self.execute(fake_process=Mock(side_effect=AssertionError("no process")))
        self.assertEqual((output / "sentinel").read_text(), TEST_ONLY)


class BinaryBindingTests(RunCase):
    def snapshot(self):
        return {"native_python_paths": [{"binary_files": [
            {"path": "/TEST_ONLY/_make_it_stand.cpython-312.so", "sha256": self.pins["native_sha256"]},
            {"path": "/TEST_ONLY/_cherchi_core_boolean.cpython-312.so", "sha256": self.pins["bridge_sha256"]},
            {"path": "/TEST_ONLY/_cherchi_rational_moments.cpython-312.so", "sha256": "a"*64}]}],
            "w0_source_files": {"python/make_it_stand/verification/cherchi_inprocess.py":
                                {"sha256": self.pins["adapter_sha256"]}}}

    def test_binary_bytes_must_match_pins(self):
        snapshot = self.snapshot()
        snapshot["native_python_paths"][0]["binary_files"][0]["sha256"] = "0"*64
        with self.assertRaisesRegex(run.ReplayRunRejected, "ACTUAL_NATIVE_SEARCH_FILE_PIN_MISMATCH"):
            run._bind_binary_pins(snapshot, self.pins)

    def test_duplicate_native_module_is_rejected(self):
        snapshot = self.snapshot()
        snapshot["native_python_paths"][0]["binary_files"].append(copy.deepcopy(snapshot["native_python_paths"][0]["binary_files"][0]))
        with self.assertRaisesRegex(run.ReplayRunRejected, "ACTUAL_NATIVE_SEARCH_FILE_PIN_MISMATCH"):
            run._bind_binary_pins(snapshot, self.pins)

    def test_arithmetic_module_must_be_present(self):
        snapshot = self.snapshot()
        snapshot["native_python_paths"][0]["binary_files"].pop()
        with self.assertRaisesRegex(run.ReplayRunRejected, "ONE_ACTUAL_RATIONAL_ARITHMETIC_MODULE_REQUIRED"):
            run._bind_binary_pins(snapshot, self.pins)


if __name__ == "__main__":
    unittest.main(verbosity=2)
