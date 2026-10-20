"""M12 real archived H8f ray tests; no native runs, no training promotion."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import w2_consumer_gate as gate
from w2_projective_ray_m12 import (
    M12Rejected, ray_certificate, review_m12, export_training,
    git_blob, w0_unsampled_unit_preview, UNIT_TOL,
)

ROOT=Path(__file__).parent
CAND=ROOT/'M9_H8F_81_EXCLUDED_CANDIDATES.json'
ARCHIVE=ROOT/'h8f_81_real.zip'
MANIFEST=ROOT/'teacher_manifest_semantic_fixture.json'


def fixture():
    """Reconstruct M9 semantic commitments; NOT an actual GitHub manifest clone."""
    return {
      'schema':'w2-cherchi-teacher-v2-pre-w0',
      'training_samples':0,'local_native_calls':0,'native_teacher_runs':0,
      'label_convention':{'w0_verifier_integrated':False},
      'data_splits':{'train':[], 'val':[], 'test':[], 'excluded':[
       {'count':81,'path':'research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json'}]},
      'm9_real_h8f_81_evidence':{
       'schema':gate.CANDIDATE_SCHEMA,'workflow_run_id':gate.RUN_ID,
       'original_workflow_conclusion':'failure','original_head_sha':gate.SOURCE_SHA,
       'archive_artifact_id':gate.ARTIFACT_ID,'archive_sha256':gate.ARCHIVE_SHA256,
       'archive_report_sha256':gate.REPORT_SHA256,
       'archive_classification_sha256':gate.CLASS_SHA256,
       'frozen_request_sha256':gate.REQUEST_SHA256,
       'candidate_index_sha256':gate.CANDIDATE_SHA256,
       'candidate_index_git_blob_sha1':gate.CANDIDATE_BLOB_SHA1,
       'W0_M9_report_blob_sha1':gate.W0_M9_REPORT_BLOB_SHA1,
       'w0_handoff_document_blob_sha1':gate.W0_HANDOFF_BLOB_SHA1,
       'original_native_evaluations':81, 'new_native_evaluations':0,
       'independently_reintegrated_materials':81,
       'independently_reintegrated_ten_moment_components':810,
       'training_admitted':0,'newton_solved':False,
       'certified_continuous_neighborhood':False,
       'derivative_J_D_published':False,
       'finite_symbolic_classifications':{'STABLE_NOT_CERTIFIED':79,'FEATURE_CHANGE':1},
       'point60':{'changed_vertex_positions':[8043,8044,8045,8046,8047],
          'removed_LPI_features':2,'added_LPI_features':2,
          'removed_oriented_triangles':17,'added_oriented_triangles':17,
          'c7_from':1.5e-6,'c7_to':3e-6},
       'candidate_index_path':'research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json'
      }
    }


class TestRayPure(unittest.TestCase):
    def test_exact_positive_scale_preserves_ray_but_not_raw_sha(self):
        c=[1.0,0,0,0,0,0,0,0.5,0.25,0]
        a=ray_certificate(c)
        b=ray_certificate([2*x for x in c])
        self.assertEqual(a['exact_positive_ray_sha256'],b['exact_positive_ray_sha256'])
        self.assertNotEqual(a['archived_native_c_sha256'],b['archived_native_c_sha256'])
    def test_negative_sign_changes_retained_ray(self):
        a=ray_certificate([0.,-1.,0.,0.,0.,0.,0.,0.5,0.,0.])
        b=ray_certificate([0.,1.,0.,0.,0.,0.,0.,-0.5,0.,0.])
        self.assertNotEqual(a['exact_positive_ray_sha256'],b['exact_positive_ray_sha256'])
    def test_exact_sign_pivot_not_lost(self):
        x=ray_certificate([-2.0,0,0,0,0,0,0,0,0,0])
        self.assertEqual(x['exact_positive_ray_ratio_tokens'][0],'-1/1')
        self.assertEqual(x['positive_max_abs_scale_binary64_hex'],(2.).hex())
    def test_invalid_zero_nan_inf_boolean(self):
        for c in ([0.]*10,[float('nan')]+[0.]*9,[float('inf')]+[0.]*9,
                  [True]+[0.]*9,[1.]*9):
            with self.assertRaises((ValueError,M12Rejected,gate.GateRejected)):
                ray_certificate(c)
    def test_projected_display_does_not_modify_native_identity(self):
        c=[1.000001,0,0,0,0,0,0,1e-7,0,0]
        before=c[:]
        r=ray_certificate(c)
        self.assertEqual(c,before)
        self.assertFalse(r['w0_native_unit_rule_already_satisfied'])
        self.assertNotEqual(r['archived_native_c'],r['w0_unit_display_only_c'])
        self.assertLessEqual(r['w0_unit_display_norm_deviation'],UNIT_TOL)
        self.assertIsNone(r['derivative_J_D'])
        self.assertFalse(r['training_admitted'])
    def test_cross_mapping_double_only_last_three(self):
        c=[1.,0,0,0,0,0,0,0.1,0.2,0.3]
        self.assertEqual(ray_certificate(c)['monomial_q_from_archived_native_c'][7:],[0.2,0.4,0.6])
    def test_ray_certificate_cannot_release_training(self):
        with self.assertRaisesRegex(M12Rejected,'CANNOT_RELEASE_TRAINING'):
            export_training('approve')


class TestRealM12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(CAND.read_bytes()).hexdigest()==gate.CANDIDATE_SHA256
        assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==gate.ARCHIVE_SHA256
        MANIFEST.write_text(json.dumps(fixture(),sort_keys=True))
        cls.candidate=json.loads(CAND.read_text())
        cls.full=review_m12(CAND,MANIFEST,archive_path=ARCHIVE,index=60)
        cls.index_only=review_m12(CAND,MANIFEST,archive_path=None,index=0)

    def test_all_archived_materials_rebound(self):
        self.assertEqual(self.full['m10_rebind_status'],
            'ARCHIVED_81_MATERIALS_REBOUND_DERIVATIVES_BLOCKED')
        self.assertEqual(self.full['source']['original_workflow_conclusion'],'failure')
    def test_inventory_81_17_64(self):
        self.assertEqual(self.full['total_archived_points'],81)
        self.assertEqual(self.full['original_norm_unit_compatible_count'],17)
        self.assertEqual(self.full['original_norm_nonunit_count'],64)
        self.assertEqual(self.full['distinct_exact_positive_rays'],81)
    def test_projective_ray_exact_rational_reconstruction(self):
        for row in self.full['certificates']:
            native=row['archived_native_c']
            pivot=row['positive_max_abs_pivot']
            denom=Fraction.from_float(abs(native[pivot]))
            expected=[Fraction.from_float(x)/denom for x in native]
            actual=[Fraction(t) for t in row['exact_positive_ray_ratio_tokens']]
            self.assertEqual(expected,actual)
    def test_no_training_jacobian_or_native_projected_evaluations(self):
        self.assertEqual(self.full['projected_native_evaluations_performed'],0)
        self.assertEqual(self.full['training_samples_admitted'],0)
        self.assertIsNone(self.full['all_derivative_J_D'])
        self.assertTrue(all(x['training_admitted'] is False and x['derivative_J_D'] is None
                            for x in self.full['certificates']))
    def test_raw_coefficients_unmodified(self):
        for a,b in zip(self.candidate['samples'],self.full['certificates']):
            self.assertEqual(a['native_c'],b['archived_native_c'])
            self.assertEqual(a['same_call_material_gzip_sha256'],b['archived_material_gzip_sha256'])
    def test_point60_true_change_and_positive_sign(self):
        p=self.full['certificates'][60]
        self.assertEqual(p['archived_native_c'][7],3e-6)
        self.assertEqual(p['monomial_q_from_archived_native_c'][7],6e-6)
        self.assertEqual(p['finite_feature_status'],gate.CHANGED)
        self.assertFalse(p['w0_native_unit_rule_already_satisfied'])
        self.assertTrue(self.full['point60_observed_constructor_change_preserved'])
    def test_w0_unsampled_preview_not_run(self):
        w=self.full['focus_w0_unsampled_unit_display_preview']
        self.assertEqual(w['schema'],'MomentContractV1')
        self.assertEqual(w['moments']['status'],'NOT_RUN')
        self.assertIsNone(w['moments']['variable_r'])
        self.assertIsNone(w['jacobian']['values'])
        self.assertFalse(w['jacobian']['derivative_defined'])
        self.assertFalse(self.full['focus_w0_preview_is_native_result'])
        self.assertLessEqual(abs(float(np.linalg.norm(w['coefficients']['c']))-1),UNIT_TOL)
    def test_frame_and_original_F_D_binding(self):
        g=self.full['focus_w0_unsampled_unit_display_preview']['geometry']
        self.assertEqual(g['original_sha256'],
            'fbada64691e30b458bc5b5375f8d4ad351cb0b383d800512bb659077b29532f6')
        self.assertEqual(g['fixed_F_sha256'],
            '45c83ffd19c94b6c75ea63e7e7261fda645cd00ec0920c1a6ecc68e703c3a5b0')
    def test_index_only_does_not_claim_real_packet(self):
        self.assertEqual(self.index_only['m10_rebind_status'],
            'PINNED_M9_INDEX_ONLY_DERIVATIVES_BLOCKED')
        self.assertIsNone(self.index_only['focus_w0_unsampled_unit_display_preview'])
    def test_malformed_manifest_rejected_before_ray_claim(self):
        bad=fixture();bad['training_samples']=1
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json';p.write_text(json.dumps(bad))
            with self.assertRaisesRegex(gate.GateRejected,'MANIFEST_FORGED_NATIVE'):
                review_m12(CAND,p)
    def test_fake_w3_stage11_sha_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w3.json';p.write_text('{}')
            with self.assertRaisesRegex(M12Rejected,'W3_STAGE11_GIT_BLOB_DRIFT'):
                review_m12(CAND,MANIFEST,w3_stage11_path=p)
    def test_fake_w0_schema_sha_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'w0.json';p.write_text('{}')
            with self.assertRaisesRegex(M12Rejected,'W0_SCHEMA_GIT_BLOB_DRIFT'):
                review_m12(CAND,MANIFEST,w0_schema_path=p)
    def test_reject_unpinned_candidate_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'c.json'
            changed=copy.deepcopy(self.candidate)
            changed['samples'][60]['native_c'][7]=2.5e-6
            p.write_text(json.dumps(changed))
            with self.assertRaisesRegex(gate.GateRejected,'UNTRUSTED_CANDIDATE_BYTES_SHA256'):
                review_m12(p,MANIFEST)
    def test_negative_projective_ray_never_same_as_positive(self):
        c=self.candidate['samples'][60]['native_c']
        self.assertNotEqual(ray_certificate(c)['exact_positive_ray_sha256'],
                            ray_certificate([-x for x in c])['exact_positive_ray_sha256'])


if __name__=='__main__':unittest.main()
