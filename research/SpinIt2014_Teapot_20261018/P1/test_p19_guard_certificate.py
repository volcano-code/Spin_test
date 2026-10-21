"""Independent positive-guard, forged-proof and real frozen-outer regressions."""
from copy import deepcopy
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from p17_boundary_certificate import read_binary64_obj
from p18_exact_surface import audit_exact_surface
from p19_guard_certificate import (
    MINIMUM_GAP, ORIGINAL_SHAFT_SHA256, P18_REPORT_SHA256,
    audit_frozen_outer_shaft_intrusion, audit_radial_shaft_guard,
)


ROOT = Path(__file__).resolve().parent
PACKET = ROOT / 'P17_material_case'
SHAFT = PACKET / 'source/shaft-reference.obj'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def annular_square_prism(inner=Q(1, 16), outer=Q(1, 4)):
    """Explicit genus-one solid; its exact minimum XY radius is inner."""
    ring = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    vertices = tuple((r * x, r * y, z) for z in (Q(1, 2), Q(3, 4))
                     for r in (outer, inner) for x, y in ring)
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.extend(((i, j, 8 + j), (i, 8 + j, 8 + i),
                      (4 + i, 12 + j, 4 + j), (4 + i, 12 + i, 12 + j),
                      (8 + i, 8 + j, 12 + j), (8 + i, 12 + j, 12 + i),
                      (i, 4 + j, j), (i, 4 + i, 4 + j)))
    return vertices, tuple(faces)


def save_mesh(path, vertices, faces):
    data = ''.join('v ' + ' '.join(format(float(x), '.17g') for x in p) + '\n'
                   for p in vertices)
    data += ''.join('f ' + ' '.join(str(i + 1) for i in face) + '\n' for face in faces)
    path.write_text(data, encoding='ascii')
    return path


def fraction(item):
    return Q(int(item['numerator']), int(item['denominator']))


class PositiveGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.design = save_mesh(cls.root / 'annular-design.obj', *annular_square_prism())
        cls.expected = dict(design=sha256(cls.design), shaft=ORIGINAL_SHAFT_SHA256)
        cls.report = audit_radial_shaft_guard(cls.design, SHAFT, expected_sha256=cls.expected)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_known_annular_solid_has_exact_radial_minimum_and_required_gap(self):
        result = self.report
        self.assertEqual(result['design_triangles_exactly_processed'], 32)
        self.assertEqual(result['shaft_vertices_exactly_processed'], 258)
        minimum = result['minimum_design_surface_projected_radius']
        self.assertEqual(Q(minimum['squared_distance_exact']), Q(1, 256))
        self.assertEqual(Q(minimum['lower_bound_reference_exact']), Q(1, 16))
        self.assertGreaterEqual(fraction(result['full_solid_distance_lower_bound_reference']), MINIMUM_GAP)
        self.assertIs(result['full_original_shaft_disjoint_from_design'], True)
        self.assertIs(result['positive_full_solid_distance_certified'], True)

    def test_whole_saved_shaft_is_bounded_by_the_radius_not_one_core_point(self):
        shaft = read_binary64_obj(SHAFT)
        maximum = max(x * x + y * y for x, y, _ in shaft.vertices)
        bound = self.report['maximum_shaft_vertex_projected_radius']
        self.assertEqual(Q(bound['squared_distance_exact']), maximum)
        self.assertGreaterEqual(Q(bound['upper_bound_reference_exact']) ** 2, maximum)
        self.assertIs(self.report['shaft_embedded_connected_outward_bounded_solid'], True)
        self.assertEqual(self.report['inputs']['shaft']['sha256'], ORIGINAL_SHAFT_SHA256)

    def test_outside_anchor_and_surface_certificates_are_recomputed_and_bound(self):
        result = self.report
        self.assertIs(result['surface_certificates_recomputed_here'], True)
        self.assertEqual(result['axis_anchor_classification']['classification'], 'OUTSIDE')
        self.assertLess(Q(result['axis_anchor_exact'][2]), Q(1, 2))
        self.assertIs(result['all_z_axis_cylinder_excluded_from_design_solid'], True)
        self.assertEqual(result['surface_audits']['design']['input']['sha256'], self.expected['design'])
        self.assertEqual(result['surface_audits']['shaft']['input']['sha256'], ORIGINAL_SHAFT_SHA256)

    def test_guard_certificate_does_not_grant_outer_containment_or_approval(self):
        self.assertIs(self.report['full_original_shaft_in_F_requires_separate_outer_containment'], True)
        self.assertIs(self.report['optimization_admitted'], False)
        self.assertIs(self.report['training_admitted'], False)
        self.assertTrue(all(flag is False for flag in self.report['scientific_flags'].values()))
        self.assertIsNone(self.report['geometric_tolerance'])
        self.assertIs(self.report['geometry_modified'], False)

    def test_positive_but_sub_registered_gap_is_not_accepted(self):
        path = save_mesh(self.root / 'too-small-gap.obj', *annular_square_prism(inner=Q(61, 1000)))
        result = audit_radial_shaft_guard(path, SHAFT,
            expected_sha256=dict(design=sha256(path), shaft=ORIGINAL_SHAFT_SHA256))
        self.assertGreater(fraction(result['radial_gap_lower_bound_reference']), 0)
        self.assertLess(fraction(result['radial_gap_lower_bound_reference']), MINIMUM_GAP)
        self.assertIs(result['radial_bounds_meet_registered_gap'], False)
        self.assertIs(result['full_original_shaft_disjoint_from_design'], False)
        self.assertIsNone(result['full_solid_distance_lower_bound_reference'])

    def test_inward_orientation_cannot_turn_radial_bounds_into_a_solid_proof(self):
        vertices, faces = annular_square_prism()
        path = save_mesh(self.root / 'inward.obj', vertices, tuple((a, c, b) for a, b, c in faces))
        result = audit_radial_shaft_guard(path, SHAFT,
            expected_sha256=dict(design=sha256(path), shaft=ORIGINAL_SHAFT_SHA256))
        self.assertIs(result['radial_bounds_meet_registered_gap'], True)
        self.assertIs(result['surface_audits']['design']['exact_embedded_closed_oriented_2manifold'], True)
        self.assertIs(result['design_embedded_connected_outward_bounded_solid'], False)
        self.assertIs(result['full_original_shaft_disjoint_from_design'], False)
        self.assertIsNone(result['full_solid_distance_lower_bound_reference'])

    def test_open_surface_and_forged_pass_certificate_are_rejected(self):
        vertices, faces = annular_square_prism()
        path = save_mesh(self.root / 'open.obj', vertices, faces[1:])
        expected = dict(design=sha256(path), shaft=ORIGINAL_SHAFT_SHA256)
        result = audit_radial_shaft_guard(path, SHAFT, expected_sha256=expected)
        self.assertIs(result['design_embedded_connected_outward_bounded_solid'], False)
        self.assertIs(result['full_original_shaft_disjoint_from_design'], False)
        forged = deepcopy(result['surface_audits']['design'])
        forged['exact_embedded_closed_oriented_2manifold'] = True
        with self.assertRaisesRegex(ValueError, 'DIFFERS_FROM_REPLAY'):
            audit_radial_shaft_guard(path, SHAFT, expected_sha256=expected,
                                    design_surface_certificate=forged)

    def test_supplied_certificate_hash_and_boolean_type_are_not_trusted(self):
        for change in ('hash', 'integer'):
            with self.subTest(change=change):
                supplied = deepcopy(self.report['surface_audits']['design'])
                if change == 'hash':
                    supplied['input']['sha256'] = '0' * 64
                else:
                    supplied['exact_embedded_closed_oriented_2manifold'] = 1
                with self.assertRaisesRegex(ValueError, 'DIFFERS_FROM_REPLAY'):
                    audit_radial_shaft_guard(self.design, SHAFT, expected_sha256=self.expected,
                                            design_surface_certificate=supplied)

    def test_matching_external_proof_still_replays_and_only_timing_may_change(self):
        supplied = deepcopy(self.report['surface_audits']['design'])
        supplied['elapsed_seconds'] = 12345.0
        result = audit_radial_shaft_guard(self.design, SHAFT, expected_sha256=self.expected,
                                        design_surface_certificate=supplied,
                                        shaft_surface_certificate=self.report['surface_audits']['shaft'])
        self.assertIs(result['surface_certificates_recomputed_here'], True)
        self.assertEqual(result['supplied_surface_certificates_compared'], dict(design=True, shaft=True))
        self.assertIs(result['full_original_shaft_disjoint_from_design'], True)

    def test_rewriting_sha_and_manifest_cannot_replace_the_original_shaft(self):
        substituted = self.root / 'substituted-shaft.obj'
        substituted.write_bytes(SHAFT.read_bytes() + b'# changed byte identity\n')
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_SHAFT_IDENTITY_CHANGED'):
            audit_radial_shaft_guard(self.design, substituted,
                expected_sha256=dict(design=self.expected['design'], shaft=sha256(substituted)))
        with self.assertRaisesRegex(ValueError, 'INPUT_SHA256_MISMATCH'):
            audit_radial_shaft_guard(self.design, substituted, expected_sha256=self.expected)

    def test_hash_set_and_fixed_positive_guard_budget_fail_closed(self):
        for expected in ({}, {'design': self.expected['design']}, dict(self.expected, extra='0' * 64),
                         dict(design='not-a-hash', shaft=ORIGINAL_SHAFT_SHA256)):
            with self.subTest(expected=expected), self.assertRaises(ValueError):
                audit_radial_shaft_guard(self.design, SHAFT, expected_sha256=expected)
        for gap in (0, -1, Q(1, 1000), Q(1, 10), True, 0.002):
            with self.subTest(gap=gap), self.assertRaisesRegex(ValueError, 'MINIMUM_GAP_CHANGED'):
                audit_radial_shaft_guard(self.design, SHAFT, expected_sha256=self.expected, minimum_gap=gap)
        for grid in (0, -1, True, 1.0):
            with self.subTest(grid=grid), self.assertRaisesRegex(ValueError, 'SQRT_GRID'):
                audit_radial_shaft_guard(self.design, SHAFT, expected_sha256=self.expected, sqrt_grid=grid)

    def test_old_unexpanded_native_design_fails_whole_shaft_guard(self):
        path = PACKET / 'material/D_native_carveable_trial.obj'
        result = audit_radial_shaft_guard(path, SHAFT, expected_sha256=dict(
            design='1d4a0673e9297d95adfb5722158ba1d859a83099046d01116a2b363cb3cb386b',
            shaft=ORIGINAL_SHAFT_SHA256))
        self.assertIs(result['design_embedded_connected_outward_bounded_solid'], True)
        self.assertEqual(result['axis_anchor_classification']['classification'], 'OUTSIDE')
        self.assertLess(fraction(result['radial_gap_lower_bound_reference']), 0)
        self.assertIs(result['full_original_shaft_disjoint_from_design'], False)


class FrozenOuterCounterexampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outer = PACKET / 'material/M_repaired_outer.obj'
        cls.p18 = ROOT / 'P18_EXACT_SOLID_AND_SHAFT_REPORT.json'
        cls.report = audit_frozen_outer_shaft_intrusion(cls.outer, SHAFT, p18_report_path=cls.p18)

    def test_frozen_report_and_exact_seventy_five_vertex_counterexample(self):
        result = self.report
        self.assertEqual(sha256(self.p18), P18_REPORT_SHA256)
        self.assertEqual(result['strict_intruding_vertex_count'], 75)
        self.assertIs(result['full_original_shaft_subset_of_frozen_outer_refuted'], True)
        self.assertIs(result['positive_volume_shaft_outside_frozen_outer_proved'], True)
        self.assertIs(result['historical_embedding_certificate_authenticated'], True)
        self.assertIs(result['historical_embedding_certificate_recomputed_here'], False)
        self.assertIs(result['exact_vertex_and_ray_witnesses_recomputed_here'], True)
        self.assertTrue(all(Q(row['minimum_strict_wall_determinant_exact']) > 0
                            for row in result['strict_intruding_vertices']))

    def test_junction_extents_and_explicit_boundary_inside_classifications(self):
        result = self.report
        self.assertEqual(Q(result['strict_intruding_vertex_z_min_exact']), Q(1354083613885025, 9007199254740992))
        self.assertEqual(Q(result['strict_intruding_vertex_z_max_exact']), Q(6338306757043263, 4503599627370496))
        for item in result['exact_boundary_and_inside_ray_witnesses']:
            self.assertEqual(item['outer_classification']['classification'], 'BOUNDARY')
            self.assertEqual(item['shaft_classification']['classification'], 'INSIDE')
        self.assertEqual(result['exact_boundary_and_inside_ray_witnesses'][0]['vertex_index'], 3587)
        self.assertIs(result['vertex_range_is_not_an_exhaustive_violating_face_extent'], True)

    def test_authenticated_historical_proof_cannot_be_replaced_by_self_consistent_flags(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'forged-p18.json'
            altered = json.loads(self.p18.read_text())
            altered['scientific_flags']['full_original_shaft_contained_in_fixed_material'] = True
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, 'FROZEN_P18_REPORT_SHA256_MISMATCH'):
                audit_frozen_outer_shaft_intrusion(self.outer, SHAFT, p18_report_path=path)

    def test_frozen_outer_byte_tampering_rejected_before_witness_interpretation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'outer.obj'
            path.write_bytes(self.outer.read_bytes() + b'# modified\n')
            with self.assertRaisesRegex(ValueError, 'INPUT_SHA256_MISMATCH'):
                audit_frozen_outer_shaft_intrusion(path, SHAFT, p18_report_path=self.p18)


if __name__ == '__main__':
    unittest.main()
