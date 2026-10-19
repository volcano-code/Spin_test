"""M6 tests: executable C++/GMP exact tetra, independent Python Fraction, fail-closed archives."""
from __future__ import annotations
import copy
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from m6_archived_validation_replay import (
    ExclusiveClock, rational, python_fraction_ten, run_binary,
    independent_fd, run, ARCHIVE_SHA, strict_archive,
)

TETRA_VERTICES=[['0/1','0/1','0/1'],['1/1','0/1','0/1'],
                ['0/1','1/1','0/1'],['0/1','0/1','1/1']]
TETRA_FACES=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]

class M6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('g++'):
            raise RuntimeError('CXX_COMPILER_REQUIRED_FOR_M6')
        cls.temp=tempfile.TemporaryDirectory(prefix='w1-m6-tests-')
        cls.binary=Path(cls.temp.name)/'m6_tetra'
        build=subprocess.run(['g++','-O2','-std=c++17','-Wall','-Wextra','-pedantic',
            str(HERE/'m6_independent_tetra_gmp.cpp'),'-o',str(cls.binary),'-lgmpxx','-lgmp'],
            text=True,capture_output=True,timeout=120)
        if build.returncode:
            raise AssertionError('M6_CPP_COMPILATION_FAILED:'+build.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def stream(self,points=None,faces=None,tail=''):
        points=points or TETRA_VERTICES
        faces=faces or TETRA_FACES
        return ('W1_REAL_H8_V1\n'+f'{len(points)} {len(faces)}\n'+
                ''.join(' '.join(p)+'\n' for p in points)+
                ''.join(' '.join(map(str,f))+'\n' for f in faces)+tail)

    def call(self,payload):
        return subprocess.run([str(self.binary)],input=payload,text=True,capture_output=True,timeout=10)

    def test_exact_tetra_analytic_and_old_python(self):
        report=self.call(self.stream())
        self.assertEqual(report.returncode,0,report.stderr)
        obj=json.loads(report.stdout)
        self.assertEqual(obj['vertices'],4)
        self.assertEqual(obj['faces'],4)
        self.assertEqual(obj['exact_ten'],['1/6']+['1/24']*3+['1/60']*3+['1/120']*3)
        self.assertEqual([rational(s) for s in obj['exact_ten']],
                         python_fraction_ten(TETRA_VERTICES,TETRA_FACES))
        self.assertFalse(obj['fresh_boolean'])
        self.assertFalse(obj['new_self_intersection_audit'])
        self.assertIsNone(obj['full_solver_speedup'])

    def test_reject_noncanonical_fraction_both(self):
        for s in ('2/4','00/1','-0/1','1/0','1/-3','0b1/1','1','-1//1'):
            points=copy.deepcopy(TETRA_VERTICES)
            points[1][0]=s
            self.assertNotEqual(self.call(self.stream(points=points)).returncode,0,s)
            with self.assertRaises(ValueError,msg=s):rational(s)

    def test_reject_invalid_face(self):
        for faces in ([[0,2,1],[0,1,3],[0,3,2],[1,2,2]],
                      [[0,2,1],[0,1,3],[0,3,2],[1,2,4]],
                      [[0,2,1],[0,1,3],[0,3,2],[0,1,2]],
                      [[0,1,2],[0,1,3],[0,3,2],[1,2,3]]):
            self.assertNotEqual(self.call(self.stream(faces=faces)).returncode,0,faces)

    def test_reject_truncated_and_extra_data(self):
        for stream in (self.stream()[:-4],self.stream()+"UNTRUSTED_EXTRA\n",
                       self.stream().replace('W1_REAL_H8_V1','INJECTED_STREAM')):
            self.assertNotEqual(self.call(stream).returncode,0)

    def test_python_reject_inconsistent_faces(self):
        with self.assertRaisesRegex(ValueError,'INVALID_EXACT_FACE'):
            python_fraction_ten(TETRA_VERTICES,[[0,0,2]])

    def test_exclusive_timer_disjoint_fail_closed(self):
        clock=ExclusiveClock()
        with clock.stage('read_archive'):
            with self.assertRaisesRegex(ValueError,'OVERLAPPING'):
                with clock.stage('native_exact_tetra'): pass
        with self.assertRaisesRegex(ValueError,'SENTINEL'):
            with clock.stage('parity'):
                raise ValueError('SENTINEL')
        totals=clock.summary()
        self.assertLessEqual(sum(x['elapsed_ns'] for x in totals['stages']),totals['wall_ns'])
        self.assertFalse(totals['all_passed'])

    def test_missing_binary_blocks_without_success(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaisesRegex(FileNotFoundError,'NATIVE_BINARY_REQUIRED'):
                run(root/'missing.zip',root/'missing-binary',root/'out',count=1,
                    reference_indices=(0,))
            self.assertTrue((root/'out/failure.json').is_file())
            self.assertFalse((root/'out/baseline-performance.json').exists())

    def test_wrong_archive_hash_and_no_fabricated_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'fake.zip').write_bytes(b'fake zip')
            with self.assertRaisesRegex(ValueError,'ZIP_SHA_DRIFT'):
                run(root/'fake.zip',self.binary,root/'out',count=1,
                    reference_indices=(0,))
            x=json.loads((root/'out/failure.json').read_text())
            self.assertIsNone(x['full_solver_speedup'])

    def test_no_out_of_bounds_jobs(self):
        with self.assertRaisesRegex(ValueError,'UNSAFE_SAMPLE_SELECTION'):
            run('x','y','z',count=26,reference_indices=(0,))
        with self.assertRaisesRegex(ValueError,'UNSAFE_SAMPLE_SELECTION'):
            run('x','y','z',count=25,reference_indices=(1,1))

    def test_archive_original_h8e_failure_preserved(self):
        archive=os.environ.get('W1_M6_H8E_ARCHIVE')
        if not archive:
            self.skipTest('real artifact is opt-in for limited CI environments')
        from hashlib import sha256
        self.assertEqual(sha256(Path(archive).read_bytes()).hexdigest(),ARCHIVE_SHA)
        with ZipFile(archive) as z:
            r=strict_archive(z)
        self.assertEqual(r['changed_feature_hash_points'],8)
        self.assertFalse(r['formal_newton_converged'])

    def test_real_first_packet_exact_python_vs_gmp(self):
        archive=os.environ.get('W1_M6_H8E_ARCHIVE')
        if not archive:
            self.skipTest('real artifact is opt-in for limited CI environments')
        with tempfile.TemporaryDirectory() as td:
            result=run(archive,self.binary,Path(td)/'out',count=1,reference_indices=(0,))
            self.assertTrue(result['exact_python_fraction_gmp_parity_on_samples'])
            self.assertEqual(result['ten_component_historical_parity_count'],10)
            self.assertEqual(result['fresh_cherchi_boolean_calls'],0)

if __name__=='__main__':unittest.main()
