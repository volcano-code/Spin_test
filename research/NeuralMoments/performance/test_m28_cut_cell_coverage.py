import unittest
from fractions import Fraction as Q
from m28_cut_cell_coverage import audit

A, B, C, M = (0, 0), (2, 0), (0, 2), (1, 1)
P, L, R = (A, B, C), (A, M, C), (A, B, M)


class ExactCells(unittest.TestCase):
    def test_alternate_triangulation(self):
        self.assertTrue(audit(P, [], [R, L[::-1]], lambda p: True)['passes'])

    def test_same_area_wrong_half(self):
        r = audit(P, [(A, M)], [R], lambda p: p[1] > p[0])
        self.assertEqual((r['missing'], r['extra']), (1, 1))

    def test_duplicates_with_gap(self):
        r = audit(P, [], [R, R], lambda p: True)
        self.assertEqual((r['missing'], r['overlap']), (1, 1))

    def test_crossing_and_vertical_cuts(self):
        cuts = [(A, M), ((Q(1, 2), 0), (Q(1, 2), Q(3, 2))), ((0, 1), (1, 0))]
        self.assertTrue(audit(P, cuts, [L], lambda p: p[1] > p[0])['passes'])

    def test_exact_sliver(self):
        h = Q(1, 10**100)
        r = audit(P, [((h, 0), (0, h))], [], lambda p: sum(p) < h)
        self.assertEqual(r['missing'], h*h/2)

    def test_collinear_and_zero_length(self):
        self.assertTrue(audit(P, [(A, M), (M, A), (A, A)], [L], lambda p: p[1] > p[0])['passes'])

    def test_invalid_geometry_or_input(self):
        for t in [(A, B, A), (A, B, (1, 2)), (A, B, (0, 1.0))]:
            with self.subTest(t=t), self.assertRaises(ValueError):
                audit(P, [], [t], lambda p: True)

    def test_ambiguous(self):
        with self.assertRaises(ValueError):
            audit(P, [], [], lambda p: None)
