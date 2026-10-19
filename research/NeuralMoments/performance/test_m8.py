"""M8 strict isolated real H8 construction parity, with negative evidence gates."""
import copy
from fractions import Fraction
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

import m8_exact_construction_trial as m

ARCHIVE = Path(os.environ.get('W1_M8_H8E_ARCHIVE','/mnt/data/h8e-25point-39121571756.zip'))

class TestM8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file():
            raise AssertionError('M8_REAL_H8E_ARCHIVE_MUST_BE_SUPPLIED_FOR_REAL_TESTS')
        cls.z=ZipFile(ARCHIVE)
        cls.data,cls.hist=m.load_identity(cls.z,ARCHIVE)
        cls.design=cls.data['design_vertices']
        cls.packet,cls.ref=m.load_point(cls.z,0)

    @classmethod
    def tearDownClass(cls):
        cls.z.close()

    def test_fraction_semantics_exact_and_errors(self):
        for token in ('-0b101/0b100','1/3','0/1','-500/7','18/0b101','-1/-2'):
            self.assertEqual(m.reference_fraction(token),m.fraction_parser(True)(token))
        for bad in ('1/0','not-a-fraction','1/2/3'):
            with self.assertRaises((ValueError,ZeroDivisionError)):
                m.reference_fraction(bad)
            with self.assertRaises((ValueError,ZeroDivisionError)):
                m.fraction_parser(True)(bad)

    def test_cached_parser_is_bounded_per_call(self):
        a=m.fraction_parser(True)
        for _ in range(100): self.assertEqual(a('8/11'),Fraction(8,11))
        self.assertEqual(a.cache_info().misses,1)
        self.assertEqual(a.cache_info().hits,99)
        self.assertEqual(a.cache_info().maxsize,65536)
        self.assertEqual(m.fraction_parser(True).cache_info().currsize,0)

    def test_exact_identity_target_and_nongeneric_fallback(self):
        p=[(Fraction(1,7),Fraction(3,7),Fraction(1,10))]
        ax=[[1,0,0],[0,1,0],[0,0,1]]
        a,_=m.target_coordinates(p,ax,[0,0,-.115],mode='original')
        b,isunit=m.target_coordinates(p,ax,[0,0,-.115],mode='optimized')
        self.assertTrue(isunit);self.assertEqual(a,b)
        ax=[[0,-1,0],[1,0,0],[0,0,1]]
        a,_=m.target_coordinates(p,ax,[1,.3,2],mode='original')
        b,isunit=m.target_coordinates(p,ax,[1,.3,2],mode='optimized')
        self.assertFalse(isunit);self.assertEqual(a,b)

    def test_nested_unregistered_stages_rejected(self):
        x=m.Clock()
        with self.assertRaisesRegex(ValueError,'M8_STAGE_NESTING'):
            with x.stage('parse_exact_vertices'):
                with x.stage('target_coordinates'):pass
        self.assertFalse(x.finish()['all_passed'])
        with self.assertRaisesRegex(ValueError,'M8_STAGE_NESTING'):
            with x.stage('FAKE_PRODUCTION_BOOLEAN'):pass

    def test_original_first_actual_point_reproduces_full_archive(self):
        result=m.evaluate_packet(self.packet,self.design,self.data,'original')
        self.assertEqual(result['record_count'],8455)
        self.assertTrue(result['unit_axes'])
        self.assertTrue(result['timing']['all_passed'])

    def test_candidate_first_actual_point_reproduces_full_archive(self):
        result=m.evaluate_packet(self.packet,self.design,self.data,'optimized')
        self.assertEqual(result['record_count'],8455)
        self.assertGreater(result['parser_cache']['hits'],30000)
        self.assertLess(result['parser_cache']['misses'],30000)

    def test_original_and_candidate_real_12_24_parity(self):
        for idx in (12,24):
            p,_=m.load_point(self.z,idx)
            for mode in ('original','optimized'):
                self.assertTrue(m.evaluate_packet(p,self.design,self.data,mode)['timing']['all_passed'])

    def test_reference_provenance_change_rejected(self):
        p=copy.deepcopy(self.packet)
        p['material_proof']['resolved_construction_records'][0]['vertex_index']=999
        with self.assertRaisesRegex(ValueError,'M8_PROVENANCE_RECORD_DRIFT'):
            m.evaluate_packet(p,self.design,self.data,'optimized')

    def test_float_drift_rejected(self):
        p=copy.deepcopy(self.packet)
        p['variable_vertices'][0][0]+=0.01
        with self.assertRaisesRegex(ValueError,'M8_BINARY64_TARGET_COORDINATE_DRIFT'):
            m.evaluate_packet(p,self.design,self.data,'optimized')

    def test_fraction_target_drift_rejected(self):
        p=copy.deepcopy(self.packet)
        p['variable_rational_vertices'][0][0]='999/1'
        with self.assertRaisesRegex(ValueError,'M8_EXACT_TARGET_COORDINATE_DRIFT'):
            m.evaluate_packet(p,self.design,self.data,'optimized')

    def test_frozen_request_checksum_and_zip_drift_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            bad=tmp/'wrong.zip';bad.write_bytes(b'PK\x03\x04fake')
            with self.assertRaisesRegex(ValueError,'M8_ARCHIVE_SHA_DRIFT'):
                with ZipFile(ARCHIVE) as z: m.load_identity(z,bad)
            with self.assertRaisesRegex(ValueError,'M8_UNPINNED_PRODUCTION_SOURCE'):
                source=tmp/'not_the_original.py';source.write_text('print(5)')
                m.verify_pinned_python_source(source)

    def test_out_of_range_job_rejected_and_original_hash_failure_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            # Unsafe job sizes reject before any scientific use.
            with self.assertRaisesRegex(ValueError,'M8_BAD_SAMPLE_COUNT'):
                m.run(ARCHIVE,Path(temp)/'no-write',count=26)
        self.assertEqual(self.hist['changed_feature_hash_points'],8)

    def test_real_single_point_scope_does_not_claim_solver_speed(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'run'
            r=m.run(ARCHIVE,out,count=1)
            self.assertEqual(r['checked_point_evaluations'],4)
            self.assertIsNone(r['production_speedup'])
            self.assertFalse(r['source_on_disk_verified'])
            self.assertTrue((out/'baseline-performance.json').is_file())
            self.assertFalse((out/'failure.json').exists())

if __name__=='__main__': unittest.main()
