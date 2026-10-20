"""W1 M16: adversarial original-native same-run evidence tests."""
from __future__ import annotations
import copy
from pathlib import Path
import os
import json
import tempfile
import unittest

from m16_native_actions_forensics import load_original,reconcile,check_job_log,main

ROOT=Path(__file__).resolve().parent
ARCHIVE=Path(os.environ.get('W1_M16_H8E_ARCHIVE','/mnt/data/h8e-25point-39121571756.zip'))
LOG=ROOT/'evidence/m16-original-verified-job-lines.log'

@unittest.skipUnless(ARCHIVE.is_file(),'W1_M16_REAL_ORIGINAL_H8E_ARCHIVE_UNAVAILABLE')
class M16RealNativeForensics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report,cls.rows=load_original(ARCHIVE)

    def safe(self):
        return copy.deepcopy(self.report),copy.deepcopy(self.rows)

    def test_01_real_archive_25_and_original_failure(self):
        d=reconcile(self.report,self.rows)
        self.assertEqual(d['sample_count'],25)
        self.assertEqual(d['original_ci_outcome'],'FAILURE_FEATURE_HASH_DRIFT')
        self.assertEqual(d['observed_feature_hash_changed_indices'],list(range(17,25)))
        self.assertIsNone(d['faster_full_solver_speedup'])
        self.assertEqual(d['fresh_W1_optimized_cherchi_calls'],0)

    def test_02_full_same_run_wall_closed(self):
        d=reconcile(self.report,self.rows)
        self.assertAlmostEqual(d['sum_named_native_stages_seconds'],77.94430469400072,places=5)
        self.assertAlmostEqual(d['sum_unidentified_within_point_seconds'],301.3634490239989,places=5)
        self.assertAlmostEqual(d['outside_point_orchestration_seconds'],.18597416500040254,places=5)

    def test_03_genuine_console_binding(self):
        d=check_job_log(LOG.read_text(),self.rows,self.report['wall_seconds'])
        self.assertEqual(d['real_actions_console_rows'],25)
        self.assertTrue(d['all_console_point_durations_match_archive'])

    def test_04_tamper_report_stage_rejected(self):
        r,p=self.safe();r['stage_totals_seconds']['boolean']+=.25
        with self.assertRaisesRegex(ValueError,'STAGE_SUMMARY'):reconcile(r,p)

    def test_05_tamper_point_wall_rejected(self):
        r,p=self.safe();p[2]['wall_seconds']=.01
        with self.assertRaisesRegex(ValueError,'NEGATIVE_POINT'):reconcile(r,p)

    def test_06_absent_native_stage_rejected(self):
        r,p=self.safe();p[3]['stages_seconds'].pop('boolean')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNTRUSTWORTHY'):reconcile(r,p)

    def test_07_negative_native_stage_rejected(self):
        r,p=self.safe();p[3]['stages_seconds']['boolean']=-1
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNTRUSTWORTHY'):reconcile(r,p)

    def test_08_nonfinite_moment_rejected(self):
        r,p=self.safe();p[8]['independent_variable_raw_moments'][0]=float('nan')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNTRUSTWORTHY'):reconcile(r,p)

    def test_09_missing_snapshot_digest_rejected(self):
        r,p=self.safe();p[9]['exact_same_call_material_archive_sha256']='bad'
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNTRUSTWORTHY'):reconcile(r,p)

    def test_10_feature_history_cannot_be_promoted(self):
        r,p=self.safe();r['all_tested_stencils_same_feature_hash']=True
        with self.assertRaisesRegex(ValueError,'FAILURE_SCOPE_CHANGED'):reconcile(r,p)

    def test_11_changed_point_indices_rejected(self):
        r,p=self.safe();p[21]['feature_branch_hash']=p[0]['feature_branch_hash']
        with self.assertRaisesRegex(ValueError,'EIGHT_CHANGED'):reconcile(r,p)

    def test_12_nonfinite_jacobian_rejected(self):
        r,p=self.safe();r['analytic_10_by_10_jacobian'][3][4]=float('inf')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_MOMENT_JACOBIAN'):reconcile(r,p)

    def test_13_wrong_original_binary_sha_rejected(self):
        r,p=self.safe();r['actual_cherchi_sha256']='fake'
        with self.assertRaisesRegex(ValueError,'NATIVE_BUNDLE_IDENTITY'):reconcile(r,p)

    def test_14_incomplete_console_rejected(self):
        data=LOG.read_text().replace('H8e REAL_CHERCHI 25/25','H8e REAL_CHERCHI 24/25')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_DUPLICATE'):check_job_log(data,self.rows,self.report['wall_seconds'])

    def test_15_forged_console_point_time_rejected(self):
        data=LOG.read_text().replace('1/25 14.94s','1/25 5.00s')
        with self.assertRaisesRegex(ValueError,'LOG_NOT_MATCHING'):check_job_log(data,self.rows,self.report['wall_seconds'])

    def test_16_wrong_console_final_state_rejected(self):
        data=LOG.read_text().replace('"changed_feature_hash_points": 8','"changed_feature_hash_points": 0')
        with self.assertRaisesRegex(ValueError,'FINAL_STATUS'):check_job_log(data,self.rows,self.report['wall_seconds'])

    def test_17_archive_hash_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'fake.zip';p.write_bytes(b'not the real archive')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_NOT_ORIGINAL'):load_original(p)

    def test_18_no_original_newton_or_full_solver_claim(self):
        d=reconcile(self.report,self.rows)
        self.assertFalse(d['newton_or_terminal_material_proven'])
        self.assertFalse(d['original_branch_neighborhood_admission'])
        self.assertFalse(d['paper_speed_qualified'])

    def test_19_missing_point_rejected(self):
        with self.assertRaisesRegex(ValueError,'ORIGINAL_MOMENT_JACOBIAN'):reconcile(self.report,self.rows[:-1])

    def test_20_rational_boundary_flag_rejected(self):
        r,p=self.safe();p[0]['exact_native_material_boundary_passed']=False
        with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_UNTRUSTWORTHY'):reconcile(r,p)

if __name__=='__main__':unittest.main()
