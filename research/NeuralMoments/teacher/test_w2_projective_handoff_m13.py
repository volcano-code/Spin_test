"""W2 M13: exact projective W0 handoff, historical source strictly excluded."""
from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import w2_consumer_gate as gate
import w2_projective_ray_m12 as m12
from w2_projective_handoff_m13 import (
    M13Rejected, exact_native_polynomial, primitive_positive_ray,
    read_rational, review_m13, export_training, main,
)
from test_w2_projective_ray_m12 import fixture

ROOT=Path(__file__).resolve().parent
CAND=ROOT/'M9_H8F_81_EXCLUDED_CANDIDATES.json'
ARCHIVE=Path(os.environ.get('W2_H8F_ARCHIVE',str(ROOT/'h8f_81_real.zip')))
MANIFEST=ROOT/'teacher_manifest.json'


class TestPrimitivePositiveRay(unittest.TestCase):
    def test_exact_positive_scale_stable_integer_ray(self):
        c=[1.0,0.,0.,0.,0.,0.,0.,0.5,0.25,-0.125]
        a=primitive_positive_ray(c)
        b=primitive_positive_ray([2*x for x in c])
        self.assertEqual(a['positive_primitive_ray_sha256'],
                         b['positive_primitive_ray_sha256'])
        self.assertNotEqual(a['raw_native_c_sha256'],b['raw_native_c_sha256'])
        self.assertEqual(a['positive_primitive_ray_identity']['primitive_signed_integer_c'],
                         ['8','0','0','0','0','0','0','4','2','-1'])
        self.assertEqual(a['exact_positive_scale'],'1/8')
        self.assertEqual(b['exact_positive_scale'],'1/4')

    def test_negative_projective_reversal_is_not_equivalent(self):
        c=[-1.,0.,0.,0.,0.,0.,0.,1.,0.,0.]
        a=primitive_positive_ray(c)
        b=primitive_positive_ray([-x for x in c])
        self.assertNotEqual(a['positive_primitive_ray_sha256'],
                            b['positive_primitive_ray_sha256'])

    def test_nonlinear_float_scale_not_silently_equated(self):
        c=[0.1,0.,0.,0.,0.,0.,0.,0.3,0.,0.]
        b=[3*x for x in c]
        a=primitive_positive_ray(c)
        scaled=primitive_positive_ray(b)
        # Python float multiplication may alter the exact binary64 ray.
        if a['positive_primitive_ray_sha256'] != scaled['positive_primitive_ray_sha256']:
            self.assertNotEqual(a['m12_ray_sha256'],scaled['m12_ray_sha256'])
        else:
            self.assertEqual(a['m12_ray_sha256'],scaled['m12_ray_sha256'])

    def test_exact_coefficient_w0_cross_factors(self):
        c=[1.,0.,0.,0.,0.,0.,0.,0.125,-0.25,0.375]
        cert=primitive_positive_ray(c)
        q=[read_rational(x) for x in cert['exact_monomial_q_tokens']]
        self.assertEqual(q[7:],[Fraction(1,4),Fraction(-1,2),Fraction(3,4)])
        self.assertEqual(q[4:7],[Fraction(0)]*3)

    def test_rational_evaluation_matches_full_native_matrix_form(self):
        c=[2.,3.,5.,7.,11.,13.,17.,19.,23.,29.]
        xyz=(Fraction(1,2),Fraction(-2,3),Fraction(3,4))
        x,y,z=xyz
        direct=Fraction(2)+3*x+5*y+7*z+11*x*x+13*y*y+17*z*z+38*y*z+46*x*z+58*x*y
        from_evaluator=exact_native_polynomial(tuple(Fraction(t) for t in c),xyz)
        self.assertEqual(direct,from_evaluator)
        cert=primitive_positive_ray(c)
        self.assertEqual(len(cert['exact_positive_scale_probes']),7)
        self.assertTrue(all(p['exact_factor_relation'] and p['sign_consistent']
                            for p in cert['exact_positive_scale_probes']))

    def test_invalid_exact_rational_token(self):
        for t in ('1/-2','1/0','NaN/1','1','2.3/1','0b11/2'):
            with self.assertRaises(M13Rejected):read_rational(t)

    def test_nonprimitive_signed_vector_rejects_false_equivalence(self):
        c=[-2.,0.,0.,0.,0.,0.,0.,-4.,0.,0.]
        certificate=primitive_positive_ray(c)
        self.assertEqual(certificate['positive_primitive_ray_identity']['primitive_signed_integer_c'][0],'-1')
        self.assertEqual(certificate['positive_primitive_ray_identity']['primitive_signed_integer_c'][7],'-2')
        self.assertEqual(certificate['exact_positive_scale'],'2/1')

    def test_zero_nan_bool_infinity_and_wrong_size_rejected(self):
        invalid=([0.]*10,[float('nan')]+[0.]*9,[float('inf')]+[0.]*9,
                 [True]+[0.]*9,[1.]*9)
        for c in invalid:
            with self.subTest(c=str(c)), self.assertRaises((ValueError,gate.GateRejected)):
                primitive_positive_ray(c)

    def test_train_release_is_unconditionally_denied(self):
        with self.assertRaisesRegex(M13Rejected,'NEVER_AUTHORIZES'):
            export_training('signed W0 approval',signed=True)

    def test_plain_algebra_never_certifies_native_or_derivative(self):
        r=primitive_positive_ray([1.,0,0,0,0,0,0,0,0,0])
        self.assertFalse(r['native_boolean_material_proof_from_this_certificate'])
        self.assertIsNone(r['derivative_J_D'])
        self.assertFalse(r['training_admitted'])
        self.assertFalse(r['certified_continuous_neighborhood'])


class TestM13RealArchivedH8f(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file():
            raise unittest.SkipTest('Real 81-point ZIP required (W2_H8F_ARCHIVE)')
        cls.temp=TemporaryDirectory()
        cls.manifest=MANIFEST
        cls.manifest_is_actual=MANIFEST.is_file()
        if not cls.manifest_is_actual:
            cls.manifest=Path(cls.temp.name)/'m9_semantic_fixture.json'
            cls.manifest.write_text(json.dumps(fixture(),sort_keys=True))
        assert hashlib.sha256(CAND.read_bytes()).hexdigest()==gate.CANDIDATE_SHA256
        assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==gate.ARCHIVE_SHA256
        cls.candidates=json.loads(CAND.read_text())
        cached=os.environ.get('W2_M13_REVIEW_RESULT')
        if cached and Path(cached).is_file():
            cls.report=json.loads(Path(cached).read_text())
            assert cls.report['schema']=='w2-m13-projective-ray-handoff-v1'
            assert cls.report['archived_real_cherchi_materials_rebound_this_run']==1
            assert cls.report['source']['candidate_file_sha256']==gate.CANDIDATE_SHA256
            assert cls.report['source']['original_artifact_zip_sha256']==gate.ARCHIVE_SHA256
        else:
            cls.report=review_m13(CAND,cls.manifest,ARCHIVE,index=60)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_real_81_materials_rebound(self):
        self.assertEqual(self.report['archived_real_cherchi_materials_rebound_this_run'],1)
        self.assertTrue(self.report['selected_same_call_material_sha_verified'])
        self.assertEqual(self.report['historical_workflow_conclusion'],'failure')

    def test_all_samples_unique_positive_projective_rays(self):
        self.assertEqual(self.report['signed_rays_compared'],81)
        self.assertEqual(self.report['distinct_positive_primitive_rays'],81)
        self.assertEqual(len(self.report['records']),81)

    def test_actual_c_decompositions_all_exact(self):
        for raw,record in zip(self.candidates['samples'],self.report['records']):
            self.assertEqual(record['index'],raw['index'])
            integers=[int(x) for x in record['positive_primitive_ray_identity']['primitive_signed_integer_c']]
            scale=read_rational(record['exact_positive_scale'])
            self.assertGreater(scale,0)
            self.assertEqual([Fraction.from_float(c) for c in raw['native_c']],
                             [scale*x for x in integers])
            self.assertEqual(raw['same_call_material_gzip_sha256'],
                             record['same_call_material_gzip_sha256'])

    def test_actual_17_64_partition_with_no_normalization_promotion(self):
        self.assertEqual(self.report['w0_unit_c_input_compatible'],17)
        self.assertEqual(self.report['nonunit_native_c_input_cases'],64)
        self.assertTrue(self.report['raw_native_c_unmodified'])
        self.assertFalse(self.report['w0_projective_protocol_officially_adopted'])

    def test_h8_point60_original_witness_preserved(self):
        row=self.report['records'][60]
        self.assertEqual(row['original_constructive_status'],gate.CHANGED)
        self.assertFalse(row['raw_archived_c_unit_compatible'])
        self.assertEqual(self.report['focus_original'][7],3e-6)
        self.assertTrue(self.report['point60_constructive_feature_change'])

    def test_w0_preview_is_not_run_and_never_stores_moments(self):
        p=self.report['focus_w0_structural_preview_only_not_run']
        self.assertEqual(p['schema'],'MomentContractV1')
        self.assertEqual(p['moments']['status'],'NOT_RUN')
        self.assertIsNone(p['moments']['variable_r'])
        self.assertIsNone(p['moments']['total_r'])
        self.assertIsNone(p['jacobian']['values'])
        self.assertFalse(self.report['focus_preview_is_original_native_sample'])

    def test_all_finite_probes_exact_signed_relation(self):
        for record in self.report['records']:
            self.assertEqual(len(record['exact_positive_scale_probes']),7)
            self.assertTrue(all(t['sign_consistent'] and t['exact_factor_relation']
                                for t in record['exact_positive_scale_probes']))

    def test_no_false_training_or_newton(self):
        self.assertEqual(self.report['new_native_calls'],0)
        self.assertEqual(self.report['training_admitted_count'],0)
        self.assertIsNone(self.report['all_derivative_J_D'])
        self.assertFalse(self.report['native_newton_accepted'])
        self.assertFalse(self.report['independent_native_continuity_proved'])

    def test_unverified_w0_w3_metadata_never_admits(self):
        self.assertFalse(self.report['w0_structural_schema_observation']['observed'])
        self.assertFalse(self.report['w3_stage11_observation']['observed'])
        self.assertFalse(self.report['w0_projective_protocol_officially_adopted'])

    def test_no_zip_means_not_real_evidence(self):
        with self.assertRaisesRegex(M13Rejected,'H8F_REAL_ARCHIVE_REQUIRED'):
            review_m13(CAND,self.manifest,None)

    def test_manifest_admission_mutation_rejected(self):
        forged=fixture();forged['training_samples']=1
        p=Path(self.temp.name)/'forged_manifest.json'
        p.write_text(json.dumps(forged))
        with self.assertRaisesRegex(gate.GateRejected,'MANIFEST_FORGED_NATIVE'):
            review_m13(CAND,p,ARCHIVE)

    def test_false_w0_or_w3_proof_rejected(self):
        for label in ('w0_schema_path','w3_stage11_path'):
            p=Path(self.temp.name)/('fake_'+label+'.json')
            p.write_text('{}')
            expected=m12.W0_SCHEMA_BLOB if label=='w0_schema_path' else m12.W3_STAGE11_BLOB
            with self.subTest(label=label), self.assertRaises((M13Rejected,m12.M12Rejected)):
                m12._optional_pinned_json(p,expected,label)

    def test_raw_81_candidate_sha_tampering_rejected(self):
        p=Path(self.temp.name)/'tampered.json'
        changed=copy.deepcopy(self.candidates)
        changed['samples'][60]['native_c'][7]=2.9e-6
        p.write_text(json.dumps(changed))
        with self.assertRaisesRegex(gate.GateRejected,'UNTRUSTED_CANDIDATE_BYTES_SHA256'):
            review_m13(p,self.manifest,ARCHIVE)

    def test_no_false_certificate_from_modified_m12_result(self):
        legitimate=m12.review_m12(CAND,self.manifest,archive_path=None,index=60)
        fake=dict(legitimate)
        fake['m10_rebind_status']='ARCHIVED_81_MATERIALS_REBOUND_DERIVATIVES_BLOCKED'
        with patch.object(m12,'review_m12',return_value=fake):
            with self.assertRaises((M13Rejected,KeyError,IndexError)):
                review_m13(CAND,self.manifest,ARCHIVE)

    def test_cli_exclusive_output_and_rejected_training_status(self):
        # Reuse fake for a quick negative CLI path, no repeated original archive pass.
        p=Path(self.temp.name)/'cli_failure.json'
        code=main(['--candidate',str(CAND),'--manifest',str(self.manifest),
                   '--archive',str(self.temp.name+'/missing.zip'),
                   '--output',str(p)])
        self.assertEqual(code,2)
        d=json.loads(p.read_text())
        self.assertEqual(d['status'],'REJECTED')
        self.assertEqual(d['training_admitted_count'],0)
        with self.assertRaisesRegex(gate.GateRejected,'REFUSE_OVERWRITE_SCIENTIFIC_EVIDENCE'):
            main(['--candidate',str(CAND),'--manifest',str(self.manifest),
                  '--archive',str(ARCHIVE),'--output',str(p)])


if __name__=='__main__':unittest.main()
