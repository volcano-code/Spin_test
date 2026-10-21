"""Lightweight P19 package integrity tests; no native or geometry reruns.

Frozen packet authentication and guard regeneration use real saved files.
Report replay uses an explicitly named TEST_ONLY audit fixture. Rebuild tests
inject errors with explicitly fake identities/calls, exercise rejection paths
only, and never create an accepted native reconstruction or geometry report.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from p17_boundary_certificate import read_binary64_obj
import p19_material_candidate as candidate
import p19_native_smoke as native_identity_module


ROOT = Path(__file__).resolve().parent
PACKET = Path(os.environ.get('W4_P19_FINAL_CASE_ROOT', ROOT/'P19_material_case'))
FROZEN_MANIFEST_SHA256 = 'c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+'\n', encoding='utf-8')


class FrozenPacketAuthenticationTests(unittest.TestCase):
    def test_external_digest_authenticates_actual_packet_and_receipts(self):
        self.assertTrue(PACKET.is_dir(), 'Required frozen P19 packet is missing')
        self.assertEqual(candidate.MANIFEST_SHA256, FROZEN_MANIFEST_SHA256)
        self.assertEqual(digest(PACKET/'manifest.json'), FROZEN_MANIFEST_SHA256)
        manifest = candidate.validate_packet(PACKET)
        self.assertEqual(set(manifest['material_files']), {'M', 'F', 'D', 'S'})
        self.assertTrue(all(value is False for value in manifest['scientific_flags'].values()))
        for name in ('M', 'D', 'F'):
            receipt = json.loads((PACKET/'receipts'/(name+'_native.obj.native.json')).read_text())
            self.assertIs(type(receipt['returncode']), int)
            self.assertEqual(receipt['returncode'], 0)
            self.assertEqual(receipt['output_sha256'],
                             manifest['files_sha256'][manifest['material_files'][name]])
            self.assertIs(receipt['new_native_process_launched'], True)

    def test_internally_consistent_manifest_and_receipt_rewrite_cannot_replace_frozen_package(self):
        with tempfile.TemporaryDirectory() as temp:
            altered = Path(temp)/'package'
            shutil.copytree(PACKET, altered)
            manifest = json.loads((altered/'manifest.json').read_text())
            design_relative = manifest['material_files']['D']
            design = altered/design_relative
            design.write_bytes(design.read_bytes()+b'# TEST_ONLY changed saved identity\n')
            new_design_sha = digest(design)
            manifest['files_sha256'][design_relative] = new_design_sha
            for name in ('D', 'F'):
                relative = 'receipts/'+name+'_native.obj.native.json'
                receipt = json.loads((altered/relative).read_text())
                if name == 'D':
                    receipt['output_sha256'] = new_design_sha
                else:
                    receipt['input_sha256'][1] = new_design_sha
                save_json(altered/relative, receipt)
                manifest['files_sha256'][relative] = digest(altered/relative)
            save_json(altered/'manifest.json', manifest)
            # All internal file hashes and altered receipt links now agree.
            self.assertTrue(all(digest(altered/rel) == sha for rel, sha in manifest['files_sha256'].items()))
            self.assertNotEqual(digest(altered/'manifest.json'), FROZEN_MANIFEST_SHA256)
            with self.assertRaisesRegex(ValueError, 'EXTERNAL_FROZEN_MANIFEST_MISMATCH'):
                candidate.validate_packet(altered)

    def test_receipt_rewrite_without_manifest_rewrite_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            altered = Path(temp)/'package'
            shutil.copytree(PACKET, altered)
            receipt_path = altered/'receipts/M_native.obj.native.json'
            receipt = json.loads(receipt_path.read_text())
            receipt['returncode'] = False  # Python equality to zero is insufficient.
            save_json(receipt_path, receipt)
            self.assertEqual(digest(altered/'manifest.json'), FROZEN_MANIFEST_SHA256)
            with self.assertRaisesRegex(ValueError, 'FROZEN_FILE_MISMATCH_receipts/M_native'):
                candidate.validate_packet(altered)

    def test_byte_identical_symlink_is_not_a_frozen_regular_file(self):
        with tempfile.TemporaryDirectory() as temp:
            altered = Path(temp)/'package'
            shutil.copytree(PACKET, altered)
            path = altered/'inputs/inner_guard.obj'
            expected = digest(path)
            path.unlink()
            path.symlink_to((PACKET/'inputs/inner_guard.obj').resolve())
            self.assertEqual(digest(path), expected)
            with self.assertRaisesRegex(ValueError, 'PACKET_SYMLINK_NOT_SELF_CONTAINED'):
                candidate.validate_packet(altered)


class DeterministicGuardRegenerationTests(unittest.TestCase):
    def test_two_real_regenerations_match_frozen_hashes_and_preserve_tip_and_every_z(self):
        manifest = candidate.validate_packet(PACKET)
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp)/'first', Path(temp)/'second'
            hashes_a = candidate.regenerate_guards(PACKET, first)
            hashes_b = candidate.regenerate_guards(PACKET, second)
            self.assertEqual(hashes_a, hashes_b)
            for name, sha in hashes_a.items():
                self.assertEqual(sha, manifest['files_sha256']['inputs/'+name])
                self.assertEqual((first/name).read_bytes(), (second/name).read_bytes())
            shaft = read_binary64_obj(PACKET/'source/shaft-reference.obj')
            envelope = read_binary64_obj(first/'shaft-envelope.obj')
            self.assertEqual(shaft.faces, envelope.faces)
            self.assertEqual(len(shaft.vertices), len(envelope.vertices))
            self.assertEqual(tuple(p[2] for p in shaft.vertices), tuple(p[2] for p in envelope.vertices))
            zero = (Fraction(0),)*3
            self.assertIn(zero, shaft.vertices)
            self.assertIn(zero, envelope.vertices)
            for original, expanded in zip(shaft.vertices, envelope.vertices):
                if original[0] == original[1] == 0:
                    self.assertEqual(expanded, original)

    def test_regeneration_preserves_preexisting_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'guards'
            output.mkdir()
            sentinel = output/'keep.txt'
            sentinel.write_bytes(b'original evidence')
            with self.assertRaises(FileExistsError):
                candidate.regenerate_guards(PACKET, output)
            self.assertEqual(sentinel.read_bytes(), b'original evidence')
            self.assertEqual(set(p.name for p in output.iterdir()), {'keep.txt'})

    def test_changed_frozen_guard_source_stops_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            altered, output = Path(temp)/'package', Path(temp)/'guards'
            shutil.copytree(PACKET, altered)
            path = altered/'source/shaft-reference.obj'
            path.write_bytes(path.read_bytes()+b'# TEST_ONLY modified source\n')
            with self.assertRaisesRegex(ValueError, 'FROZEN_FILE_MISMATCH_source/shaft-reference'):
                candidate.regenerate_guards(altered, output)
            self.assertFalse(output.exists())


class StrictReportReplayFixtureTests(unittest.TestCase):
    """Only report-comparison semantics; audit_packet is explicitly mocked."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.report = Path(self.temp.name)/'TEST_ONLY_report.json'
        raw = (Fraction(1), Fraction(0), Fraction(0), Fraction(0),
               Fraction(1, 12), Fraction(1, 12), Fraction(1, 12),
               Fraction(0), Fraction(0), Fraction(0))
        exact = [{'numerator': str(x.numerator), 'denominator': str(x.denominator)} for x in raw]
        inertia = [[1/6 if i == j else 0.0 for j in range(3)] for i in range(3)]
        physical = {
            'schema': 'TEST_ONLY_CENTERED_UNIT_CUBE_COMPARISON_FIXTURE',
            'materials': {'M': {
                'principal_inertia_kg_m2': [1/6]*3,
                'source_raw_ten_exact': deepcopy(exact),
                'si_raw_ten_exact': deepcopy(exact),
                'full_inertia_origin_kg_m2': deepcopy(inertia),
                'full_inertia_com_kg_m2': deepcopy(inertia),
                'mass_kg': 1.0,
                'W0_physical_tip_or_FD_approved': False,
            }},
            'physical_table': [{'material': 'M', 'mass_kg': 1.0,
                                'principal_inertia_kg_m2': [1/6]*3,
                                'full_inertia_com_kg_m2': deepcopy(inertia)}],
        }
        self.actual = {
            'schema': 'TEST_ONLY_NOT_A_GEOMETRY_OR_NATIVE_REPORT',
            'status': 'TEST_ONLY_EXPECTED_AUDIT_FIXTURE',
            'geometry': {'fixture_pass': True, 'count': 3, 'exact': '1/500',
                         'nested': [{'elapsed_seconds': 1.0, 'audit_elapsed_seconds': 2.0,
                                     'wall_seconds': 3.0, 'approval': False}]},
            'scientific_flags': {'training_admitted': False},
            'physical_proposal': physical,
            'optimization_admitted': False,
            'elapsed_seconds': 4.0,
        }

    def verify_fixture(self, claimed):
        save_json(self.report, claimed)
        with patch.object(candidate, 'audit_packet', return_value=deepcopy(self.actual)) as audit_stub:
            with patch.object(candidate, 'audit_material', side_effect=AssertionError('NO_REAL_GEOMETRY_IN_FIXTURE_TEST')):
                result = candidate.verify_report('TEST_ONLY_PACKET', self.report, 'TEST_ONLY_PREVIOUS')
            audit_stub.assert_called_once_with('TEST_ONLY_PACKET', 'TEST_ONLY_PREVIOUS')
        return result

    def test_only_two_named_timing_fields_may_differ_recursively(self):
        claimed = deepcopy(self.actual)
        claimed['elapsed_seconds'] = 999.0
        claimed['geometry']['nested'][0]['elapsed_seconds'] = 888.0
        claimed['geometry']['nested'][0]['audit_elapsed_seconds'] = 777.0
        result = self.verify_fixture(claimed)
        self.assertEqual(result['status'], 'P19_COMPLETE_REPORT_RECOMPUTED_AND_VALIDATED')
        self.assertEqual(result['report_status'], 'TEST_ONLY_EXPECTED_AUDIT_FIXTURE')
        self.assertEqual(result['only_ignored_fields'], ['elapsed_seconds', 'audit_elapsed_seconds'])
        self.assertIs(result['optimization_admitted'], False)

    def test_principal_display_one_ulp_is_the_only_numerical_exception(self):
        claimed = deepcopy(self.actual)
        for item in (claimed['physical_proposal']['materials']['M'],
                     claimed['physical_proposal']['physical_table'][0]):
            item['principal_inertia_kg_m2'] = [math.nextafter(x, math.inf)
                                              for x in item['principal_inertia_kg_m2']]
        result = self.verify_fixture(claimed)
        self.assertEqual(result['principal_inertia_display_relative_tolerance'], 1e-12)
        self.assertEqual(result['only_numerically_compared_fields'],
                         'physical_proposal principal_inertia_kg_m2 only')
        self.assertIs(result['all_exact_moments_and_full_inertia_tensors_compared_exactly'], True)

    def test_large_nontyped_or_nonfinite_principal_display_is_rejected(self):
        for value in (1/6+1e-6, 1, True, math.nan, math.inf):
            with self.subTest(value=value):
                claimed = deepcopy(self.actual)
                claimed['physical_proposal']['materials']['M']['principal_inertia_kg_m2'][0] = value
                with self.assertRaisesRegex(ValueError, 'FROZEN_REPORT_RECOMPUTATION_MISMATCH'):
                    self.verify_fixture(claimed)

    def test_exact_moments_mass_and_full_tensors_have_no_display_tolerance(self):
        for change in ('raw', 'si', 'origin_tensor', 'com_tensor', 'table_tensor', 'mass'):
            with self.subTest(change=change):
                claimed = deepcopy(self.actual)
                material = claimed['physical_proposal']['materials']['M']
                if change in ('raw', 'si'):
                    field = 'source_raw_ten_exact' if change == 'raw' else 'si_raw_ten_exact'
                    material[field][0]['numerator'] = '2'
                elif change == 'mass':
                    material['mass_kg'] = math.nextafter(material['mass_kg'], math.inf)
                else:
                    owner = claimed['physical_proposal']['physical_table'][0] if change == 'table_tensor' else material
                    field = 'full_inertia_origin_kg_m2' if change == 'origin_tensor' else 'full_inertia_com_kg_m2'
                    owner[field][0][0] = math.nextafter(owner[field][0][0], math.inf)
                with self.assertRaisesRegex(ValueError, 'FROZEN_REPORT_RECOMPUTATION_MISMATCH'):
                    self.verify_fixture(claimed)

    def test_python_equal_but_differently_typed_claims_are_rejected(self):
        for change in ('true-to-one', 'int-to-float', 'false-to-zero'):
            with self.subTest(change=change):
                claimed = deepcopy(self.actual)
                if change == 'true-to-one':
                    claimed['geometry']['fixture_pass'] = 1
                elif change == 'int-to-float':
                    claimed['geometry']['count'] = 3.0
                else:
                    claimed['scientific_flags']['training_admitted'] = 0
                with self.assertRaisesRegex(ValueError, 'FROZEN_REPORT_RECOMPUTATION_MISMATCH'):
                    self.verify_fixture(claimed)

    def test_other_timings_scientific_flags_extra_and_missing_fields_are_not_ignored(self):
        for change in ('wall', 'approval', 'extra', 'missing', 'exact'):
            with self.subTest(change=change):
                claimed = deepcopy(self.actual)
                if change == 'wall':
                    claimed['geometry']['nested'][0]['wall_seconds'] = 999.0
                elif change == 'approval':
                    claimed['geometry']['nested'][0]['approval'] = True
                elif change == 'extra':
                    claimed['forged_extra_pass'] = True
                elif change == 'missing':
                    del claimed['geometry']['count']
                else:
                    claimed['geometry']['exact'] = '1/499'
                with self.assertRaisesRegex(ValueError, 'FROZEN_REPORT_RECOMPUTATION_MISMATCH'):
                    self.verify_fixture(claimed)


class ExactNativeSerializationComparisonTests(unittest.TestCase):
    """Ordering is immaterial; coordinates and oriented facet multiplicities are exact."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vertices = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        self.faces = ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3))
        self.reference = self.write('reference.obj', self.vertices, self.faces)

    def write(self, name, vertices, faces):
        path = self.root/name
        text = ''.join('v '+' '.join(format(float(x), '.17g') for x in point)+'\n'
                       for point in vertices)
        text += ''.join('f '+' '.join(str(i+1) for i in face)+'\n' for face in faces)
        path.write_text(text, encoding='ascii')
        return path

    def test_reindex_face_order_and_cyclic_vertex_changes_preserve_exact_geometry(self):
        order = (2, 0, 3, 1)
        inverse = {old: new for new, old in enumerate(order)}
        vertices = tuple(self.vertices[index] for index in order)
        faces = []
        for offset, index in enumerate((3, 1, 0, 2)):
            face = tuple(inverse[i] for i in self.faces[index])
            shift = offset % 3
            faces.append(face[shift:]+face[:shift])
        actual = self.write('reordered.obj', vertices, faces)
        self.assertNotEqual(digest(actual), digest(self.reference))
        before = actual.read_bytes()
        report = candidate.compare_saved_geometry(self.reference, actual)
        self.assertIs(report['exact_saved_geometry_equal'], True)
        self.assertIs(report['raw_bytes_equal'], False)
        self.assertEqual(report['reference_sha256'], digest(self.reference))
        self.assertEqual(report['actual_sha256'], digest(actual))
        self.assertIsNone(report['coordinate_tolerance'])
        self.assertIs(report['mesh_rewritten'], False)
        self.assertEqual(actual.read_bytes(), before, 'comparison must not rewrite native output')

    def test_one_reversed_face_is_not_an_ordering_change(self):
        faces = list(self.faces)
        faces[0] = faces[0][::-1]
        actual = self.write('reversed.obj', self.vertices, faces)
        report = candidate.compare_saved_geometry(self.reference, actual)
        self.assertIs(report['exact_saved_geometry_equal'], False)
        self.assertIs(report['exact_vertex_multisets_equal'], True)
        self.assertIs(report['exact_oriented_triangle_multisets_equal'], False)

    def test_nonzero_two_to_minus_fifty_displacement_is_rejected_without_tolerance(self):
        vertices = list(self.vertices)
        vertices[1] = (Fraction(1)+Fraction(1, 2**50), 0, 0)
        actual = self.write('moved.obj', vertices, self.faces)
        parsed = read_binary64_obj(actual)
        self.assertEqual(parsed.vertices[1][0]-1, Fraction(1, 2**50))
        report = candidate.compare_saved_geometry(self.reference, actual)
        self.assertIs(report['exact_saved_geometry_equal'], False)
        self.assertIs(report['algebraic_face_cancellation_allowed'], False)

    def test_extra_opposite_oriented_facets_cannot_hide_in_signed_chain_cancellation(self):
        face = self.faces[0]
        actual = self.write('canceling-duplicates.obj', self.vertices,
                            self.faces+(face, face[::-1]))
        report = candidate.compare_saved_geometry(self.reference, actual)
        self.assertIs(report['exact_saved_geometry_equal'], False)

    def test_unused_extra_vertex_is_rejected_even_when_its_coordinate_already_exists(self):
        for label, extra in (('new-coordinate', (7, 5, 3)), ('duplicate-coordinate', self.vertices[0])):
            with self.subTest(kind=label):
                actual = self.write(label+'.obj', self.vertices+(extra,), self.faces)
                report = candidate.compare_saved_geometry(self.reference, actual)
                self.assertIs(report['exact_saved_geometry_equal'], False)
                self.assertIs(report['exact_vertex_multisets_equal'], False)
                self.assertIs(report['exact_oriented_triangle_multisets_equal'], True)


class NativeRebuildFailClosedFixtureTests(unittest.TestCase):
    """Error-injection orchestration tests, never a genuine native execution."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root/'w4_cherchi_reference_native'
        self.binary.write_bytes(b'TEST_ONLY_NOT_AN_EXECUTABLE_OR_NATIVE_BINARY')
        self.source = self.root/'TEST_ONLY_checkout'
        self.source.mkdir()
        self.output = self.root/'rebuild'
        self.fake_identity = {
            'mode': 'unmodified',
            'classification': 'TEST_ONLY_NOT_NATIVE_IDENTITY',
            'binary_sha256': digest(self.binary),
        }

    def fake_call(self, binary, operation, operands, output):
        """Copy a frozen file solely to reach later rejection gates, not a Boolean."""
        output = Path(output)
        with output.open('xb') as stream:
            stream.write((PACKET/'material'/(output.stem+'_native.obj')).read_bytes())
        record = {
            'schema': 'TEST_ONLY_FAKE_CALL_NOT_NATIVE_EVIDENCE',
            'operation': operation,
            'returncode': 0,
            'input_sha256': [digest(path) for path in operands],
            'output_sha256': digest(output),
            'new_native_process_launched': False,
            'fixture_only': True,
        }
        # The orchestration pins the helper's saved receipt as well as OBJ.
        # This is a plainly labelled mock record, never native evidence.
        save_json(str(output)+'.native.json', record)
        return record

    def run_expected_early_failure(self, side_effect, error):
        with patch.object(native_identity_module, 'validate_native_identity', return_value=self.fake_identity):
            with patch.object(candidate, 'native_call', side_effect=side_effect) as call:
                with patch.object(candidate, 'audit_material', side_effect=AssertionError('GEOMETRY_MUST_NOT_RUN')) as geometry:
                    with self.assertRaisesRegex(ValueError, error):
                        candidate.rebuild_native(PACKET, self.binary, self.source, self.output)
                    geometry.assert_not_called()
                self.assertFalse((self.output/'native-rebuild-report.json').exists())
                return call.call_count

    def test_real_identity_gate_rejects_nonexecutable_binary_before_output_or_call(self):
        with patch.object(candidate, 'native_call', side_effect=AssertionError('NATIVE_MUST_NOT_RUN')) as call:
            with self.assertRaisesRegex(ValueError, 'PINNED_NATIVE_EXECUTABLE_REQUIRED'):
                candidate.rebuild_native(PACKET, self.binary, self.source, self.output)
            call.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_preexisting_output_is_preserved_without_a_native_call(self):
        self.output.mkdir()
        sentinel = self.output/'M.obj'
        sentinel.write_bytes(b'PREEXISTING EVIDENCE')
        with patch.object(native_identity_module, 'validate_native_identity', return_value=self.fake_identity):
            with patch.object(candidate, 'native_call') as call:
                with self.assertRaises(FileExistsError):
                    candidate.rebuild_native(PACKET, self.binary, self.source, self.output)
                call.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), b'PREEXISTING EVIDENCE')
        self.assertEqual(set(p.name for p in self.output.iterdir()), {'M.obj'})

    def test_failed_process_or_wrong_output_digest_stops_after_first_call(self):
        for fault in ('returncode', 'sha256'):
            with self.subTest(fault=fault):
                self.output = self.root/fault

                def faulty_call(*args):
                    rec = self.fake_call(*args)
                    if fault == 'returncode':
                        rec['returncode'] = 9
                    else:
                        rec['output_sha256'] = '0'*64
                    return rec

                calls = self.run_expected_early_failure(faulty_call, 'SAVED_OUTPUT_DIFFERS_M')
                self.assertEqual(calls, 1)

    def test_binary_change_between_calls_is_rejected_before_second_call(self):
        def change_binary(*args):
            rec = self.fake_call(*args)
            self.binary.write_bytes(self.binary.read_bytes()+b' changed')
            return rec
        self.assertEqual(self.run_expected_early_failure(change_binary, 'PRIOR_BYTES_CHANGED'), 1)

    def test_guard_not_yet_used_by_first_call_is_already_pinned(self):
        def change_guard(*args):
            rec = self.fake_call(*args)
            path = self.output/'guards/inner_guard.obj'
            path.write_bytes(path.read_bytes()+b'# TEST_ONLY changed future operand\n')
            return rec
        self.assertEqual(self.run_expected_early_failure(change_guard, 'PRIOR_BYTES_CHANGED'), 1)

    def test_prior_M_output_cannot_change_before_F_uses_it(self):
        def change_M_after_D(binary, operation, operands, output):
            rec = self.fake_call(binary, operation, operands, output)
            if Path(output).stem == 'D':
                path = self.output/'M.obj'
                path.write_bytes(path.read_bytes()+b'# TEST_ONLY changed prior output\n')
            return rec
        self.assertEqual(self.run_expected_early_failure(change_M_after_D, 'PRIOR_BYTES_CHANGED'), 2)

    def test_post_audit_mutation_cannot_emit_success_even_with_explicit_mock_geometry(self):
        def fake_geometry_then_mutate(*args):
            path = self.output/'F.obj'
            path.write_bytes(path.read_bytes()+b'# TEST_ONLY late mutation\n')
            return {'schema': 'TEST_ONLY_NOT_A_GEOMETRY_CERTIFICATE', 'research_geometry_gate_passed': True}
        with patch.object(native_identity_module, 'validate_native_identity', return_value=self.fake_identity):
            with patch.object(candidate, 'native_call', side_effect=self.fake_call) as call:
                with patch.object(candidate, 'audit_material', side_effect=fake_geometry_then_mutate) as geometry:
                    with self.assertRaisesRegex(ValueError, 'OUTPUT_CHANGED_DURING_AUDIT'):
                        candidate.rebuild_native(PACKET, self.binary, self.source, self.output)
                    self.assertEqual(call.call_count, 3)
                    geometry.assert_called_once()
        self.assertFalse((self.output/'native-rebuild-report.json').exists())


if __name__ == '__main__':
    unittest.main()
