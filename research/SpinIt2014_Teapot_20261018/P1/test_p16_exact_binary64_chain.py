"""W4 P16 mathematical and genuinely archived Cherchi source regressions."""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from p16_exact_binary64_chain import (
    P14_SHA256, P15_SHA256, CASES, SCHEMA, analyze, check_sources,
    chain_difference, exact_ten, oriented_counter, read_obj_binary64, sha,
)

BASE=Path(__file__).resolve().parent
P14=Path(os.environ.get('W4_P16_REAL_P14_DIR',str(BASE/'p14/research/SpinIt2014_Teapot_20261018/P1')))
P15=Path(os.environ.get('W4_P16_REAL_P15_DIR',str(BASE/'p15')))


class AnalyticChainTests(unittest.TestCase):
    def test_exact_undoubled_ten_tetrahedron(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        f=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        r=exact_ten(v,f)
        self.assertEqual(r[0],Fraction(1,6))
        self.assertEqual(r[1:4],(Fraction(1,24),)*3)
        self.assertEqual(r[4:7],(Fraction(1,60),)*3)
        self.assertEqual(r[7:10],(Fraction(1,120),)*3)
        self.assertTrue(all(isinstance(x,Fraction) for x in r))

    def test_binary64_fraction_does_not_round_to_decimal_heuristic(self):
        v=[(0.1,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
        f=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        r=exact_ten(v,f)
        self.assertIsInstance(r[0],Fraction)
        self.assertNotEqual(r[0],Fraction(9,60))
        self.assertNotEqual(Fraction(0.1),Fraction('0.1'))

    def test_oriented_signed_triangle_respects_only_cyclic_permutations(self):
        v=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        a=oriented_counter(v,[(0,1,2)])
        b=oriented_counter(v,[(1,2,0)])
        inv=oriented_counter(v,[(0,2,1)])
        self.assertEqual(a,b)
        self.assertNotEqual(a,inv)
        self.assertFalse(chain_difference((1,a),(-1,b)))
        self.assertTrue(chain_difference((1,a),(-1,inv)))

    def test_negative_zero_normalized_in_strict_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'tiny.obj'
            f.write_text('v -0.0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
            vertices,faces=read_obj_binary64(f)
            self.assertEqual(vertices[0][0],0.)
            self.assertEqual(oriented_counter(vertices,faces),oriented_counter(
                [(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)],[(0,1,2)]))

    def test_no_nonsensical_face_or_nan_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'bad.obj'
            cases=('v nan 0 0\n','v 0 0 0\nf 1 2 3 4\n',
                   'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 7\n')
            for sample in cases:
                f.write_text(sample)
                with self.assertRaises(ValueError):
                    read_obj_binary64(f)


@unittest.skipUnless(P14.exists() and P15.exists(),'real native P14/P15 archives not materialized')
class AuthenticCherchiP16Tests(unittest.TestCase):
    def test_real_source_reports_and_immutable_identity(self):
        p14=P14/'p14-cherchi-junction-study/p14-junction-native-study.json'
        p15=P15/'p15-inherited-sliver-study.json'
        self.assertEqual(sha(p14),P14_SHA256)
        self.assertEqual(sha(p15),P15_SHA256)
        original,clean,files=check_sources(P14,P15)
        self.assertEqual(set(files),set(CASES))
        self.assertTrue(original.is_file() and clean.is_file())

    def test_full_real_exact_rational_and_chain(self):
        with tempfile.TemporaryDirectory() as d:
            data=analyze(P14,P15,Path(d)/'certificate.json')
            self.assertEqual(data['schema'],SCHEMA)
            self.assertEqual(data['status'],'EXACT_BINARY64_MOMENT_CANCELLATION_WITH_STRICT_SURFACE_NONIDENTITY')
            v=data['exact_saved_binary64_outer_volume_difference']
            self.assertEqual(v['numerator'],'3727329694084957988057560810167920790317082511')
            self.assertEqual(v['denominator'],'842498333348457493583344221469363458551160763204392890034487820288')
            self.assertFalse(v['is_zero'])
            self.assertAlmostEqual(v['decimal_projection'],4.424138952620733e-21,delta=1e-32)
            self.assertEqual(len(data['cases']),3)
            self.assertEqual(data['signed_oriented_chain_change_term_count'],90)
            self.assertTrue(data['signed_chain_face_difference_preserved_for_all_three'])
            self.assertEqual([r['saved_triangle_chain_residual_terms_native'] for r in data['cases']],
                             [1280,1248,1248])
            for r in data['cases']:
                self.assertTrue(r['exact_oriented_chain_change_identical_for_M_and_F'])
                self.assertTrue(r['exact_original_signed_tetra_ten_moment_residual_all_zero'])
                self.assertTrue(r['exact_cleaned_signed_tetra_ten_moment_residual_all_zero'])
                self.assertTrue(r['boundary_chain_residual_is_nonzero'])
                self.assertEqual(r['exact_native_volume_delta']['numerator'],v['numerator'])
                self.assertEqual(r['exact_native_volume_delta']['denominator'],v['denominator'])
            self.assertFalse(data['exact_implicit_Cherchi_surface_certified'])
            self.assertFalse(data['full_set_equality_original_vs_microweld'])
            self.assertFalse(data['W0_physical_tip_or_FD_approved'])
            self.assertFalse(data['Faster_optimization_executed'])
            self.assertTrue((Path(d)/'certificate.json').is_file())

    def test_no_output_writes_to_original_artifacts(self):
        orig=P14/'p13-native-Cherchi-domain/p13-outer-cherchi-union.obj'
        clean=P15/'outer_numeric_microweld.obj'
        pinned=[sha(orig),sha(clean)]
        with tempfile.TemporaryDirectory() as d:
            analyze(P14,P15,Path(d)/'new.json')
        self.assertEqual([sha(orig),sha(clean)],pinned)

    def test_mutated_p15_output_rejected_by_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'p15'
            shutil.copytree(P15,dest)
            target=dest/'rotate_1p5/F_numeric_microweld.obj'
            target.write_bytes(target.read_bytes()+b'\n# unjustified extra data\n')
            with self.assertRaisesRegex(ValueError,'P15_NATIVE_CASE_OR_FILE_SHA_INVALID'):
                check_sources(P14,dest)

    def test_mutated_p14_report_never_claimed_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'p14'
            shutil.copytree(P14,dest)
            target=dest/'p14-cherchi-junction-study/p14-junction-native-study.json'
            doc=json.loads(target.read_text())
            doc['admissible_candidate']={'fake':'yes'}
            target.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError,'FROZEN_P14_OR_P15_ACTUAL_REPORT_DIGEST_MISMATCH'):
                check_sources(dest,P15)

    def test_all_moment_ratios_exact_not_tolerance_heuristic(self):
        with tempfile.TemporaryDirectory() as temp:
            data=analyze(P14,P15,Path(temp)/'proof.json')
            m=data['exact_saved_binary64_outer_moment_delta']
            self.assertEqual(set(m),{'M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY'})
            self.assertTrue(all((not x['is_zero']) for x in m.values()))
            self.assertGreater(abs(m['QZZ']['decimal_projection']),abs(m['M']['decimal_projection']))


if __name__=='__main__':
    unittest.main()
