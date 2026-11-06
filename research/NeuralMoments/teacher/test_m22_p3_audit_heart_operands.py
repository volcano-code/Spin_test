"""Regression tests for the exact Heart operand embedding audit."""
import os
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from m22_p3_audit_heart_operands import (
    exact_volume, make_checker_input, parse_checker_output,
    rational_from_binary64, load_inputs,
)


class TestHeartOperandAudit(unittest.TestCase):
    def test_binary64_is_encoded_as_exact_binary_rational(self):
        self.assertEqual(rational_from_binary64(0.1), Fraction(3602879701896397, 36028797018963968))

    def test_boolean_is_not_a_coordinate(self):
        with self.assertRaisesRegex(ValueError, "EXPECTED_BINARY64_COORDINATE"):
            rational_from_binary64(True)

    def test_exact_tetrahedron_volume(self):
        vertices = [[0.0,0.0,0.0],[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]]
        faces = [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        self.assertEqual(exact_volume(vertices, faces), Fraction(1,6))

    def test_reversed_tetrahedron_volume_is_negative(self):
        vertices = [[0.0,0.0,0.0],[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]]
        faces = [[0,1,2],[0,3,1],[0,2,3],[1,3,2]]
        self.assertEqual(exact_volume(vertices, faces), Fraction(-1,6))

    def test_stream_is_deterministic_and_exact(self):
        vertices = [[0.1,0.0,0.0],[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]]
        faces = [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        with TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a.m26", Path(tmp)/"b.m26"
            self.assertEqual(make_checker_input(vertices, faces, a), make_checker_input(vertices, faces, b))
            self.assertIn("3602879701896397/36028797018963968", a.read_text())

    def test_checker_output_requires_exact_pass(self):
        raw = ("status=EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE\nvertices=4\nfaces=4\n"
               "candidate_pairs=6\nexact_pairs_checked=6\nadjacent_pairs=6\n"
               "nonadjacent_pairs=0\nelapsed_seconds=0.01\n")
        self.assertEqual(parse_checker_output(raw, 0)["vertices"], 4)
        with self.assertRaisesRegex(ValueError, "FAILED"):
            parse_checker_output(raw.replace("EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE",
                                             "TIMEOUT_NO_CERTIFICATION"), 3)

    def test_real_archives_bind_to_the_same_frozen_request(self):
        h8f, m21 = os.environ.get("W2_H8F_ARCHIVE"), os.environ.get("W2_M21_ARCHIVE")
        if not h8f or not m21:
            self.skipTest("real archive paths not configured")
        request, point0 = load_inputs(Path(h8f), Path(m21))
        self.assertEqual((len(request["design_vertices"]), len(request["design_faces"])), (13122,26244))
        self.assertEqual((len(point0["quadric_source_vertices"]), len(point0["quadric_source_faces"])), (162,320))
        self.assertEqual((len(point0["variable_rational_vertices"]), len(point0["variable_faces"])), (8455,16910))


if __name__ == "__main__":
    unittest.main(verbosity=2)
