"""Tests for real-native archived H8e dual-GMP experiment and recovered 25 points."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from m15_consolidate import merge
from m15_real_native_surface_tetra import scientific_check, run


class M15Gates(unittest.TestCase):
    @staticmethod
    def sample():
        stage=lambda variant: dict(variant=variant,reference_or_roundtrip_ns=3,
            boundary_gate_ns=5,gmp_ten_ns=17,total_ns=26)
        return dict(schema='w1-m3-real-h8-exact-gmp-v2',vertices=8455,faces=16910,
            exact_ten_moments_equal=True,recomputed_cherchi_boolean=False,
            jacobian_recomputed=False,ten_exact=['1/1']*10,
            stages=[stage(v) for v in ('legacy','prepared','prepared','legacy')])
    @staticmethod
    def tetra():
        return dict(schema='w1-m6-exact-independent-tetra-v1',vertices=8455,
            faces=16910,exact_ten=['1/1']*10,input_parse_ns=10,
            full_boundary_gate_ns=10,independent_tetra_ns=10)

    def test_valid_exact_synthetic(self):
        self.assertEqual(scientific_check(self.sample(),self.tetra(),[1.0]*10),0)
    def test_wrong_exact_moment_rejected(self):
        b=self.tetra();b['exact_ten'][9]='2/1'
        with self.assertRaisesRegex(ValueError,'EXACT_DRIFT'):
            scientific_check(self.sample(),b,[1.0]*10)
    def test_reference_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'HISTORICAL_INDEPENDENT'):
            scientific_check(self.sample(),self.tetra(),[9.0]*10)
    def test_wrong_geometry_rejected(self):
        a=self.sample();a['faces']=4
        with self.assertRaisesRegex(ValueError,'SCOPE_OR_SIZE'):
            scientific_check(a,self.tetra(),[1.0]*10)
    def test_missing_boundary_stage_rejected(self):
        a=self.sample();a['stages'][0]['boundary_gate_ns']=999
        with self.assertRaisesRegex(ValueError,'NEGATIVE_TIMER'):
            scientific_check(a,self.tetra(),[1.0]*10)
    def test_two_variants_mandatory(self):
        a=self.sample();a['stages'][0]['variant']='prepared'
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_EXCLUSIVE'):
            scientific_check(a,self.tetra(),[1.0]*10)
    def test_recomputed_boolean_claim_rejected(self):
        a=self.sample();a['recomputed_cherchi_boolean']=True
        with self.assertRaisesRegex(ValueError,'SCOPE_OR_SIZE'):
            scientific_check(a,self.tetra(),[1.0]*10)
    def test_reject_empty_point_range(self):
        with self.assertRaisesRegex(ValueError,'SAMPLE_RANGE'):
            run('bad','bad','bad','unused',points=0)
    def test_reject_out_of_bounds_start(self):
        with self.assertRaisesRegex(ValueError,'SAMPLE_RANGE'):
            run('bad','bad','bad','unused',points=25,start=25)

    @staticmethod
    def env():
        names=('W1_M15_ARCHIVE','W1_M15_SURFACE_BIN','W1_M15_TETRA_BIN',
               'W1_M15_INTERRUPTED','W1_M15_RESUMED')
        return [os.environ.get(s) for s in names]

    def test_recovered_25_real_archive_rows(self):
        vals=self.env()
        if any(not x for x in vals):self.skipTest('set real archived native evidence paths')
        report,ba,rows=merge(vals[3],vals[4],vals[1],vals[2])
        self.assertEqual(len(rows),25)
        self.assertEqual(report['exact_components_matched'],250)
        self.assertEqual(report['native_boolean_calls'],0)
        self.assertEqual(report['original_branch_hash_changes'],8)
        self.assertGreater(report['isolated_surface_ref_ratio'],0)
        self.assertIsNone(ba['full_production_faster_speedup'])

    def test_actual_one_point_fresh_compiled_native(self):
        vals=self.env()
        if any(not x for x in vals[:3]):self.skipTest('requires authentic H8e archive and two compiled GMP binaries')
        with tempfile.TemporaryDirectory() as tmp:
            result=run(vals[0],vals[1],vals[2],Path(tmp)/'real-one',points=1)
            self.assertEqual(result['real_archived_points'],1)
            self.assertTrue(result['exact_ten_equal_each_point'])
            self.assertEqual(result['max_independent_reference_scaled_error'],0.0)

    def test_wrong_archive_fail_closed(self):
        vals=self.env()
        if any(not x for x in vals[1:3]):self.skipTest('requires two compiled GMP binaries')
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)/'wrong.zip';archive.write_bytes(b'wrong archive')
            out=Path(tmp)/'bad'
            with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA_MISMATCH'):
                run(archive,vals[1],vals[2],out,points=1)
            failure=json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['completed_packets'],0)
            self.assertFalse((out/'baseline-performance.json').exists())

    def test_tampered_25point_log_rejected(self):
        vals=self.env()
        if any(not x for x in vals[1:]):self.skipTest('requires actual recovered 25 point files')
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(vals[4]);target=Path(tmp)/'tampered';target.mkdir()
            (target/'baseline-performance.json').write_bytes((src/'baseline-performance.json').read_bytes())
            text=(src/'point-events.jsonl').read_text().splitlines()
            row=json.loads(text[0]);row['feature_hash']='tampered'
            text[0]=json.dumps(row)
            (target/'point-events.jsonl').write_text('\n'.join(text)+'\n')
            with self.assertRaisesRegex(ValueError,'EIGHT_BRANCH'):
                merge(vals[3],target,vals[1],vals[2])

if __name__=='__main__':unittest.main()
