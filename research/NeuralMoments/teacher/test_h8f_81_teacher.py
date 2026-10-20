"""W2 M9 historical 81 point gate — no native Cherchi job in test process."""
import copy
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile
import json
import os
import unittest
import tempfile
import numpy as np
from audit_h8f_81_teacher import (ARCHIVE_SHA, REPORT_SHA, CLASS_SHA, REQUEST_SHA,
  ROOT, STABLE, CHANGED, audit, digest, exact10, fixed_in_target,
  finite_difference, face_keys, witness_59_60, require)

ARCHIVE=os.environ.get('W2_H8F_ARCHIVE')
CANDIDATES=os.environ.get('W2_M9_CANDIDATES')

class TestIndependentOracle(unittest.TestCase):
    def test_exact_tetra_moments(self):
        v=[['0','0','0'],['1','0','0'],['0','1','0'],['0','0','1']]
        f=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        r=exact10(v,f)
        self.assertEqual(r[0],Fraction(1,6))
        self.assertEqual(r[1:4],[Fraction(1,24)]*3)
        self.assertEqual(r[4:7],[Fraction(1,60)]*3)
        self.assertEqual(r[7:10],[Fraction(1,120)]*3)
    def test_wrong_winding_fails(self):
        v=[['0','0','0'],['1','0','0'],['0','1','0'],['0','0','1']]
        f=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        with self.assertRaisesRegex(ValueError,'NONPOSITIVE_EXACT_MASS'):
            exact10(v,[a[::-1] for a in f])
    def test_open_boundary_fails(self):
        v=[['0','0','0'],['1','0','0'],['0','1','0'],['0','0','1']]
        f=[[0,2,1],[0,1,3],[0,3,2]]
        with self.assertRaisesRegex(ValueError,'OPEN_OR_ORIENTATION_FAILED'):
            exact10(v,f)
    def test_frozen_sha_properties(self):
        for x in (ARCHIVE_SHA,REPORT_SHA,CLASS_SHA,REQUEST_SHA):
            self.assertEqual(len(x),64)
    def test_fail_closed_invalid_mode(self):
        with self.assertRaisesRegex(ValueError,'INVALID_EXACT_MODE'):
            audit('/tmp/notthere.zip',exact_mode='bogus')
    def test_report_full_replay_required(self):
        with self.assertRaisesRegex(ValueError,'UNRECOGNIZED_H8F_ARCHIVE_SHA'):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'bad.zip';p.write_bytes(b'not an archive')
                audit(p)

@unittest.skipUnless(ARCHIVE and Path(ARCHIVE).is_file(), 'authentic H8f zip not supplied')
class TestHistoricalH8f(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with ZipFile(ARCHIVE) as z:
            cls.report=json.loads(z.read(ROOT+'report.json'))
            cls.classifier=json.loads(z.read('artifacts/h8f-81-exact-construction-classification.json'))
            cls.sample59=json.loads(__import__('gzip').decompress(z.read(ROOT+'point-059-material.json.gz')))
            cls.sample60=json.loads(__import__('gzip').decompress(z.read(ROOT+'point-060-material.json.gz')))
    def test_point60_actual_source_feature_change(self):
        p=witness_59_60(self.sample59,self.sample60)
        self.assertEqual(p['changed_vertex_indices'],[8043,8044,8045,8046,8047])
        self.assertEqual(p['removed_feature_count'],2)
        self.assertEqual(p['added_feature_count'],2)
        self.assertEqual(p['removed_oriented_triangle_count'],17)
        self.assertEqual(p['added_oriented_triangle_count'],17)
        self.assertFalse(p['continuous_branch_certified'])
    def test_witness_rejects_forged_equal_features(self):
        with self.assertRaisesRegex(ValueError,'H8_POINT60_WITNESS_DRIFT'):
            witness_59_60(self.sample59,self.sample59)
    def test_classification_explicitly_excludes_point60(self):
        c=self.classifier
        self.assertEqual(c['classifications'],{STABLE:79,CHANGED:1})
        rows={e['index']:e['status'] for e in c['comparisons']}
        self.assertEqual(rows[60],CHANGED)
        self.assertEqual(rows[59],STABLE)
        self.assertFalse(c['certified_smooth_neighborhood'])
    def test_fd_30_report_not_derivative_proof(self):
        if not CANDIDATES or not Path(CANDIDATES).is_file():
            self.skipTest('precomputed candidate index not available')
        rows=json.loads(Path(CANDIDATES).read_text())['samples']
        fd=finite_difference(rows,self.report)
        self.assertEqual(fd['checked_stencils'],30)
        self.assertEqual(fd['raw_hash_unstable_stencils'],9)
        self.assertLess(fd['max_scaled_error'],1e-8)
        self.assertTrue(fd['numerical_only_not_smooth_certificate'])
    def test_fd_tamper_rejected(self):
        if not CANDIDATES or not Path(CANDIDATES).is_file():
            self.skipTest('precomputed candidate index not available')
        rows=json.loads(Path(CANDIDATES).read_text())['samples']
        forged=copy.deepcopy(rows)
        forged[1]['r_D'][4]+=1e-2
        with self.assertRaisesRegex(ValueError,'FD_REPORT_MISMATCH'):
            finite_difference(forged,self.report)
    def test_candidate_labels_have_no_derivatives(self):
        if not CANDIDATES or not Path(CANDIDATES).is_file():
            self.skipTest('precomputed candidate index not available')
        report=json.loads(Path(CANDIDATES).read_text())
        self.assertEqual(report['candidate_count'],81)
        self.assertEqual(report['formal_training_samples'],0)
        self.assertEqual(report['derivative_training_samples'],0)
        self.assertEqual(sum(p['J_D'] is not None for p in report['samples']),0)
        self.assertEqual(set(p['split'] for p in report['samples']),{'excluded'})
        self.assertEqual(report['samples'][60]['finite_feature_status'],CHANGED)
        self.assertEqual(report['samples'][0]['finite_feature_status'],'BASELINE_ONLY')
    def test_cross_coefficients_doubled_in_polynomial(self):
        if not CANDIDATES or not Path(CANDIDATES).is_file():
            self.skipTest('precomputed candidate index not available')
        report=json.loads(Path(CANDIDATES).read_text())
        for p in report['samples']:
            c,q=p['native_c'],p['polynomial_q']
            self.assertEqual(q[:7],c[:7]);self.assertEqual(q[7:],[2*x for x in c[7:]])
    def test_archive_workflow_failure_is_preserved(self):
        if not CANDIDATES or not Path(CANDIDATES).is_file():
            self.skipTest('precomputed candidate index not available')
        report=json.loads(Path(CANDIDATES).read_text())
        self.assertEqual(report['source']['upstream_workflow_conclusion'],'failure')
        self.assertFalse(report['formal_smooth_neighborhood_certified'])
        self.assertFalse(report['newton_converged'])

if __name__=='__main__':unittest.main()
