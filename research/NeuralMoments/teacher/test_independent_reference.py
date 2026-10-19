import copy
import unittest
from fractions import Fraction
from independent_reference import integrate_exact_boundary, compare_exact_reference

V=[[0,0,0],[2,0,0],[2,3,0],[0,3,0],[0,0,4],[2,0,4],[2,3,4],[0,3,4]]
F=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
   [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]]
EXPECTED=[48,48,72,96,64,144,256,144,96,72]

class TestIndependentReference(unittest.TestCase):
    def test_closed_box_ten_moments(self):
        exact,proof=integrate_exact_boundary(V,F,2)
        self.assertEqual(exact,list(map(Fraction,EXPECTED)))
        self.assertTrue(compare_exact_reference(EXPECTED,exact)["within_tolerance"])
        self.assertEqual(proof["face_count"],12)
    def test_disagreeing_component_fails(self):
        result=compare_exact_reference(EXPECTED[:7]+[145]+EXPECTED[8:],list(map(Fraction,EXPECTED)))
        self.assertFalse(result["within_tolerance"])
        self.assertEqual(result["absolute_errors"][7],1)
    def test_binary64_density_exact_and_finite(self):
        moments,proof=integrate_exact_boundary(V,F,2.0)
        self.assertEqual(moments,list(map(Fraction,EXPECTED)))
        with self.assertRaisesRegex(ValueError,"INVALID_BINARY64_DENSITY"):
            integrate_exact_boundary(V,F,float('nan'))
    def test_open_boundary_rejected(self):
        with self.assertRaisesRegex(ValueError,"BOUNDARY_NOT_CLOSED"):
            integrate_exact_boundary(V,F[:-1],2)
    def test_orientation_rejected(self):
        wrong=copy.deepcopy(F);wrong[0]=wrong[0][::-1]
        with self.assertRaisesRegex(ValueError,"BOUNDARY_NOT_CLOSED"):
            integrate_exact_boundary(V,wrong,2)
    def test_negative_orientation_rejected(self):
        with self.assertRaisesRegex(ValueError,"NONPOSITIVE"):
            integrate_exact_boundary(V,[f[::-1] for f in F],2)
    def test_floats_rejected(self):
        v=copy.deepcopy(V);v[0][0]=0.0
        with self.assertRaisesRegex(ValueError,"EXACT_RATIONAL"):
            integrate_exact_boundary(v,F,2)
    def test_degenerate_face_rejected(self):
        v=copy.deepcopy(V);v[1]=v[0]
        with self.assertRaisesRegex(ValueError,"DEGENERATE"):
            integrate_exact_boundary(v,F,2)
    def test_duplicate_face_rejected(self):
        with self.assertRaisesRegex(ValueError,"DUPLICATE_FACE"):
            integrate_exact_boundary(V,F+[F[0]],2)
    def test_nonfinite_fails(self):
        with self.assertRaisesRegex(ValueError,"NONFINITE"):
            compare_exact_reference([float('nan')]*10,list(map(Fraction,EXPECTED)))

if __name__=='__main__': unittest.main()
