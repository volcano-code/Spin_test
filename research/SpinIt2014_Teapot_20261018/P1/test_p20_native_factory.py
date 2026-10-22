"""TEST_ONLY byte/coordinate guard regressions; no native proof is mocked in."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import p20_native_factory as factory
from p20_owned_material_audit import run_owned_preparation
import p20_owned_material_audit as owned_audit


class FrozenP19InputTests(unittest.TestCase):
    def test_real_registered_inputs_and_dimensions(self):
        config, observed = factory.load_request()
        self.assertEqual(len(observed), 7)
        self.assertEqual(config['geometry_policy']['shaft_material'],
                         'S_ALREADY_INCLUDED_IN_F_NEVER_ADDED_AGAIN')
        for name, spec in config['material_inputs'].items():
            vertices, faces = factory.read_frozen_obj(factory.BASE/spec['path'])
            self.assertEqual((len(vertices), len(faces)), (spec['vertices'], spec['faces']), name)
        self.assertTrue(all(x is False for x in factory.ADMISSION.values()))

    def copy_inputs(self, directory):
        config, observed = factory.load_request()
        for relative in observed:
            target = Path(directory)/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(factory.BASE/relative, target)
        return config, observed

    def test_same_geometry_changed_serialization_is_not_frozen_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, _ = self.copy_inputs(temporary)
            path = Path(temporary)/config['material_inputs']['F']['path']
            path.write_bytes(path.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError, 'SHA256_MISMATCH_F'):
                factory.load_request(temporary)

    def test_changed_unit_and_seed_request_rejected_before_native_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, _ = self.copy_inputs(temporary)
            config['units']['length_m_per_reference_binary64'] = 0.03
            config['seed']['reference_literal_coefficients_exact'][0] = '1'
            (Path(temporary)/'P20_native_request.json').write_text(json.dumps(config))
            with mock.patch.object(factory, 'verify_core_python', side_effect=AssertionError('must not import native')):
                with self.assertRaisesRegex(ValueError, 'REGISTERED_REQUEST_SHA256'):
                    factory.prepare_context(base=temporary)

    def test_same_byte_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, _ = self.copy_inputs(temporary)
            path = Path(temporary)/config['material_inputs']['D']['path']
            path.unlink()
            path.symlink_to(factory.BASE/config['material_inputs']['D']['path'])
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                factory.load_request(temporary)

    def test_mutation_after_initial_read_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, observed = self.copy_inputs(temporary)
            path = Path(temporary)/config['manifest']['path']
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'CHANGED_DURING_PREPARATION'):
                factory.recheck_inputs(observed, temporary)

    def test_signed_zero_and_tiny_distinct_vertices_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'input.obj'
            path.write_text('v -0.0 0 0\nv 5e-324 0 0\nv 0 1 0\nf 1 2 3\n')
            vertices, faces = factory.read_frozen_obj(path)
            self.assertEqual(math.copysign(1.0, vertices[0][0]), -1.0)
            self.assertNotEqual(vertices[0][0], vertices[1][0])
            self.assertEqual(faces, ((0, 1, 2),))

    def test_nonfinite_or_unregistered_obj_records_rejected(self):
        for value, expected in (('v inf 0 0\nf 1 2 3\n', 'NONFINITE'),
                                ('o repaired\n', 'UNREGISTERED'),
                                ('v 0 0 0\nf 1 1 1\n', 'REPEATED')):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary)/'bad.obj'
                path.write_text(value)
                with self.assertRaisesRegex(ValueError, expected):
                    factory.read_frozen_obj(path)


class CoreSourceAndBoundedReceiptTests(unittest.TestCase):
    def test_actual_frozen_core_python_bytes_match_independent_git_blobs(self):
        root = Path(os.environ.get('P20_CORE_SOURCE_ROOT', str(factory.BASE.parents[2])))
        source = root/'python/make_it_stand/__init__.py'
        self.assertTrue(source.is_file(), 'P20_CORE_SOURCE_ROOT must name the actual frozen core checkout')
        spec = importlib.util.spec_from_file_location('make_it_stand', source)
        config, _ = factory.load_request()
        # TEST_ONLY location injection; this observes source bytes, not native execution.
        with mock.patch.object(factory.importlib.util, 'find_spec', return_value=spec):
            actual_root, observed = factory.verify_core_python(config)
        self.assertEqual(actual_root.resolve(), root.resolve())
        self.assertEqual(observed, config['runtime_python_git_blobs'])
        self.assertEqual(len(observed), 77)

    def test_core_same_path_wrong_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root/'python/make_it_stand/__init__.py'
            source.parent.mkdir(parents=True)
            source.write_text('TEST_ONLY_WRONG_SOURCE = True\n')
            spec = importlib.util.spec_from_file_location('make_it_stand', source)
            config, _ = factory.load_request()
            with mock.patch.object(factory.importlib.util, 'find_spec', return_value=spec):
                with self.assertRaisesRegex(ValueError, 'CORE_SOURCE_BLOB_MISMATCH'):
                    factory.verify_core_python(config)

    def test_preparation_cannot_overwrite_an_existing_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'old-report.json'
            path.write_bytes(b'old failure retained\n')
            with self.assertRaisesRegex(ValueError, 'NO_OVERWRITE'):
                run_owned_preparation(path)
            self.assertEqual(path.read_bytes(), b'old failure retained\n')

    def test_failed_preparation_cannot_publish_real_pins_or_admission(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, pins = Path(temporary)/'report.json', Path(temporary)/'pins.json'
            test_resources = {'physical': {'SwapTotal_bytes': 1024}, 'TEST_ONLY': True}
            with mock.patch('p20_owned_material_audit.resource_observation', return_value=test_resources):
                code, report = run_owned_preparation(output, pins_output=pins)
            self.assertEqual(code, 2)
            self.assertFalse(report['completed'])
            self.assertFalse(pins.exists())
            self.assertFalse(any(report['admission'].values()))
            self.assertEqual(json.loads(output.read_text())['status'], 'P20_BOUNDED_PREPARATION_BLOCKED')

    def test_nonfinite_coefficient_json_never_gets_a_pin(self):
        with self.assertRaises(ValueError):
            factory.canonical_digest([float('nan')]*10)
        c = [1.0]+[0.0]*9
        expected_bytes = b'[1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]'
        self.assertEqual(factory.canonical_digest(c), hashlib.sha256(expected_bytes).hexdigest())

    def test_pins_write_failure_after_worker_is_not_a_successful_launch(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, pins = Path(temporary)/'report.json', Path(temporary)/'pins.json'
            worker_path = Path(temporary)/'report.worker.json'
            fixture = {'schema': owned_audit.SCHEMA, 'status': 'TEST_ONLY_NO_NATIVE_EXECUTION',
                       'completed': True, 'admission': dict(factory.ADMISSION),
                       'observed_six_pins': {}}
            child = mock.Mock()
            def simulated_wait(timeout=None):
                worker_path.write_text(json.dumps(fixture))
                return 0
            child.wait.side_effect = simulated_wait
            real_write = owned_audit._new_json
            def failed_pin_write(path, value):
                if Path(path) == pins:
                    raise OSError('TEST_ONLY_SIMULATED_PINS_WRITE_FAILURE')
                return real_write(path, value)
            with mock.patch.object(owned_audit.subprocess, 'Popen', return_value=child), \
                 mock.patch.object(owned_audit, '_new_json', side_effect=failed_pin_write), \
                 mock.patch.object(owned_audit, 'resource_observation', return_value={'physical': {'SwapTotal_bytes': 0}, 'TEST_ONLY': True}):
                code, report = run_owned_preparation(output, pins_output=pins)
            self.assertEqual(code, 2)
            self.assertTrue(report['worker_completed'])
            self.assertFalse(report['completed'])
            self.assertEqual(report['status'], 'P20_BOUNDED_PREPARATION_BLOCKED')
            self.assertFalse(pins.exists())
            self.assertFalse(any(report['admission'].values()))


if __name__ == '__main__':
    unittest.main()
