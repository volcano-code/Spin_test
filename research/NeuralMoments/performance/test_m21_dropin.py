"""W1 M21 source-pinned arithmetic-only candidate regression."""
from __future__ import annotations
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
from zipfile import ZipFile
import gzip

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=Path(os.environ.get('W1_M21_SOURCE_PATH', ROOT/'research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/verify_h8_exact_moments.py'))
ARCHIVE=Path(os.environ.get('W1_M21_H8E_ARCHIVE','/mnt/data/h8e-25point-39121571756.zip'))
CANDIDATE=HERE/'m21_independent_verifier_candidate.py'
EXPECTED='79ca86064b2b2d990ab5b42b202e3339b6356509'

def loaded(path,label):
    spec=importlib.util.spec_from_file_location(label,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ExactCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=SOURCE.read_bytes()
        cls.assert_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\x00'+raw).hexdigest()
        cls.original=loaded(SOURCE,'w1_pinned_reference')
        cls.candidate=loaded(CANDIDATE,'w1_candidate')

    def same(self, vertices,faces):
        a=self.original.independent_ten_raw_moments(vertices,faces)
        b=self.candidate.independent_ten_raw_moments(vertices,faces)
        self.assertEqual(a,b)
        self.assertEqual(len(b),10)
        self.assertTrue(all(isinstance(x,Fraction) for x in b))
        return b

    def test_source_authentic(self):
        self.assertEqual(self.assert_blob,EXPECTED)
    def test_parser_not_changed(self):
        for token in ('1/2','-3/7','0b101/0b111','0/1'):
            self.assertEqual(self.original.exact(token),self.candidate.exact(token))
    def test_invalid_token_same_exception(self):
        for token in ('1/0','1/-1','xyz/1','3/4/5'):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):self.original.exact(token)
                with self.assertRaises(ValueError):self.candidate.exact(token)
    def test_tetrahedron_positive(self):
        v=[['0/1','0/1','0/1'],['1/1','0/1','0/1'],['0/1','1/1','0/1'],['0/1','0/1','1/1']]
        f=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        self.assertEqual(self.same(v,f)[0],Fraction(1,6))
    def test_tetrahedron_negative(self):
        v=[['0/1','0/1','0/1'],['1/1','0/1','0/1'],['0/1','1/1','0/1'],['0/1','0/1','1/1']]
        f=[[0,1,2],[0,3,1],[0,2,3],[1,3,2]]
        self.assertEqual(self.same(v,f)[0],Fraction(-1,6))
    def test_degenerate_zero(self):
        v=[['0/1','0/1','0/1']]*4
        self.assertEqual(self.same(v,[[0,1,2]]),tuple(Fraction(0) for _ in range(10)))
    def test_bad_face_same_error(self):
        v=[['0/1','0/1','0/1']]*4
        for f in ([0,1,4],[-1,1,2],[False,1,2],[0,1]):
            with self.subTest(face=f):
                with self.assertRaisesRegex(ValueError,'INVALID_EXACT_FACE'):
                    self.original.independent_ten_raw_moments(v,[f])
                with self.assertRaisesRegex(ValueError,'INVALID_EXACT_FACE'):
                    self.candidate.independent_ten_raw_moments(v,[f])
    def test_large_denominator(self):
        v=[['0/1','0/1','0/1'],['1/999999998899','0/1','0/1'],['0/1','1/3141592653589793','0/1'],['0/1','0/1','1/2718281828459045']]
        self.same(v,[[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
    def test_actual_h8e_0_exact_parity(self):
        if not ARCHIVE.is_file():self.skipTest('real H8e input required')
        with ZipFile(ARCHIVE) as z:
            v=json.loads(gzip.decompress(z.read('artifacts/h8e-jacobian-cols0-4-8/point-000-material.json.gz')))
        got=self.same(v['variable_rational_vertices'],v['variable_faces'])
        self.assertEqual(tuple(float(x) for x in got),tuple(v['variable_raw_moments']))
    def test_evidence_scope(self):
        d=json.loads((HERE/'evidence/m21-dropin-real-3point.json').read_text())
        self.assertEqual(d['points'],[0,8,17])
        self.assertEqual(d['exact_ten_components'],30)
        self.assertEqual(d['native_boolean_calls'],0)
        self.assertIsNone(d['full_solver_speedup'])
        self.assertFalse(d['candidate_production_admitted'])

if __name__=='__main__':unittest.main()
