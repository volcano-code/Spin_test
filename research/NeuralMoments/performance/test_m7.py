"""M7 adversarial + actual archive and compiled GMP decoder A/B smoke."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(DIR))
from m6_archived_validation_replay import (ARCHIVE_SHA, decoder_for, scientific_fingerprint,
                                           strict_archive)
from m7_matched_decoder_ab import (STANDARD_ORDER,TWO_ORDER, run_ab,
                                    summarize_pair, _scientific_receipt)


def fake_packet():
    return dict(geometry_hash='geom',topology_hash='topo',
        quadric_source_identity='qsource',boolean_backend_identity='real_cherchi',
        quadric_coefficients=[1.0]*10,variable_raw_moments=[2.0]*10,
        raw_moments=[3.0]*10,moment_jacobian=[[float(i+j) for j in range(10)] for i in range(10)])


def fake_row(name, r):
    return dict(backend=name,point_count=25,science_receipt_sha256='same',
        native_binary_sha256='binary',wall_seconds=r,parse_json_seconds=r/4,
        native_gmp_seconds=r/2)


class M7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('g++'):
            raise RuntimeError('M7_REQUIRES_CPP_COMPILER')
        cls.tmp=tempfile.TemporaryDirectory(prefix='w1-m7-native-')
        cls.binary=Path(cls.tmp.name)/'independent_tetra'
        command=['g++','-std=c++17','-O2','-Wall','-Wextra','-pedantic',
                 str(DIR/'m6_independent_tetra_gmp.cpp'),'-o',str(cls.binary),'-lgmpxx','-lgmp']
        r=subprocess.run(command,capture_output=True,text=True,timeout=120)
        if r.returncode:
            raise AssertionError('M7_REAL_NATIVE_BUILD_FAILED:'+r.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_decode_backend_validation(self):
        self.assertEqual(decoder_for('stdlib')(b'{"n":1}'), {'n':1})
        self.assertEqual(decoder_for('orjson')(b'{"n":1}'), {'n':1})
        with self.assertRaisesRegex(ValueError,'UNKNOWN_DECODER'):
            decoder_for('skip_proofs')

    def test_decoder_rejects_nonfinite_and_malformed_archive_json(self):
        with self.assertRaises((ValueError,json.JSONDecodeError)):
            decoder_for('orjson')(b'{"float":NaN}')
        with self.assertRaises((ValueError,json.JSONDecodeError)):
            decoder_for('orjson')(b'{')

    def test_bitwise_scientific_equivalence(self):
        data=fake_packet()
        parser_a=decoder_for('stdlib')
        parser_b=decoder_for('orjson')
        encoded=json.dumps(data,allow_nan=False).encode()
        self.assertEqual(scientific_fingerprint(parser_a(encoded)),
                         scientific_fingerprint(parser_b(encoded)))

    def test_mutated_jacobian_or_quadric_fails_parity(self):
        old=fake_packet();new=fake_packet()
        old_fp=scientific_fingerprint(old)
        new['moment_jacobian'][4][5]+=1e-8
        self.assertNotEqual(old_fp,scientific_fingerprint(new))
        new=fake_packet();new['quadric_coefficients'][1]=1.0000000000000002
        self.assertNotEqual(old_fp,scientific_fingerprint(new))

    def test_missing_required_identity_and_nan_fails(self):
        data=fake_packet();data['quadric_source_identity']=''
        with self.assertRaisesRegex(ValueError,'MISSING_SCIENTIFIC_IDENTITY'):
            scientific_fingerprint(data)
        data=fake_packet();data['moment_jacobian'][0][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'NONFINITE_SCIENTIFIC_VALUE'):
            scientific_fingerprint(data)
        data=fake_packet();data['moment_jacobian'][0]=[]
        with self.assertRaisesRegex(ValueError,'INVALID_SCIENTIFIC_MATRIX'):
            scientific_fingerprint(data)

    def test_abba_summary_matched_and_scope_preserved(self):
        runs=[fake_row('stdlib',4),fake_row('orjson',2),
              fake_row('orjson',2.5),fake_row('stdlib',4.5)]
        result=summarize_pair(runs,25,STANDARD_ORDER)
        self.assertAlmostEqual(result['paired_end_to_end_archived_validator_ratio_old_over_new'],4.25/2.25)
        self.assertTrue(result['complete_25_point_scientific_parity'])
        self.assertEqual(result['fresh_cherchi_boolean_calls'],0)
        self.assertIsNone(result['production_full_solver_speedup'])
        self.assertTrue(result['original_h8e_ci_failure_preserved'])

    def test_changed_scientific_receipt_fails(self):
        runs=[fake_row('stdlib',4),fake_row('orjson',2)]
        runs[1]['science_receipt_sha256']='changed'
        with self.assertRaisesRegex(ValueError,'SCIENTIFIC_BITWISE_DRIFT'):
            summarize_pair(runs,25,TWO_ORDER)

    def test_invalid_ab_sequence_and_missing_native_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp)
            with self.assertRaisesRegex(ValueError,'INVALID_AB_SEQUENCE'):
                run_ab('x','y',t/'out',order=('orjson','stdlib'))
            with self.assertRaisesRegex(FileNotFoundError,'PINNED_ARCHIVE_AND_COMPILED_GMP_REQUIRED'):
                run_ab(t/'missing.zip', t/'missing-native',t/'out')
            self.assertTrue((t/'out/failure.json').is_file())
            self.assertFalse((t/'out/baseline-performance.json').exists())

    def test_wrong_archive_sha_no_false_speedup(self):
        with tempfile.TemporaryDirectory() as tmp:
            t=Path(tmp);(t/'false.zip').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_HASH_DRIFT'):
                run_ab(t/'false.zip',self.binary,t/'out',points=1,order=TWO_ORDER)
            report=json.loads((t/'out/failure.json').read_text())
            self.assertIsNone(report['production_speedup'])
            self.assertFalse(report['paper_speed_qualified'])

    def test_historical_25_point_failure_is_immutable(self):
        archive=os.environ.get('W1_M7_H8E_ARCHIVE')
        if not archive:
            self.skipTest('M7 exact archive not supplied in this environment')
        from hashlib import sha256
        self.assertEqual(sha256(Path(archive).read_bytes()).hexdigest(),ARCHIVE_SHA)
        with ZipFile(archive) as z:
            r=strict_archive(z)
        self.assertFalse(r['formal_newton_converged'])
        self.assertEqual(r['changed_feature_hash_points'],8)

    def test_one_real_packet_both_decoders_complete_and_identical(self):
        archive=os.environ.get('W1_M7_H8E_ARCHIVE')
        if not archive:
            self.skipTest('M7 exact archive not supplied in this environment')
        with tempfile.TemporaryDirectory() as t:
            report=run_ab(archive,self.binary,Path(t)/'ab',points=1,order=TWO_ORDER)
            self.assertTrue(report['all_checks_passed'])
            self.assertEqual(len(report['executions']),2)
            self.assertEqual(len(set(x['science_receipt_sha256'] for x in report['executions'])),1)
            self.assertFalse(report['matched_pair']['complete_25_point_scientific_parity'])
            self.assertIsNone(report['matched_pair']['production_full_solver_speedup'])

    def test_scientific_receipt_checks_original_failure(self):
        minimal=dict(independent_fd=dict(status='INCOMPLETE_NO_FD'),
                     full_newton_solver_measured=False,fresh_cherchi_boolean_calls=0,
                     new_independent_self_intersection_audits=0,paper_speed_qualified=False)
        row=dict(index=0,archive_material_sha256='sha',topology_hash='topo',
                 q=[0.0]*10,moments=[1.0]*10,m7_scientific_fingerprint='foo')
        self.assertEqual(len(_scientific_receipt([row],minimal)),64)
        minimal['fresh_cherchi_boolean_calls']=1
        with self.assertRaisesRegex(ValueError,'FORBIDDEN_FRESH_SOLVER_CLAIM'):
            _scientific_receipt([row],minimal)

if __name__=='__main__':unittest.main()
