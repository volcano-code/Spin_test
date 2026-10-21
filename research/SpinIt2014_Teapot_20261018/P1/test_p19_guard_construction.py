"""Independent P19 guard geometry and fail-closed construction regressions.

Process doubles below are deliberately unit-test fixtures. They authenticate no
native execution or scientific result. Native analytical execution evidence is
kept separately; these tests neither rebuild Cherchi nor rerun Teapot Booleans.
"""
from collections import Counter
from contextlib import ExitStack
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import p19_guard_construction as construction
from p17_boundary_certificate import read_binary64_obj


SQUARE = ((-1, -1), (1, -1), (1, 1), (-1, 1))
TETRAHEDRON = (b'v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\n'
               b'f 1 3 2\nf 1 2 4\nf 1 4 3\nf 2 3 4\n')


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def independent_prism_checks(testcase, path, polygon, zlo, zhi):
    """Check all directed edges, face normals, and analytic prism volume."""
    polygon = [tuple(map(Q, p)) for p in polygon]
    zlo, zhi = Q(zlo), Q(zhi)
    mesh = read_binary64_obj(path)
    n = len(polygon)
    testcase.assertEqual(len(mesh.vertices), 2*n+2)
    testcase.assertEqual(len(mesh.faces), 4*n)
    testcase.assertEqual(mesh.vertices[:n], tuple((x, y, zlo) for x, y in polygon))
    testcase.assertEqual(mesh.vertices[n:2*n], tuple((x, y, zhi) for x, y in polygon))
    center = (sum(p[0] for p in polygon)/n, sum(p[1] for p in polygon)/n, (zlo+zhi)/2)
    directed = Counter()
    actual_volume = Q(0)
    for face in mesh.faces:
        a, b, c = [mesh.vertices[i] for i in face]
        normal = cross(tuple(b[i]-a[i] for i in range(3)), tuple(c[i]-a[i] for i in range(3)))
        testcase.assertGreater(sum(normal[i]*(a[i]-center[i]) for i in range(3)), 0)
        actual_volume += sum(a[i]*cross(b, c)[i] for i in range(3))/6
        for u, v in zip(face, (face[1], face[2], face[0])):
            directed[(u, v)] += 1
    testcase.assertTrue(all(count == 1 and directed[(v, u)] == 1
                            for (u, v), count in directed.items()))
    area = sum(polygon[i][0]*polygon[(i+1)%n][1]-polygon[i][1]*polygon[(i+1)%n][0]
               for i in range(n))/2
    testcase.assertGreater(area, 0)
    testcase.assertEqual(actual_volume, area*(zhi-zlo))
    return actual_volume


class DyadicPrismTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_all_registered_guards_have_exact_closed_outward_boundaries(self):
        plan = construction.registered_plan()
        outer = plan['outer_collars']
        cases = [(outer['polygon_ccw'], *heights) for heights in outer['z_intervals']]
        cases.append((plan['inner_guard']['polygon_ccw'], *plan['inner_guard']['z_interval']))
        for i, (polygon, lo, hi) in enumerate(cases):
            with self.subTest(guard=i):
                path = self.root / f'guard-{i}.obj'
                result = construction.write_dyadic_prism(path, polygon, lo, hi)
                volume = independent_prism_checks(self, path, polygon, lo, hi)
                self.assertEqual(result['exact_volume'], str(volume))
                self.assertEqual(result['sha256'], file_sha(path))

    def test_bad_polygon_geometry_is_rejected_before_writing(self):
        polygons = [SQUARE[::-1], SQUARE[:-1],  # clockwise and non-dyadic triangular cap center
                    [(-1, -1), (1, -1), (0, 0), (1, 1), (-1, 1)],
                    [(-1, -1), (0, -1), (1, -1), (1, 1), (-1, 1)],
                    [*SQUARE, SQUARE[0]], [(0, 0), (1, 0)],
                    [(0, 0, 0), (1, 0), (0, 1)]]
        for i, polygon in enumerate(polygons):
            with self.subTest(polygon=i):
                path = self.root / f'invalid-{i}.obj'
                with self.assertRaises((ValueError, TypeError)):
                    construction.write_dyadic_prism(path, polygon, 0, 1)
                self.assertFalse(path.exists())

    def test_nonfinite_nonbinary64_and_reversed_heights_are_rejected(self):
        cases = [(SQUARE, 1, 1), (SQUARE, 1, 0), (SQUARE, 0, '1/3'),
                 (SQUARE, 0, float('nan')), (SQUARE, 0, float('inf')),
                 ([(Q(1, 3), -1), *SQUARE[1:]], 0, 1),
                 ([(float('nan'), -1), *SQUARE[1:]], 0, 1),
                 ([(2**1024, -1), *SQUARE[1:]], 0, 1)]
        for i, args in enumerate(cases):
            with self.subTest(case=i):
                path = self.root / f'nonbinary-{i}.obj'
                with self.assertRaises((ValueError, OverflowError)):
                    construction.write_dyadic_prism(path, *args)
                self.assertFalse(path.exists())

    def test_existing_guard_and_json_evidence_are_never_overwritten(self):
        path = self.root / 'preserved.obj'
        path.write_bytes(b'existing scientific evidence\n')
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            construction.write_dyadic_prism(path, SQUARE, 0, 1)
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(FileExistsError):
            construction.write_new_json(path, {'replacement': True})
        self.assertEqual(path.read_bytes(), before)

    def test_plan_fixes_positive_gap_and_never_grants_admission(self):
        plan = construction.registered_plan()
        self.assertEqual(plan['source_P18_commit'], 'b33fc93bd1fecd5b42fbd8d2eabfefd6ec9db7be')
        self.assertEqual(Q(plan['minimum_design_to_original_shaft_gap_reference']), Q(1, 500))
        self.assertTrue(plan['minimum_gap_is_not_maximum_shape_change_budget'])
        self.assertTrue(plan['outer_shape_and_volume_changes_must_be_reported_separately'])
        self.assertEqual([(x['op'], x['inputs'], x['output']) for x in plan['native_operations']],
                         [('union', ['old_outer', 'lower_collar', 'upper_collar'], 'M.obj'),
                          ('subtraction', ['cavity', 'inner_guard'], 'D.obj'),
                          ('subtraction', ['M.obj', 'D.obj'], 'F.obj')])
        for flag in ('automatic_mesh_postprocess_allowed', 'W0_physical_approval',
                     'W2_Teapot_teacher_admission', 'optimization_admitted', 'training_admitted'):
            self.assertIs(plan[flag], False)
        plan['native_operations'][0]['op'] = 'unit-test mutation'
        self.assertEqual(construction.registered_plan()['native_operations'][0]['op'], 'union')


class ConstructionFixtureTests(unittest.TestCase):
    """Use temporary source hashes and explicit fake process/auditor fixtures."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = self.root / 'packet'
        self.packet.mkdir()
        (self.packet/'manifest.json').write_text('{"unit_test_fixture": true}\n')
        self.source_paths = {}
        sources = {}
        for name, (rel, _) in construction.SOURCES.items():
            path = self.packet/rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'# '+name.encode()+b' unit-test fixture\n'+TETRAHEDRON)
            sources[name] = (rel, file_sha(path))
            self.source_paths[name] = path
        self.binary = self.root/'w4_cherchi_reference_native'
        self.binary.write_bytes(b'UNIT-TEST FIXTURE; NOT A REAL NATIVE EXECUTABLE\n')
        self.upstream = self.root/'upstream'
        self.upstream.mkdir()
        self.output = self.root/'new-output'
        self.native_commands = []
        self.process_returncode = 0
        self.process_writes_output = True
        self.process_hook = None
        self.audit_hook = None
        self.git_status = ''
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(construction, 'SOURCES', sources))
        self.stack.enter_context(patch.object(construction, 'SOURCE_MANIFEST_SHA', file_sha(self.packet/'manifest.json')))
        self.native_identity = self.stack.enter_context(patch('p7_cherchi_native_union.native_identity',
            side_effect=lambda binary, source: {'binary_sha256': file_sha(binary),
                                               'upstream_commit': 'TEST_FIXTURE_NOT_AUTHENTICATION'}))
        self.process = self.stack.enter_context(patch.object(construction.subprocess, 'run', side_effect=self.fake_process))
        self.auditor = self.stack.enter_context(patch.object(construction, 'audit_exact_surface', side_effect=self.fake_audit))

    def fake_process(self, command, **kwargs):
        if command[0] == 'git':
            self.assertIn('status', command)
            return subprocess.CompletedProcess(command, 0, self.git_status, '')
        self.assertEqual(command[0], str(self.binary.resolve()))
        self.native_commands.append(command)
        output = Path(command[-1])
        if self.process_writes_output:
            output.write_bytes(TETRAHEDRON)
        if self.process_hook:
            self.process_hook(command)
        return subprocess.CompletedProcess(command, self.process_returncode,
                                           'unit-test process double', '')

    def fake_audit(self, path, expected_sha256):
        self.assertEqual(file_sha(path), expected_sha256)
        result = {'exact_embedded_closed_oriented_2manifold': True,
                  'unit_test_fixture_only': True}
        if self.audit_hook:
            self.audit_hook(Path(path), result)
        return result

    def run_fixture(self):
        return construction.run(self.packet, self.binary, self.upstream, self.output)

    def assert_run_rejected_or_raised(self):
        try:
            result = self.run_fixture()
        except (ValueError, RuntimeError, OSError):
            result = None
        if result is not None:
            self.assertNotEqual(result['status'], 'NATIVE_SAVED_SURFACES_PASS_FULL_MATERIAL_PROOF_PENDING')
            self.assertIs(result['geometry_accepted'], False)
        journal = self.output/'construction-journal.json'
        if journal.is_file():
            self.assertNotEqual(json.loads(journal.read_text())['status'],
                                'NATIVE_SAVED_SURFACES_PASS_FULL_MATERIAL_PROOF_PENDING')

    def test_prepare_rejects_changed_manifest_or_source_before_creating_output(self):
        manifest = self.packet/'manifest.json'
        original = manifest.read_bytes()
        manifest.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError, 'FROZEN_P17_MANIFEST'):
            construction.prepare(self.packet, self.output)
        self.assertFalse(self.output.exists())
        manifest.write_bytes(original)
        self.source_paths['cavity'].write_bytes(b'changed source')
        with self.assertRaisesRegex(ValueError, 'SOURCE_SHA_MISMATCH'):
            construction.prepare(self.packet, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.process.call_count, 0)

    def test_prepare_is_new_only_and_registers_exact_guard_hashes(self):
        construction.prepare(self.packet, self.output)
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        identities = json.loads((self.output/'guard-identities.json').read_text())
        for name, identity in identities.items():
            self.assertEqual(identity['sha256'], file_sha(self.output/(name+'.obj')))
        self.assertEqual(json.loads((self.output/'registered-plan.json').read_text()), construction.registered_plan())
        with self.assertRaises(FileExistsError):
            construction.prepare(self.packet, self.output)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertEqual(self.process.call_count, 0)

    def test_invalid_operation_timeout_or_operand_count_never_starts_process(self):
        a, b = self.source_paths['old_outer'], self.source_paths['cavity']
        for operation in ('', 'intersection', 'xor', 'UNION', 'unrecognized'):
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                construction.native_call(self.binary, operation, [a, b], self.root/'invalid.obj')
        for timeout in (0, -1, 121, float('nan'), float('inf')):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                construction.native_call(self.binary, 'union', [a, b], self.root/'invalid.obj', timeout=timeout)
        for operands in ([], [a]):
            with self.subTest(operand_count=len(operands)), self.assertRaises(ValueError):
                construction.native_call(self.binary, 'union', operands, self.root/f'invalid-count-{len(operands)}.obj')
        self.assertEqual(self.process.call_count, 0)

    def test_existing_output_or_receipt_is_not_overwritten(self):
        a, b = self.source_paths['old_outer'], self.source_paths['cavity']
        for target in ('result.obj', 'result.obj.native.json'):
            with self.subTest(target=target):
                path = self.root/target
                path.write_bytes(b'old evidence\n')
                with self.assertRaisesRegex(ValueError, 'OVERWRITE'):
                    construction.native_call(self.binary, 'union', [a, b], self.root/'result.obj')
                self.assertEqual(path.read_bytes(), b'old evidence\n')
                path.unlink()
        self.assertEqual(self.process.call_count, 0)

    def test_missing_binary_cannot_claim_a_process_was_launched(self):
        with self.assertRaises((FileNotFoundError, ValueError)):
            construction.native_call(self.root/'missing-native', 'union', list(self.source_paths.values())[:2], self.root/'result.obj')
        self.assertEqual(self.process.call_count, 0)
        self.assertFalse((self.root/'result.obj').exists())

    def test_os_launch_error_never_creates_success_evidence(self):
        self.process.side_effect = PermissionError('unit-test launch denial')
        output = self.root/'result.obj'
        try:
            result = construction.native_call(self.binary, 'union', list(self.source_paths.values())[:2], output)
        except OSError:
            result = None
        if result is not None:
            self.assertIs(result['new_native_process_launched'], False)
            self.assertNotEqual(result.get('returncode'), 0)
        receipt = Path(str(output)+'.native.json')
        if receipt.is_file():
            record = json.loads(receipt.read_text())
            self.assertIs(record['new_native_process_launched'], False)
            self.assertNotEqual(record.get('returncode'), 0)
        self.assertFalse(output.exists())

    def test_receipt_binds_exact_input_output_and_binary_bytes(self):
        inputs = list(self.source_paths.values())[:2]
        before = [file_sha(p) for p in inputs]
        output = self.root/'result.obj'
        record = construction.native_call(self.binary, 'subtraction', inputs, output)
        self.assertEqual(record['input_sha256'], before)
        self.assertEqual(record['output_sha256'], file_sha(output))
        self.assertEqual(record['binary_sha256'], file_sha(self.binary))
        self.assertTrue(record['inputs_unchanged'])
        self.assertTrue(record['binary_unchanged'])
        self.assertEqual(record, json.loads(Path(str(output)+'.native.json').read_text()))

    def test_run_cannot_count_a_launch_error_as_a_real_native_call(self):
        def fail_native_launch(command, **kwargs):
            if command[0] == 'git':
                return self.fake_process(command, **kwargs)
            raise PermissionError('unit-test child process never started')
        self.process.side_effect = fail_native_launch
        try:
            result = self.run_fixture()
        except OSError:
            result = None
        if result is not None:
            self.assertNotEqual(result['status'], 'NATIVE_SAVED_SURFACES_PASS_FULL_MATERIAL_PROOF_PENDING')
            self.assertEqual(result['new_Teapot_native_calls'], 0)
            self.assertTrue(all(operation['new_native_process_launched'] is False
                                for operation in result['operations']))
        self.assertFalse(self.native_commands)
        for name in ('M.obj', 'D.obj', 'F.obj'):
            self.assertFalse((self.output/name).exists())

    def test_input_or_binary_mutation_during_call_is_recorded_and_rejected(self):
        for target_name in ('input', 'binary'):
            with self.subTest(target=target_name):
                target = self.source_paths['old_outer'] if target_name == 'input' else self.binary
                original = target.read_bytes()
                self.process_hook = lambda command: target.write_bytes(original+b'modified')
                output = self.root/(target_name+'.obj')
                with self.assertRaisesRegex(ValueError, 'MUTATED_PINNED'):
                    construction.native_call(self.binary, 'union', list(self.source_paths.values())[:2], output)
                record = json.loads(Path(str(output)+'.native.json').read_text())
                self.assertFalse(record['inputs_unchanged' if target_name == 'input' else 'binary_unchanged'])
                target.write_bytes(original)

    def test_timeout_keeps_partial_output_but_never_reports_success(self):
        output = self.root/'timeout.obj'
        def timeout(command, **kwargs):
            Path(command[-1]).write_bytes(b'partial OBJ')
            raise subprocess.TimeoutExpired(command, kwargs['timeout'], output=b'partial stdout')
        self.process.side_effect = timeout
        record = construction.native_call(self.binary, 'union', list(self.source_paths.values())[:2], output)
        self.assertEqual(record['status'], 'NATIVE_TIMEOUT')
        self.assertIsNone(record['returncode'])
        self.assertEqual(record['output_sha256'], file_sha(output))
        self.assertEqual(output.read_bytes(), b'partial OBJ')

    def test_registered_plan_exists_before_calls_and_success_still_has_no_admission(self):
        def observe(command):
            plan_path = self.output/'registered-plan.json'
            self.assertTrue(plan_path.is_file())
            plan = json.loads(plan_path.read_text())
            spec = plan['native_operations'][len(self.native_commands)-1]
            self.assertEqual(command[1], spec['op'])
            self.assertEqual(Path(command[-1]).name, spec['output'])
            self.assertEqual(len(command)-3, len(spec['inputs']))
        self.process_hook = observe
        result = self.run_fixture()
        self.assertEqual(result['status'], 'NATIVE_SAVED_SURFACES_PASS_FULL_MATERIAL_PROOF_PENDING')
        self.assertEqual(result['new_Teapot_native_calls'], 3)
        self.assertEqual(result['registered_plan_sha256'], file_sha(self.output/'registered-plan.json'))
        for flag in ('geometry_accepted', 'optimization_admitted', 'training_admitted', 'automatic_postprocess_executed'):
            self.assertIs(result[flag], False)
        self.assertEqual(result['operations'][2]['input_sha256'],
                         [result['operations'][0]['output_sha256'], result['operations'][1]['output_sha256']])

    def test_failed_surface_does_not_start_F_or_grant_success(self):
        def reject_m(path, result):
            if path.name == 'M.obj':
                result['exact_embedded_closed_oriented_2manifold'] = False
        self.audit_hook = reject_m
        result = self.run_fixture()
        self.assertEqual(result['status'], 'NATIVE_SAVED_SURFACE_REJECTED')
        self.assertEqual(len(self.native_commands), 2)
        self.assertFalse((self.output/'F.obj').exists())
        self.assertIs(result['geometry_accepted'], False)

    def test_zero_exit_without_output_and_nonzero_with_output_both_reject(self):
        for index, (returncode, writes) in enumerate(((0, False), (7, True))):
            with self.subTest(returncode=returncode, writes_output=writes):
                self.output = self.root/f'failure-{index}'
                self.native_commands.clear()
                self.process_returncode, self.process_writes_output = returncode, writes
                result = self.run_fixture()
                self.assertEqual(result['status'], 'NATIVE_SAVED_SURFACE_REJECTED')
                self.assertEqual(len(self.native_commands), 2)
                self.assertFalse((self.output/'F.obj').exists())
        self.auditor.assert_not_called()

    def test_frozen_source_changed_after_prepare_is_not_used_as_registered_input(self):
        original_prepare = construction.prepare
        def prepare_then_change(packet, output):
            result = original_prepare(packet, output)
            self.source_paths['cavity'].write_bytes(b'changed after registration\n'+TETRAHEDRON)
            return result
        with patch.object(construction, 'prepare', side_effect=prepare_then_change):
            self.assert_run_rejected_or_raised()
        cavity = str(self.source_paths['cavity'].resolve())
        self.assertTrue(all(cavity not in command[2:-1] for command in self.native_commands))

    def test_M_changed_between_its_audit_and_F_is_rejected_before_F_launch(self):
        def change_m_during_d(command):
            if Path(command[-1]).name == 'D.obj':
                (self.output/'M.obj').write_bytes(b'changed between calls\n'+TETRAHEDRON)
        self.process_hook = change_m_during_d
        self.assert_run_rejected_or_raised()
        self.assertTrue(all(Path(command[-1]).name != 'F.obj' for command in self.native_commands))

    def test_registered_guard_changed_after_prepare_is_not_used_as_registered_input(self):
        original_prepare = construction.prepare
        def prepare_then_change(packet, output):
            result = original_prepare(packet, output)
            path = Path(output)/'inner_guard.obj'
            path.write_bytes(path.read_bytes()+b'# modified after guard registration\n')
            return result
        with patch.object(construction, 'prepare', side_effect=prepare_then_change):
            self.assert_run_rejected_or_raised()
        guard = str((self.output/'inner_guard.obj').resolve())
        self.assertTrue(all(guard not in command[2:-1] for command in self.native_commands))

    def test_binary_changed_after_first_audit_is_not_accepted_as_a_new_baseline(self):
        def replace_binary(path, result):
            if path.name == 'M.obj':
                self.binary.write_bytes(b'changed after initial source identity check\n')
        self.audit_hook = replace_binary
        self.assert_run_rejected_or_raised()
        self.assertTrue(all(Path(command[-1]).name not in ('D.obj', 'F.obj')
                            for command in self.native_commands))

    def test_output_modified_during_last_audit_cannot_be_declared_frozen(self):
        def mutate_after_read(path, result):
            if path.name == 'F.obj':
                path.write_bytes(path.read_bytes()+b'# post-read mutation\n')
        self.audit_hook = mutate_after_read
        self.assert_run_rejected_or_raised()

    def test_wrong_upstream_identity_and_dirty_tracked_source_are_rejected(self):
        self.native_identity.side_effect = ValueError('PINNED_REFERENCE_IDENTITY_MISMATCH')
        with self.assertRaisesRegex(ValueError, 'IDENTITY_MISMATCH'):
            self.run_fixture()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.native_commands)
        self.native_identity.side_effect = lambda binary, source: {'binary_sha256': file_sha(binary)}
        self.git_status = ' M code/booleans.cpp\n'
        with self.assertRaisesRegex(ValueError, 'TRACKED_SOURCE_TREE_DIRTY'):
            self.run_fixture()
        self.assertFalse(self.output.exists())
        self.assertFalse(self.native_commands)


if __name__ == '__main__':
    unittest.main()
