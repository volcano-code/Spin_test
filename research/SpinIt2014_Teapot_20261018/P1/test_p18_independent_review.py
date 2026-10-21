"""Independent analytic and frozen-witness checks for the P18 solid proof.

These tests use known solids and exact rational expected answers.  They do not
replace the exhaustive real-mesh surface audits or grant an approval flag.
"""
from fractions import Fraction as Q
import copy
from itertools import permutations
from pathlib import Path
import unittest

from p17_boundary_certificate import ExactMesh, read_binary64_obj
from p18_solid_domain import (
    FALSE_FLAGS, check_report_replay, classify_point, exact_signed_volume,
    fixed_component_correspondence, point_triangle_distance_squared,
    radial_ball_clearance, sqrt_bounds,
)
from p18_shaft_domain import (
    clip_triangle_to_prism, halfplanes, plane_value, verify_shaft_prism_band,
)


ROOT = Path(__file__).resolve().parent
PACKET = ROOT / 'P17_material_case'
BOX_FACES = (
    (0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
    (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
    (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7),
)


def mesh(vertices, faces, label='independent analytic fixture'):
    return ExactMesh(path=label, sha256='analytic-fixture-not-a-source-hash',
                     vertices=tuple(tuple(Q(x) for x in p) for p in vertices),
                     faces=tuple(tuple(f) for f in faces))


def box(half=Q(1), center=(0, 0, 0)):
    corners = ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
               (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))
    return mesh(tuple(tuple(Q(c) + Q(half) * x for c, x in zip(center, p))
                      for p in corners), BOX_FACES)


def tetrahedron():
    return mesh(((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
                ((0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)))


def reverse(source):
    return mesh(source.vertices, ((a, c, b) for a, b, c in source.faces))


def combine(*sources):
    vertices, faces = [], []
    for source in sources:
        offset = len(vertices)
        vertices.extend(source.vertices)
        faces.extend(tuple(i + offset for i in f) for f in source.faces)
    return mesh(vertices, faces)


def from_fraction_json(item):
    return Q(int(item['numerator']), int(item['denominator']))


class ExactRayIndependentReview(unittest.TestCase):
    def test_box_inside_outside_face_edge_and_vertex(self):
        surface = box()
        for point, expected in (
            ((Q(1, 7), Q(-1, 5), Q(2, 9)), 'INSIDE'),
            ((3, 0, 0), 'OUTSIDE'),
            ((1, Q(1, 7), Q(-1, 3)), 'BOUNDARY'),
            ((1, 1, Q(1, 7)), 'BOUNDARY'),
            ((1, 1, 1), 'BOUNDARY'),
        ):
            with self.subTest(point=point):
                self.assertEqual(classify_point(surface, point)['classification'], expected)
        self.assertEqual(exact_signed_volume(surface), Q(8))

    def test_tetrahedron_non_dyadic_query_and_oblique_face(self):
        surface = tetrahedron()
        for point, expected in (
            ((Q(1, 8),) * 3, 'INSIDE'),
            ((1, 1, 1), 'OUTSIDE'),
            ((Q(1, 3),) * 3, 'BOUNDARY'),
            ((Q(1, 2), Q(1, 2), 0), 'BOUNDARY'),
            ((0, 0, 0), 'BOUNDARY'),
        ):
            with self.subTest(point=point):
                self.assertEqual(classify_point(surface, point)['classification'], expected)
        self.assertEqual(exact_signed_volume(surface), Q(1, 6))

    def test_parity_does_not_certify_outward_orientation(self):
        reversed_surface = reverse(tetrahedron())
        result = classify_point(reversed_surface, (Q(1, 8),) * 3)
        self.assertEqual(result['classification'], 'INSIDE')
        self.assertTrue(result['surface_validity_must_be_certified_separately'])
        self.assertEqual(exact_signed_volume(reversed_surface), Q(-1, 6))

    def test_vertex_ray_retried_without_retaining_partial_crossings(self):
        result = classify_point(box(), (0, 0, 0), directions=((1, 1, 1), (1, 2, 4)))
        self.assertEqual(result['classification'], 'INSIDE')
        self.assertEqual(result['direction'], [1, 2, 4])
        self.assertEqual(result['rejected_degenerate_rays'], 1)
        self.assertEqual(result['crossings'], 1)

    def test_coplanar_ray_retried_and_all_ambiguous_rays_fail_closed(self):
        result = classify_point(box(), (2, 0, 1), directions=((1, 1, 0), (1, 2, 4)))
        self.assertEqual(result['classification'], 'OUTSIDE')
        self.assertEqual(result['rejected_degenerate_rays'], 1)
        for directions in ((), ((1, 1, 1),), ((1, 1, 1), (-1, -1, -1))):
            with self.subTest(directions=directions):
                with self.assertRaisesRegex(ValueError, 'NO_NONDEGENERATE_EXACT_RAY_DIRECTION'):
                    classify_point(box(), (0, 0, 0), directions=directions)

    def test_no_tolerance_near_boundary_and_invalid_rays_rejected(self):
        epsilon = Q(1, 2 ** 100)
        self.assertEqual(classify_point(box(), (1 - epsilon, 0, 0))['classification'], 'INSIDE')
        self.assertEqual(classify_point(box(), (1 + epsilon, 0, 0))['classification'], 'OUTSIDE')
        for direction in ((0, 0, 0), (1.0, 2, 4), (True, 2, 4), (1, 2)):
            with self.subTest(direction=direction):
                with self.assertRaises(ValueError):
                    classify_point(box(), (0, 0, 0), directions=(direction,))

    def test_invalid_queries_empty_boundary_and_degenerate_triangle(self):
        for point in ((True, 0, 0), (float('inf'), 0, 0), (float('nan'), 0, 0), (0, 0)):
            with self.subTest(point=point):
                with self.assertRaises(ValueError):
                    classify_point(box(), point)
        with self.assertRaises(ValueError):
            classify_point(mesh((), ()), (0, 0, 0))
        with self.assertRaises(ValueError):
            classify_point(mesh(((0, 0, 0), (1, 0, 0), (2, 0, 0)), ((0, 1, 2),)), (0, 1, 0))


class ExactDistanceIndependentReview(unittest.TestCase):
    def test_interior_edge_vertex_and_offplane_distances(self):
        triangle = ((0, 0, 0), (2, 0, 0), (0, 2, 0))
        for point, expected in (
            ((Q(1, 2), Q(1, 2), 3), Q(9)),
            ((2, 2, 0), Q(2)),
            ((3, 0, 4), Q(17)),
            ((1, -2, 3), Q(13)),
            ((1, 1, 0), Q(0)),
            ((Q(1, 2), Q(1, 2), 0), Q(0)),
        ):
            with self.subTest(point=point):
                self.assertEqual(point_triangle_distance_squared(point, triangle), expected)

    def test_oblique_face_and_permutation_invariance(self):
        triangle = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        for ordering in permutations(triangle):
            self.assertEqual(point_triangle_distance_squared((0, 0, 0), ordering), Q(1, 3))
            self.assertEqual(point_triangle_distance_squared((1, 1, 1), ordering), Q(4, 3))

    def test_non_dyadic_coordinates_and_degenerate_rejection(self):
        triangle = ((0, 0, Q(1, 5)), (Q(2, 3), 0, Q(1, 5)), (0, Q(2, 3), Q(1, 5)))
        self.assertEqual(point_triangle_distance_squared((Q(1, 7), Q(1, 7), Q(3, 5)), triangle), Q(4, 25))
        with self.assertRaises(ValueError):
            point_triangle_distance_squared((0, 1, 0), ((0, 0, 0), (1, 0, 0), (2, 0, 0)))

    def test_rational_sqrt_bounds_are_proved_and_conservative(self):
        for value, grid in ((Q(2), 1000), (Q(1, 3), 17), (Q(0), 100),
                            (Q(9, 16), 100), (Q(1, 10 ** 30), 1000)):
            with self.subTest(value=value, grid=grid):
                lower, upper = sqrt_bounds(value, grid)
                self.assertIsInstance(lower, Q)
                self.assertIsInstance(upper, Q)
                self.assertLessEqual(lower * lower, value)
                self.assertGreaterEqual(upper * upper, value)
                self.assertLessEqual(upper - lower, Q(1, grid))
        self.assertEqual(sqrt_bounds(Q(9, 16), 100), (Q(3, 4), Q(3, 4)))
        for value, grid in ((-1, 100), (1, 0), (1, -1), (1, 1.0), (1, True)):
            with self.subTest(value=value, grid=grid):
                with self.assertRaises(ValueError):
                    sqrt_bounds(value, grid)

    def test_ball_bounds_known_nested_boxes(self):
        result = radial_ball_clearance(box(2), box(Q(1, 4)), (0, 0, 0))
        self.assertEqual(from_fraction_json(result['minimum_center_to_outer_distance_squared']), Q(4))
        self.assertEqual(from_fraction_json(result['maximum_design_vertex_radius_squared']), Q(3, 16))
        self.assertTrue(result['positive_gap_proved'])
        self.assertGreater(from_fraction_json(result['cavity_to_outer_clearance_lower_bound_reference']), Q(3, 2))
        self.assertEqual(result['outer_faces_tested'], 12)
        self.assertEqual(result['design_vertices_tested'], 8)

    def test_positive_gap_alone_does_not_prove_containment(self):
        center = (10, 0, 0)
        result = radial_ball_clearance(box(), box(Q(1, 4), center), center)
        self.assertTrue(result['positive_gap_proved'])
        self.assertEqual(classify_point(box(), center)['classification'], 'OUTSIDE')
        self.assertTrue(result['entire_solid_containment_requires_closed_embedded_surfaces_and_center_inside'])
        self.assertFalse(result['whole_object_wall_thickness_or_printability_certified'])
        self.assertNotIn('regular_solid_partition_certified', result)

    def test_coarse_sqrt_grid_can_only_withhold_positive_gap(self):
        result = radial_ball_clearance(box(Q(1, 10 ** 12)), box(Q(1, 10 ** 14)), (0, 0, 0))
        self.assertFalse(result['positive_gap_proved'])
        self.assertLessEqual(from_fraction_json(result['cavity_to_outer_clearance_lower_bound_reference']), 0)


class FixedComponentIndependentReview(unittest.TestCase):
    def test_outer_plus_reversed_cavity_and_exact_volume(self):
        outer, design = box(2), box(Q(1, 4))
        fixed = combine(outer, reverse(design))
        result = fixed_component_correspondence(outer, fixed, design)
        self.assertTrue(result['exact_outer_and_reversed_cavity_components'])
        self.assertTrue(result['no_hidden_duplicate_cancellation'])
        self.assertTrue(result['alone_is_not_an_embedded_solid_certificate'])
        self.assertEqual(result['fixed_boundary_components'], 2)
        self.assertEqual(result['component_face_counts'], [12, 12])
        self.assertEqual(exact_signed_volume(fixed), Q(64) - Q(1, 8))

    def test_positive_volume_does_not_fix_wrong_cavity_orientation(self):
        outer, design = box(2), box(Q(1, 4))
        fixed = combine(outer, design)
        self.assertGreater(exact_signed_volume(fixed), 0)
        self.assertFalse(fixed_component_correspondence(outer, fixed, design)['exact_outer_and_reversed_cavity_components'])

    def test_opposite_duplicate_facets_cannot_hide_in_signed_chain(self):
        outer, design = box(2), box(Q(1, 4))
        fixed = combine(outer, reverse(design))
        a, b, c = fixed.faces[0]
        corrupted = mesh(fixed.vertices, fixed.faces + ((a, b, c), (a, c, b)))
        self.assertEqual(exact_signed_volume(corrupted), exact_signed_volume(fixed))
        result = fixed_component_correspondence(outer, corrupted, design)
        self.assertTrue(all(row['unique_match'] for row in result['matches']))
        self.assertFalse(result['no_hidden_duplicate_cancellation'])
        self.assertFalse(result['exact_outer_and_reversed_cavity_components'])

    def test_extra_component_rejected_even_with_cancelled_total_moments(self):
        outer, design = box(2), box(Q(1, 4))
        bubble = tetrahedron()
        fixed = combine(outer, reverse(design), bubble, reverse(bubble))
        self.assertEqual(exact_signed_volume(fixed), exact_signed_volume(outer) - exact_signed_volume(design))
        result = fixed_component_correspondence(outer, fixed, design)
        self.assertEqual(result['fixed_boundary_components'], 4)
        self.assertFalse(result['exact_outer_and_reversed_cavity_components'])

    def test_all_scientific_admission_flags_remain_literal_false(self):
        self.assertTrue(FALSE_FLAGS)
        for name, value in FALSE_FLAGS.items():
            with self.subTest(flag=name):
                self.assertIs(value, False)
        for name in ('W0_physical_tip_or_FD_approved', 'W2_teacher_training_allowed',
                     'full_original_shaft_contained_in_fixed_material',
                     'native_Cherchi_implicit_region_partition_certified',
                     'MuJoCo_real_optimized_before_after_executed'):
            self.assertIs(FALSE_FLAGS[name], False)


class ShaftWitnessIndependentReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The checked-in packet is required: absence must fail, never skip.
        cls.design = read_binary64_obj(PACKET / 'material/D_native_carveable_trial.obj')
        cls.shaft = read_binary64_obj(PACKET / 'source/shaft-reference.obj')
        cls.prism = verify_shaft_prism_band(cls.shaft,
            min(p[2] for p in cls.design.vertices), max(p[2] for p in cls.design.vertices))

    def test_frozen_sources_and_actual_saved_shaft_intrusion(self):
        self.assertEqual(self.design.sha256, '1d4a0673e9297d95adfb5722158ba1d859a83099046d01116a2b363cb3cb386b')
        self.assertEqual(self.shaft.sha256, '65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0')
        polygon = self.prism['polygon']
        self.assertEqual(len(polygon), 32)
        # Independently evaluate signed edge determinants, without plane_value.
        inside = []
        for index, (x, y, z) in enumerate(self.design.vertices):
            determinants = [(b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
                            for a, b in zip(polygon, polygon[1:] + polygon[:1])]
            if all(value > 0 for value in determinants):
                self.assertLess(self.prism['z_lo'], z)
                self.assertLess(z, self.prism['z_hi'])
                inside.append(index)
        self.assertEqual(len(inside), 74)
        # One exact original boundary point in an open shaft neighborhood is a
        # strict counterexample to full-shaft protection once D is embedded.
        witness = self.design.vertices[inside[0]]
        self.assertTrue(all(plane_value(plane, witness) > 0 for plane in self.prism['planes']))

    def test_real_clipped_face_witness_is_exact_original_face_point(self):
        planes = self.prism['planes']
        index = next(i for i, point in enumerate(self.design.vertices)
                     if all(plane_value(plane, point) > 0 for plane in planes))
        face = next(f for f in self.design.faces if index in f)
        triangle = tuple(self.design.vertices[i] for i in face)
        result = clip_triangle_to_prism(triangle, planes)
        self.assertIsNotNone(result)
        weights, point = result['barycentric'], result['point']
        self.assertEqual(sum(weights), 1)
        self.assertGreaterEqual(min(weights), 0)
        self.assertEqual(point, tuple(sum(weights[i] * triangle[i][j] for i in range(3)) for j in range(3)))
        self.assertTrue(all(value > 0 for value in result['halfplane_signs']))

    def test_clip_detects_edge_crossing_without_an_inside_vertex(self):
        polygon = tuple(tuple(Q(v) for v in p) for p in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
        planes = halfplanes(polygon)
        triangle = tuple(tuple(Q(v) for v in p) for p in ((-2, 0, 0), (2, 0, 0), (0, 2, 1)))
        self.assertFalse(any(all(plane_value(p, v) > 0 for p in planes) for v in triangle))
        result = clip_triangle_to_prism(triangle, planes)
        self.assertIsNotNone(result)
        self.assertTrue(all(value > 0 for value in result['halfplane_signs']))

    def test_boundary_only_shaft_contact_is_not_strict_intrusion(self):
        polygon = tuple(tuple(Q(v) for v in p) for p in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
        planes = halfplanes(polygon)
        for triangle in (
            ((1, -1, 0), (1, 1, 0), (1, 0, 1)),
            ((1, 0, 0), (2, -1, 0), (2, 1, 0)),
            ((2, 0, 0), (3, -1, 0), (3, 1, 0)),
        ):
            with self.subTest(triangle=triangle):
                self.assertIsNone(clip_triangle_to_prism(tuple(tuple(Q(x) for x in p) for p in triangle), planes))

    def test_frozen_fixed_components_match_and_volume_is_exact_partition(self):
        outer = read_binary64_obj(PACKET / 'material/M_repaired_outer.obj')
        fixed = read_binary64_obj(PACKET / 'material/F_repaired_fixed_trial.obj')
        self.assertEqual(outer.sha256, '4c2e4d480d1041f4817128a8b4b61675d80a699e448e7a5a253311c1805a3aa2')
        self.assertEqual(fixed.sha256, '47c08ee597d5666069416985e0dc8900d204481c590b73596f90daccd2b068d1')
        result = fixed_component_correspondence(outer, fixed, self.design)
        self.assertTrue(result['exact_outer_and_reversed_cavity_components'])
        self.assertEqual(result['component_face_counts'], [7558, 640])
        self.assertEqual(exact_signed_volume(outer), exact_signed_volume(fixed) + exact_signed_volume(self.design))


class ReplayIndependentReview(unittest.TestCase):
    def setUp(self):
        # A small analytic proof record exercises the replay trust boundary;
        # the production CLI must itself supply the independently replayed side.
        self.replayed = dict(optimization_admitted=False,
            saved_repaired_solid_partition_certified=True,
            shaft_excluded_from_design_domain=False,
            scientific_flags=dict(FALSE_FLAGS),
            p18_proof_source_sha256={'analytic_fixture.py': 'review-fixture-sha'},
            exact_squared_distance={'numerator': '1', 'denominator': '3'},
            audit_elapsed_seconds=1.25,
            nested={'elapsed_seconds': 0.25, 'positive_volume_overlap': True})

    def test_replay_accepts_only_time_measurement_differences(self):
        saved = copy.deepcopy(self.replayed)
        saved['audit_elapsed_seconds'] = 9.5
        saved['nested']['elapsed_seconds'] = 2.5
        result = check_report_replay(saved, self.replayed)
        self.assertEqual(result['status'], 'P18_EXACT_PROOF_REPLAY_MATCH')
        self.assertIs(result['scientific_admission'], False)
        self.assertIs(result['protected_shaft_exclusion'], False)

    def test_replay_rejects_claim_upgrade_boolean_integer_and_deleted_fact(self):
        changes = (
            lambda report: report.update(optimization_admitted=True),
            lambda report: report.update(shaft_excluded_from_design_domain=True),
            lambda report: report.update(optimization_admitted=0),
            lambda report: report['scientific_flags'].update(W0_physical_tip_or_FD_approved=True),
            lambda report: report['nested'].pop('positive_volume_overlap'),
        )
        for change in changes:
            with self.subTest(change=change):
                saved = copy.deepcopy(self.replayed)
                change(saved)
                with self.assertRaisesRegex(ValueError, 'P18_SAVED_PROOF_DIFFERS_FROM_EXACT_REPLAY'):
                    check_report_replay(saved, self.replayed)

    def test_replay_rejects_exact_rational_or_source_identity_tampering(self):
        for field, key, replacement in (
            ('exact_squared_distance', 'numerator', '2'),
            ('p18_proof_source_sha256', 'analytic_fixture.py', 'changed-source-sha'),
        ):
            with self.subTest(field=field):
                saved = copy.deepcopy(self.replayed)
                saved[field][key] = replacement
                with self.assertRaisesRegex(ValueError, 'P18_SAVED_PROOF_DIFFERS_FROM_EXACT_REPLAY'):
                    check_report_replay(saved, self.replayed)


if __name__ == '__main__':
    unittest.main()
