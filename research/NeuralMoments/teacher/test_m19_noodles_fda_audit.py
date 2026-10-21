"""W2 M19 real V7 94-part SHA and exact rational physical-moment tests.

Historical Boolean F/D/A rational packets are deliberately NOT reconstructed,
and none of these tests authorize native Cherchi or a Jacobian training label.
"""
from __future__ import annotations
import copy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import warnings
from zipfile import ZipFile, ZIP_STORED

import m19_noodles_fda_audit as m

BUNDLE = os.environ.get('W2_M18_SOURCE_BUNDLE')
FULL = os.environ.get('W2_M19_ALL94_RESULT') or str(
    Path(__file__).with_name('M19_NOODLES_ALL94_EXACT_SOURCE_MOMENTS.json'))


def stage_modified_zip(path, replacements=None, omit=(), duplicate=None):
    replacements=replacements or {}
    with ZipFile(BUNDLE) as original, ZipFile(path, 'w', compression=ZIP_STORED) as out:
        for filename in original.namelist():
            if filename in omit:continue
            out.writestr(filename,replacements.get(filename,original.read(filename)))
        if duplicate is not None:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                out.writestr(duplicate,b'duplicate')


class TestM19AuthenticNoodles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BUNDLE or not Path(BUNDLE).is_file():
            raise unittest.SkipTest('Set W2_M18_SOURCE_BUNDLE to authentic M18 188-OBJ bundle for 16 real-asset tests')
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.quick=m.audit_source_bundle(BUNDLE,exact_all_parts=False)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_all_94_actual_source_names(self):
        self.assertEqual(self.quick['source_parts_identity_checked'],94)
    def test_188_real_sha(self):
        self.assertEqual(self.quick['original_obj_sha256_verified'],188)
    def test_original_88040_source_triangles(self):
        self.assertEqual(self.quick['source_triangles_total'],88040)
    def test_93_fixed_overlaps_not_conflated_with_F(self):
        self.assertEqual(self.quick['original_fixed_parts_count'],93)
        self.assertTrue(self.quick['source_mass_moments_must_not_be_summed_to_fixed_F'])
        self.assertFalse(self.quick['historical_CSG_independent_partition_certified'])
    def test_frozen_corpus_and_receipt(self):
        self.assertEqual(self.quick['source_corpus_188_digest'],m.CORPUS_DIGEST_188)
        self.assertEqual(self.quick['original_CSG_receipt_sha256'],m.CSG_RECEIPT_SHA256)
        self.assertEqual(self.quick['original_historic_exact_CSG_calls'],96)
        self.assertEqual(self.quick['new_exact_CSG_calls'],0)
    def test_independent_actual_envelope_exact_ten(self):
        r=self.quick['source_moment_snapshots']['outer-ellipsoid']['r10_normalized_target_frame']
        self.assertEqual(len(r),10)
        self.assertAlmostEqual(r[0],1.401599858658712,places=14)
        self.assertAlmostEqual(r[3],1.4856958501782347,places=14)
    def test_provenance_remains_not_author_cad(self):
        self.assertIn('NOT_AUTHOR_CAD',self.quick['scope'])
        self.assertIsNone(self.quick['J_D'])
        self.assertEqual(self.quick['training_admitted'],0)
    def test_complete_run_and_exit_2_persists_actual_failure(self):
        output=self.root/'m19_actual_failure.json'
        result=m.run(BUNDLE,output,exact_all_parts=False)
        self.assertTrue(output.is_file())
        self.assertEqual(result['status'],'SOURCE_MOMENTS_VERIFIED_CSG_PACKETS_MISSING_NATIVE_TEACHER_BLOCKED')
        self.assertEqual(result['historic_CSG_packet_evidence']['historical_csg_packets_missing'],list(m.PACKETS))
        self.assertFalse(result['native_teacher_request_admitted'])
        with self.assertRaisesRegex(m.GateError,'REFUSE_OVERWRITE_EXISTING_EVIDENCE'):
            m._atomic_exclusive_json(output,{})
    def test_csg_empty_directory_is_not_historic_packets(self):
        root=self.root/'empty-csg';root.mkdir(exist_ok=True)
        receipt=self.root/'historical-receipt.json'
        with ZipFile(BUNDLE) as z:receipt.write_bytes(z.read(m.BUNDLE_CSG_RECEIPT))
        x=m.historical_csg_gate(root,receipt)
        self.assertEqual(len(x['historical_csg_packets_missing']),6)
        self.assertFalse(x['historical_CSG_independent_partition_certified'])
    def test_fake_csg_packet_rejected_even_when_named_correctly(self):
        root=self.root/'fraud';root.mkdir(exist_ok=True)
        receipt=self.root/'real-construction.json'
        with ZipFile(BUNDLE) as z:receipt.write_bytes(z.read(m.BUNDLE_CSG_RECEIPT))
        (root/'fixed-rational.json').write_text('{"vertices":[],"faces":[]}')
        with self.assertRaisesRegex(m.GateError,'HISTORIC_CSG_PACKET_SHA_CHANGED:fixed'):
            m.historical_csg_gate(root,receipt)
    def test_untrusted_external_csg_receipt_rejected(self):
        root=self.root/'bad-receipt';root.mkdir(exist_ok=True)
        (root/'construction.json').write_text('{"csg_executed_current_process":96}')
        with self.assertRaisesRegex(m.GateError,'HISTORIC_CSG_RECEIPT_SHA256_MISMATCH'):
            m.historical_csg_gate(root,root/'construction.json')
    def test_archive_missing_original_obj_is_rejected(self):
        fake=self.root/'minus-one.zip'
        stage_modified_zip(fake,omit=['OBJ/tube-078-fixed-si.obj'])
        with self.assertRaisesRegex(m.GateError,'MISSING_BUNDLE_MEMBER'):
            m.audit_source_bundle(fake,exact_all_parts=False)
    def test_archive_forged_original_obj_is_rejected(self):
        fake=self.root/'forged-source.zip'
        stage_modified_zip(fake,replacements={'OBJ/outer-ellipsoid-model.obj':b'v 0 0 0\n'})
        with self.assertRaisesRegex(m.GateError,'FROZEN_SOURCE_SHA_DRIFT:outer-ellipsoid'):
            m.audit_source_bundle(fake,exact_all_parts=False)
    def test_archive_manifest_recode_is_rejected(self):
        fake=self.root/'recode-manifest.zip'
        with ZipFile(BUNDLE) as z:raw=z.read(m.BUNDLE_MANIFEST)
        stage_modified_zip(fake,replacements={m.BUNDLE_MANIFEST:raw+b' '})
        with self.assertRaisesRegex(m.GateError,'ORIGINAL_MANIFEST_SHA256_MISMATCH'):
            m.audit_source_bundle(fake,exact_all_parts=False)
    def test_archive_duplicate_member_rejected(self):
        fake=self.root/'duplicate.zip'
        stage_modified_zip(fake,duplicate='OBJ/outer-ellipsoid-model.obj')
        with self.assertRaisesRegex(m.GateError,'DUPLICATE_ZIP_MEMBER'):
            m.audit_source_bundle(fake,exact_all_parts=False)
    def test_exact_all94_saved_report_when_supplied(self):
        if FULL is None or not Path(FULL).is_file():
            raise RuntimeError('W2_M19_ALL94_RESULT must name actual all94 result, not mock')
        x=m.json_strict(Path(FULL).read_bytes())
        self.assertEqual(x['independently_reintegrated_source_meshes'],94)
        self.assertEqual(x['independently_reintegrated_ten_moment_components'],940)
        self.assertEqual(len(x['source_moment_snapshots']),94)
        self.assertLessEqual(x['max_volume_error_relative_to_frozen_f64_source_audit'],1e-12)
        self.assertEqual(x['original_obj_sha256_verified'],188)
        self.assertFalse(x['native_teacher_request_admitted'])


class TestM19ExactRational(unittest.TestCase):
    def setUp(self):
        self.xyz=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]]
        self.faces=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
    def test_exact_closed_tetra_volume_and_moments(self):
        m.oriented_topology(self.xyz,self.faces)
        r=m.exact_signed_ten(self.xyz,self.faces)
        self.assertEqual(r[0],Fraction(1,6))
        self.assertEqual(r[1],Fraction(1,24))
        self.assertEqual(r[4],Fraction(1,60))
        self.assertEqual(r[9],Fraction(1,120))
    def test_target_translation_has_correct_moment(self):
        r=m.exact_signed_ten(self.xyz,self.faces,target_origin=(0,0,-1))
        self.assertEqual(r[0],Fraction(1,6))
        self.assertEqual(r[3],Fraction(5,24))
    def test_orientation_flip_is_rejected_by_exact_mass(self):
        with self.assertRaisesRegex(m.GateError,'NONPOSITIVE_SOURCE_EXACT_VOLUME'):
            m.exact_signed_ten(self.xyz,[list(reversed(t)) for t in self.faces])
    def test_open_surface_is_not_watertight(self):
        with self.assertRaisesRegex(m.GateError,'ORIENTED_TWO_MANIFOLD_EDGE_PAIRING_FAILED'):
            m.oriented_topology(self.xyz,self.faces[:3])
    def test_obj_nontriangle_refused(self):
        with self.assertRaisesRegex(m.GateError,'OBJ_NOT_ABSOLUTE_TRIANGLE'):
            m.read_static_triangles(b'v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\nf 1 2 3 4\n','bogus')
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(m.GateError,'DUPLICATE_JSON_KEY'):
            m.json_strict(b'{"a":1,"a":2}')
    def test_nan_json_rejected(self):
        with self.assertRaisesRegex(m.GateError,'UNSUPPORTED_JSON_NUMBER'):
            m.json_strict(b'{"a":NaN}')
    def test_alternate_source_corpus_encoding_forbidden(self):
        self.assertNotEqual(m.CORPUS_DIGEST_188,'0'*64)

if __name__=='__main__':unittest.main()
