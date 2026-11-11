"""Synthetic recovery/launch tests only; no compiler or Cherchi calls."""
import ast
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SOURCE))
import h9_m21_6d_safe_build as b


class SafeBuildTests(unittest.TestCase):
    def test_unique_record_does_not_precreate_build_leaf(self):
        with tempfile.TemporaryDirectory() as folder:
            record, leaf = b.new_session(Path(folder) / 'reports')
            self.assertTrue(record.is_dir())
            self.assertFalse(leaf.exists())
            record2, leaf2 = b.new_session(Path(folder) / 'reports')
            self.assertNotEqual(record, record2)
            self.assertFalse(leaf2.exists())

    def test_memavailable_is_not_memtotal(self):
        memory = b.meminfo('MemTotal: 63369652 kB\nMemAvailable: 18923568 kB\nSwapTotal: 0 kB\n')
        self.assertEqual(memory['available_bytes'], 19377733632)
        self.assertIn('AVAILABLE_RAM_BELOW_24_GIB', b.resource_reasons(memory, [49*b.GIB]))

    def test_missing_memavailable_refuses(self):
        with self.assertRaisesRegex(b.Blocked, 'MEMINFO_INCOMPLETE'):
            b.meminfo('MemTotal: 1000000 kB\nSwapTotal: 0 kB\n')

    def test_available_ram_threshold_passes_with_zero_swap(self):
        self.assertEqual(b.resource_reasons({'available_bytes': 24*b.GIB, 'swap_bytes': 0},
                                           [4*b.GIB, 49*b.GIB]), [])

    def test_swap_is_not_capacity_to_borrow(self):
        self.assertIn('SWAP_MUST_BE_ZERO', b.resource_reasons(
            {'available_bytes': 60*b.GIB, 'swap_bytes': b.GIB}, [49*b.GIB]))

    def test_disk_threshold_is_absolute_not_percentage(self):
        self.assertEqual(b.resource_reasons({'available_bytes': 24*b.GIB, 'swap_bytes': 0},
                                           [19*b.GIB, 49*b.GIB]), [])
        self.assertIn('DISK_FREE_BELOW_OPERATIONAL_4_GIB_FLOOR', b.resource_reasons(
            {'available_bytes': 24*b.GIB, 'swap_bytes': 0}, [b.GIB]))

    def test_clean_environment_is_self_contained(self):
        with tempfile.TemporaryDirectory() as folder:
            lib = Path(folder) / 'libstdc++.so.6'
            lib.write_bytes(b'synthetic-library-not-loaded')
            env = b.clean_env(sys.executable, lib, folder,
                              {'PY': '', 'PYTHONPATH': '/untrusted', 'LD_LIBRARY_PATH': '/conda',
                               'CONDA_PREFIX': '/conda', 'LD_PRELOAD': '/old'})
            self.assertNotIn('PYTHONPATH', env)
            self.assertNotIn('CONDA_PREFIX', env)
            self.assertNotIn('LD_LIBRARY_PATH', env)
            self.assertEqual(env['LD_PRELOAD'], str(lib.resolve()))
            self.assertEqual(env['PYTHONINTMAXSTRDIGITS'], '100000')

    def test_empty_python_path_refuses_before_exec(self):
        with self.assertRaisesRegex(b.Blocked, 'PYTHON_NOT_EXECUTABLE'):
            b.clean_env('', '/nonexistent-lib', '/tmp', {})

    def test_pin_export_is_available_to_quarterpoint_import(self):
        # Static regression against the actual repository module, not a mock import.
        tree = ast.parse((SOURCE / 'h9_m21_layered_replay.py').read_text())
        values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                  and any(isinstance(x, ast.Name) and x.id == 'BINARY_SHA' for x in n.targets)]
        self.assertEqual(values, ['d66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd'])

    def test_cache_hashing_and_ambiguous_library_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            expected = {}
            for key, (directory, name) in b.MODULES.items():
                target = repo / 'build' / directory / 'python' / (name + '.cpython-313.so')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(('fixture-' + key).encode())
                expected[key] = b.digest(target)
            self.assertEqual(b.cache_hashes(repo), expected)
            duplicate = repo / 'build/h9-w3-core/python/_make_it_stand.other.so'
            duplicate.write_bytes(b'duplicate-fixture')
            with self.assertRaisesRegex(b.Blocked, 'AMBIGUOUS_CACHED_MODULE'):
                b.cache_hashes(repo)

    def evidence(self):
        hashes = {key: str(i)*64 for i, key in enumerate(b.MODULES, 1)}
        doc = {'status': 'NATIVE_BINARIES_BUILT_AND_IMPORTABLE_NOT_YET_EVALUATED',
               'head_after_build': 'a'*40, 'newton_admitted': False,
               'module_sha256': {name: hashes[k] for k, (_, name) in b.MODULES.items()}}
        return doc, hashes

    def test_current_head_and_modules_accept(self):
        evidence, hashes = self.evidence()
        self.assertEqual(b.verify_evidence(evidence, 'a'*40, hashes), evidence['module_sha256'])

    def test_old_head_evidence_refuses(self):
        evidence, hashes = self.evidence()
        with self.assertRaisesRegex(b.Blocked, 'BUILD_HEAD_MISMATCH'):
            b.verify_evidence(evidence, 'b'*40, hashes)

    def test_failed_build_file_is_not_success(self):
        evidence, hashes = self.evidence()
        evidence['status'] = 'FAILED_OR_INCOMPLETE'
        with self.assertRaisesRegex(b.Blocked, 'BUILD_NOT_SUCCESSFUL'):
            b.verify_evidence(evidence, 'a'*40, hashes)

    def test_binary_drift_refuses(self):
        evidence, hashes = self.evidence()
        hashes['core'] = 'f'*64
        with self.assertRaisesRegex(b.Blocked, 'BUILD_MODULE_SHA_MISMATCH'):
            b.verify_evidence(evidence, 'a'*40, hashes)

    def test_untrusted_plan_hash_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'plan.json'
            path.write_text('{}')
            with self.assertRaisesRegex(b.Blocked, 'PINNED_PLAN_SHA_MISMATCH'):
                b.load_plan(path)

    def test_plan_rejects_newton_claim_even_at_expected_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'plan.json'
            data = {'schema': 'heart-h9-m21-6d-four-quarterpoint-plan-v1',
                    'status': 'FOUR_REAL_QUARTERPOINTS_PREDECLARED_NOT_EXECUTED',
                    'point_count': 4, 'newton_admitted': True,
                    'new_boolean_calls_executed': 0, 'new_native_source_calls_executed': 0}
            path.write_text(json.dumps(data))
            with patch.object(b, 'PLAN_SHA', b.digest(path)):
                with self.assertRaisesRegex(b.Blocked, 'PLAN_SCOPE_CHANGED'):
                    b.load_plan(path)

    def test_child_failure_is_returned_and_logged(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'failure.log'
            code = b.logged_run([sys.executable, '-c', 'print("synthetic-child"); raise SystemExit(3)'],
                                log, dict(os.environ), folder, 5)
            self.assertEqual(code, 3)
            self.assertIn('synthetic-child', log.read_text())

    def test_timeout_is_returned_without_killing_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            code = b.logged_run([sys.executable, '-c', 'import time; time.sleep(10)'],
                                Path(folder) / 'timeout.log', dict(os.environ), folder, 0.05)
            self.assertEqual(code, 124)


if __name__ == '__main__':
    unittest.main()
