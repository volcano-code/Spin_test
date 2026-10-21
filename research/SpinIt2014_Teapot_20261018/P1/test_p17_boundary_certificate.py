"""Independent analytic/adversarial and optional real-archive P17 checks."""

from fractions import Fraction
import hashlib
import itertools
import math
import os
from pathlib import Path
import tempfile
import unittest

from p17_boundary_certificate import (
    FALSE_FLAGS, audit_boundary_partition, certify_triangle_chain,
    cyclic_key, read_binary64_obj, signed_triangle_key,
)


TETRA_FACES = ((0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3))


def write_obj(path, vertices, faces):
    text = "".join("v " + " ".join(format(x, ".17g") for x in p) + "\n" for p in vertices)
    text += "".join("f " + " ".join(str(i + 1) for i in f) + "\n" for f in faces)
    path.write_text(text, encoding="utf-8")
    return path


class BoundaryCertificateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ov = ((0., 0., 0.), (4., 0., 0.), (0., 4., 0.), (0., 0., 4.))
        self.dv = ((.5, .5, .5), (.75, .5, .5), (.5, .75, .5), (.5, .5, .75))
        self.of = TETRA_FACES
        self.ff = self.of + tuple((a + 4, c + 4, b + 4) for a, b, c in self.of)
        self.outer = write_obj(self.root / "outer.obj", self.ov, self.of)
        self.design = write_obj(self.root / "design.obj", self.dv, self.of)
        self.retained = write_obj(self.root / "retained.obj", self.ov + self.dv, self.ff)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_six_permutations_use_correct_orientation_sign(self):
        tri = read_binary64_obj(self.outer).triangles[0]
        key, sign = signed_triangle_key(tri)
        parity = {p: (-1) ** sum(p[i] > p[j] for i in range(3) for j in range(i + 1, 3))
                  for p in itertools.permutations(range(3))}
        for permutation, expected_parity in parity.items():
            other_key, other_sign = signed_triangle_key(tuple(tri[i] for i in permutation))
            self.assertEqual(other_key, key)
            self.assertEqual(other_sign, sign * expected_parity)

    def test_analytic_cavity_eliminates_legacy_false_residual(self):
        r = audit_boundary_partition(self.outer, self.retained, self.design)
        self.assertTrue(r["exact_signed_triangle_chain_zero"])
        self.assertEqual(r["signed_triangle_residual_terms"], 0)
        self.assertEqual(r["legacy_cyclic_multiset_residual_terms"], 8)
        self.assertEqual(r["legacy_reverse_orientation_pairs"], 4)
        self.assertIsNone(r["tolerance_used"])
        self.assertEqual(r["scientific_flags"], FALSE_FLAGS)
        self.assertFalse(any(r["scientific_flags"].values()))

    def test_actual_cavity_winding_error_is_not_erased(self):
        wrong = self.of + tuple(tuple(i + 4 for i in f) for f in self.of)
        path = write_obj(self.root / "wrong.obj", self.ov + self.dv, wrong)
        r = audit_boundary_partition(self.outer, path, self.design)
        self.assertFalse(r["exact_signed_triangle_chain_zero"])
        self.assertEqual(r["signed_triangle_residual_terms"], 4)
        self.assertEqual(r["signed_triangle_residual_l1_multiplicity"], 8)

    def test_duplicate_face_cannot_be_cancelled_away_as_a_set(self):
        path = write_obj(self.root / "duplicate.obj", self.ov + self.dv, self.ff + (self.ff[-1],))
        r = audit_boundary_partition(self.outer, path, self.design)
        self.assertFalse(r["exact_signed_triangle_chain_zero"])
        self.assertEqual(r["signed_triangle_residual_terms"], 1)
        self.assertEqual(r["signed_triangle_residual_l1_multiplicity"], 1)

    def test_one_binary64_ulp_perturbation_is_detected(self):
        vertices = list(self.ov + self.dv)
        vertices[1] = (math.nextafter(4., math.inf), 0., 0.)
        path = write_obj(self.root / "ulp.obj", vertices, self.ff)
        r = audit_boundary_partition(self.outer, path, self.design)
        self.assertFalse(r["exact_signed_triangle_chain_zero"])
        self.assertGreater(r["signed_triangle_residual_terms"], 0)

    def test_vertex_reindex_face_order_and_cyclic_corners_are_invariant(self):
        vertices = self.ov + self.dv
        permutation = (5, 2, 7, 0, 6, 3, 1, 4)
        inverse = {old: new for new, old in enumerate(permutation)}
        faces = tuple(tuple(inverse[i] for i in f[1:] + f[:1]) for f in reversed(self.ff))
        path = write_obj(self.root / "reordered.obj", tuple(vertices[i] for i in permutation), faces)
        r = audit_boundary_partition(self.outer, path, self.design)
        self.assertTrue(r["exact_signed_triangle_chain_zero"])
        self.assertNotEqual(r["inputs"]["retained"]["sha256"], hashlib.sha256(self.retained.read_bytes()).hexdigest())

    def test_binary64_values_are_not_decimal_rationals(self):
        path = write_obj(self.root / "decimal.obj", ((0.1, 0., 0.), (1., 0., 0.), (0., 1., 0.)), ((0, 1, 2),))
        value = read_binary64_obj(path).vertices[0][0]
        self.assertEqual(value, Fraction.from_float(0.1))
        self.assertNotEqual(value, Fraction(1, 10))

    def test_chain_identity_does_not_authorize_open_or_nonphysical_meshes(self):
        path = write_obj(self.root / "open.obj", self.ov[:3], ((0, 1, 2),))
        mesh = read_binary64_obj(path)
        r = certify_triangle_chain(((mesh, 1), (mesh, -1)))
        self.assertTrue(r["exact_signed_triangle_chain_zero"])
        self.assertFalse(r["scientific_flags"]["ordinary_solid_region_equality_certified"])
        self.assertFalse(r["scientific_flags"]["W0_physical_tip_or_FD_approved"])

    def test_literal_failure_does_not_claim_coplanar_set_inequality(self):
        vertices = ((0., 0., 0.), (1., 0., 0.), (1., 1., 0.), (0., 1., 0.))
        a = read_binary64_obj(write_obj(self.root / "diag_a.obj", vertices, ((0, 1, 2), (0, 2, 3))))
        b = read_binary64_obj(write_obj(self.root / "diag_b.obj", vertices, ((0, 1, 3), (1, 2, 3))))
        r = certify_triangle_chain(((a, 1), (b, -1)))
        self.assertFalse(r["exact_signed_triangle_chain_zero"])
        self.assertEqual(r["status"], "SIGNED_CHAIN_IDENTITY_NOT_DEMONSTRATED")
        self.assertFalse(r["scientific_flags"]["ordinary_solid_region_equality_certified"])

    def test_fixed_input_hashes_checked_and_immutable(self):
        paths = dict(zip(("outer", "retained", "design"), (self.outer, self.retained, self.design)))
        before = {name: path.read_bytes() for name, path in paths.items()}
        expected = {name: hashlib.sha256(data).hexdigest() for name, data in before.items()}
        r = audit_boundary_partition(self.outer, self.retained, self.design, expected)
        self.assertTrue(r["frozen_sha256_manifest_checked"])
        self.assertFalse(r["geometry_modified"])
        self.assertEqual(before, {name: path.read_bytes() for name, path in paths.items()})
        wrong = dict(expected, design="0" * 64)
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            audit_boundary_partition(self.outer, self.retained, self.design, wrong)
        with self.assertRaisesRegex(ValueError, "all three"):
            audit_boundary_partition(self.outer, self.retained, self.design, {"outer": expected["outer"]})

    def test_invalid_obj_rejected_even_if_a_future_chain_would_cancel_it(self):
        invalid = {
            "nan": "v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
            "zero_index": "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 2 3\n",
            "degenerate": "v 0 0 0\nv 1 0 0\nv 2 0 0\nf 1 2 3\n",
            "quad": "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n",
            "empty": "# no geometry\n",
        }
        for name, text in invalid.items():
            with self.subTest(name=name):
                path = self.root / (name + ".obj")
                path.write_text(text)
                with self.assertRaises(ValueError):
                    read_binary64_obj(path)

    def test_negative_obj_indices_and_texture_fields_preserve_geometry(self):
        path = self.root / "negative.obj"
        path.write_text("v 0 0 0\nv 4 0 0\nv 0 4 0\nf -3/5/1 -1/6/1 -2/7/1\n")
        tri = read_binary64_obj(path).triangles[0]
        self.assertEqual(cyclic_key(tri), cyclic_key(read_binary64_obj(self.outer).triangles[0]))

    @unittest.skipUnless(os.environ.get("W4_P17_P14_ROOT") and os.environ.get("W4_P17_P15_ROOT"),
                         "set both W4_P17_P14_ROOT and W4_P17_P15_ROOT for authentic real-archive replay")
    def test_all_six_real_p14_p15_partitions_and_legacy_counts(self):
        p14, p15 = Path(os.environ["W4_P17_P14_ROOT"]), Path(os.environ["W4_P17_P15_ROOT"])
        cases = (("rotate_1p5", 1280), ("translate_y_008", 1248), ("translate_xy_012_m008", 1248))
        for case, legacy_count in cases:
            d = p14 / "p14-cherchi-junction-study" / case / "D_minus_shaft_cherchi.obj"
            pairs = (
                (p14 / "p13-native-Cherchi-domain" / "p13-outer-cherchi-union.obj",
                 p14 / "p14-cherchi-junction-study" / case / "F_retained_cherchi.obj"),
                (p15 / "outer_numeric_microweld.obj", p15 / case / "F_numeric_microweld.obj"),
            )
            for outer, retained in pairs:
                with self.subTest(case=case, outer=outer.name):
                    r = audit_boundary_partition(outer, retained, d)
                    self.assertTrue(r["exact_signed_triangle_chain_zero"])
                    self.assertEqual(r["signed_triangle_residual_terms"], 0)
                    self.assertEqual(r["legacy_cyclic_multiset_residual_terms"], legacy_count)
                    self.assertEqual(r["legacy_reverse_orientation_pairs"], legacy_count // 2)
                    self.assertFalse(any(r["scientific_flags"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
