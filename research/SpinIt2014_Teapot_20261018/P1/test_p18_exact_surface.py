"""Adversarial geometry, coverage, topology and frozen real-archive P18 tests."""

from fractions import Fraction as Q
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from p18_exact_surface import (
    aabb_candidate_pairs, audit_exact_surface, exact_plane,
    exact_triangle_intersection, intersection_equals_shared_simplex,
)


TETRA_FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
TETRA_VERTICES = ((0., 0., 0.), (2., 0., 0.), (0., 2., 0.), (0., 0., 2.))


def write_mesh(path, vertices, faces):
    text = "".join("v " + " ".join(format(float(x), ".17g") for x in point) + "\n" for point in vertices)
    text += "".join("f " + " ".join(str(i + 1) for i in face) + "\n" for face in faces)
    path.write_text(text, encoding="utf-8")
    return path


class ExactTriangleTests(unittest.TestCase):
    def test_noncoplanar_transverse_intersection_and_order_symmetry(self):
        a = ((0, 0, 0), (4, 0, 0), (0, 4, 0))
        b = ((1, 1, -1), (1, 1, 1), (2, 1, 0))
        expected = {(Q(1), Q(1), Q(0)), (Q(2), Q(1), Q(0))}
        self.assertEqual(set(exact_triangle_intersection(a, b)), expected)
        self.assertEqual(set(exact_triangle_intersection(b, a)), expected)

    def test_coplanar_area_overlap_and_all_vertex_permutations(self):
        a = ((0, 0, 0), (4, 0, 0), (0, 4, 0))
        b = ((1, 1, 0), (2, 1, 0), (1, 2, 0))
        for permutation in itertools.permutations(b):
            self.assertEqual(set(exact_triangle_intersection(a, permutation)), set(b))

    def test_coplanar_clipping_creates_exact_non_dyadic_intersections(self):
        a = ((0, 0, 0), (2, 0, 0), (0, 2, 0))
        b = ((1, -1, 0), (3, 2, 0), (1, 3, 0))
        expected = {(Q(1), Q(0), Q(0)), (Q(5, 3), Q(0), Q(0)),
                    (Q(9, 5), Q(1, 5), Q(0)), (Q(1), Q(1), Q(0))}
        self.assertEqual(set(exact_triangle_intersection(a, b)), expected)
        self.assertEqual(set(exact_triangle_intersection(b, a)), expected)

    def test_adjacent_shared_edge_coplanar_overlap_is_rejected(self):
        a = ((0, 0, 0), (4, 0, 0), (0, 4, 0))
        b = ((4, 0, 0), (0, 0, 0), (1, 1, 0))
        points = exact_triangle_intersection(a, b)
        self.assertFalse(intersection_equals_shared_simplex(points, ((0, 0, 0), (4, 0, 0))))

    def test_valid_shared_edge_is_equal_including_endpoints(self):
        a = ((0, 0, 0), (2, 0, 0), (0, 2, 0))
        for b in (((2, 0, 0), (0, 0, 0), (0, -2, 0)),
                  ((2, 0, 0), (0, 0, 0), (0, 0, 2))):
            points = exact_triangle_intersection(a, b)
            self.assertTrue(intersection_equals_shared_simplex(points, ((0, 0, 0), (2, 0, 0))))
        self.assertFalse(intersection_equals_shared_simplex(((0, 0, 0),), ((0, 0, 0), (2, 0, 0))))

    def test_shared_vertex_does_not_hide_segment_penetration(self):
        a = ((0, 0, 0), (4, 0, 0), (0, 4, 0))
        b = ((0, 0, 0), (1, 1, -1), (1, 1, 1))
        points = exact_triangle_intersection(a, b)
        self.assertEqual(set(points), {(0, 0, 0), (1, 1, 0)})
        self.assertFalse(intersection_equals_shared_simplex(points, ((0, 0, 0),)))

    def test_point_touch_disjoint_parallel_and_tiny_exact_penetration(self):
        a = ((0, 0, 0), (2, 0, 0), (0, 2, 0))
        touch = ((0, 0, 0), (-1, 0, 1), (0, -1, 1))
        self.assertEqual(exact_triangle_intersection(a, touch), ((0, 0, 0),))
        parallel = ((0, 0, Q(1, 2 ** 100)), (2, 0, Q(1, 2 ** 100)), (0, 2, Q(1, 2 ** 100)))
        self.assertEqual(exact_triangle_intersection(a, parallel), ())
        tiny = ((Q(1, 2), Q(1, 2), -Q(1, 2 ** 100)),
                (Q(1, 2), Q(1, 2), Q(1, 2 ** 100)),
                (Q(3, 4), Q(1, 2), 0))
        self.assertEqual(len(exact_triangle_intersection(a, tiny)), 2)

    def test_public_float_input_uses_binary64_exactness(self):
        a = ((0.1, 0., 0.), (1., 0., 0.), (0., 1., 0.))
        b = ((0.1, 0., 0.), (0.1, -1., 1.), (0.1, -1., -1.))
        points = exact_triangle_intersection(a, b)
        self.assertEqual(points, ((Q.from_float(.1), Q(0), Q(0)),))
        self.assertNotEqual(points[0][0], Q(1, 10))
        with self.assertRaises(ValueError):
            exact_plane(((math.nan, 0, 0), (1, 0, 0), (0, 1, 0)))

    def test_aabb_sweep_exactly_matches_all_pairs_and_cross_mesh_indices(self):
        triangles = np.array([
            [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
            [[1, 0, 0], [2, 0, 0], [1, 1, 0]],
            [[0, 0, 1], [1, 0, 1], [0, 1, 1]],
            [[.5, .5, -1], [.5, .5, 1], [1, .5, 0]],
            [[9, 9, 9], [10, 9, 9], [9, 10, 9]],
        ], dtype=float)
        lo, hi = triangles.min(1), triangles.max(1)
        expected = {(i, j) for i in range(5) for j in range(i + 1, 5)
                    if np.all(hi[i] >= lo[j]) and np.all(hi[j] >= lo[i])}
        self.assertEqual(set(aabb_candidate_pairs(triangles)), expected)
        cross_expected = {(i, j) for i in range(5) for j in range(5)
                          if np.all(hi[i] >= lo[j]) and np.all(hi[j] >= lo[i])}
        self.assertEqual(set(aabb_candidate_pairs(triangles, triangles)), cross_expected)
        self.assertTrue(all((i, i) in cross_expected for i in range(5)))


class ExactSurfaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def audit(self, vertices=TETRA_VERTICES, faces=TETRA_FACES):
        return audit_exact_surface(write_mesh(self.root / "test.obj", vertices, faces))

    def test_closed_tetra_all_six_adjacent_pairs_are_covered(self):
        r = self.audit()
        self.assertTrue(r["exact_embedded_closed_oriented_2manifold"])
        self.assertEqual(r["coverage"]["aabb_candidate_pairs"], 6)
        self.assertEqual(r["coverage"]["candidate_pairs_by_shared_original_vertex_count"]["2"], 6)
        self.assertEqual(r["coverage"]["exact_noncoplanar_shared_edge_theorem_checks"], 6)
        self.assertEqual(r["coverage"]["adjacent_candidates_excluded"], 0)
        self.assertEqual(r["topology"]["euler_characteristic"], 2)
        self.assertFalse(any(r["scientific_flags"].values()))

    def test_inward_surface_is_oriented_but_no_outward_solid_claim(self):
        r = self.audit(faces=tuple((a, c, b) for a, b, c in TETRA_FACES))
        self.assertTrue(r["exact_embedded_closed_oriented_2manifold"])
        self.assertLess(Q(r["component_signed_volumes_exact"][0]), 0)
        self.assertFalse(r["scientific_flags"]["ordinary_solid_region_equality_certified"])

    def test_open_flipped_and_duplicate_faces_fail(self):
        cases = (
            (TETRA_FACES[:-1], "edge_incidence_error_count"),
            (((0, 1, 2),) + TETRA_FACES[1:], "edge_orientation_error_count"),
            (TETRA_FACES + (TETRA_FACES[0],), "duplicate_face_groups"),
        )
        for faces, metric in cases:
            with self.subTest(metric=metric):
                r = self.audit(faces=faces)
                self.assertFalse(r["exact_embedded_closed_oriented_2manifold"])
                self.assertGreater(r["topology"][metric], 0)
                self.assertTrue(r["coverage"]["all_candidate_pairs_checked"])

    def test_bow_tie_vertex_link_of_two_tetrahedra_is_not_a_circle(self):
        vertices = TETRA_VERTICES + ((-2., 0., 0.), (0., -2., 0.), (0., 0., -2.))
        mapping = {0: 0, 1: 4, 2: 5, 3: 6}
        other = tuple(tuple(mapping[i] for i in (a, c, b)) for a, b, c in TETRA_FACES)
        r = self.audit(vertices, TETRA_FACES + other)
        self.assertFalse(r["exact_embedded_closed_oriented_2manifold"])
        self.assertEqual(r["topology"]["edge_incidence_error_count"], 0)
        self.assertEqual(r["topology"]["vertex_link_non_circle_count"], 1)
        self.assertEqual(r["forbidden_intersection_pair_count"], 0)

    def test_duplicate_coordinates_at_different_indices_are_not_welded(self):
        other_vertices = tuple(tuple(-x for x in p) for p in TETRA_VERTICES)
        other_faces = tuple((a + 4, c + 4, b + 4) for a, b, c in TETRA_FACES)
        r = self.audit(TETRA_VERTICES + other_vertices, TETRA_FACES + other_faces)
        self.assertFalse(r["exact_embedded_closed_oriented_2manifold"])
        self.assertEqual(r["topology"]["duplicate_coordinate_index_groups"], 1)
        self.assertGreater(r["forbidden_intersection_kinds"].get("illegal_point_contact", 0), 0)

    def test_closed_combinatorial_manifolds_can_transversely_self_intersect(self):
        other_vertices = tuple(tuple(x + .5 for x in p) for p in TETRA_VERTICES)
        other_faces = tuple(tuple(i + 4 for i in f) for f in TETRA_FACES)
        r = self.audit(TETRA_VERTICES + other_vertices, TETRA_FACES + other_faces)
        self.assertTrue(r["topology"]["indexed_closed_consistently_oriented_2manifold"])
        self.assertFalse(r["exact_embedded_closed_oriented_2manifold"])
        self.assertGreater(r["forbidden_intersection_kinds"].get("transverse_penetration", 0), 0)

    def test_adjacent_coplanar_overlap_detected_despite_original_shared_edge(self):
        vertices = ((0., 0., 0.), (4., 0., 0.), (0., 4., 0.), (1., 1., 0.))
        r = self.audit(vertices, ((0, 1, 2), (1, 0, 3)))
        self.assertEqual(r["forbidden_intersection_kinds"].get("coplanar_area_overlap"), 1)
        self.assertEqual(r["coverage"]["candidate_pairs_by_shared_original_vertex_count"]["2"], 1)
        self.assertEqual(r["coverage"]["exact_triangle_intersection_checks"], 1)

    def test_nonadjacent_edge_contact_without_duplicate_vertices_is_rejected(self):
        vertices = ((0., 0., 0.), (4., 0., 0.), (0., 4., 0.),
                    (1., 0., 0.), (3., 0., 0.), (2., -1., 0.))
        r = self.audit(vertices, ((0, 1, 2), (3, 4, 5)))
        self.assertEqual(r["topology"]["duplicate_coordinate_index_groups"], 0)
        self.assertEqual(r["forbidden_intersection_kinds"].get("illegal_edge_contact"), 1)
        self.assertEqual(r["coverage"]["candidate_pairs_by_shared_original_vertex_count"]["0"], 1)

    def test_two_disjoint_nested_components_have_opposite_volume_signs(self):
        inner = ((.2, .2, .2), (.4, .2, .2), (.2, .4, .2), (.2, .2, .4))
        inner_faces = tuple((a + 4, c + 4, b + 4) for a, b, c in TETRA_FACES)
        r = self.audit(TETRA_VERTICES + inner, TETRA_FACES + inner_faces)
        self.assertTrue(r["exact_embedded_closed_oriented_2manifold"])
        self.assertEqual(r["topology"]["surface_components"], 2)
        volumes = list(map(Q, r["component_signed_volumes_exact"]))
        self.assertGreater(volumes[0], 0)
        self.assertLess(volumes[1], 0)

    def test_frozen_hash_and_bytes_preserved_and_degenerate_input_rejected(self):
        path = write_mesh(self.root / "input.obj", TETRA_VERTICES, TETRA_FACES)
        before = path.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        r = audit_exact_surface(path, digest)
        self.assertTrue(r["frozen_sha256_checked"])
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            audit_exact_surface(path, "0" * 64)
        invalid = write_mesh(self.root / "degenerate.obj", ((0., 0., 0.), (1., 0., 0.), (2., 0., 0.)), ((0, 1, 2),))
        with self.assertRaisesRegex(ValueError, "zero-area"):
            audit_exact_surface(invalid)

    @unittest.skipUnless(os.environ.get("W4_P18_CASE_ROOT"), "set W4_P18_CASE_ROOT for authentic P17 material replay")
    def test_real_frozen_m_f_d_all_pairs_including_adjacent(self):
        root = Path(os.environ["W4_P18_CASE_ROOT"])
        manifest = json.loads((root / "manifest.json").read_text())
        expected = {"M": (7558, 56504, 1), "F": (8198, 61888, 2), "D": (640, 5384, 1)}
        for name, (faces, pairs, components) in expected.items():
            with self.subTest(material=name):
                relative = manifest["materials"][name]
                r = audit_exact_surface(root / relative, manifest["files_sha256"][relative])
                self.assertTrue(r["exact_embedded_closed_oriented_2manifold"])
                self.assertEqual(r["input"]["faces"], faces)
                self.assertEqual(r["coverage"]["aabb_candidate_pairs"], pairs)
                self.assertEqual(r["topology"]["surface_components"], components)
                self.assertEqual(r["forbidden_intersection_pair_count"], 0)
                self.assertEqual(r["coverage"]["adjacent_candidates_excluded"], 0)
                self.assertEqual(r["coverage"]["exact_noncoplanar_shared_edge_theorem_checks"]
                                 + r["coverage"]["exact_triangle_intersection_checks"], pairs)
                self.assertFalse(any(r["scientific_flags"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
