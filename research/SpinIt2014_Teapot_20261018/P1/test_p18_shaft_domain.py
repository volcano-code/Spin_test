"""Analytic exact shaft/cavity counterexamples and frozen real P17 regression."""
from fractions import Fraction as Q
import hashlib
import math
import os
from pathlib import Path
import tempfile
import unittest

from p17_boundary_certificate import read_binary64_obj
from p18_shaft_domain import (
    audit_shaft_exclusion, clip_triangle_to_prism, convex_hull, halfplanes,
    projected_triangle_minimum_radius_squared, rational_sqrt_lower_bound,
    verify_shaft_prism_band,
)


SQUARE = tuple((Q(x), Q(y)) for x, y in [(-1, -1), (1, -1), (1, 1), (-1, 1)])
PLANES = halfplanes(SQUARE)
SHAFT_VERTICES = tuple((float(x), float(y), z) for z in (0., 2.) for x, y in SQUARE)
SHAFT_FACES = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7)]
for i in range(4):
    j = (i + 1) % 4
    SHAFT_FACES.extend([(i, j, j + 4), (i, j + 4, i + 4)])


def rational_triangle(points):
    return tuple(tuple(Q(value) for value in point) for point in points)


def save_obj(path, vertices, faces):
    rows = ['v ' + ' '.join(format(float(x), '.17g') for x in vertex) for vertex in vertices]
    rows += ['f ' + ' '.join(str(i + 1) for i in face) for face in faces]
    path.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tetra_faces(vertices):
    a, b, c = [tuple(Q(vertices[i][k]) - Q(vertices[0][k]) for k in range(3)) for i in (1, 2, 3)]
    determinant = (a[0] * (b[1] * c[2] - b[2] * c[1]) +
                   a[1] * (b[2] * c[0] - b[0] * c[2]) +
                   a[2] * (b[0] * c[1] - b[1] * c[0]))
    if not determinant:
        raise ValueError('test tetrahedron degenerate')
    faces = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]
    return faces if determinant > 0 else [face[::-1] for face in faces]


class ShaftDomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.shaft = self.root / 'shaft.obj'
        self.shaft_sha = save_obj(self.shaft, SHAFT_VERTICES, SHAFT_FACES)

    def tearDown(self):
        self.tmp.cleanup()

    def audit_tetra(self, vertices):
        design = self.root / 'design.obj'
        digest = save_obj(design, vertices, tetra_faces(vertices))
        return audit_shaft_exclusion(design, self.shaft, expected_prism_sides=4,
                                     expected_sha256={'design': digest, 'shaft': self.shaft_sha})

    def test_actual_faces_certify_square_prism(self):
        proof = verify_shaft_prism_band(read_binary64_obj(self.shaft), Q(1, 2), Q(3, 2), expected_sides=4)
        self.assertEqual(proof['polygon'], SQUARE)
        self.assertEqual(proof['z_lo'], 0)
        self.assertEqual(proof['z_hi'], 2)
        self.assertEqual(len(proof['source_wall_face_indices']), 8)
        self.assertTrue(proof['exact_wall_coverage'])

    def test_wrong_native_side_count_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SIDE_COUNT_CHANGED'):
            verify_shaft_prism_band(read_binary64_obj(self.shaft), Q(1, 2), Q(3, 2))

    def test_unequal_top_and_bottom_rings_rejected(self):
        vertices = list(SHAFT_VERTICES)
        vertices[4] = (-.9, -1., 2.)
        save_obj(self.shaft, vertices, SHAFT_FACES)
        with self.assertRaisesRegex(ValueError, 'RINGS_DIFFER'):
            verify_shaft_prism_band(read_binary64_obj(self.shaft), Q(1, 2), Q(3, 2), expected_sides=4)

    def test_missing_shaft_face_and_inward_wall_rejected(self):
        save_obj(self.shaft, SHAFT_VERTICES, SHAFT_FACES[:-1])
        with self.assertRaisesRegex(ValueError, 'NOT_CLOSED_OR_ORIENTED'):
            verify_shaft_prism_band(read_binary64_obj(self.shaft), Q(1, 2), Q(3, 2), expected_sides=4)
        save_obj(self.shaft, SHAFT_VERTICES, [face[::-1] for face in SHAFT_FACES])
        with self.assertRaisesRegex(ValueError, 'NOT_OUTWARD_ORIENTED'):
            verify_shaft_prism_band(read_binary64_obj(self.shaft), Q(1, 2), Q(3, 2), expected_sides=4)

    def test_geometry_inside_design_height_band_is_not_silently_ignored(self):
        vertices = list(SHAFT_VERTICES)
        vertices[4] = (-1., -1., 1.)
        save_obj(self.shaft, vertices, SHAFT_FACES)
        with self.assertRaisesRegex(ValueError, 'INTERMEDIATE_HEIGHT'):
            verify_shaft_prism_band(read_binary64_obj(self.shaft), Q(1, 2), Q(3, 2), expected_sides=4)

    def test_nonconvex_or_collinear_extra_ring_point_rejected(self):
        with self.assertRaisesRegex(ValueError, 'NOT_STRICTLY_CONVEX'):
            convex_hull([*SQUARE, (Q(0), Q(-1))])

    def test_clipping_detects_intrusion_even_when_every_vertex_is_outside(self):
        triangle = rational_triangle([(-2, 0, 1), (2, 0, 1), (0, 2, 1)])
        witness = clip_triangle_to_prism(triangle, PLANES)
        self.assertIsNotNone(witness)
        self.assertTrue(all(sign > 0 for sign in witness['halfplane_signs']))
        self.assertEqual(sum(witness['barycentric']), 1)
        self.assertGreaterEqual(min(witness['barycentric']), 0)

    def test_boundary_contact_is_not_strict_intrusion(self):
        triangle = rational_triangle([(1, 0, Q(1, 2)), (1, Q(1, 2), Q(1, 2)), (1, 0, 1)])
        self.assertIsNone(clip_triangle_to_prism(triangle, PLANES))

    def test_one_binary64_ulp_intrusion_is_retained_without_epsilon(self):
        vertices = [(math.nextafter(1., 0.), 0., 1.),
                    (1., .25, .75), (1., -.25, .75), (1., 0., 1.25)]
        result = self.audit_tetra(vertices)
        self.assertEqual(result['strict_intruding_vertex_count'], 1)
        self.assertEqual(result['strict_intruding_face_count'], 3)
        self.assertEqual(result['design_triangles_exactly_processed'], 4)
        self.assertIsNone(result['tolerance_used'])
        self.assertTrue(result['positive_volume_overlap_certified_if_D_is_embedded_bounded_regular_solid'])
        self.assertFalse(result['positive_volume_overlap_unconditionally_certified'])
        for witness in result['strict_intrusion_witnesses']:
            self.assertGreater(min(map(Q, witness['halfplane_signs_exact'])), 0)

    def test_no_surface_intrusion_does_not_automatically_certify_whole_shaft(self):
        result = self.audit_tetra([(1., 0., .5), (1., .5, .5), (1., 0., 1.), (2., .2, .6)])
        self.assertEqual(result['strict_intruding_face_count'], 0)
        self.assertFalse(result['entire_shaft_protected_certified'])
        self.assertTrue(result['whole_shaft_exclusion_still_requires_D_embeddedness_and_outside_anchor'])
        core = result['conservative_axis_core']
        self.assertTrue(core['squared_radius_strictly_below_D_surface'])
        self.assertTrue(core['squared_radius_strictly_below_shaft_walls'])
        self.assertTrue(core['core_does_not_certify_entire_original_shaft'])

    def test_projected_triangle_interior_contains_origin(self):
        result = projected_triangle_minimum_radius_squared(
            rational_triangle([(-1, -1, 1), (1, -1, 1), (0, 1, 2)]))
        self.assertEqual(result['squared_distance'], 0)
        self.assertEqual(result['feature'], 'PROJECTED_TRIANGLE_CONTAINS_ORIGIN')

    def test_exact_projected_edge_distance(self):
        result = projected_triangle_minimum_radius_squared(
            rational_triangle([(2, -1, 0), (2, 1, 0), (3, 0, 1)]))
        self.assertEqual(result['squared_distance'], 4)
        self.assertEqual(result['closest_xy'], (2, 0))
        self.assertEqual(result['edge_parameter'], Q(1, 2))

    def test_projected_degenerate_segment_crossing_axis(self):
        result = projected_triangle_minimum_radius_squared(
            rational_triangle([(-1, 0, 0), (1, 0, 0), (1, 0, 1)]))
        self.assertEqual(result['squared_distance'], 0)

    def test_rational_sqrt_is_a_proved_floor_not_an_error_tolerance(self):
        for value in (Q(0), Q(1), Q(2), Q(7, 31), Q(1, 10**30)):
            bound = rational_sqrt_lower_bound(value)
            self.assertLessEqual(bound * bound, value)
            self.assertLess(value, (bound + Q(1, 10**12)) ** 2)
        with self.assertRaises(ValueError): rational_sqrt_lower_bound(Q(-1))

    def test_axis_touching_design_has_no_certified_positive_core(self):
        result = self.audit_tetra([(0., 0., .5), (.5, 0., .5), (0., .5, .5), (0., 0., 1.)])
        self.assertEqual(Q(result['minimum_design_surface_projected_radius']['squared_distance_exact']), 0)
        self.assertFalse(result['conservative_axis_core']['positive_radius_available'])
        self.assertFalse(result['conservative_axis_core']['protected_if_D_is_embedded_bounded_regular_solid'])

    def test_wrong_frozen_input_hash_rejected(self):
        design = self.root / 'design.obj'
        vertices = [(1., 0., .5), (1., .5, .5), (1., 0., 1.), (2., .2, .6)]
        save_obj(design, vertices, tetra_faces(vertices))
        with self.assertRaisesRegex(ValueError, 'SHA256_MISMATCH'):
            audit_shaft_exclusion(design, self.shaft, expected_prism_sides=4,
                                  expected_sha256={'design': '0' * 64, 'shaft': self.shaft_sha})

    def test_real_frozen_p17_prism_and_exact_intrusion(self):
        case = Path(os.environ.get('W4_P18_CASE_ROOT', str(Path(__file__).parent / 'P17_material_case')))
        design = case / 'material/D_native_carveable_trial.obj'
        shaft = case / 'source/shaft-reference.obj'
        if not design.is_file() or not shaft.is_file():
            self.skipTest('Original P17 material files not supplied')
        result = audit_shaft_exclusion(design, shaft, expected_sha256={
            'design': '1d4a0673e9297d95adfb5722158ba1d859a83099046d01116a2b363cb3cb386b',
            'shaft': '65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0',
        })
        self.assertEqual(result['verified_shaft_prism']['side_count'], 32)
        self.assertEqual(len(result['verified_shaft_prism']['source_wall_face_indices']), 64)
        self.assertEqual(result['design_triangles_exactly_processed'], 640)
        self.assertEqual(result['strict_intruding_vertex_count'], 74)
        self.assertEqual(result['strict_intruding_face_count'], 283)
        self.assertTrue(result['positive_volume_overlap_certified_if_D_is_embedded_bounded_regular_solid'])
        for witness in result['strict_intrusion_witnesses']:
            self.assertGreater(min(map(Q, witness['halfplane_signs_exact'])), 0)
        core = result['conservative_axis_core']
        radius = Q(core['radius_reference_exact'])
        self.assertGreater(radius, Q(59, 1000))
        self.assertLess(radius, Q(6, 100))
        self.assertLess(radius**2, Q(core['D_surface_radius_squared_lower_bound_exact']))
        self.assertLess(radius**2, Q(core['shaft_inradius_squared_exact']))
        self.assertFalse(result['entire_shaft_protected_certified'])
        self.assertFalse(result['W0_physical_tip_or_FD_approved'])


if __name__ == '__main__':
    unittest.main()
