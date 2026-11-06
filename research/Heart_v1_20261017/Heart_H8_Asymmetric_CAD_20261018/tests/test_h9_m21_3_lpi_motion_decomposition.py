from fractions import Fraction as F
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
import h9_m21_3_lpi_motion_decomposition as m
import h9_m21_motion_math as mm

def tok(x):
    x=F(x)
    return f"{x.numerator}/{x.denominator}"

def fixture(points, velocities):
    objects=[(0,0),(0,1),(1,0),(1,1),(1,2)]
    ops=[{"status":"UNIQUE","source_vertices":[{"input_object":o,"input_vertex":i}]}
         for o,i in objects]
    raw={"point_type":"LPI","operand_coordinates_exact":[[tok(x) for x in p] for p in points]}
    resolved={"point_type":"LPI","operands":ops}
    return raw,resolved

class LpiDecompositionTests(unittest.TestCase):
    def setUp(self):
        self.points=[[0,0,0],[0,0,2],[0,0,1],[1,0,1],[0,1,1]]

    def test_translating_plane_exact_decomposition(self):
        vel=[[0,0,3],[0,0,3],[0,0,3]]
        raw,res=fixture(self.points,vel); d=m.decompose_lpi(raw,res,vel)
        self.assertEqual(F(d["d_exact"]),F(2))
        self.assertEqual(F(d["dprime_total"]),F(0))
        self.assertEqual(F(d["t_exact"]),F(1,2))
        self.assertEqual(F(d["tprime_total"]),F(3,2))
        self.assertEqual(tuple(map(F,d["velocity_exact"])),(F(0),F(0),F(3)))
        self.assertTrue(d["decomposition_identity_exact"])

    def test_tilted_plane_has_denominator_derivative(self):
        vel=[[0,0,0],[1,0,0],[0,0,0]]
        raw,res=fixture(self.points,vel); d=m.decompose_lpi(raw,res,vel)
        p=[mm.vec(x) for x in raw["operand_coordinates_exact"]]
        v=[mm.ZERO,mm.ZERO,*[mm.vec(x) for x in vel]]
        _,expected=mm.construction("LPI",p,v)
        self.assertNotEqual(F(d["dprime_total"]),0)
        self.assertEqual(tuple(map(F,d["velocity_exact"])),expected)
        self.assertEqual(F(d["tprime_total"]),
            F(d["tprime_plane_denominator"])+F(d["tprime_point_motion"])+F(d["tprime_line_motion"]))

    def test_denominator_and_tprime_term_reconstruction(self):
        vel=[[1,0,2],[0,1,0],[0,0,-1]]
        raw,res=fixture(self.points,vel); d=m.decompose_lpi(raw,res,vel)
        self.assertEqual(F(d["dprime_total"]),F(d["dprime_plane"])+F(d["dprime_line"]))
        self.assertEqual(F(d["numerator_prime_total"]),
            F(d["numerator_prime_plane"])+F(d["numerator_prime_point"]))
        self.assertTrue(d["decomposition_identity_exact"])

    def test_analytic_velocity_matches_independent_position_finite_difference(self):
        vel=[[0,0,0],[1,0,0],[0,0,0]]
        raw,res=fixture(self.points,vel); d=m.decompose_lpi(raw,res,vel)
        p=[mm.vec(x) for x in raw["operand_coordinates_exact"]]
        v=[mm.ZERO,mm.ZERO,*[mm.vec(x) for x in vel]]
        x0=mm.construction("LPI",p,[mm.ZERO]*5)[0]
        eps=F(1,10**7)
        p_eps=[mm.add(x,mm.mul(eps,dx)) for x,dx in zip(p,v)]
        x1=mm.construction("LPI",p_eps,[mm.ZERO]*5)[0]
        fd=mm.mul(1/eps,mm.sub(x1,x0))
        analytic=tuple(map(F,d["velocity_exact"]))
        self.assertLess(max(float(abs(a-b)) for a,b in zip(fd,analytic)),1e-5)

    def test_parallel_line_rejected(self):
        points=[[0,0,1],[1,0,1],[0,0,1],[1,0,1],[0,1,1]]
        vel=[[0,0,0]]*3
        raw,res=fixture(points,vel)
        with self.assertRaisesRegex(ValueError,"PARALLEL"):
            m.decompose_lpi(raw,res,vel)

    def test_feature_key_canonicalizes_endpoint_and_plane_order(self):
        self.assertEqual(m.feature_key((3756,3813),(24,86,87)),
                         m.feature_key((3813,3756),(87,24,86)))

    def test_non_unique_operand_rejected(self):
        vel=[[0,0,0]]*3
        raw,res=fixture(self.points,vel); res["operands"][2]["status"]="AMBIGUOUS"
        with self.assertRaisesRegex(ValueError,"NOT_UNIQUE"):
            m.decompose_lpi(raw,res,vel)

    def test_bad_source_velocity_index_rejected(self):
        vel=[[0,0,0]]*2
        raw,res=fixture(self.points,vel)
        with self.assertRaisesRegex(ValueError,"INDEX_OOB"):
            m.decompose_lpi(raw,res,vel)

    def test_decomposition_terms_are_exactly_reconstructed(self):
        vel=[[0,0,0]]*3
        raw,res=fixture(self.points,vel); d=m.decompose_lpi(raw,res,vel)
        self.assertTrue(d["decomposition_identity_exact"])

if __name__=="__main__":
    unittest.main(verbosity=2)
