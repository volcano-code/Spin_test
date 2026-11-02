"""W3 Stage18: cross-build provenance identity without false H8f equality.

Authentic archived H8f sample59 is only a fixture. Synthetic changed identities
simulate a different binary; NO new Cherchi run or Newton claim is made.
"""
from __future__ import annotations
import copy
import gzip
import os
from pathlib import Path
import sys
import unittest
import zipfile
import json
from hashlib import sha256

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from audit_h9_new_native_sides import validate_native_packet_provenance

H8F_SHA='99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
NEW_BOOLEAN_SHA='9e04eb5b61767563c988a1e00a68f76b294c4c16ecc262c4220f8b49ae1c51b0'
BACKEND_PREFIX='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'
ARCHIVE=Path(os.environ.get('H9_EVIDENCE_ZIP','/mnt/data/w3-h8f-evidence-12135528290.zip'))


class CrossBuildProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file():
            raise unittest.SkipTest('needs real original H8f ZIP')
        if sha256(ARCHIVE.read_bytes()).hexdigest() != H8F_SHA:
            raise AssertionError('ACTUAL_H8F_ZIP_SHA_MISMATCH')
        with zipfile.ZipFile(ARCHIVE) as z:
            cls.historical=json.loads(gzip.decompress(
                z.read('artifacts/h8f-all81-points/point-059-material.json.gz')))
            cls.report=json.loads(z.read('artifacts/h8f-all81-points/report.json'))
        cls.arithmetic_sha=cls.report['actual_arithmetic_sha256']
        cls.historical_boolean_sha=cls.report['actual_cherchi_sha256']

    def make_cross_build(self, *, map_id='a'*64, boolean_sha=NEW_BOOLEAN_SHA):
        p=copy.deepcopy(self.historical)
        p['boolean_backend_identity']=BACKEND_PREFIX+boolean_sha
        p['evaluation_map_identity']=map_id
        return p

    def validate(self,p,**kwargs):
        return validate_native_packet_provenance(
            p,self.historical,self.arithmetic_sha,
            boolean_sha=NEW_BOOLEAN_SHA,**kwargs)

    def test_historical_material_still_valid_with_historical_binary(self):
        self.assertTrue(validate_native_packet_provenance(
            self.historical,self.historical,self.arithmetic_sha,
            boolean_sha=self.historical_boolean_sha))

    def test_different_pinned_core_and_boolean_map_accepted_as_new_build_only(self):
        p=self.make_cross_build()
        self.assertNotEqual(p['evaluation_map_identity'],self.historical['evaluation_map_identity'])
        self.assertTrue(self.validate(p))

    def test_four_same_run_map_identities_pass(self):
        for _ in range(4):
            self.assertTrue(self.validate(self.make_cross_build(),expected_map_identity='a'*64))

    def test_changed_map_inside_one_run_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'NEW_NATIVE_EVALUATION_MAP_IDENTITY_CHANGED_WITHIN_FOUR_SIDES'):
            self.validate(self.make_cross_build(map_id='b'*64), expected_map_identity='a'*64)

    def test_wrong_boolean_binary_sha_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            self.validate(self.make_cross_build(boolean_sha='0'*64))

    def test_arithmetic_module_sha_mismatch_rejected(self):
        p=self.make_cross_build()
        p['rational_arithmetic_identity']['module_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            self.validate(p)

    def test_arithmetic_algorithm_mismatch_rejected(self):
        p=self.make_cross_build()
        p['rational_arithmetic_identity']['algorithm']='FORGED'
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            self.validate(p)

    def test_non_hex_context_identity_rejected(self):
        p=self.make_cross_build(map_id='not-a-sha')
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            self.validate(p)

    def test_false_derivative_not_allowed(self):
        p=self.make_cross_build()
        p['derivative_defined']=False
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            self.validate(p)

    def test_operation_change_is_rejected(self):
        p=self.make_cross_build()
        p['boolean_operation']='intersection'
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            self.validate(p)

    def test_source_triangulation_change_rejected(self):
        p=self.make_cross_build()
        p['quadric_source_faces'][0][0]=-1
        with self.assertRaisesRegex(ValueError,'NATIVE_SOURCE_TRIANGULATION_CHANGED_IN_PROBE_INTERVAL'):
            self.validate(p)

    def test_mismatched_historical_binary_sha_cannot_relabel_new_packet(self):
        p=self.make_cross_build()
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            validate_native_packet_provenance(p,self.historical,self.arithmetic_sha,
                                               boolean_sha=self.historical_boolean_sha)


if __name__=='__main__':
    unittest.main()
