"""W2 M15: frozen Heart asset validation, Noodles gaps, no mock native."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from m15_dual_teacher_campaign import (
    HEART_ZIP_SHA256, HEART_PARTITION_PREDECLARED_TOLERANCE,
    NOODLES_FINAL_OBJ_SHA256, NOODLES_MOMENT_PREDECLARED_TOLERANCE,
    parse_obj_bytes, integrate_raw_ten, file_sha256, verify_frozen_heart,
    describe_noodles, run_campaign, create_normalized_obj, require_native_resources,
)
HEART=os.environ.get('W2_H8F_ARCHIVE')

class TestM15Analytic(unittest.TestCase):
    def test_reference_box_ten_raw_moments(self):
        v=np.asarray([[0,0,0],[2,0,0],[2,3,0],[0,3,0],
                      [0,0,4],[2,0,4],[2,3,4],[0,3,4]],float)
        f=np.asarray([[0,2,1],[0,3,2],[4,5,6],[4,6,7],
                      [0,1,5],[0,5,4],[3,7,6],[3,6,2],
                      [0,4,7],[0,7,3],[1,2,6],[1,6,5]])
        np.testing.assert_allclose(integrate_raw_ten(v,f),
           [24,24,36,48,32,72,128,72,48,36],rtol=0,atol=1e-13)
    def test_reverse_surface_changes_signed_mass(self):
        v=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]]
        f=np.asarray([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        self.assertAlmostEqual(integrate_raw_ten(v,f)[0],1/6)
        self.assertAlmostEqual(integrate_raw_ten(v,f[:,::-1])[0],-1/6)
    def test_no_nontriangle_fallback(self):
        with self.assertRaisesRegex(ValueError,'OBJ_NONTRIANGLE'):
            parse_obj_bytes(b'v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3 4\n')
    def test_reject_nonfinite_vertex(self):
        with self.assertRaisesRegex(ValueError,'OBJ_NONFINITE'):
            parse_obj_bytes(b'v nan 0 0\n')
    def test_two_predeclared_budgets(self):
        self.assertEqual(HEART_PARTITION_PREDECLARED_TOLERANCE,1e-9)
        self.assertEqual(NOODLES_MOMENT_PREDECLARED_TOLERANCE,1e-10)

class TestM15NoodlesHonesty(unittest.TestCase):
    def test_final_obj_not_frozen_teacher_input(self):
        x=describe_noodles()
        self.assertEqual(x['source']['final_obj_sha256'],NOODLES_FINAL_OBJ_SHA256)
        self.assertEqual(x['status'],'BLOCKED_FROZEN_NOODLES_NATIVE_F_D_INPUT_ABSENT')
        self.assertFalse(x['native_teacher_preflight_passed'])
    def test_historical_request_digest_not_full_request(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'old.json';p.write_text('{"request_digest":"x","settings":{}}')
            with self.assertRaisesRegex(ValueError,'NOODLES_NOT_A_FULL_FROZEN_REQUEST'):
                describe_noodles(frozen_request_path=p)
    def test_unverified_full_request_still_not_native(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'untrusted.json'
            p.write_text(json.dumps({'request':{'outer_vertices':[],
                'outer_faces':[],'design_vertices':[],'design_faces':[],
                'fixed_shell_moments':[]}}))
            result=describe_noodles(frozen_request_path=p)
            self.assertFalse(result['native_teacher_preflight_passed'])
            self.assertIn('NOT_INDEPENDENTLY_CERTIFIED',result['status'])
    def test_unpinned_model_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake.obj';p.write_text('v 0 0 0')
            with self.assertRaisesRegex(ValueError,'UNRECOGNIZED_NOODLES_V7_FINAL_OBJ_SHA'):
                describe_noodles(final_obj_path=p)

class TestM15RealHeart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HEART or not Path(HEART).is_file():
            raise unittest.SkipTest('W2_H8F_ARCHIVE genuine 81-point ZIP required')
        cls.verified=verify_frozen_heart(HEART)
    def test_real_archive_source_sha(self):
        self.assertEqual(file_sha256(HEART),HEART_ZIP_SHA256)
    def test_real_raw_native_source_counts(self):
        x=self.verified
        self.assertEqual((x['outer_vertices'],x['outer_faces']),(15646,31288))
        self.assertEqual((x['design_vertices'],x['design_faces']),(13122,26244))
        self.assertEqual((x['fixed_vertices'],x['fixed_faces']),(28768,57532))
    def test_source_mm_vs_request_m_distinguished(self):
        self.assertEqual(self.verified['physical_obj_mm_per_normalized_unit'],25.0)
        self.assertEqual(self.verified['request_m_per_normalized_unit'],0.025)
        self.assertTrue(self.verified['independent_archived_input_audit_passed'])
    def test_real_F_D_partition(self):
        self.assertLess(self.verified['fixed_r_vs_registered_max_abs_error'],1e-10)
        self.assertLess(self.verified['F_plus_D_vs_outer_max_abs_error'],1e-10)
    def test_actual_archived_native_c(self):
        self.assertEqual(len(self.verified['frozen_initial_native_c']),10)
        self.assertEqual(self.verified['frozen_initial_native_c'][0],0.3701323978732728)
    def test_reject_forged_archive(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.zip';p.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'NOT_H8F_FROZEN_ARCHIVE'):
                verify_frozen_heart(p)
    def test_normalized_view_binary64_order(self):
        with tempfile.TemporaryDirectory() as d:
            req=self.verified['_prepared_request']['request']
            proven=create_normalized_obj(req,Path(d)/'heart-normalized.obj',
                 self.verified['source']['mesh_file_sha256']['initial_top.obj'])
            v,f=parse_obj_bytes(Path(proven['path']).read_bytes())
            self.assertEqual(v.tobytes(),np.asarray(req['outer_vertices'],dtype='<f8').tobytes())
            self.assertEqual(f.tobytes(),np.asarray(req['outer_faces'],dtype='<i4').tobytes())
            self.assertNotEqual(proven['sha256'],proven['original_source_sha256'])
    def test_real_attempt_without_compiled_binary_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            result=run_campaign(HEART,d,execute_native=True)
            self.assertEqual(result['heart']['status'],'BLOCKED_COMPILED_NATIVE_MODULE_FILE_ABSENT')
            self.assertEqual(result['new_native_calls_verified'],0)
            self.assertFalse(result['noodles']['native_teacher_preflight_passed'])
            self.assertEqual(result['training_admitted'],0)
            self.assertTrue((Path(d)/'M15_CAMPAIGN_RESULT.json').is_file())
            with self.assertRaisesRegex(ValueError,'REFUSE_OVERWRITE_CAMPAIGN_RESULT'):
                run_campaign(HEART,d,execute_native=True)
    def test_insufficient_memory_blocks_even_fake_binary(self):
        with tempfile.TemporaryDirectory() as d:
            fake=Path(d)/'fake.so';fake.write_bytes(b'not a native module')
            with patch('m15_dual_teacher_campaign.read_cgroup_memory',return_value=4*1024**3):
                result=run_campaign(HEART,Path(d)/'report',native_module=fake,execute_native=True)
            self.assertEqual(result['heart']['status'],'BLOCKED_NATIVE_RESOURCE_OR_IDENTITY_PREFLIGHT')
            self.assertIn('24GIB',result['heart']['native_preflight_reason'])
            self.assertEqual(result['new_native_calls_verified'],0)
    def test_resource_limit_alone(self):
        with patch('m15_dual_teacher_campaign.read_cgroup_memory',return_value=4*1024**3):
            with self.assertRaisesRegex(ValueError,'AT_LEAST_24GIB'):
                require_native_resources()

class TestM15OptionalNativeFinalOBJ(unittest.TestCase):
    def test_verified_main_noodles_export_when_supplied(self):
        path=os.environ.get('W2_NOODLES_FINAL_OBJ')
        if not path or not Path(path).is_file():
            self.skipTest('Noodles V7 final 4.23MB source OBJ not mounted; its GitHub blob is separately audited')
        result=describe_noodles(final_obj_path=path)
        self.assertEqual(result['terminal_obj_audit']['vertex_count'],42932)
        self.assertLess(result['terminal_obj_audit']['ten_raw_moments_max_abs_error'],1e-10)
        self.assertFalse(result['native_teacher_preflight_passed'])

if __name__=='__main__':
    unittest.main()
