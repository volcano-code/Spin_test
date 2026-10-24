"""W3 H9 stage17: exact native tuple-vs-JSON list identity bug regression.

Tests do not claim fresh Cherchi execution. Historical sample59 is an original
H8f archive reused as a fixture; native runtime material is not forged as data.
"""
from __future__ import annotations

import gzip
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

SRC = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SRC))
import h9_same_call_capture as capture

H8F_SHA = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:inprocess'
ZIP = os.environ.get('H9_EVIDENCE_ZIP')


def fixture():
    q = [0.125, -0.25, 0.375, -0.5, 0.625, -0.75, 0.875, 2.1805862283444328e-6, 0.0, -0.0]
    material = {
        'quadric_coefficients': tuple(q),
        'boolean_backend_identity': BACKEND,
        'material_proof': {'schema': 'cherchi-same-call-material-v1'},
        'fixture_not_fresh_native': True,
    }
    return q, material


class Stage17NativeTupleIdentity(unittest.TestCase):
    def run_capture(self, q, material):
        with tempfile.TemporaryDirectory() as d:
            result = capture.capture_same_call(
                d, index=0, side='left-coarse', coefficients=q,
                material=material, backend_identity=BACKEND)
            archive = Path(d) / 'unverified-00-left-coarse.json.gz'
            meta = Path(d) / 'unverified-00-left-coarse.json'
            saved = json.loads(gzip.decompress(archive.read_bytes()))
            proof = json.loads(meta.read_text())
            self.assertEqual(result, proof)
            self.assertEqual(result['coefficients'], q)
            self.assertEqual(proof['archive_sha256'], capture.digest(archive))
            self.assertEqual(saved['quadric_coefficients'], q)
            self.assertFalse(proof['strict_native_boundary_certified'])
            self.assertFalse(proof['newton_admitted'])
            return saved

    def rejected(self, q, material):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(capture.CaptureRejected,
                                        'NEW_NATIVE_CAPTURE_QUADRIC_IDENTITY_MISMATCH'):
                capture.capture_same_call(d,index=0,side='left-coarse',
                    coefficients=q,material=material,backend_identity=BACKEND)
            self.assertEqual(list(Path(d).iterdir()), [],
                             'identity rejection must not publish any checkpoint')

    def test_actual_native_material_tuple_is_accepted_without_modification(self):
        q, material = fixture()
        before = dict(material)
        self.run_capture(q, material)
        self.assertEqual(material, before)
        self.assertIsInstance(material['quadric_coefficients'], tuple)

    def test_historical_json_decoded_list_remains_accepted(self):
        q, material = fixture()
        material['quadric_coefficients'] = list(material['quadric_coefficients'])
        self.run_capture(q, material)

    def test_one_ulp_drift_rejected_without_material_archive(self):
        q, material = fixture()
        drift = list(q)
        drift[7] = math.nextafter(drift[7], math.inf)
        material['quadric_coefficients'] = tuple(drift)
        self.rejected(q, material)

    def test_signed_zero_binary64_drift_rejected(self):
        q, material = fixture()
        altered = list(q)
        altered[9] = 0.0  # requested was -0.0
        material['quadric_coefficients'] = tuple(altered)
        self.rejected(q, material)

    def test_reordered_coefficients_rejected(self):
        q, material = fixture()
        altered = list(q)
        altered[1], altered[2] = altered[2], altered[1]
        material['quadric_coefficients'] = tuple(altered)
        self.rejected(q, material)

    def test_wrong_length_rejected(self):
        q, material = fixture()
        material['quadric_coefficients'] = tuple(q[:-1])
        self.rejected(q, material)
        q, material = fixture()
        self.rejected(q[:-1], material)

    def test_nonfinite_and_boolean_rejected(self):
        q, material = fixture()
        altered = list(q)
        altered[3] = float('nan')
        material['quadric_coefficients'] = tuple(altered)
        self.rejected(q, material)
        q, material = fixture()
        altered = list(q)
        altered[8] = True
        material['quadric_coefficients'] = tuple(altered)
        self.rejected(q, material)

    def test_non_sequence_native_field_rejected(self):
        q, material = fixture()
        material['quadric_coefficients'] = {'value': q}
        self.rejected(q, material)

    def test_fresh_q_with_historical_q_packet_rejected(self):
        q, material = fixture()
        planned = list(q)
        planned[7] = 2.2705862283444327e-6
        self.rejected(planned, material)

    @unittest.skipUnless(ZIP and Path(ZIP).is_file(), 'requires authentic H8f 81-point artifact')
    def test_real_h8f_sample59_list_tuple_equivalence(self):
        artifact = Path(ZIP)
        self.assertEqual(sha256(artifact.read_bytes()).hexdigest(), H8F_SHA)
        with zipfile.ZipFile(artifact) as z:
            name = 'artifacts/h8f-all81-points/point-059'
            point = json.loads(z.read(name + '.json'))
            material = json.loads(gzip.decompress(z.read(name + '-material.json.gz')))
        coefficients = point['coefficients']
        saved_coefficients = material['quadric_coefficients']
        self.assertTrue(capture.same_binary64_coefficients(coefficients, saved_coefficients))
        material['quadric_coefficients'] = tuple(saved_coefficients)
        self.assertTrue(capture.same_binary64_coefficients(coefficients, material['quadric_coefficients']))
        with tempfile.TemporaryDirectory() as folder:
            out = capture.capture_same_call(
                folder, index=0, side='left-coarse', coefficients=coefficients,
                material=material, backend_identity=point['native_boolean_backend'])
            archived = json.loads(gzip.decompress(
                (Path(folder)/'unverified-00-left-coarse.json.gz').read_bytes()))
            self.assertEqual(archived['quadric_coefficients'], coefficients)
            self.assertFalse(out['newton_admitted'])


if __name__ == '__main__':
    unittest.main()
