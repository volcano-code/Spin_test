"""TEST_ONLY analytic fixtures; no native, Cherchi, factory or M6 execution."""
from __future__ import annotations

import copy
from fractions import Fraction
import json
from pathlib import Path
import struct
import tempfile
import unittest

import p21_replay_verify as verify


TEST_ONLY = 'TEST_ONLY_ANALYTIC_BOXES_NO_NATIVE_EXECUTION'


def box(x0, x1):
    points = [(x0, 0, 0), (x1, 0, 0), (x1, 1, 0), (x0, 1, 0),
              (x0, 0, 1), (x1, 0, 1), (x1, 1, 1), (x0, 1, 1)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
             (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
             (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return tuple(tuple(Fraction(x) for x in row) for row in points), tuple(faces)


def obj_data(boundary):
    points, faces = boundary
    rows = ['v ' + ' '.join(repr(float(x)) for x in p) for p in points]
    rows += ['f ' + ' '.join(str(i+1) for i in face) for face in faces]
    return ('\n'.join(rows) + '\n').encode('ascii')


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')


class AnalyticBundle:
    """Explicitly synthetic successful receipt shape for arithmetic tests only."""

    def __init__(self, root, *, complete=False):
        self.root = root
        self.boundaries = {'M': box(0, 2), 'F': box(0, 1), 'D': box(1, 2)}
        self.rows = []
        self.request = {'schema': 'W4_P20_TEAPOT_NATIVE_REQUEST_V1', 'TEST_ONLY': TEST_ONLY,
                        'units': {'fixed_density': 1, 'design_density': 1}, 'material_inputs': {}}
        for key, value in self.boundaries.items():
            raw = obj_data(value)
            self.add(key + '.obj', raw, 'material_' + key)
            self.request['material_inputs'][key] = {'sha256': verify.sha256(raw), 'vertices': 8, 'faces': 12}
        self.add('request.json', json_bytes(self.request), 'request')
        self.manifest = {'schema': verify.BUNDLE_SCHEMA, 'test_only': True, 'TEST_ONLY': TEST_ONLY,
                         'collection_completed': True, 'collection_errors': [],
                         'formal_executed': False, 'formal_exit_code': 3,
                         'source_w4_baseline_commit': verify.W4_BASELINE, 'w0_commit': verify.W0_COMMIT}
        self.launch = verify._launcher()
        self.formal = self.launch._base_report()
        self.formal.update(status='BLOCKED_INSUFFICIENT_PHYSICAL_RAM',
                           resources=self.resources(physical=10, effective=8))
        if complete:
            self.success()
        self.add('formal.json', json_bytes(self.formal), 'formal_report')
        self.freeze()

    @staticmethod
    def resources(physical=24, effective=24):
        return {'physical_memory_bytes': physical * 1024**3, 'effective_memory_bytes': effective * 1024**3,
                'swap_kib': 0, 'cgroup_memory_limits': [{'path': '/TEST_ONLY/memory.max', 'limit_bytes': effective * 1024**3}],
                'child_address_space_limit_bytes': min(effective, 24) * 1024**3}

    def add(self, path, raw, role):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        self.rows.append({'path': path, 'sha256': verify.sha256(raw), 'bytes': len(raw), 'role': role})

    def freeze(self):
        self.manifest['files'] = self.rows
        raw = json_bytes(self.manifest)
        (self.root / 'manifest.json').write_bytes(raw)
        self.manifest_sha = verify.sha256(raw)

    def rewrite_formal(self):
        raw = json_bytes(self.formal)
        (self.root / 'formal.json').write_bytes(raw)
        row = next(r for r in self.rows if r['role'] == 'formal_report')
        row.update(bytes=len(raw), sha256=verify.sha256(raw))
        self.freeze()

    def success(self):
        import numpy as np
        from p21_same_call_capture import CaptureSession
        self.manifest.update(formal_executed=True, formal_exit_code=0)
        retained, cavity = box(1, Fraction(3, 2)), box(Fraction(3, 2), 2)
        c = [1.] + [0.] * 9
        pins = {key: verify.sha256((TEST_ONLY + key).encode()) for key in verify.PIN_KEYS}
        pins['c_sha256'] = verify.digest(c)
        pins_raw = json_bytes(pins)
        self.add('pins.json', pins_raw, 'pins')
        raw = {key: verify.exact_raw10(*value) for key, value in
               {**self.boundaries, 'R': retained, 'C': cavity}.items()}
        tokens = lambda boundary: [verify.encode(row) for row in boundary[0]]
        packet = lambda boundary: {'vertices': [[float(x) for x in row] for row in boundary[0]],
                                   'faces': [list(f) for f in boundary[1]], 'exact_vertices': tokens(boundary),
                                   'construction_records': [], 'backend': verify.CHERCHI + '-inprocess-v1'}
        rp, cp = packet(retained), packet(cavity)
        source = {'defined': True, 'side_selection_defined': True, 'interior_is_positive': True,
                  'vertices': rp['vertices'], 'faces': rp['faces'], 'TEST_ONLY': TEST_ONLY}
        derivative = np.eye(10, dtype=np.float64)
        derivative[0, 1] = -0.0
        original_partition = {'whole_digest': '1'*64, 'part_digests': ['2'*64, '3'*64]}
        normalization = {'origin': [0., 0., 0.], 'L': 1., 'R': 1.,
                         'axes': [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]}
        context = {'c': c, 'pins': pins, 'normalization': normalization,
                   'request': {'target_origin': [0., 0., 0.], 'target_axes': normalization['axes'], 'material_density': 1.},
                   'fixed': list(map(float, raw['F'])), 'problem_input_digest': pins['problem_input_digest'],
                   'problem_identity': {'normalization': normalization, 'partition': original_partition},
                   'TEST_ONLY': TEST_ONLY}
        material = {'quadric_coefficients': c, 'evaluation_map_identity': pins['context_sha256'],
                    'boolean_backend_identity': verify.CHERCHI + ':TEST_ONLY', 'derivative_defined': True,
                    'boolean_operation': 'intersection', 'quadric_source_vertices': rp['vertices'],
                    'quadric_source_faces': rp['faces'],
                    'quadric_source_identity': verify.digest({'vertices': rp['vertices'], 'faces': rp['faces'], 'coefficients': c}),
                    'material_proof': {'exact_vertices': rp['exact_vertices'], 'construction_records': [],
                                       'orientation': {'flipped_face_indices': []}},
                    'variable_faces': rp['faces'], 'variable_rational_vertices': rp['exact_vertices'],
                    'variable_vertices': rp['vertices'], 'geometry_hash': verify.digest({'vertices': rp['exact_vertices'], 'faces': rp['faces']}),
                    'moment_jacobian': derivative.tolist(), 'variable_raw_moments': list(map(float, raw['R'])),
                    'raw_moments': [float(f+r) for f, r in zip(raw['F'], raw['R'])], 'TEST_ONLY': TEST_ONLY}
        capture = CaptureSession(self.root / 'capture', context)
        capture.mark_factory_ready()
        capture('source', lambda: source)
        capture('boolean', lambda: rp)
        capture('intersection_motion', lambda: np.zeros((8, 3, 10), dtype=np.float64))
        capture('derivative', lambda: derivative)
        capture('integration', lambda: np.asarray(material['variable_raw_moments'], dtype=np.float64))
        capture('material_attachment_serialization', lambda: json.dumps(material, sort_keys=True, allow_nan=False))
        capture('boolean', lambda: cp)
        capture('integration', lambda: np.asarray(list(map(float, raw['C'])), dtype=np.float64))
        for path in sorted((self.root / 'capture').iterdir()):
            role = {'manifest.json': 'capture_manifest', 'context.json': 'capture_context',
                    'events.jsonl': 'capture_events'}.get(path.name, 'capture_artifact')
            data = path.read_bytes()
            self.rows.append({'path': 'capture/' + path.name, 'sha256': verify.sha256(data), 'bytes': len(data), 'role': role})
        m4 = {'native_execution_observed': True, 'native_region_proved': True, 'mathematical_replay_passed': True,
              'training_admissible': False, 'source_geometry_sha256': material['geometry_hash'],
              'source_quadric_sha256': material['quadric_source_identity'], 'TEST_ONLY': TEST_ONLY}
        for key, pin in {'native_source_sha256': 'native_sha256', 'native_bridge_sha256': 'bridge_sha256',
                         'native_adapter_sha256': 'adapter_sha256', 'frozen_native_c_sha256': 'c_sha256',
                         'frozen_problem_digest': 'problem_input_digest', 'frozen_context_sha256': 'context_sha256'}.items():
            m4[key] = pins[pin]
        predicates = []
        for label, whole, parts in [('fixed_plus_design', '1'*64, ['2'*64, '3'*64]),
                                    ('design_cut', '3'*64, ['4'*64, '5'*64]),
                                    ('full_outer', '1'*64, ['2'*64, '4'*64, '5'*64])]:
            partition_digest = verify.digest({'TEST_ONLY': label})
            facts = {'completed': True, 'complete_partition': True, 'union_equals_whole': True,
                     'no_positive_volume_overlap': True, 'missing_whole_content': False, 'excess_union_content': False,
                     'part_subset_whole': [True]*len(parts), 'positive_volume_overlap_pairs': [],
                     'partition_digest': partition_digest, 'whole_digest': whole, 'part_digests': parts, 'TEST_ONLY': TEST_ONLY}
            predicates.append({'label': label, 'part_count': len(parts), 'partition_digest': partition_digest,
                               'native_predicate_facts': facts})
        evidence = {'schema': self.launch.M6_SCHEMA, 'native_full_partition_certified': True,
                    'retained_plus_cavity_equals_design_r10_exact': True, 'fixed_plus_retained_density_weighted_moments_verified': True,
                    'training_admissible': False, 'smooth_derivative_certified': False, 'newton_terminal_certified': False,
                    'scope': 'EXACT_REPRESENTED_POLYHEDRAL_SETS_AND_R10_ONLY', 'observed_native_source_calls': 1,
                    'observed_native_boolean_calls': 2, 'complement_additional_source_calls': 0, 'complement_additional_boolean_calls': 1,
                    'exact_partition_predicates': predicates, 'M5_evidence': {'schema': 'W0_M5_LIVE_W0_W2_PARITY_V1',
                    'training_admissible': False, 'm4_native_evidence': m4, 'w2_exact_math_reference': {'exact_r10': verify.encode(raw['R'])}},
                    'TEST_ONLY': TEST_ONLY}
        snapshot = {'factory_file': {'sha256': '6'*64}, 'TEST_ONLY': TEST_ONLY}
        module_files = {key: {'sha256': pins[key], 'path': '/TEST_ONLY/' + key}
                        for key in ('native_sha256', 'bridge_sha256', 'adapter_sha256')}
        worker = self.launch._base_report(self.launch.WORKER_SCHEMA)
        worker.update(run_nonce='7'*32, resources=self.resources(), native_full_partition_certified=True,
                      source_files_unchanged=True, source_snapshot_sha256=verify.digest(snapshot),
                      pins_file_sha256=verify.sha256(pins_raw), m6_evidence=evidence, native_module_files=module_files,
                      worker_started=True, native_audit_invoked=True, factory_imported=True,
                      native_call_counts_observed={'source': 1, 'boolean': 2},
                      child_limits={'RLIMIT_AS_soft_bytes': 24*1024**3, 'RLIMIT_AS_hard_bytes': 24*1024**3,
                                    'wall_alarm_seconds': 3600},
                      status='REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE', TEST_ONLY=TEST_ONLY)
        stdout = (self.launch.RESULT_PREFIX + verify.canonical(worker) + '\n').encode()
        self.add('worker.stdout', stdout, 'worker_stdout')
        self.add('worker.stderr', b'', 'worker_stderr')
        child = {'returncode': 0, 'timed_out': False, 'worker_report': worker,
                 'stdout_log': {'sha256': verify.sha256(stdout), 'bytes': len(stdout)},
                 'stderr_log': {'sha256': verify.sha256(b''), 'bytes': 0}}
        self.formal.update(status='REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE',
                           resources=self.resources(), native_full_partition_certified=True, worker_started=True,
                           native_audit_invoked=True, factory_imported=True, source_files_unchanged=True,
                           native_call_counts_observed={'source': 1, 'boolean': 2},
                           source_snapshot=snapshot, source_snapshot_sha256=verify.digest(snapshot),
                           external_pins_sha256=verify.sha256(pins_raw), pins_file_sha256=verify.sha256(pins_raw),
                           external_factory_sha256='6'*64, child_process=child, m6_evidence=evidence,
                           native_module_files=module_files, TEST_ONLY=TEST_ONLY)


class ArithmeticTests(unittest.TestCase):
    def test_unit_box_has_analytic_ten_moments(self):
        self.assertEqual(verify.exact_raw10(*box(0, 1)),
                         (Fraction(1), Fraction(1, 2), Fraction(1, 2), Fraction(1, 2),
                          Fraction(1, 3), Fraction(1, 3), Fraction(1, 3),
                          Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)))

    def test_exact_two_piece_partition(self):
        whole = verify.exact_raw10(*box(1, 2))
        left = verify.exact_raw10(*box(1, Fraction(3, 2)))
        right = verify.exact_raw10(*box(Fraction(3, 2), 2))
        self.assertEqual(tuple(a+b for a, b in zip(left, right)), whole)

    def test_inward_cavity_shell_keeps_negative_contribution(self):
        outer = box(0, 3)
        inner = box(1, 2)
        points = outer[0] + inner[0]
        faces = outer[1] + tuple((a+8, c+8, b+8) for a, b, c in inner[1])
        moments = verify.exact_raw10(points, faces)
        self.assertEqual(moments[0], 2)

    def test_local_winding_is_replayed_without_coordinate_changes(self):
        points, faces = box(0, 1)
        broken = list(faces)
        a, b, c = broken[4]
        broken[4] = (a, c, b)
        normalized, flips = verify.orient_packet(points, broken)
        self.assertEqual(normalized, faces)
        self.assertEqual(flips, [4])

    def test_open_mesh_rejected(self):
        points, faces = box(0, 1)
        with self.assertRaisesRegex(verify.VerificationRejected, 'OPEN_OR_NONMANIFOLD'):
            verify.exact_raw10(points, faces[:-1])

    def test_duplicate_triangle_rejected(self):
        points, faces = box(0, 1)
        with self.assertRaisesRegex(verify.VerificationRejected, 'DUPLICATE_TRIANGLE'):
            verify.exact_raw10(points, (*faces, faces[0]))

    def test_bool_face_index_rejected(self):
        points, faces = box(0, 1)
        bad = list(faces)
        bad[0] = (False, 2, 1)
        with self.assertRaisesRegex(verify.VerificationRejected, 'FACE_INDEX_INVALID'):
            verify.exact_raw10(points, bad)

    def test_binary_rational_tokens_are_exact(self):
        self.assertEqual(verify.fraction('-0b11/0b100'), Fraction(-3, 4))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(verify.VerificationRejected, 'DUPLICATE_JSON'):
            verify.strict_json('{"a":0,"a":1}')

    def test_nan_json_rejected(self):
        with self.assertRaisesRegex(verify.VerificationRejected, 'NONFINITE_JSON'):
            verify.strict_json('{"a":NaN}')

    def test_overflowing_json_exponent_rejected(self):
        with self.assertRaisesRegex(verify.VerificationRejected, 'NONFINITE_JSON_EXPONENT'):
            verify.strict_json('{"a":1e999}')

    def test_packed_float_preserves_negative_zero(self):
        self.assertNotEqual(verify.packed([-0.], 1), verify.packed([0.], 1))

    def test_scientific_admission_true_rejected(self):
        with self.assertRaisesRegex(verify.VerificationRejected, 'FORBIDDEN_SCIENTIFIC_RELEASE'):
            verify.reject_scientific_release({'nested': {'W2_teacher_training_allowed': True}})


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='p21-TEST_ONLY-replay-')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_blocked_fixture_does_not_claim_formal_or_cut_pass(self):
        case = AnalyticBundle(self.root)
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertEqual(result['status'], 'TEST_ONLY_BLOCKED_FORMAL_M6_NOT_EXECUTED', result)
        self.assertFalse(result['formal_M6_receipt_success'])
        self.assertFalse(result['same_call_100_Jacobian_bytes_match'])
        self.assertTrue(result['frozen_MFD_arithmetic']['all_ten_residuals_zero'])

    def test_production_rejects_test_only_bundle(self):
        case = AnalyticBundle(self.root)
        result = verify.verify_bundle(self.root, case.manifest_sha)
        self.assertEqual(result['status'], 'REJECTED')
        self.assertIn('TEST_ONLY', result['error'])

    def test_external_manifest_digest_required(self):
        AnalyticBundle(self.root)
        result = verify.verify_bundle(self.root, '0'*64, allow_test_only=True)
        self.assertIn('EXTERNAL_MANIFEST_SHA_MISMATCH', result['error'])

    def test_archived_input_tampering_rejected(self):
        case = AnalyticBundle(self.root)
        with (self.root / 'M.obj').open('ab') as f:
            f.write(b'# tamper\n')
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertIn('BUNDLE_FILE_HASH_MISMATCH', result['error'])

    def test_relative_path_escape_rejected(self):
        case = AnalyticBundle(self.root)
        case.rows[0]['path'] = '../M.obj'
        case.freeze()
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertIn('ARCHIVE_PATH_ESCAPE', result['error'])

    def test_symlink_artifact_rejected(self):
        case = AnalyticBundle(self.root)
        original = (self.root / 'M.obj').read_bytes()
        (self.root / 'M.obj').unlink()
        (self.root / 'copy.obj').write_bytes(original)
        (self.root / 'M.obj').symlink_to(self.root / 'copy.obj')
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertIn('ARCHIVE_SYMLINK_REJECTED', result['error'])

    def test_nonexecution_cannot_hide_started_worker(self):
        case = AnalyticBundle(self.root)
        case.formal['worker_started'] = True
        data = json_bytes(case.formal)
        (self.root / 'formal.json').write_bytes(data)
        row = next(r for r in case.rows if r['role'] == 'formal_report')
        row.update(bytes=len(data), sha256=verify.sha256(data))
        case.freeze()
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertIn('NONEXECUTION_ENVELOPE_CONTRADICTION', result['error'])

    def test_collection_failure_cannot_claim_completed_review(self):
        case = AnalyticBundle(self.root)
        case.manifest.update(collection_completed=False, collection_errors=['TEST_ONLY resource observation failed'])
        case.freeze()
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertEqual(result['status'], 'INPUT_INCOMPLETE_COLLECTION')
        self.assertFalse(result['completed'])

    def test_parent_worker_nonce_must_match_archived_stdout(self):
        case = AnalyticBundle(self.root, complete=True)
        case.formal['child_process']['worker_report']['run_nonce'] = '8'*32
        case.rewrite_formal()
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertIn('WORKER_STDOUT_ENVELOPE_MISMATCH', result['error'])

    def test_bool_native_counter_is_not_an_integer_count(self):
        case = AnalyticBundle(self.root, complete=True)
        case.formal['native_call_counts_observed']['source'] = True
        case.rewrite_formal()
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertIn('ENVELOPE_NATIVE_COUNTS_MISMATCH', result['error'])

    def test_complete_analytic_capture_replays_but_cannot_prove_native(self):
        case = AnalyticBundle(self.root, complete=True)
        result = verify.verify_bundle(self.root, case.manifest_sha, allow_test_only=True)
        self.assertEqual(result['status'], 'TEST_ONLY_ARITHMETIC_REPLAY_CONSISTENT_NO_NATIVE_PROOF', result)
        self.assertTrue(result['same_call_100_Jacobian_bytes_match'])
        self.assertTrue(result['artifact_arithmetic_replay_passed'])
        self.assertFalse(result['native_execution_independently_proved'])
        self.assertFalse(result['numerical_J_correctness_proved'])
        self.assertEqual(result['replay']['D_minus_R_minus_C_exact'], ['0/1']*10)
        self.assertEqual(result['replay']['M_minus_F_minus_R_minus_C_exact'], ['0/1']*10)

    def test_derivative_bytes_changed_inside_capture_rejected(self):
        case = AnalyticBundle(self.root, complete=True)
        bundle = verify.Bundle(self.root, case.manifest_sha, True)
        context, stages, artifact = verify._capture(bundle)
        pins = bundle.json_role('pins')
        def altered(stage, ordinal, role):
            row, raw = artifact(stage, ordinal, role)
            if role == 'derivative_f64le':
                values = list(struct.unpack('<100d', raw))
                values[1] = 0.  # Only the sign bit changes; numeric equality would miss it.
                raw = struct.pack('<100d', *values)
            return row, raw
        with self.assertRaisesRegex(verify.VerificationRejected, 'SAME_CALL_100_JACOBIAN_BYTES_MISMATCH'):
            verify._replay_cut(context, altered, stages, case.boundaries, pins, case.formal['m6_evidence'], test_only=True)


if __name__ == '__main__':
    unittest.main()
