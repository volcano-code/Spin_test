"""M27 adversarial cases for the W1 exact post-Boolean surface checker."""
from fractions import Fraction
import subprocess
import unittest

from test_m26_exact_intersection import BIN, join, packet, tetra


class TestM27IntersectionAdversarial(unittest.TestCase):
    def check(self, mesh, expected_status, expected_exit):
        cp = subprocess.run(
            [str(BIN), "--max-seconds", "10"],
            input=packet(*mesh), capture_output=True, timeout=15,
        )
        output = cp.stdout.decode() + cp.stderr.decode()
        self.assertEqual(cp.returncode, expected_exit, output)
        self.assertIn("status=" + expected_status, cp.stdout.decode())

    def test_coplanar_adjacent_faces_sharing_only_diagonal_are_allowed(self):
        # A closed square pyramid has two coplanar base triangles sharing one legal edge.
        vertices = [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0), (1, 1, 2)]
        faces = [(0, 3, 2), (0, 2, 1), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
        self.check((vertices, faces), "EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE", 0)

    def test_coplanar_positive_area_overlap_is_rejected(self):
        # Distinct topological IDs do not excuse overlapping coplanar surface interiors.
        a = tetra()
        b = tetra((Fraction(1, 2), 0, 0))
        b[0][3] = (Fraction(1, 2), 0, -2)
        self.check(join([a, b]), "POST_BOOLEAN_SELF_INTERSECTION", 2)

    def test_geometric_point_contact_without_shared_vertex_id_is_rejected(self):
        # The shells touch at one exact coordinate, but do not share a vertex index.
        self.check(join([tetra(), tetra((2, 0, 0))]), "POST_BOOLEAN_SELF_INTERSECTION", 2)

    def test_sub_ulp_rational_gap_is_not_a_false_intersection(self):
        # AABBs may overlap after binary64 outward rounding; the exact predicate must not.
        shift = Fraction(2) + Fraction(1, 2**80)
        self.check(join([tetra(), tetra((shift, 0, 0))]), "EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE", 0)


if __name__ == "__main__":
    unittest.main()
