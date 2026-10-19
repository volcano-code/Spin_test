"""M8 offline proofs; archived material is optional via W2_H8E_ARCHIVE_ZIP."""
import copy
import gzip
import json
import os
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from audit_archived_h8e import (PREFIX, exact_fraction, independent_exact_ten,
                               check_ulp, check_point_header, audit_archive,
                               digest, sha, require, valid10)


class TestOfflineExactOracle(unittest.TestCase):
    def setUp(self):
        self.vertices=[['0/1','0/1','0/1'],['1/1','0/1','0/1'],
                       ['0/1','1/1','0/1'],['0/1','0/1','1/1']]
        self.faces=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]

    def test_tetrahedron_exact_ten_moments(self):
        r=independent_exact_ten(self.vertices,self.faces)
        self.assertEqual(r[0],Fraction(1,6))
        self.assertEqual(r[1:4],[Fraction(1,24)]*3)
        self.assertEqual(r[4:7],[Fraction(1,60)]*3)
        self.assertEqual(r[7:10],[Fraction(1,120)]*3)

    def test_winding_reversed_fails(self):
        with self.assertRaisesRegex(ValueError,'EXACT_NONPOSITIVE_MASS'):
            independent_exact_ten(self.vertices,[f[::-1] for f in self.faces])

    def test_open_tetra_fails(self):
        with self.assertRaisesRegex(ValueError,'EXACT_BOUNDARY_NOT_CLOSED'):
            independent_exact_ten(self.vertices,self.faces[:-1])

    def test_invalid_fraction(self):
        for token in ('0b11/0b10','4/0','1/-2','nan/1'):
            with self.assertRaises(ValueError):exact_fraction(token)

    def test_independent_numeric_ulp_gate(self):
        actual=[float(Fraction(1,6))]+[0.0]*9
        self.assertEqual(check_ulp(actual,[Fraction(1,6)]+[Fraction(0)]*9,'T')[1],0.0)
        actual[8]=1
        with self.assertRaisesRegex(ValueError,'ARCHIVED_INDEPENDENT_TEN_MOMENT_ULP_MISMATCH'):
            check_ulp(actual,[Fraction(1,6)]+[Fraction(0)]*9,'T')

    def test_scalar_vector_shape_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'INVALID_TEN'):
            valid10([0]*9,'TEST')
        with self.assertRaisesRegex(ValueError,'NONFINITE_TEN'):
            valid10([float('nan')]+[0]*9,'TEST')


ARCHIVE=os.environ.get('W2_H8E_ARCHIVE_ZIP')

@unittest.skipUnless(ARCHIVE and Path(ARCHIVE).is_file(),
                     'Real archive not supplied; set W2_H8E_ARCHIVE_ZIP')
class TestHistoricalCherchiArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=ZipFile(ARCHIVE)
        cls.report=json.loads(cls.archive.read(PREFIX+'report.json'))
        cls.row=json.loads(cls.archive.read(PREFIX+'point-000.json'))
        cls.blob=cls.archive.read(PREFIX+'point-000-material.json.gz')
        cls.material=json.loads(gzip.decompress(cls.blob))

    @classmethod
    def tearDownClass(cls):cls.archive.close()

    def test_same_call_header_real(self):
        c=check_point_header(0,self.row,self.blob,self.material,self.report)
        self.assertEqual(len(c),10)
        self.assertEqual(self.report['production_cherchi_calls'],25)

    def test_archive_gzip_sha_mutation_rejected(self):
        changed=copy.deepcopy(self.row)
        changed['exact_same_call_material_archive_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'MATERIAL_GZIP_SHA_MISMATCH'):
            check_point_header(0,changed,self.blob,self.material,self.report)

    def test_archived_cross_coefficient_swap_rejected(self):
        changed=copy.deepcopy(self.row)
        changed['coefficients'][7],changed['coefficients'][8]=1,2
        with self.assertRaisesRegex(ValueError,'SAME_CALL_NATIVE_C_MISMATCH'):
            check_point_header(0,changed,self.blob,self.material,self.report)

    def test_geometry_hash_mutation_rejected(self):
        changed=copy.deepcopy(self.material)
        changed['geometry_hash']='0'*64
        with self.assertRaisesRegex(ValueError,'SAME_CALL_GEOMETRY_MISMATCH'):
            check_point_header(0,self.row,self.blob,changed,self.report)

    def test_exact_one_real_point_reverified(self):
        report=audit_archive(ARCHIVE,limit=1)
        self.assertEqual(report['verified_points'],1)
        self.assertEqual(report['max_exact_raw_ten_moment_absolute_error'],0)
        self.assertEqual(report['training_samples_admitted'],0)
        self.assertEqual(report['source']['workflow_conclusion'],'failure')

if __name__=='__main__': unittest.main()
