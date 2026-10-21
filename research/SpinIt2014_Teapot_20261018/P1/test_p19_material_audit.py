"""Real computations on small solids; original shaft identity is never relaxed."""
from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import p19_material_audit as audit
from p19_guard_certificate import ORIGINAL_SHAFT_SHA256


ROOT = Path(__file__).resolve().parent
SHAFT = ROOT / 'P17_material_case/source/shaft-reference.obj'
FINAL_MANIFEST_SHA256 = 'c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box(lo, hi):
    x, y, z = lo
    X, Y, Z = hi
    vertices = ((x, y, z), (X, y, z), (X, Y, z), (x, Y, z),
                (x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z))
    faces = ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
             (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
             (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7))
    return vertices, faces


def save_mesh(path, mesh):
    vertices, faces = mesh
    text = ''.join('v ' + ' '.join(format(float(x), '.17g') for x in point) + '\n'
                   for point in vertices)
    text += ''.join('f ' + ' '.join(str(i + 1) for i in face) + '\n' for face in faces)
    path.write_text(text, encoding='ascii')
    return path


def cavity_boundary(outer, design):
    vertices, faces = outer
    inner_vertices, inner_faces = design
    offset = len(vertices)
    reversed_inner = tuple((offset+a, offset+c, offset+b) for a, b, c in inner_faces)
    return tuple(vertices) + tuple(inner_vertices), tuple(faces) + reversed_inner


def prepare(directory, *, outer=None, design=None, fixed=None):
    directory.mkdir(parents=True, exist_ok=True)
    outer = outer or box((-1, -1, -1), (1, 1, 3))
    design = design or box((Q(1, 4), -Q(1, 16), Q(1, 2)),
                           (Q(3, 8), Q(1, 16), Q(3, 4)))
    fixed = fixed or cavity_boundary(outer, design)
    paths = {name: save_mesh(directory / (name+'.obj'), mesh)
             for name, mesh in (('M', outer), ('F', fixed), ('D', design))}
    expected = {name: sha256(path) for name, path in paths.items()}
    return paths, expected


def full(paths, expected, shaft=SHAFT):
    return audit.audit_material(paths['M'], paths['F'], paths['D'], shaft,
                                dict(expected, S=ORIGINAL_SHAFT_SHA256))


def rational(payload):
    return Q(int(payload['numerator']), int(payload['denominator']))


class PartitionGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.paths, cls.expected = prepare(cls.root / 'valid')
        cls.report = audit.audit_partition_geometry(**cls.paths, expected_sha256=cls.expected)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_exact_box_with_cavity_has_independent_moments_and_real_partition(self):
        result = self.report
        self.assertIs(result['partition_geometry_valid'], True)
        self.assertIs(result['fixed_and_design_interiors_disjoint'], True)
        self.assertIs(result['fixed_and_design_union_equals_outer'], True)
        volumes = result['exact_signed_volumes']
        self.assertEqual(rational(volumes['M']), 16)
        self.assertEqual(rational(volumes['D']), Q(1, 256))
        self.assertEqual(rational(volumes['F']), 16-Q(1, 256))
        moments = result['exact_ten_moment_partition']
        self.assertIs(moments['independent_exact_volumes_match_ten_mass_components'], True)
        self.assertTrue(all(rational(item) == 0 for item in moments['M_minus_F_minus_D_exact'].values()))
        self.assertEqual(result['center_in_outer']['classification'], 'INSIDE')
        self.assertIs(result['cavity_ball_and_clearance_certificate']['positive_gap_proved'], True)
        self.assertIs(result['exact_signed_boundary_chain']['exact_signed_triangle_chain_zero'], True)

    def test_geometry_only_helper_cannot_grant_complete_shaft_or_scientific_approval(self):
        result = self.report
        self.assertIs(result['shaft_evaluated'], False)
        self.assertIs(result['complete_original_shaft_in_fixed'], False)
        self.assertIs(result['research_geometry_gate_passed'], False)
        self.assertIs(result['optimization_admitted'], False)
        self.assertIs(result['training_admitted'], False)
        self.assertTrue(all(value is False for value in result['scientific_flags'].values()))
        self.assertEqual(Q(result['cavity_center_exact'][2]), Q.from_float(.67))
        self.assertNotEqual(Q(result['cavity_center_exact'][2]), Q(67, 100))

    def test_zero_chain_and_all_ten_moments_do_not_certify_external_cavity(self):
        design = box((2, Q(-1, 16), Q(1, 2)), (Q(17, 8), Q(1, 16), Q(3, 4)))
        paths, expected = prepare(self.root / 'external-cavity', design=design)
        result = audit.audit_partition_geometry(**paths, expected_sha256=expected)
        self.assertIs(result['all_material_surfaces_exact_embedded_closed_oriented'], True)
        self.assertIs(result['exact_signed_boundary_chain']['exact_signed_triangle_chain_zero'], True)
        self.assertIs(result['exact_ten_moment_partition']['all_ten_residuals_zero'], True)
        self.assertIs(result['fixed_component_correspondence']['exact_outer_and_reversed_cavity_components'], True)
        self.assertIs(result['design_strictly_inside_outer'], False)
        self.assertIs(result['partition_geometry_valid'], False)
        self.assertTrue(result['set_semantics'].startswith('NOT_ESTABLISHED'))
        self.assertTrue(result['containment_proof'].startswith('NOT_ESTABLISHED'))

    def test_positive_ball_clearance_needs_center_in_the_outer_solid(self):
        outer = box((2, -1, -1), (4, 1, 3))
        paths, expected = prepare(self.root / 'outer-away', outer=outer)
        result = audit.audit_partition_geometry(**paths, expected_sha256=expected)
        self.assertIs(result['cavity_ball_and_clearance_certificate']['positive_gap_proved'], True)
        self.assertEqual(result['center_in_outer']['classification'], 'OUTSIDE')
        self.assertIs(result['exact_ten_moment_partition']['all_ten_residuals_zero'], True)
        self.assertIs(result['partition_geometry_valid'], False)

    def test_inward_design_cannot_become_a_valid_solid_via_cancellation(self):
        vertices, faces = box((Q(1, 4), -Q(1, 16), Q(1, 2)),
                              (Q(3, 8), Q(1, 16), Q(3, 4)))
        paths, expected = prepare(self.root / 'inward-design',
                                  design=(vertices, tuple((a, c, b) for a, b, c in faces)))
        result = audit.audit_partition_geometry(**paths, expected_sha256=expected)
        self.assertIs(result['all_material_surfaces_exact_embedded_closed_oriented'], True)
        self.assertIs(result['exact_ten_moment_partition']['all_ten_residuals_zero'], True)
        self.assertIs(result['individual_single_embedded_outward_solids']['D'], False)
        self.assertIs(result['partition_geometry_valid'], False)

    def test_wrong_fixed_orientation_is_rejected_even_with_legal_surfaces(self):
        outer = box((-1, -1, -1), (1, 1, 3))
        design = box((Q(1, 4), -Q(1, 16), Q(1, 2)), (Q(3, 8), Q(1, 16), Q(3, 4)))
        vertices, faces = cavity_boundary(outer, design)
        fixed = vertices, tuple((a, c, b) for a, b, c in faces)
        paths, expected = prepare(self.root / 'wrong-fixed', fixed=fixed)
        result = audit.audit_partition_geometry(**paths, expected_sha256=expected)
        self.assertIs(result['all_material_surfaces_exact_embedded_closed_oriented'], True)
        self.assertIs(result['design_strictly_inside_outer'], True)
        self.assertIs(result['fixed_component_correspondence']['exact_outer_and_reversed_cavity_components'], False)
        self.assertIs(result['exact_ten_moment_partition']['all_ten_residuals_zero'], False)
        self.assertIs(result['partition_geometry_valid'], False)

    def test_open_fixed_surface_is_an_explicit_rejection_not_a_pass(self):
        paths, expected = prepare(self.root / 'open-fixed')
        rows = paths['F'].read_text().splitlines()
        paths['F'].write_text('\n'.join(rows[:-1])+'\n')
        expected['F'] = sha256(paths['F'])
        result = audit.audit_partition_geometry(**paths, expected_sha256=expected)
        self.assertIs(result['exact_surface_audits']['F']['exact_embedded_closed_oriented_2manifold'], False)
        self.assertIs(result['partition_geometry_valid'], False)


class CompleteOriginalShaftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SHAFT.is_file():
            raise AssertionError('Required immutable original-shaft fixture is missing: '+str(SHAFT))
        if sha256(SHAFT) != ORIGINAL_SHAFT_SHA256:
            raise AssertionError('The immutable original-shaft fixture changed')
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.paths, cls.expected = prepare(cls.root / 'valid')
        cls.report = full(cls.paths, cls.expected)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_small_materials_prove_complete_real_original_shaft(self):
        result = self.report
        self.assertIs(result['partition_geometry_valid'], True)
        self.assertIs(result['full_original_shaft_contained_in_outer'], True)
        self.assertIs(result['design_shaft_separation_certified'], True)
        self.assertIs(result['complete_original_shaft_in_fixed'], True)
        self.assertIs(result['research_geometry_gate_passed'], True)
        self.assertTrue(result['set_semantics'].startswith('CERTIFIED:'))
        self.assertTrue(result['containment_proof'].startswith('CERTIFIED:'))
        self.assertTrue(result['complete_shaft_proof'].startswith('CERTIFIED:'))
        self.assertEqual(result['inputs']['S']['sha256'], ORIGINAL_SHAFT_SHA256)
        self.assertIs(result['whole_shaft_containment']['coverage']['all_candidate_pairs_checked'], True)
        self.assertIs(result['whole_shaft_design_gap']['surface_certificates_recomputed_here'], True)
        self.assertIs(result['whole_shaft_design_gap']['scientific_flags']['full_original_shaft_contained_in_fixed_material'], False)
        self.assertIs(result['whole_shaft_design_gap_local_flag_scope']['not_a_negative_whole_material_containment_result'], True)
        self.assertEqual(result['whole_shaft_design_gap_local_flag_scope']['whole_material_conclusion_field'],
                         'complete_original_shaft_in_fixed')
        self.assertTrue(all(value is False for value in result['scientific_flags'].values()))
        self.assertIs(result['physical_approval'], False)
        self.assertIs(result['optimization_admitted'], False)

    def test_successful_guard_and_partition_cannot_hide_missing_shaft_ends(self):
        paths, expected = prepare(self.root / 'truncated-outer',
                                  outer=box((-1, -1, Q(1, 8)), (1, 1, Q(3, 2))))
        result = full(paths, expected)
        self.assertIs(result['partition_geometry_valid'], True)
        self.assertIs(result['design_shaft_separation_certified'], True)
        self.assertIs(result['full_original_shaft_contained_in_outer'], False)
        self.assertIs(result['complete_original_shaft_in_fixed'], False)
        self.assertIs(result['research_geometry_gate_passed'], False)
        self.assertEqual(result['status'], 'PARTIAL_GUARD_PASS_SHAFT_CONTAINMENT_REJECTED')
        self.assertIs(result['whole_shaft_containment']['shaft_not_contained_counterexample_certified'], True)
        self.assertTrue(result['set_semantics'].startswith('CERTIFIED:'))
        self.assertTrue(result['containment_proof'].startswith('CERTIFIED:'))
        self.assertTrue(result['complete_shaft_proof'].startswith('NOT_ESTABLISHED'))

    def test_positive_but_subregistered_gap_cannot_complete_material_gate(self):
        design = box((Q(63, 1024), -Q(1, 1024), Q(1, 2)),
                     (Q(65, 1024), Q(1, 1024), Q(3, 4)))
        paths, expected = prepare(self.root / 'insufficient-gap', design=design)
        result = full(paths, expected)
        self.assertIs(result['partition_geometry_valid'], True)
        self.assertIs(result['full_original_shaft_contained_in_outer'], True)
        gap = rational(result['whole_shaft_design_gap']['radial_gap_lower_bound_reference'])
        self.assertGreater(gap, 0)
        self.assertLess(gap, Q(1, 500))
        self.assertIs(result['design_shaft_separation_certified'], False)
        self.assertIs(result['complete_original_shaft_in_fixed'], False)

    def test_malformed_outer_retains_true_guard_but_cannot_emit_complete_pass(self):
        paths, expected = prepare(self.root / 'degenerate-outer')
        with paths['M'].open('a') as stream:
            stream.write('f 1 2 2\n')
        expected['M'] = sha256(paths['M'])
        result = full(paths, expected)
        self.assertIs(result['inputs']['M']['strict_binary64_triangle_parse_passed'], False)
        self.assertIs(result['partition_geometry_valid'], False)
        self.assertIs(result['design_shaft_separation_certified'], True)
        self.assertEqual(result['status'], 'PARTIAL_GUARD_PASS_SHAFT_CONTAINMENT_REJECTED')
        self.assertIs(result['research_geometry_gate_passed'], False)
        self.assertIs(result['input_sha256_checked_before_and_after'], True)

    def test_original_shaft_cannot_be_replaced_even_with_a_new_self_consistent_manifest(self):
        shaft = self.root / 'substituted-shaft.obj'
        shaft.write_bytes(SHAFT.read_bytes()+b'# same geometry, changed identity\n')
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_SHAFT_IDENTITY_CHANGED'):
            audit.audit_material(**self.paths, S=shaft,
                expected_sha256=dict(self.expected, S=sha256(shaft)))
        with self.assertRaisesRegex(ValueError, 'INPUT_SHA256_MISMATCH_S'):
            full(self.paths, self.expected, shaft=shaft)

    def test_exact_manifest_keys_and_sha_types_fail_closed(self):
        proper = dict(self.expected, S=ORIGINAL_SHAFT_SHA256)
        for manifest in ({}, self.expected, dict(proper, external_PASS=True),
                         dict(proper, M='0'*63), dict(proper, M=True), dict(proper, M='A'*64)):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                audit.audit_material(**self.paths, S=SHAFT, expected_sha256=manifest)

    def test_final_hash_detects_mutation_after_real_geometric_computations(self):
        paths, expected = prepare(self.root / 'late-mutation')
        actual_guard = audit.audit_radial_shaft_guard

        def real_guard_then_change_file(*args, **kwargs):
            result = actual_guard(*args, **kwargs)
            with paths['F'].open('a') as stream:
                stream.write('# changed after all geometry computations\n')
            return result

        with patch.object(audit, 'audit_radial_shaft_guard', side_effect=real_guard_then_change_file):
            with self.assertRaisesRegex(ValueError, 'INPUT_CHANGED_DURING_AUDIT_F'):
                full(paths, expected)


class FinalP19PacketIntegrationTests(unittest.TestCase):
    def test_final_packet_replays_all_geometry_and_preserves_denied_approvals(self):
        packet = Path(os.environ.get('W4_P19_FINAL_CASE_ROOT', ROOT/'P19_material_case'))
        self.assertTrue(packet.is_dir(), 'Required P19 final packet is missing: '+str(packet))
        manifest_path = packet/'manifest.json'
        self.assertTrue(manifest_path.is_file(), 'Required P19 final manifest is missing')
        self.assertEqual(sha256(manifest_path), FINAL_MANIFEST_SHA256,
                         'The independently frozen P19 packet identity changed')
        manifest = json.loads(manifest_path.read_text())
        names = manifest['material_files']
        self.assertEqual(set(names), {'M', 'F', 'D', 'S'})
        paths = {name: packet/relative for name, relative in names.items()}
        expected = {name: manifest['files_sha256'][relative] for name, relative in names.items()}
        before = {name: sha256(path) for name, path in paths.items()}
        self.assertEqual(before, expected)
        result = audit.audit_material(**paths, expected_sha256=expected)
        self.assertIs(result['partition_geometry_valid'], True)
        self.assertIs(result['full_original_shaft_contained_in_outer'], True)
        self.assertIs(result['design_shaft_separation_certified'], True)
        self.assertIs(result['complete_original_shaft_in_fixed'], True)
        self.assertIs(result['research_geometry_gate_passed'], True)
        self.assertEqual({name: sha256(path) for name, path in paths.items()}, before)
        self.assertTrue(all(value is False for value in result['scientific_flags'].values()))
        self.assertIs(result['optimization_admitted'], False)
        self.assertIs(result['training_admitted'], False)


if __name__ == '__main__':
    unittest.main()
