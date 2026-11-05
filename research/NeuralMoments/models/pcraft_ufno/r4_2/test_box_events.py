"""Run from this directory with python -m unittest -v (standard library only)."""
from fractions import Fraction as F
from itertools import product
from math import inf, nan, nextafter
from random import Random
import unittest

from box_events import classify_box


BOX = ((-1,) * 3, (1,) * 3)


class BoxEvents(unittest.TestCase):
    def case(self, c, status, bounds=BOX):
        result = classify_box(c, *bounds)
        self.assertEqual(result["status"], status)
        self.assertIsNone(result["J_D"])
        self.assertFalse(result["training_admitted"])
        return result

    def test_regular_plane_and_vertex_event(self):
        a = self.case([0, 1, 0, 0] + [0] * 6, "REGULAR_ZERO_SET")
        self.assertEqual(a["range"], (-1, 1))
        b = self.case([-3, 1, 1, 1] + [0] * 6, "ZERO_STRATUM_EVENT")
        self.assertIn({"walls": (1, 1, 1), "point": (1, 1, 1)}, b["events"])

    def test_nonzero_gradient_can_touch_face_or_edge(self):
        for c, walls, point in [
            ([1, 1, 0, 0, 0, 1, 1, 0, 0, 0], (-1, 0, 0), (-1, 0, 0)),
            ([2, 1, 1, 0, 0, 0, 1, 0, 0, 0], (-1, -1, 0), (-1, -1, 0)),
        ]:
            result = self.case(c, "ZERO_STRATUM_EVENT")
            self.assertIn({"walls": walls, "point": point}, result["events"])

    def test_enclosed_sphere_and_exact_adjacent_face_tangency(self):
        for radius2, status in [(F(1, 4), "REGULAR_ZERO_SET"), (nextafter(1., 0.), "REGULAR_ZERO_SET"),
                                (1, "ZERO_STRATUM_EVENT"), (nextafter(1., inf), "REGULAR_ZERO_SET")]:
            result = self.case([-radius2, 0, 0, 0, 1, 1, 1, 0, 0, 0], status)
            self.assertEqual(result["range"], (-F(radius2), 3 - F(radius2)))
        self.case([1, 0, 0, 0, 1, 1, 1, 0, 0, 0], "STRICT_POSITIVE")

    def test_interior_singularity_and_flat_event(self):
        for c in ([0, 0, 0, 0, 1, 1, -1, 0, 0, 0], [0] * 10):
            self.assertIn({"walls": (0, 0, 0), "point": (0, 0, 0)},
                          self.case(c, "ZERO_STRATUM_EVENT")["events"])

    def test_uncertain_flat_blocks_regular_classification(self):
        # The stationary line x=3,y=2 falls outside the box, but x-y=1 cuts it.
        self.case([5, -6, 4, 0, 1, -1, 0, 0, 0, 0], "UNKNOWN")

    def test_native_cross_order_and_factor_two(self):
        box = ((1, 2, 3), (2, 3, 5))
        for index, expected in enumerate([(12, 30), (6, 20), (4, 12)], start=7):
            c = [0] * 10
            c[index] = -3
            self.assertEqual(self.case(c, "STRICT_NEGATIVE", box)["range"],
                             (-3 * expected[1], -3 * expected[0]))

    def test_36_fixed_seed_separable_ranges_against_scalar_extrema(self):
        rng = Random(24041)
        for _ in range(36):
            c = [rng.randint(-7, 7) for _ in range(7)] + [0, 0, 0]
            mins, maxs = [], []
            for a, b in zip(c[4:7], c[1:4]):
                pts = [F(-1), F(1)]
                if a and abs(F(-b, 2 * a)) < 1:
                    pts.append(F(-b, 2 * a))
                vals = [a * t * t + b * t for t in pts]
                mins.append(min(vals))
                maxs.append(max(vals))
            result = classify_box(c, *BOX)
            self.assertEqual(result["range"], (c[0] + sum(mins), c[0] + sum(maxs)))

    def test_oblique_shifted_quadric_matches_known_global_bounds(self):
        # (x+y+z-1/3)^2 + (x-y)^2 + (z-1/3)^2, minimum attained at (0,0,1/3).
        # Convexity puts the maximum at a vertex.
        c = [F(2, 9), F(-2, 3), F(-2, 3), F(-4, 3), 2, 2, 2, 1, 1, 0]
        def direct(x, y, z):
            return (x+y+z-F(1,3))**2 + (x-y)**2 + (z-F(1,3))**2
        result = self.case(c, "ZERO_STRATUM_EVENT")
        self.assertEqual(result["range"], (0, max(direct(*p) for p in product((-1, 1), repeat=3))))
        self.assertIn({"walls": (0, 0, 0), "point": (0, 0, F(1, 3))}, result["events"])

    def test_invalid_inputs_fail_before_return(self):
        for c, lo, hi in [([0]*9, *BOX), ([nan]+[0]*9, *BOX), ([True]+[0]*9, *BOX),
                          ([0]*10, (0, 0, 0), (1, 1, 0)), ([0]*10, (0, 0, 0), (inf, 1, 1))]:
            with self.assertRaises(ValueError):
                classify_box(c, lo, hi)


if __name__ == "__main__":
    unittest.main()
