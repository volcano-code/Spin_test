"""W1 M4 contract and frozen-real-archive regression; never substitutes synthetic data for native runs."""
import json
import os
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
import numpy as np
from m4_25point_attribution import (Clock, exact, fraction_ten, five_weights,
                                    verify_fd, strict_archive, replay, ARCHIVE_SHA)
from m4_25point_attribution import H8E_ROOT

ARCHIVE = Path(os.environ.get('W1_H8E_ARCHIVE', '/path/to/not-provided.zip'))
BIN = Path(os.environ.get('W1_M4_NATIVE_BIN', '/path/to/not-provided'))

class M4Tests(unittest.TestCase):
    def test_tetra_exact_independent_formula(self):
        coords=[(Fraction(x),Fraction(y),Fraction(z)) for x,y,z in (
            (0,0,0),(1,0,0),(0,1,0),(0,0,1))]
        faces=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        ten=fraction_ten(coords,faces)
        self.assertEqual(ten[0],1/6)
        self.assertEqual(ten[1:4],[1/24]*3)
        self.assertEqual(ten[4:7],[1/60]*3)
        self.assertEqual(ten[7:],[1/120]*3)

    def test_reject_bad_rational(self):
        for value in ('1', '1/0','abc/1','1/-2','1/2/3','-0/1','0/0','02/3','2/4'):
            with self.subTest(value=value), self.assertRaises(ValueError):exact(value)
        self.assertEqual(exact('-7/3'),Fraction(-7,3))

    def test_reject_geometry_bounds(self):
        coords=[(Fraction(0),)*3 for _ in range(4)]
        with self.assertRaisesRegex(ValueError,'INVALID_FACE_INDEX'):
            fraction_ten(coords,[[1,2,4]])
        with self.assertRaisesRegex(ValueError,'NONPOSITIVE_MASS'):
            fraction_ten(coords,[[0,1,2]])

    def test_clock_exclusivity_and_no_fake_timer(self):
        clock=Clock()
        with clock.stage('zip_read'):
            with self.assertRaisesRegex(ValueError,'W1_OVERLAPPING'):
                with clock.stage('json_decode'):pass
        report=clock.report()
        self.assertTrue(report['all_returned'])
        self.assertGreaterEqual(report['unattributed_ns'],0)
        with self.assertRaisesRegex(ValueError,'UNREGISTERED'):
            with clock.stage('skip_integrity'):pass

    def test_clock_captures_failure(self):
        clock=Clock()
        with self.assertRaises(RuntimeError):
            with clock.stage('packet_sha256'):raise RuntimeError('bad')
        self.assertFalse(clock.report()['all_returned'])

    def test_fd_polynomial(self):
        x=np.array([-1.,-.5,0.,.5,1.])
        w=five_weights(x)
        for n in range(5):
            self.assertAlmostEqual(w@(x**n),float(n==1),places=10)
        with self.assertRaises(ValueError):five_weights([0]*5)

    def test_reject_archive_sha(self):
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            (p/'wrong.zip').write_bytes(b'wrong')
            fake=p/'fakebinary';fake.write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'ARCHIVED_25POINT_ZIP_SHA_MISMATCH'):
                replay(p/'wrong.zip',p/'out',fake)
            self.assertFalse((p/'out'/'baseline-performance.json').exists())
            self.assertTrue((p/'out'/'failure.json').is_file())

    def test_real_archive_immutability_and_original_ci_failure(self):
        if not ARCHIVE.is_file():self.skipTest('archived ZIP not supplied')
        from hashlib import sha256
        self.assertEqual(sha256(ARCHIVE.read_bytes()).hexdigest(),ARCHIVE_SHA)
        with ZipFile(ARCHIVE) as z:
            report=strict_archive(z)
        self.assertEqual(report['completed_samples'],25)
        self.assertFalse(report['all_tested_stencils_same_feature_hash'])
        self.assertEqual(report['changed_feature_hash_points'],8)
        self.assertFalse(report['formal_newton_converged'])

    def test_real_archived_fd_independently_recomputed_from_stored_ten(self):
        if not ARCHIVE.is_file():self.skipTest('archived ZIP not supplied')
        with ZipFile(ARCHIVE) as z:
            report=strict_archive(z)
            rows={}
            for i in range(25):
                point=json.loads(z.read(H8E_ROOT+f'point-{i:03d}.json'))
                rows[i]=dict(q=point['coefficients'],
                    fraction_ten=point['independent_variable_raw_moments'],
                    topology_hash=point['feature_branch_hash'])
        fd=verify_fd(rows,report)
        self.assertEqual(fd['tested_stencils'],9)
        self.assertEqual(fd['original_changed_feature_hash_points'],8)
        self.assertFalse(all(x['original_feature_hash_stable'] for x in fd['checks']))

    def test_missing_executable_fails_closed(self):
        if not ARCHIVE.is_file():self.skipTest('archived ZIP not supplied')
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(FileNotFoundError,'REAL_NATIVE_GMP_BINARY_REQUIRED'):
                replay(ARCHIVE,Path(root)/'out',Path(root)/'absent')

if __name__=='__main__':unittest.main()
