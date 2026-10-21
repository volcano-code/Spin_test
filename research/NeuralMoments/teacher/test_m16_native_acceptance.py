"""W2 M16 tests: genuine frozen H8f ZIP, zero invented Cherchi calls.

Tests produce only new temporary outputs; no source or CI status mutations.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from m16_native_acceptance import (
  SOURCE_SHA,HEART_ARTIFACT_SHA,REQUEST_SHA,HEART_SOURCE_SHA,NATIVE_CAP_BYTES,
  canonical,blob_hash,strict_json,strict_mesh,signed_ten,oriented_edges,
  prepare_frozen_heart,runtime_limits,verify_source_checkout,
  validate_module_manifest,audit_imports,run,require,
)

REAL=Path(os.environ.get('W2_H8F_ARCHIVE','/mnt/data/h8f_81_real.zip'))

class TestAnalyticPreflight(unittest.TestCase):
    def test_signed_tetra(self):
        v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype='<f8')
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype='<i4')
        result=signed_ten(v,f)
        np.testing.assert_allclose(result,[1/6,1/24,1/24,1/24,1/60,1/60,1/60,1/120,1/120,1/120],atol=1e-16,rtol=0)
        self.assertEqual(oriented_edges(f),6)
    def test_nonclosed_rejected(self):
        faces=np.array([[0,2,1],[0,1,3],[0,3,2]],dtype='<i4')
        with self.assertRaisesRegex(ValueError,'NOT_CLOSED_ORIENTED'):oriented_edges(faces)
    def test_negative_volume_on_reversed_faces(self):
        v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype='<f8')
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype='<i4')
        self.assertAlmostEqual(signed_ten(v,f[:,::-1])[0],-1/6)
    def test_nan_vertex_rejected(self):
        with self.assertRaisesRegex(ValueError,'OBJ_NONFINITE'):strict_mesh(b'v nan 0 0\n')
    def test_quad_rejected(self):
        with self.assertRaisesRegex(ValueError,'OBJ_UNTRIANGULATED'):strict_mesh(b'v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3 4\n')
    def test_relative_face_rejected(self):
        with self.assertRaisesRegex(ValueError,'OBJ_UNTRIANGULATED'):strict_mesh(b'v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf -3 -2 -1\n')
    def test_json_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError,'JSON_DUPLICATE_KEY'):strict_json(b'{"x":1,"x":2}')
    def test_json_nan(self):
        with self.assertRaisesRegex(ValueError,'NONFINITE_JSON'):strict_json(b'{"x":NaN}')
    def test_repo_blob_sha(self):
        self.assertEqual(blob_hash(b'hi'),'32f95c0d1244a78b2be1bab8de17906fabb2c4a8')
    def test_real_memory_resource_gate(self):
        x=runtime_limits()
        self.assertGreaterEqual(x['host_available_bytes'],0)
        self.assertFalse(x['qualified_for_native_24gib_job']) if x['cgroup_memory_limit_bytes']==4294967296 else None
    def test_no_fake_binary_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'manifest.json';p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'NATIVE_MODULE_MANIFEST_REQUIRED'):validate_module_manifest(p)
    def test_fake_three_module_manifest_strict_elf(self):
        with tempfile.TemporaryDirectory() as d:
            from m16_native_acceptance import MODULES
            src=Path(d)/'text.so';src.write_bytes(b'not ELF')
            m={'schema':'w2-m16-externally-frozen-ELF-extensions-v1','extensions':{
                 k:{'path':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()} for k in MODULES}}
            p=Path(d)/'manifest.json';p.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'NOT_A_NATIVE_ELF_BINARY'):validate_module_manifest(p)
    def test_elf_with_wrong_sha_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            from m16_native_acceptance import MODULES
            src=Path(d)/'candidate.so';src.write_bytes(b'\x7fELFfake binary')
            m={'schema':'w2-m16-externally-frozen-ELF-extensions-v1','extensions':{
                 k:{'path':str(src),'sha256':'0'*64} for k in MODULES}}
            p=Path(d)/'manifest.json';p.write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'NATIVE_BINARY_SHA_MISMATCH'):validate_module_manifest(p)
    def test_wrong_branch_or_missing_repo(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'COMPLETE_GIT_W2_CHECKOUT_REQUIRED'):verify_source_checkout(d)
    def test_native_budget_is_not_input_budget(self):
        with tempfile.TemporaryDirectory() as d:
            obj=Path(d)/'metadata.json';obj.write_text('{}')
            # Resource admission must not magically accept an absent source identity.
            with self.assertRaisesRegex(ValueError,'COMPLETE_GIT_W2_CHECKOUT_REQUIRED'):verify_source_checkout(d)

@unittest.skipUnless(REAL.exists(),'Set W2_H8F_ARCHIVE to original 81-point GitHub ZIP')
class TestRealHistoricalFrozenHeart(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.path=Path(cls.tmp.name)/'frozen'
        cls.value=prepare_frozen_heart(REAL,cls.path)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_zip_sha(self):self.assertEqual(self.value['archive_sha256'],HEART_ARTIFACT_SHA)
    def test_request_sha(self):self.assertEqual(self.value['request_sha256'],REQUEST_SHA)
    def test_all_three_real_sources(self):
        self.assertEqual({k:v['source_sha256'] for k,v in self.value['source_meshes'].items()},HEART_SOURCE_SHA)
    def test_actual_heart_faces(self):self.assertEqual(self.value['source_meshes']['initial_top.obj']['faces'],31288)
    def test_actual_design_faces(self):self.assertEqual(self.value['source_meshes']['design_domain.obj']['faces'],26244)
    def test_actual_fixed_faces(self):self.assertEqual(self.value['source_meshes']['fixed_shell.obj']['faces'],57532)
    def test_geometric_partition(self):self.assertLess(self.value['outer_F_D_error_max_abs'],1e-12)
    def test_fixed_reference(self):self.assertLess(self.value['fixed_r_source_error_max_abs'],1e-12)
    def test_actual_native_c_sha(self):
        self.assertEqual(self.value['native_c_sha256'],'8be318f8e19909a2c63ba5287d712665b9723b1b7a9cca42dc4ba23c16819a47')
    def test_true_binary64_view(self):
        a,b=strict_mesh((self.path/'frozen_normalized_outer.obj').read_bytes())
        self.assertEqual(a.tobytes(),np.asarray(self.value['frozen_request']['outer_vertices'],dtype='<f8').tobytes())
        self.assertEqual(b.tobytes(),np.asarray(self.value['frozen_request']['outer_faces'],dtype='<i4').tobytes())
    def test_input_partition_is_not_boolean_cert(self):
        self.assertTrue(self.value['input_budget_does_not_validate_Cherchi_boolean'])
        self.assertFalse(self.value['derivative_training_admitted'])
    def test_prevent_overwrite(self):
        with self.assertRaisesRegex(ValueError,'REFUSE_EXISTING_OUTPUT_DIRECTORY'):
            prepare_frozen_heart(REAL,self.path)
    def test_actual_no_native_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            report=run(REAL,Path(d)/'run',execute=True)
            self.assertEqual(report['status'],'BLOCKED_BEFORE_NATIVE_CALL')
            self.assertEqual(report['new_native_teacher_verified'],0)
            self.assertEqual(report['J_D_training_admitted'],0)
            self.assertIn('THREE_COMPILED_NATIVE_BINARIES_NOT_PINNED',report['preflight']['blockers'])
            self.assertTrue((Path(d)/'run'/'M16_EXECUTION_RESULT.json').is_file())
            self.assertFalse((Path(d)/'run'/'M16_NEW_CHERCHI_TEACHER.json').exists())
    def test_wont_treat_h8f_old_failure_as_pass(self):
        self.assertEqual(self.value['original_workflow_conclusion'],'failure')
        self.assertEqual(self.value['new_native_calls'],0)
    def test_invalid_external_ten_budgets(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'INVALID_CHERCHI_TEN_MOMENT_BUDGET'):
                run(REAL,Path(d)/'reject',execute=True,reference_budgets=[1.e-9]*9)

if __name__=='__main__':unittest.main()
