import unittest
from fractions import Fraction as Q
from m28_3_3_extract_exact_cuts import plane_segment
P=((0,0,0),(2,0,0),(0,2,0))
class ExactCutExtraction(unittest.TestCase):
 def test_crossing_segment(self):
  s=plane_segment(P,((1,-1,-1),(1,2,1),(1,2,-1)))
  self.assertEqual(set(s),{(Q(1),Q(1,2),Q(0)),(Q(1),Q(1),Q(0))})
 def test_disjoint(self):
  self.assertEqual(plane_segment(P,((3,0,-1),(3,1,1),(3,1,-1))),())
 def test_exact_rational_endpoint(self):
  s=plane_segment(P,((Q(1,2),-1,-1),(Q(1,2),2,1),(Q(1,2),2,-1)))
  self.assertEqual(set(s),{(Q(1,2),Q(1,2),Q(0)),(Q(1,2),Q(3,2),Q(0))})
 def test_coplanar_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"COPLANAR_PAIR"):
   plane_segment(P,((0,0,0),(1,0,0),(0,1,0)))
 def test_degenerate_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"DEGENERATE"):
   plane_segment(P,((0,0,0),(1,0,0),(2,0,0)))
if __name__=="__main__": unittest.main()
