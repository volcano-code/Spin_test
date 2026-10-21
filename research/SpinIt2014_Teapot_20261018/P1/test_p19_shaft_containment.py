"""Whole-region, coincident-boundary, internal-seam and real-shaft regressions."""

from fractions import Fraction as Q
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from p17_boundary_certificate import read_binary64_obj
from p19_shaft_containment import (
    audit_full_shaft_containment, clip_triangle_to_tetrahedron, plane_value,
    tetrahedron_inward_planes, triangle_tetrahedron_aabb_pairs, verify_surface,
)


VERTICES = ((-1, -1, -1), (1, 0, 0), (0, 1, 0), (0, 0, 1))
FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))
ORIGIN = (Q(0), Q(0), Q(0))


def write_mesh(path, vertices, faces=FACES):
    text = "".join("v " + " ".join(format(float(x), ".17g") for x in p) + "\n" for p in vertices)
    text += "".join("f " + " ".join(str(i + 1) for i in face) + "\n" for face in faces)
    path.write_text(text, encoding="utf-8")
    return path


def midpoint_subdivision(vertices, faces):
    output = list(vertices)
    edges, triangles = {}, []
    def midpoint(a, b):
        key = tuple(sorted((a, b)))
        if key not in edges:
            edges[key] = len(output)
            output.append(tuple((Q(vertices[a][i]) + Q(vertices[b][i])) / 2 for i in range(3)))
        return edges[key]
    for a, b, c in faces:
        ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        triangles.extend(((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)))
    return tuple(output), tuple(triangles)


class StarClipTests(unittest.TestCase):
    def test_internal_tetrahedron_seam_is_strict_shaft_interior(self):
        a, b, c = tuple(tuple(Q(x) for x in VERTICES[i]) for i in FACES[0])
        tetra = (ORIGIN, a, b, c)
        # This entire triangle lies in one INTERNAL radial face, so requiring
        # strictness in every tetra halfspace would incorrectly miss it.
        triangle = (ORIGIN, tuple(x / 2 for x in a), tuple(x / 2 for x in b))
        planes = tetrahedron_inward_planes(tetra)
        polygon = clip_triangle_to_tetrahedron(triangle, inward_planes=planes)
        self.assertEqual(set(point for point, _ in polygon), set(triangle))
        self.assertTrue(all(plane_value(planes[0], point) > 0 for point, _ in polygon))
        self.assertTrue(any(all(plane_value(plane, point) == 0 for point, _ in polygon) for plane in planes[1:]))

    def test_external_base_facet_is_allowed_including_edges_and_corners(self):
        a, b, c = tuple(tuple(Q(x) for x in VERTICES[i]) for i in FACES[0])
        planes = tetrahedron_inward_planes((ORIGIN, a, b, c))
        polygon = clip_triangle_to_tetrahedron((a, b, c), inward_planes=planes)
        self.assertEqual(set(point for point, _ in polygon), {a, b, c})
        self.assertTrue(all(plane_value(planes[0], point) == 0 for point, _ in polygon))

    def test_clipping_keeps_exact_original_triangle_barycentric_witnesses(self):
        tetra = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))
        triangle = ((-1, Q(1, 3), Q(1, 3)), (2, Q(1, 3), Q(1, 3)), (0, 2, 2))
        planes = tetrahedron_inward_planes(tetra)
        polygon = clip_triangle_to_tetrahedron(triangle, inward_planes=planes)
        self.assertTrue(polygon)
        for point, weights in polygon:
            self.assertEqual(sum(weights), 1)
            self.assertGreaterEqual(min(weights), 0)
            self.assertEqual(point, tuple(sum(weights[i] * triangle[i][k] for i in range(3)) for k in range(3)))
            self.assertTrue(all(plane_value(plane, point) >= 0 for plane in planes))

    def test_aabb_sweep_matches_exhaustive_cross_pairs_including_contact(self):
        triangles = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                              [[1, 0, 0], [2, 0, 0], [1, 1, 0]],
                              [[3, 3, 3], [4, 3, 3], [3, 4, 3]]], dtype=float)
        tetrahedra = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                               [[2, 0, 0], [3, 0, 0], [2, 1, 0], [2, 0, 1]]], dtype=float)
        alo, ahi = triangles.min(1), triangles.max(1)
        blo, bhi = tetrahedra.min(1), tetrahedra.max(1)
        expected = {(i, j) for i in range(3) for j in range(2)
                    if np.all(ahi[i] >= blo[j]) and np.all(bhi[j] >= alo[i])}
        self.assertEqual(set(triangle_tetrahedron_aabb_pairs(triangles, tetrahedra)), expected)


class WholeContainmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.shaft = write_mesh(self.root / "shaft.obj", VERTICES)

    def tearDown(self):
        self.tmp.cleanup()

    def audit(self, material, **kwargs):
        return audit_full_shaft_containment(material, self.shaft, kernel_point=ORIGIN, **kwargs)

    def test_strictly_enclosing_material_contains_entire_shaft(self):
        outer = tuple(tuple(2 * x for x in p) for p in VERTICES)
        r = self.audit(write_mesh(self.root / "outer.obj", outer))
        self.assertTrue(r["full_original_shaft_contained_in_material"])
        self.assertTrue(r["exact_material_boundary_excludes_shaft_open_interior"])
        self.assertEqual(r["coverage"]["strict_shaft_interior_clip_pairs"], 0)
        self.assertTrue(r["coverage"]["all_candidate_pairs_checked"])
        self.assertFalse(any(r["scientific_flags"].values()))

    def test_identical_shared_boundary_including_all_caps_is_accepted(self):
        r = self.audit(self.shaft)
        self.assertTrue(r["full_original_shaft_contained_in_material"])
        self.assertGreater(r["coverage"]["nonempty_closed_clip_pairs"], 0)
        self.assertEqual(r["coverage"]["strict_shaft_interior_clip_pairs"], 0)

    def test_different_coplanar_triangulation_is_accepted(self):
        vertices, faces = midpoint_subdivision(VERTICES, FACES)
        r = self.audit(write_mesh(self.root / "subdivided.obj", vertices, faces))
        self.assertTrue(r["full_original_shaft_contained_in_material"])
        self.assertEqual(r["coverage"]["material_triangles"], 16)

    def test_all_shaft_vertices_can_be_shared_while_material_dents_inward(self):
        # A dyadic inward dent leaves EVERY original shaft vertex untouched.
        a, b, c = (VERTICES[i] for i in FACES[0])
        on_face = tuple(Q(a[k], 2) + Q(b[k], 4) + Q(c[k], 4) for k in range(3))
        point = tuple(x * (1 - Q(1, 2 ** 50)) for x in on_face)
        material = write_mesh(self.root / "tiny_dent.obj", VERTICES + (point,),
                              ((0, 2, 4), (2, 1, 4), (1, 0, 4)) + FACES[1:])
        self.assertTrue(set(read_binary64_obj(self.shaft).vertices).issubset(read_binary64_obj(material).vertices))
        r = self.audit(material)
        self.assertTrue(r["material_exact_surface"]["exact_embedded_closed_oriented_2manifold"])
        self.assertFalse(r["full_original_shaft_contained_in_material"])
        self.assertTrue(r["positive_volume_shaft_minus_material_certified"])
        self.assertGreater(r["coverage"]["material_faces_with_strict_shaft_intrusion"], 0)
        witness = r["counterexample_witnesses"][0]
        self.assertGreater(Q(witness["strict_positive_kernel_barycentric_weight_exact"]), 0)
        self.assertEqual(witness["independent_exact_shaft_ray"]["classification"], "INSIDE")

    def test_material_boundary_entirely_inside_shaft_is_detected(self):
        inner = tuple(tuple(Q(x, 2) for x in p) for p in VERTICES)
        r = self.audit(write_mesh(self.root / "inner.obj", inner))
        self.assertFalse(r["full_original_shaft_contained_in_material"])
        self.assertTrue(r["positive_volume_shaft_minus_material_certified"])
        self.assertEqual(r["coverage"]["material_faces_with_strict_shaft_intrusion"], 4)

    def test_no_surface_intersection_without_inside_anchor_is_not_containment(self):
        far = tuple(tuple(x + 10 for x in p) for p in VERTICES)
        r = self.audit(write_mesh(self.root / "far.obj", far))
        self.assertTrue(r["exact_material_boundary_excludes_shaft_open_interior"])
        self.assertEqual(r["kernel_in_material"]["classification"], "OUTSIDE")
        self.assertFalse(r["full_original_shaft_contained_in_material"])
        self.assertTrue(r["shaft_not_contained_counterexample_certified"])

    def test_non_strict_kernel_or_open_material_never_certified(self):
        r = audit_full_shaft_containment(self.shaft, self.shaft, kernel_point=VERTICES[0])
        self.assertFalse(r["full_original_shaft_contained_in_material"])
        self.assertEqual(r["stop_reason"], "QUERY_POINT_IS_NOT_A_STRICT_STAR_KERNEL")
        opened = write_mesh(self.root / "open.obj", VERTICES, FACES[:-1])
        r = self.audit(opened)
        self.assertFalse(r["full_original_shaft_contained_in_material"])
        self.assertIn("NOT_EXACT_EMBEDDED", r["stop_reason"])

    def test_hashes_input_bytes_and_private_cache_cannot_be_poisoned_by_return_dict(self):
        source = self.shaft.read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        report = verify_surface(self.shaft, digest)
        report["exact_embedded_closed_oriented_2manifold"] = False
        r = self.audit(self.shaft, expected_sha256={"shaft": digest, "material": digest}, reuse_verified_surfaces=True)
        self.assertTrue(r["full_original_shaft_contained_in_material"])
        self.assertTrue(all(r["in_process_verified_surface_cache_reused"].values()))
        self.assertEqual(self.shaft.read_bytes(), source)
        with self.assertRaisesRegex(ValueError, "SHA256_MISMATCH"):
            self.audit(self.shaft, expected_sha256={"shaft": digest, "material": "0" * 64})
        with self.assertRaisesRegex(ValueError, "PIN_BOTH"):
            self.audit(self.shaft, expected_sha256={"shaft": digest})

    @unittest.skipUnless(os.environ.get("W4_P19_CASE_ROOT"), "set W4_P19_CASE_ROOT for frozen real P17 source replay")
    def test_real_old_outer_rejected_but_entire_original_shaft_self_containment_passes(self):
        root = Path(os.environ["W4_P19_CASE_ROOT"])
        manifest = json.loads((root / "manifest.json").read_text())
        material = root / manifest["materials"]["M"]
        shaft = root / "source/shaft-reference.obj"
        expected = {"material": manifest["files_sha256"][manifest["materials"]["M"]],
                    "shaft": manifest["files_sha256"]["source/shaft-reference.obj"]}
        r = audit_full_shaft_containment(material, shaft, expected, max_witnesses=1)
        self.assertFalse(r["full_original_shaft_contained_in_material"])
        self.assertTrue(r["positive_volume_shaft_minus_material_certified"])
        self.assertEqual(r["coverage"]["closed_aabb_candidate_pairs"], 23794)
        self.assertEqual(r["coverage"]["strict_shaft_interior_clip_pairs"], 433)
        self.assertEqual(r["coverage"]["material_faces_with_strict_shaft_intrusion"], 314)
        self.assertEqual(r["coverage"]["internal_tetrahedron_seams_excluded"], 0)
        self.assertFalse(any(r["scientific_flags"].values()))
        own = audit_full_shaft_containment(shaft, shaft, reuse_verified_surfaces=True)
        self.assertTrue(own["full_original_shaft_contained_in_material"])
        self.assertEqual(own["coverage"]["strict_shaft_interior_clip_pairs"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
