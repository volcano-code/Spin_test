"""Portable unit fixtures; no real native executable or geometry job is run.

Process and source-query doubles are explicit fixtures. Their temporary reports
are never research evidence. Real native smoke is a separate serial CI command.
"""
from contextlib import ExitStack
from fractions import Fraction as Q
import hashlib
from itertools import product
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import p19_native_smoke as smoke


def boolean_cells(operation):
    a = set(product(range(2), repeat=3))
    b = set(product(range(1, 3), repeat=3))
    return {'union': a | b, 'intersection': a & b, 'subtraction': a-b}[operation]


def write_voxel_boundary(path, cells, shift=(0, 0, 0)):
    """Independent fixture: keep the outward unit-cell faces lacking neighbors."""
    directions = ((0, 0, -1), (0, 0, 1), (0, -1, 0), (0, 1, 0), (-1, 0, 0), (1, 0, 0))
    quads = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5))
    vertices, indices, faces = [], {}, []
    for x, y, z in sorted(cells):
        cube = ((x, y, z), (x+1, y, z), (x+1, y+1, z), (x, y+1, z),
                (x, y, z+1), (x+1, y, z+1), (x+1, y+1, z+1), (x, y+1, z+1))
        for direction, quad in zip(directions, quads):
            if tuple(c+d for c, d in zip((x, y, z), direction)) in cells:
                continue
            ids = []
            for i in quad:
                point = tuple(c+s for c, s in zip(cube[i], shift))
                if point not in indices:
                    indices[point] = len(vertices)
                    vertices.append(point)
                ids.append(indices[point])
            faces += [(ids[0], ids[1], ids[2]), (ids[0], ids[2], ids[3])]
    Path(path).write_text(''.join('v %s %s %s\n' % p for p in vertices)
                          + ''.join('f %d %d %d\n' % tuple(i+1 for i in f) for f in faces))


class TemporaryFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)


class ExactAnalyticalTests(TemporaryFixture):
    def test_all_thirty_comparisons_use_full_literal_analytical_vectors(self):
        expected = {
            'union': [Q(15), *[Q(45, 2)]*3, *[Q(43)]*3, *[Q(151, 4)]*3],
            'intersection': [Q(1), *[Q(3, 2)]*3, *[Q(7, 3)]*3, *[Q(9, 4)]*3],
            'subtraction': [Q(7), *[Q(13, 2)]*3, *[Q(25, 3)]*3, *[Q(23, 4)]*3],
        }
        self.assertEqual(smoke.expected_boolean_moments(), expected)
        for operation, wanted in expected.items():
            with self.subTest(operation=operation):
                path = self.root/(operation+'.obj')
                write_voxel_boundary(path, boolean_cells(operation))
                actual, topology = smoke.exact_mesh_moments(path)
                self.assertEqual(actual, wanted)
                self.assertTrue(topology['analytical_box_boundary_topology_pass'])
                self.assertEqual(topology['noncycle_vertex_links'], 0)

    def test_translated_shape_has_same_volume_but_fails_other_moments(self):
        path = self.root/'volume-only-fake.obj'
        write_voxel_boundary(path, boolean_cells('subtraction'), shift=(10, 0, 0))
        actual, topology = smoke.exact_mesh_moments(path)
        expected = smoke.expected_boolean_moments()['subtraction']
        self.assertEqual(actual[0], expected[0])
        self.assertNotEqual(actual[1:], expected[1:])
        self.assertTrue(topology['analytical_box_boundary_topology_pass'])

    def test_parser_uses_saved_binary64_not_exact_decimal_tokens(self):
        path = self.root/'binary64.obj'
        path.write_text('v 0.1 0 0\nv 1 0 0\nv 0 1 0\nf -3 -2 -1\n')
        vertices, faces = smoke.read_binary64_obj(path)
        self.assertEqual(vertices[0][0], Q.from_float(.1))
        self.assertNotEqual(vertices[0][0], Q(1, 10))
        self.assertEqual(faces, [(0, 1, 2)])

    def test_invalid_obj_records_and_degenerate_triangles_are_rejected(self):
        prefix = 'v 0 0 0\nv 1 0 0\nv 0 1 0\n'
        invalid = [prefix+'f 0 2 3\n', prefix+'f 1 2 9\n', prefix+'f 1 1 3\n',
                   prefix+'f 1 2 3 1\n', prefix+'l 1 2\n', 'v nan 0 0\n',
                   'v inf 0 0\n', 'v 0 0\n', '# empty\n',
                   'v 0 0 0\nv 1 0 0\nv 2 0 0\nf 1 2 3\n']
        for i, data in enumerate(invalid):
            with self.subTest(case=i):
                path = self.root/f'invalid-{i}.obj'
                path.write_text(data)
                with self.assertRaises(ValueError):
                    smoke.exact_mesh_moments(path)

    def test_open_and_duplicate_boundaries_do_not_pass_topology(self):
        path = self.root/'box.obj'
        smoke.write_box(path, 0, 2)
        original = path.read_text()
        path.write_text('\n'.join(original.splitlines()[:-1])+'\n')
        _, topology = smoke.exact_mesh_moments(path)
        self.assertFalse(topology['closed_edge_incidence_two'])
        self.assertFalse(topology['analytical_box_boundary_topology_pass'])
        path.write_text(original+original.splitlines()[-1]+'\n')
        _, topology = smoke.exact_mesh_moments(path)
        self.assertGreater(topology['duplicate_indexed_face_supports'], 0)
        self.assertFalse(topology['analytical_box_boundary_topology_pass'])

    def test_box_writer_and_json_are_new_only(self):
        path = self.root/'old-evidence'
        path.write_bytes(b'preserve me')
        with self.assertRaises(FileExistsError):
            smoke.write_box(path, 0, 2)
        with self.assertRaises(FileExistsError):
            smoke.write_new_json(path, {'spoof': True})
        self.assertEqual(path.read_bytes(), b'preserve me')


class SourceIdentityFixtureTests(TemporaryFixture):
    """Fake Git responses plus real independent hashing of tiny fixture files."""
    def setUp(self):
        super().setUp()
        self.binary = self.root/'w4_cherchi_reference_native'
        self.binary.write_bytes(b'UNIT TEST ONLY; NOT AN EXECUTABLE IMPLEMENTATION\n')
        self.binary.chmod(0o755)
        self.wrapper = self.root/'CMakeLists.txt'
        self.wrapper.write_bytes(b'# explicit unit-test CMake fixture\n')
        self.source = self.root/'source'
        self.source.mkdir()
        self.bat = sorted(smoke.PINNED_CRLF_CHECKOUT_PATHS)[0]
        self.base_bytes = {'main.cpp': b'unit-test original main\n',
                           'code/booleans.cpp': b'unit-test original exporter\n',
                           'dependency/header.h': b'unit-test dependency\n',
                           self.bat: b'echo unit-test Windows script\n'}
        for rel, data in self.base_bytes.items():
            path = self.source/rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data.replace(b'\n', b'\r\n') if rel == self.bat else data)
        self.apap_bytes = b'unit-test APAP-only exporter\n'
        self.apap_diff = b'UNIT TEST FULL HEAD PATCH; NOT REAL UPSTREAM PATCH\n'
        self.head = smoke.BASE_COMMIT
        self.status, self.diff = b'', b''
        self.tree = b''.join(b'100644 blob '+smoke.git_blob(data).encode()+b'\t'+rel.encode()+b'\0'
                             for rel, data in self.base_bytes.items())
        pins = {'MAIN_GIT_BLOB': smoke.git_blob(self.base_bytes['main.cpp']),
                'BASE_BOOLEANS_GIT_BLOB': smoke.git_blob(self.base_bytes['code/booleans.cpp']),
                'APAP_BOOLEANS_GIT_BLOB': smoke.git_blob(self.apap_bytes),
                'WRAPPER_GIT_BLOB': smoke.git_blob(self.wrapper.read_bytes()),
                'APAP_PATCH_SHA256': hashlib.sha256(self.apap_diff).hexdigest()}
        for name, value in pins.items():
            self.stack.enter_context(patch.object(smoke, name, value))
        self.stack.enter_context(patch.object(smoke, '_git_bytes', side_effect=self.fake_git))

    def fake_git(self, source, *args):
        self.assertEqual(source, self.source.resolve())
        if args == ('rev-parse', 'HEAD'):
            return self.head.encode()+b'\n'
        if args[0] == 'status':
            return self.status
        if args[0] == 'ls-tree':
            return self.tree
        if args[0] == 'diff':
            self.assertIn('HEAD', args)
            self.assertIn('--no-ext-diff', args)
            self.assertIn('--full-index', args)
            return self.diff
        raise AssertionError('Unexpected Git query in fixture')

    def identity(self, mode='unmodified'):
        return smoke.validate_native_identity(self.binary, self.source, mode, self.wrapper)

    def enable_apap(self):
        (self.source/'code/booleans.cpp').write_bytes(self.apap_bytes)
        self.status = b' M code/booleans.cpp\n'
        self.diff = self.apap_diff

    def test_unmodified_identity_rehashes_all_sources_without_claiming_build_proof(self):
        result = self.identity()
        self.assertEqual(result['tracked_file_count'], 4)
        self.assertTrue(result['all_tracked_files_independently_rehashed'])
        self.assertEqual(result['pinned_windows_script_checkout_eol_normalizations'], [self.bat])
        self.assertFalse(result['source_to_binary_compilation_chain_proven_by_this_check'])
        before = result['binary_sha256']
        self.binary.write_bytes(b'Another explicitly test-only build fixture\n')
        self.assertNotEqual(self.identity()['binary_sha256'], before)

    def test_valid_apap_requires_exact_patch_and_has_explicit_patched_classification(self):
        self.enable_apap()
        result = self.identity('apap')
        self.assertEqual(result['full_head_diff_sha256'], smoke.APAP_PATCH_SHA256)
        self.assertEqual(result['booleans_git_blob'], smoke.APAP_BOOLEANS_GIT_BLOB)
        self.assertEqual(result['classification'], 'PATCHED_APAP_EXPORTER_NOT_UNMODIFIED_REFERENCE')

    def test_wrong_head_wrapper_main_pin_and_mode_are_rejected(self):
        self.head = '0'*40
        with self.assertRaisesRegex(ValueError, 'COMMIT_MISMATCH'):
            self.identity()
        self.head = smoke.BASE_COMMIT
        with patch.object(smoke, 'MAIN_GIT_BLOB', '0'*40), self.assertRaisesRegex(ValueError, 'MAIN_BLOB'):
            self.identity()
        self.wrapper.write_bytes(b'unregistered CMake wrapper')
        with self.assertRaisesRegex(ValueError, 'WRAPPER_MISMATCH'):
            self.identity()
        with self.assertRaisesRegex(ValueError, 'MODE'):
            self.identity('cgal')

    def test_missing_or_nonexecutable_binary_is_rejected(self):
        self.binary.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'EXECUTABLE_REQUIRED'):
            self.identity()
        self.binary.unlink()
        with self.assertRaisesRegex(ValueError, 'EXECUTABLE_REQUIRED'):
            self.identity()

    def test_dirty_unmodified_source_and_additional_apap_change_are_rejected(self):
        self.status = b' M dependency/header.h\n'
        with self.assertRaisesRegex(ValueError, 'SOURCE_DIRTY'):
            self.identity()
        self.enable_apap()
        self.status += b' M dependency/header.h\n'
        with self.assertRaisesRegex(ValueError, 'CHANGE_SET'):
            self.identity('apap')

    def test_hidden_dependency_mutation_is_rejected_even_with_clean_git_status(self):
        (self.source/'dependency/header.h').write_bytes(b'assume-unchanged must not hide this')
        with self.assertRaisesRegex(ValueError, 'SOURCE_BYTES_MISMATCH'):
            self.identity()

    def test_wrong_full_apap_diff_and_wrong_exporter_bytes_are_rejected(self):
        self.enable_apap()
        self.diff += b'not the allowed full diff'
        with self.assertRaisesRegex(ValueError, 'PATCH_SHA'):
            self.identity('apap')
        self.diff = self.apap_diff
        (self.source/'code/booleans.cpp').write_bytes(b'other exporter alteration')
        with self.assertRaisesRegex(ValueError, 'SOURCE_BYTES'):
            self.identity('apap')

    def test_eol_exception_does_not_permit_changed_windows_script_or_cpp(self):
        (self.source/self.bat).write_bytes(b'echo changed body\r\n')
        with self.assertRaisesRegex(ValueError, 'SOURCE_BYTES'):
            self.identity()
        (self.source/self.bat).write_bytes(self.base_bytes[self.bat])
        (self.source/'main.cpp').write_bytes(self.base_bytes['main.cpp'].replace(b'\n', b'\r\n'))
        with self.assertRaisesRegex(ValueError, 'SOURCE_BYTES'):
            self.identity()

    def test_hidden_source_mode_or_file_kind_changes_are_rejected(self):
        dep = self.source/'dependency/header.h'
        dep.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'MODE_CHANGED'):
            self.identity()
        dep.unlink()
        dep.symlink_to(self.source/'main.cpp')
        with self.assertRaisesRegex(ValueError, 'KIND_CHANGED'):
            self.identity()


class ProcessFixtureTests(TemporaryFixture):
    """Mock child processes write voxel fixtures, never real Cherchi outputs."""
    def setUp(self):
        super().setUp()
        self.binary = self.root/'w4_cherchi_reference_native'
        self.binary.write_bytes(b'UNIT-TEST PROCESS FIXTURE ONLY\n')
        self.binary.chmod(0o755)
        self.wrapper = self.root/'CMakeLists.txt'
        self.wrapper.write_bytes(b'UNIT-TEST WRAPPER FIXTURE\n')
        self.source = self.root/'source'
        self.source.mkdir()
        self.out = self.root/'new-output'
        self.calls = []
        self.returncode = 0
        self.writes_output = True
        self.shift = (0, 0, 0)
        self.hook = None
        self.identity = {'binary_path': str(self.binary), 'binary_sha256': smoke.sha256(self.binary),
                         'wrapper_path': str(self.wrapper), 'wrapper_sha256': smoke.sha256(self.wrapper),
                         'classification': 'EXPLICIT_UNIT_TEST_FIXTURE_NOT_REAL_NATIVE_AUTHENTICATION',
                         'unit_test_fixture_only': True}
        self.auth = self.stack.enter_context(patch.object(smoke, 'validate_native_identity', return_value=dict(self.identity)))
        self.process = self.stack.enter_context(patch.object(smoke.subprocess, 'run', side_effect=self.fake_process))

    def fake_process(self, command, **kwargs):
        self.assertEqual(command[0], str(self.binary))
        self.assertIn(command[1], smoke.OPERATIONS)
        self.calls.append(command)
        if self.writes_output:
            write_voxel_boundary(command[-1], boolean_cells(command[1]), shift=self.shift)
        if self.hook:
            self.hook(command)
        return subprocess.CompletedProcess(command, self.returncode, b'UNIT TEST PROCESS DOUBLE\n', b'')

    def run_fixture(self):
        return smoke.run_smoke(self.binary, self.source, 'unmodified', self.out, wrapper=self.wrapper)

    def test_success_requires_three_calls_and_thirty_exact_comparisons(self):
        result = self.run_fixture()
        self.assertTrue(result['passed'])
        self.assertEqual(result['native_operation_calls'], 3)
        self.assertEqual(result['exact_moment_comparisons'], 30)
        self.assertEqual(result['exact_moment_comparisons_equal'], 30)
        self.assertEqual([command[1] for command in self.calls], list(smoke.OPERATIONS))
        self.assertTrue(all(value is False for value in result['scientific_flags'].values()))
        self.assertTrue(result['all_frozen_artifacts_unchanged'])
        self.assertEqual(json.loads((self.out/'analytical-smoke-report.json').read_text()), result)
        for check in result['checks']:
            self.assertTrue(check['inputs_unchanged'])
            self.assertEqual(check['output_sha256'], smoke.sha256(self.out/check['output_file']))
            self.assertEqual(len(check['exact_comparisons']), 10)

    def test_volume_only_fake_success_is_rejected_by_other_moments(self):
        self.shift = (10, 0, 0)
        result = self.run_fixture()
        self.assertFalse(result['passed'])
        self.assertEqual(result['native_operation_calls'], 3)
        self.assertEqual(result['exact_moment_comparisons'], 30)
        self.assertLess(result['exact_moment_comparisons_equal'], 30)
        for check in result['checks']:
            self.assertTrue(check['exact_comparisons']['1'])
            self.assertFalse(check['all_ten_moments_exactly_equal'])

    def test_bad_identity_rejects_before_any_process_or_output_directory(self):
        self.auth.side_effect = ValueError('UNIT_TEST_BAD_IDENTITY')
        with self.assertRaisesRegex(ValueError, 'BAD_IDENTITY'):
            self.run_fixture()
        self.assertEqual(self.process.call_count, 0)
        self.assertFalse(self.out.exists())

    def test_existing_output_directory_is_never_reused(self):
        self.out.mkdir()
        old = self.out/'old-evidence.json'
        old.write_text('preserve')
        with self.assertRaises(FileExistsError):
            self.run_fixture()
        self.assertEqual(old.read_text(), 'preserve')
        self.assertEqual(self.process.call_count, 0)

    def test_nonzero_exit_and_zero_exit_without_output_both_fail(self):
        for i, (returncode, writes) in enumerate(((4, True), (0, False))):
            with self.subTest(returncode=returncode, writes=writes):
                self.out = self.root/f'failure-{i}'
                self.returncode, self.writes_output = returncode, writes
                result = self.run_fixture()
                self.assertFalse(result['passed'])
                self.assertEqual(result['native_operation_calls'], 3)
                self.assertEqual(result['exact_moment_comparisons'], 0)

    def test_launch_failure_is_recorded_with_zero_real_processes(self):
        self.process.side_effect = PermissionError('unit-test launch denied')
        result = self.run_fixture()
        self.assertFalse(result['passed'])
        self.assertEqual(result['native_operation_calls'], 0)
        self.assertEqual(result['attempted_operations'], 1)
        self.assertFalse(result['checks'][0]['new_native_process_launched'])
        self.assertEqual(result['checks'][0]['process_status'], 'NATIVE_NOT_LAUNCHED')

    def test_timeout_preserves_partial_outputs_and_never_passes(self):
        def timeout(command, **kwargs):
            Path(command[-1]).write_bytes(b'partial native bytes')
            raise subprocess.TimeoutExpired(command, kwargs['timeout'], output=b'partial stdout')
        self.process.side_effect = timeout
        result = self.run_fixture()
        self.assertFalse(result['passed'])
        self.assertEqual(result['native_operation_calls'], 3)
        self.assertTrue(all(c['process_status'] == 'NATIVE_TIMEOUT' for c in result['checks']))
        self.assertEqual((self.out/'union.obj').read_bytes(), b'partial native bytes')

    def test_input_mutation_is_rejected_after_one_call_with_failed_receipt(self):
        self.hook = lambda command: Path(command[2]).write_bytes(b'mutated frozen input')
        result = self.run_fixture()
        self.assertFalse(result['passed'])
        self.assertEqual(result['native_operation_calls'], 1)
        self.assertFalse(result['checks'][0]['inputs_unchanged'])
        self.assertIn('MUTATED_FROZEN', result['fatal_error'])
        self.assertFalse((self.out/'intersection.obj').exists())

    def test_output_or_binary_mutation_during_audit_is_rejected_before_next_call(self):
        original = smoke.exact_mesh_moments
        for i, target in enumerate(('output', 'binary')):
            with self.subTest(target=target):
                self.out = self.root/f'audit-mutation-{i}'
                def audit_and_mutate(path):
                    result = original(path)
                    if Path(path).name == 'union.obj':
                        changed = Path(path) if target == 'output' else self.binary
                        changed.write_bytes(changed.read_bytes()+b'# mutation\n')
                    return result
                with patch.object(smoke, 'exact_mesh_moments', side_effect=audit_and_mutate):
                    result = self.run_fixture()
                self.assertFalse(result['passed'])
                self.assertEqual(result['native_operation_calls'], 1)
                self.assertIn('FROZEN_SMOKE_ARTIFACT_CHANGED', result['fatal_error'])

    def test_source_identity_must_remain_unchanged_through_smoke(self):
        self.auth.side_effect = [dict(self.identity), ValueError('CHANGED_SOURCE')]
        result = self.run_fixture()
        self.assertFalse(result['passed'])
        self.assertEqual(result['native_operation_calls'], 3)
        self.assertEqual(result['exact_moment_comparisons_equal'], 30)
        self.assertIn('CHANGED_SOURCE', result['fatal_error'])

    def test_strict_operation_timeout_count_and_prior_receipt_preflight(self):
        a, b = self.root/'a.obj', self.root/'b.obj'
        smoke.write_box(a, 0, 2)
        smoke.write_box(b, 1, 3)
        output = self.root/'result.obj'
        def call(operation='union', inputs=None, timeout=60):
            operands = [a, b] if inputs is None else inputs
            return smoke.native_operation(self.binary, operation, operands, output,
                expected_binary_sha256=self.identity['binary_sha256'],
                expected_input_sha256=[smoke.sha256(p) for p in operands], timeout=timeout)
        for operation in ('xor', 'cgal', 'UNION', ''):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                call(operation)
        for timeout in (0, 121, True, 1.5, float('nan')):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                call(timeout=timeout)
        for operands in ([], [a], [a, b, a]):
            with self.subTest(count=len(operands)), self.assertRaises(ValueError):
                call(inputs=operands)
        receipt = Path(str(output)+'.native.json')
        receipt.write_text('{"passed": true, "fake_certificate": true}')
        with self.assertRaisesRegex(ValueError, 'OVERWRITE'):
            call()
        self.assertIn('fake_certificate', receipt.read_text())
        self.assertEqual(self.process.call_count, 0)


if __name__ == '__main__':
    unittest.main()
