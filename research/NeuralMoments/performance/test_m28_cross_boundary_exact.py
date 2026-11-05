from fractions import Fraction as F
import subprocess
import unittest
from pathlib import Path

BIN = Path(__file__).with_name('m28_cross_boundary_exact')

def tri_packet(out_tri, other_tri):
    def tok(x):
        x=F(x)
        return f'{x.numerator}/{x.denominator}'
    lines=[f'3 1 3 1']
    for p in out_tri: lines.append(' '.join(tok(x) for x in p))
    lines.append('0 1 2')
    for p in other_tri: lines.append(' '.join(tok(x) for x in p))
    lines.append('0 1 2')
    return '\n'.join(lines)+'\n'

OUT=((F(0),F(0),F(0)),(F(2),F(0),F(0)),(F(0),F(2),F(0)))

def run(other, expected, code=0):
    cp=subprocess.run([str(BIN),'--max-seconds','10'],input=tri_packet(OUT,other),text=True,capture_output=True,timeout=15)
    assert cp.returncode==code,(cp.returncode,cp.stdout,cp.stderr)
    assert f'status={expected}' in cp.stdout,cp.stdout
    return cp.stdout

class TestM28CrossBoundary(unittest.TestCase):
    def test_non_coplanar_segment_crosses_output_interior(self):
        other=((F(1,2),-1,-1),(F(1,2),2,-1),(F(1,2),0,1))
        run(other,'OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR',2)

    def test_non_coplanar_contact_only_on_output_edge_is_allowed(self):
        other=((F(1,2),0,0),(F(3,2),0,0),(1,1,1))
        run(other,'EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION')

    def test_chord_with_both_endpoints_on_output_boundary_is_rejected(self):
        other=((1,0,0),(0,1,0),(F(1,2),F(1,2),1))
        run(other,'OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR',2)

    def test_coplanar_area_overlap_is_rejected(self):
        other=((F(1,2),F(1,2),0),(1,F(1,2),0),(F(1,2),1,0))
        run(other,'OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR',2)

    def test_coplanar_boundary_edge_contact_is_allowed(self):
        other=((F(1,2),0,0),(F(3,2),0,0),(1,-1,0))
        run(other,'EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION')

    def test_coplanar_single_point_contact_in_output_interior_is_rejected(self):
        other=((F(1,2),F(1,2),0),(-1,F(1,2),0),(F(1,2),-1,0))
        run(other,'OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR',2)

    def test_parallel_disjoint_triangles_are_allowed(self):
        other=((0,0,1),(2,0,1),(0,2,1))
        run(other,'EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION')


    def test_non_coplanar_single_point_contact_in_output_interior_is_rejected(self):
        other=((F(1,2),F(1,2),0),(F(1,2),F(1,2),1),(1,1,1))
        run(other,'OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR',2)

    def test_non_coplanar_single_point_contact_at_output_vertex_is_allowed(self):
        other=((0,0,0),(0,0,1),(1,1,1))
        run(other,'EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION')

    def test_reversing_output_orientation_does_not_change_geometric_intersection(self):
        out=(OUT[0],OUT[2],OUT[1])
        other=((1,0,0),(0,1,0),(F(1,2),F(1,2),1))
        cp=subprocess.run([str(BIN),'--max-seconds','10'],input=tri_packet(out,other),text=True,capture_output=True,timeout=15)
        self.assertEqual(cp.returncode,2,cp.stdout+cp.stderr)
        self.assertIn('status=OUTPUT_TRIANGLE_INTERSECTS_OPPOSITE_BOUNDARY_INTERIOR',cp.stdout)

    def test_sub_ulp_rational_gap_at_coordinate_two_is_not_intersection(self):
        eps=F(1,2**80)
        other=((2+eps,0,0),(3,0,0),(2+eps,1,0))
        run(other,'EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION')

if __name__=='__main__': unittest.main(verbosity=2)