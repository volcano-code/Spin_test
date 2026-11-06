from fractions import Fraction
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from independent_reference import integrate_exact_boundary
from m16_native_acceptance import file_hash, h256
from m22_recover_h8f_point0 import compare_material, MEMBER, read_material
from native_cherchi_teacher import digest


class TestPoint000(unittest.TestCase):
    def setUp(self):
        self.mat = {'variable_rational_vertices': [[0,0,0], [1,0,0], [0,1,0], [0,0,1]],
                    'variable_faces': [[0,2,1], [0,1,3], [0,3,2], [1,2,3]],
                    'geometry_hash': 'g', 'topology_hash': 't', 'quadric_coefficients': [0.0]*10}
        values, ref = integrate_exact_boundary(self.mat['variable_rational_vertices'],
                                               self.mat['variable_faces'], 1.0)
        self.mat['variable_raw_moments'] = [float(v) for v in values]
        self.row = {'index': 0, 'geometry_hash': 'g', 'topology_hash': 't',
                    'native_c': self.mat['quadric_coefficients'], 'r_D': self.mat['variable_raw_moments'],
                    'r_F': [1.0]*10, 'split': 'excluded', 'training_admitted': False, 'J_D': None}
        self.mat['raw_moments'] = [d+f for d, f in zip(self.row['r_D'], self.row['r_F'])]
        self.payload = {k: self.row[k] for k in ('native_c', 'r_D', 'r_F')}
        self.payload.update(density=1.0, exact_proof={
            'geometry_hash': 'g', 'topology_hash': 't', 'independent_ten_moment_audit': ref,
            'same_call_attachment': {'serialized_material_sha256': digest(self.mat)}})

    def test_full_match_keeps_exclusions(self):
        result = compare_material(self.mat, self.row, self.payload)
        self.assertEqual(result['status'], 'FULL_CANONICAL_MATERIAL_MATCH')
        self.assertEqual(result['exact_moments_matched'], 10)
        self.assertTrue(result['boundary_matched'] and result['full_canonical_material_matched'])
        self.assertIsNone(result['J_D'])
        for field in ('training_admitted', 'continuity_certified', 'historical_process_identity_certified'):
            self.assertFalse(result[field])

    def test_different_attachment_same_boundary(self):
        result = compare_material(dict(self.mat, extra='metadata'), self.row, self.payload)
        self.assertEqual(result['status'], 'BOUNDARY_ONLY')
        self.assertTrue(result['boundary_matched'])
        self.assertFalse(result['full_canonical_material_matched'])

    def test_face_order_changes_digest_with_identical_integral(self):
        mat = dict(self.mat, variable_faces=list(reversed(self.mat['variable_faces'])))
        r = compare_material(mat, self.row, self.payload)
        self.assertEqual(r['status'], 'REJECTED_BOUNDARY_CONFLICT')
        self.assertEqual(r['exact_moments_matched'], 10)
        self.assertFalse(r['boundary_matched'])

    def test_small_fraction_discrepancy(self):
        ref = self.payload['exact_proof']['independent_ten_moment_audit']
        ref['reference_raw_moments_exact'][0] = '100000000000000000001/600000000000000000000'
        self.assertEqual(float(Fraction(ref['reference_raw_moments_exact'][0])), self.row['r_D'][0])
        r = compare_material(self.mat, self.row, self.payload)
        self.assertEqual(r['status'], 'REJECTED_BOUNDARY_CONFLICT')
        self.assertEqual(r['exact_moments_matched'], 9)

    def test_reject_identity_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'IDENTITY_MISMATCH:topology_hash'):
            compare_material(dict(self.mat, topology_hash='wrong'), self.row, self.payload)
        with self.assertRaisesRegex(ValueError, 'VALUE_MISMATCH:r_F'):
            compare_material(self.mat, dict(self.row, r_F=[0.0]*10), self.payload)

    def test_reject_double_counted_fixed_mass(self):
        with self.assertRaisesRegex(ValueError, 'VALUE_MISMATCH:r_total'):
            compare_material(dict(self.mat, raw_moments=[0.0]*10), self.row, self.payload)

    def test_gzip_and_zip_paths_both_bound_to_bytes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = gzip.compress(json.dumps(self.mat).encode())
            gz = root / 'point-000-material.json.gz'
            gz.write_bytes(raw)
            archive = root / 'points.zip'
            with ZipFile(archive, 'w') as stream:
                stream.writestr(MEMBER, raw)
                stream.writestr(MEMBER.replace('000', '001'), b'wrong-point')
            for path in (archive, gz):
                self.assertEqual(read_material(path, h256(raw), file_hash(archive)), self.mat)
                with self.assertRaisesRegex(ValueError, 'POINT000_GZIP_SHA_MISMATCH'):
                    read_material(path, '0'*64, file_hash(archive))
            with self.assertRaisesRegex(ValueError, 'H8F_ARCHIVE_SHA_MISMATCH'):
                read_material(archive, h256(raw), '0'*64)
