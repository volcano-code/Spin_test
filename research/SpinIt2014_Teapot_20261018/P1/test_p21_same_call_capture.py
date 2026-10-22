"""TEST_ONLY: passive capture protocol tests; zero project-native execution."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import p21_same_call_capture as capture


TEST_ONLY = 'TEST_ONLY_NO_NATIVE_EXECUTION'


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='w4-p21-TEST_ONLY-')
        self.root = Path(self.temporary.name)
        self.session = capture.CaptureSession(self.root / 'capture', {'TEST_ONLY': TEST_ONLY})

    def tearDown(self):
        self.temporary.cleanup()

    def events(self):
        return [json.loads(line) for line in (self.session.directory / 'events.jsonl').read_text().splitlines()]

    def manifest(self):
        return json.loads((self.session.directory / 'manifest.json').read_text())

    def test_operation_called_once_and_identical_source_object_returned(self):
        result = {'defined': True, 'vertices': np.array([[0., -0., 1.]]), 'TEST_ONLY': TEST_ONLY}
        calls = []
        def operation():
            calls.append('called')
            return result
        observed = self.session('source', operation)
        self.assertIs(observed, result)
        self.assertEqual(calls, ['called'])
        begin, end = self.events()
        self.assertEqual([begin['event'], end['event']], ['begin', 'completed'])
        artifact = end['artifacts'][0]
        data = (self.session.directory / artifact['path']).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), artifact['sha256'])
        self.assertEqual(json.loads(data)['vertices'][0][1].hex(), '-0x0.0p+0')

    def test_two_boolean_packets_have_distinct_ordinal_and_no_reexecution(self):
        calls = []
        packets = [{'TEST_ONLY': TEST_ONLY, 'exact_vertices': [], 'faces': [], 'which': i} for i in (1, 2)]
        for packet in packets:
            def operation(packet=packet):
                calls.append(packet['which'])
                return packet
            self.assertIs(self.session('boolean', operation), packet)
        completed = [row for row in self.events() if row['event'] == 'completed']
        self.assertEqual([row['ordinal'] for row in completed], [1, 2])
        self.assertEqual(calls, [1, 2])
        self.assertNotEqual(completed[0]['artifacts'][0]['path'], completed[1]['artifacts'][0]['path'])

    def test_actual_derivative_bits_shape_and_negative_zero_preserved(self):
        matrix = np.arange(100., dtype=np.float64).reshape(10, 10)
        matrix[2, 3] = -0.0
        self.assertIs(self.session('derivative', lambda: matrix), matrix)
        artifact = self.events()[-1]['artifacts'][0]
        data = (self.session.directory / artifact['path']).read_bytes()
        self.assertEqual(artifact['shape'], [10, 10])
        self.assertEqual(artifact['dtype'], '<f8')
        self.assertEqual(data, struct.pack('<100d', *matrix.flat))
        self.assertEqual(len(data), 800)

    def test_noncontiguous_derivative_preserves_row_major_values(self):
        matrix = np.arange(100., dtype=np.float64).reshape(10, 10).T
        self.session('derivative', lambda: matrix)
        artifact = self.events()[-1]['artifacts'][0]
        self.assertEqual((self.session.directory / artifact['path']).read_bytes(),
                         struct.pack('<100d', *matrix.flat))

    def test_integration_keeps_actual_ten_binary64_values(self):
        values = np.linspace(0., 1., 10, dtype=np.float64)
        self.assertIs(self.session('integration', lambda: values), values)
        artifact = self.events()[-1]['artifacts'][0]
        self.assertEqual(artifact['role'], 'integration_f64le')
        self.assertEqual((self.session.directory / artifact['path']).read_bytes(), struct.pack('<10d', *values))

    def test_material_exact_serialized_string_bytes_preserved(self):
        encoded = '{ "TEST_ONLY" : "' + TEST_ONLY + '", "negative_zero": -0.0 }'
        self.assertIs(self.session('material_attachment_serialization', lambda: encoded), encoded)
        artifact = self.events()[-1]['artifacts'][0]
        self.assertEqual((self.session.directory / artifact['path']).read_bytes(), encoded.encode('utf-8'))

    def test_opaque_boundary_never_repr_or_serialized(self):
        class Opaque:
            def __repr__(self):
                raise AssertionError('REPR_FORBIDDEN')
            def tolist(self):
                raise AssertionError('SERIALIZATION_FORBIDDEN')
        value = Opaque()
        self.assertIs(self.session('prepare_arithmetic_boundary', lambda: value), value)
        end = self.events()[-1]
        self.assertEqual(end['artifacts'], [])
        self.assertTrue(end['result_type'].endswith('.Opaque'))

    def test_operation_exception_preserved_and_durable_failed_phase(self):
        error = RuntimeError(TEST_ONLY)
        calls = []
        def operation():
            calls.append(1)
            raise error
        with self.assertRaises(RuntimeError) as caught:
            self.session('boolean', operation)
        self.assertIs(caught.exception, error)
        self.assertEqual(calls, [1])
        end = self.events()[-1]
        self.assertEqual(end['event'], 'failed')
        self.assertFalse(end['operation_returned'])
        self.assertEqual(self.manifest()['state'], 'stage_failed')
        self.assertEqual(self.manifest()['completed_stage_counts'], {})

    def test_serialization_error_does_not_reexecute_operation(self):
        calls = []
        def operation():
            calls.append(1)
            return {'bad': object()}
        with self.assertRaises(capture.CaptureRejected):
            self.session('boolean', operation)
        self.assertEqual(calls, [1])
        self.assertTrue(self.events()[-1]['operation_returned'])
        self.assertEqual(self.manifest()['state'], 'capture_failed')

    def test_wrong_derivative_shape_and_nonfinite_output_rejected(self):
        for index, matrix in enumerate((np.zeros((9, 10)), np.full((10, 10), np.nan),
                                        np.zeros((10, 10), dtype=np.float32))):
            with self.subTest(index=index), self.assertRaises(capture.CaptureRejected):
                self.session('derivative', lambda matrix=matrix: matrix)

    def test_duplicate_material_keys_rejected(self):
        with self.assertRaises(capture.CaptureRejected):
            self.session('material_attachment_serialization', lambda: '{"x":1,"x":2}')

    def test_existing_capture_directory_not_overwritten(self):
        before = (self.session.directory / 'manifest.json').read_bytes()
        with self.assertRaises(capture.CaptureRejected):
            capture.CaptureSession(self.session.directory)
        self.assertEqual((self.session.directory / 'manifest.json').read_bytes(), before)

    def test_symlink_target_or_ancestor_rejected(self):
        linked = self.root / 'linked'
        linked.symlink_to(self.session.directory, target_is_directory=True)
        for path in (linked, linked / 'new'):
            with self.subTest(path=path), self.assertRaises(capture.CaptureRejected):
                capture.CaptureSession(path)

    def test_relative_capture_directory_rejected(self):
        with self.assertRaises(capture.CaptureRejected):
            capture.CaptureSession('TEST_ONLY-relative')

    def test_context_is_exclusive_and_stage_cannot_precede_context(self):
        unbound = capture.CaptureSession(self.root / 'unbound')
        calls = []
        with self.assertRaises(capture.CaptureRejected):
            unbound('source', lambda: calls.append(1))
        self.assertEqual(calls, [])
        unbound.bind_context({'TEST_ONLY': TEST_ONLY})
        with self.assertRaises(capture.CaptureRejected):
            unbound.bind_context({'TEST_ONLY': 'CHANGED'})

    def test_preparation_failure_is_durable_without_final_context(self):
        unbound = capture.CaptureSession(self.root / 'preparation-failed')
        unbound.factory_event('begin')
        unbound.observe_preparation({'event': 'start', 'stage': 'owned_region_M'})
        unbound.observe_preparation({'event': 'failed', 'stage': 'owned_region_M', 'error': TEST_ONLY})
        unbound.factory_event('failed', error=TEST_ONLY)
        manifest = json.loads((unbound.directory / 'manifest.json').read_text())
        self.assertIsNone(manifest['context'])
        self.assertEqual(manifest['state'], 'factory_failed')
        self.assertFalse((unbound.directory / 'context.json').exists())
        self.assertTrue(all(value is False for value in manifest['admission'].values()))

    def test_manifest_event_hash_matches_durable_bytes(self):
        self.session('boolean', lambda: {'TEST_ONLY': TEST_ONLY})
        data = (self.session.directory / 'events.jsonl').read_bytes()
        manifest = self.manifest()
        self.assertEqual(manifest['events']['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(manifest['events']['bytes'], len(data))
        self.assertEqual(manifest['event_count'], len(self.events()))

    def test_event_tampering_refused_before_operation(self):
        with (self.session.directory / 'events.jsonl').open('ab') as stream:
            stream.write(b'CHANGED')
        calls = []
        with self.assertRaises(capture.CaptureRejected):
            self.session('source', lambda: calls.append(1))
        self.assertEqual(calls, [])

    def test_stage_path_escape_refused_before_operation(self):
        calls = []
        with self.assertRaises(capture.CaptureRejected):
            self.session('../source', lambda: calls.append(1))
        self.assertEqual(calls, [])

    def test_attempt_counters_are_labelled_and_not_promoted_to_completion(self):
        self.session.attach_counter_provider(lambda: {'source': 1, 'boolean': 0})
        with self.assertRaises(RuntimeError):
            self.session('source', lambda: (_ for _ in ()).throw(RuntimeError(TEST_ONLY)))
        end = self.events()[-1]
        self.assertEqual(end['evaluator_attempt_counts'], {'source': 1, 'boolean': 0})
        self.assertEqual(self.manifest()['operation_attempt_counts'], {'source': 1})
        self.assertEqual(self.manifest()['completed_stage_counts'], {})

    def test_factory_missing_environment_never_prepares_native(self):
        import p21_native_factory
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(capture.CaptureRejected, 'ENVIRONMENT_REQUIRED'):
                p21_native_factory.prepare_one()

    def test_factory_actual_policy_refusal_precedes_p20_preparation(self):
        import p20_m6_launch
        import p20_native_factory
        import p21_native_factory
        target = self.root / 'factory-refused'
        with patch.dict(os.environ, {capture.CAPTURE_ENVIRONMENT_VARIABLE: str(target)}), \
             patch.object(p20_m6_launch, 'linux_resources', return_value={'TEST_ONLY': TEST_ONLY}), \
             patch.object(p20_m6_launch, 'resource_admission', return_value='BLOCKED_INSUFFICIENT_PHYSICAL_RAM'), \
             patch.object(p20_native_factory, 'prepare_context', side_effect=AssertionError('NO_NATIVE_PREPARATION')):
            with self.assertRaisesRegex(capture.CaptureRejected, 'RESOURCE_REFUSAL'):
                p21_native_factory.prepare_one()
        manifest = json.loads((target / 'manifest.json').read_text())
        self.assertEqual(manifest['state'], 'factory_failed')
        self.assertIsNone(manifest['context'])


if __name__ == '__main__':
    unittest.main()
