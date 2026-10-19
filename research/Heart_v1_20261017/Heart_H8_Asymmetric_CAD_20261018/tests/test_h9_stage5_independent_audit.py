"""W3 stage 5: real H8f rational re-integration + fail-closed side acceptance."""
from __future__ import annotations

from fractions import Fraction as F
import json
import gzip
import zipfile
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest

SRC=Path(__file__).resolve().parents[1]/'source'
sys.path.insert(0,str(SRC))
from reintegrate_h9_true_moments import (
    exact_token, exact_ten_moments, oriented_edge_audit,
    historical_replay,
)
from certify_h9_interior_edge_crossing import solve as crossing_certify
from probe_h9_crossing_sides_live import native_plan
from audit_h9_new_native_sides import audit,validate_native_packet_provenance

ZIP=os.getenv('H9_EVIDENCE_ZIP')
CERT=os.getenv('H9_CROSSING_CERTIFICATE')


class ExactMassMomentIndependentTests(unittest.TestCase):
    def test_exact_binary_token_grammar(self):
        self.assertEqual(exact_token('-0b101/0b10'),F(-5,2))
        self.assertEqual(exact_token('11/12'),F(11,12))
        self.assertEqual(exact_token('0/1'),F(0))
        for bad in ('1/0','1/-2','2/3/4','NaN/1','+1/2','0b2/0b1','1.0/2'):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                exact_token(bad)

    def test_independent_unit_tetrahedron_exact_ten_moments(self):
        points=[('0/1','0/1','0/1'),('1/1','0/1','0/1'),
                ('0/1','1/1','0/1'),('0/1','0/1','1/1')]
        faces=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        moments=exact_ten_moments(points,faces)
        self.assertEqual(moments,(F(1,6),F(1,24),F(1,24),F(1,24),
                                  F(1,60),F(1,60),F(1,60),F(1,120),F(1,120),F(1,120)))
        stats=oriented_edge_audit(faces,4)
        self.assertEqual(stats['manifold_edges_checked'],6)
        self.assertFalse(stats['global_self_intersection_checked'])

    def test_inconsistent_or_open_edge_chain_rejected(self):
        for faces in ([[0,1,2]], [[0,1,2],[0,1,3]],[[0,0,1]]):
            with self.subTest(faces=faces),self.assertRaises(ValueError):
                oriented_edge_audit(faces,4)

    @unittest.skipUnless(ZIP,'requires original H8f Actions artifact')
    def test_actual_archived_59_60_reintegrate_all_ten_exactly(self):
        report=historical_replay(ZIP)
        self.assertEqual(report['reintegrated_real_historical_samples'],[59,60])
        self.assertEqual(report['historic_run_conclusion'],'failure')
        self.assertEqual(report['new_real_native_calls_this_run'],0)
        for i in ('59','60'):
            m=report['materials'][i]
            self.assertEqual(m['edge_structure']['manifold_edges_checked'],25365)
            self.assertEqual(m['edge_structure']['triangle_count'],16910)
            self.assertEqual(m['max_scaled_error_vs_archived_independent'],0.0)
            self.assertEqual(m['max_scaled_error_vs_archived_production'],0.0)
            self.assertGreater(m['raw_ten_moments_from_independent_fraction'][0],0)
        self.assertLess(report['max_scaled_secant_difference_vs_base_analytic_jacobian'],2e-5)
        self.assertFalse(report['newton_admitted'])


class SideAuditFailClosedTests(unittest.TestCase):
    @unittest.skipUnless(ZIP,'requires genuine H8f archived same-call material')
    def test_real_material_provenance_subtraction_not_difference(self):
        with zipfile.ZipFile(ZIP) as z:
            material=json.loads(gzip.decompress(z.read('artifacts/h8f-all81-points/point-059-material.json.gz')))
            report=json.loads(z.read('artifacts/h8f-all81-points/report.json'))
        arithmetic_sha=report['actual_arithmetic_sha256']
        self.assertEqual(material['boolean_operation'],'subtraction')
        self.assertTrue(validate_native_packet_provenance(material,material,arithmetic_sha))
        changed=copy.deepcopy(material)
        changed['boolean_operation']='difference'
        with self.assertRaisesRegex(ValueError,'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE'):
            validate_native_packet_provenance(changed,material,arithmetic_sha)
        changed=copy.deepcopy(material)
        changed['quadric_source_faces'][0][0]=-1
        with self.assertRaisesRegex(ValueError,'NATIVE_SOURCE_TRIANGULATION_CHANGED_IN_PROBE_INTERVAL'):
            validate_native_packet_provenance(changed,material,arithmetic_sha)

    @unittest.skipUnless(ZIP and CERT,'requires authentic original artifact and stage4 cert')
    def test_no_new_native_snapshots_cannot_pass(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT'):
                audit(ZIP,CERT,td)

    @unittest.skipUnless(ZIP and CERT,'requires authentic original artifact and stage4 cert')
    def test_legacy_h8f_summary_relabelled_four_real_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            candidate={
                'schema':'heart-h9-crossing-sides-live-v1',
                'status':'FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED',
                'new_real_native_calls':4,'finished_indices':[0,1,2,3],
                'historical_run_id':39123384402,'historical_run_conclusion':'failure',
                'source_archive_sha256':'99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9',
                'plan':native_plan(json.loads(Path(CERT).read_text())),
                'newton_admitted':False,'actual_accepted_step':False,
                'actual_smooth_neighborhood_certified':False,'final_heart_obj_produced':False,
            }
            # A claim of four native calls without actual binary IDs/snapshots is never evidence.
            (folder/'report.json').write_text(json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,'MISSING_ACTUAL_BINARY_SHA256_IDS'):
                audit(ZIP,CERT,folder)

    @unittest.skipUnless(ZIP and CERT,'requires authentic original artifact and stage4 cert')
    def test_fake_four_call_manifest_without_snapshot_bytes_denied(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            certificate=json.loads(Path(CERT).read_text())
            candidate={
                'schema':'heart-h9-crossing-sides-live-v1',
                'status':'FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED',
                'new_real_native_calls':4,'finished_indices':[0,1,2,3],
                'historical_run_id':39123384402,'historical_run_conclusion':'failure',
                'source_archive_sha256':certificate['artifact_sha256'],
                'plan':native_plan(certificate),
                'newton_admitted':False,'actual_accepted_step':False,
                'actual_smooth_neighborhood_certified':False,'final_heart_obj_produced':False,
                'binary_hashes':{'core':'a'*64,'boolean':'b'*64,'arithmetic':'c'*64},
                'native_binary_identical_to_h8f':{'core':False,'boolean':False,'arithmetic':False},
            }
            (folder/'report.json').write_text(json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,'NEW_NATIVE_SIDE_SNAPSHOT_MISSING_0'):
                audit(ZIP,CERT,folder)

    @unittest.skipUnless(ZIP and CERT,'requires authentic original artifact and stage4 cert')
    def test_tampered_offline_certificate_denied(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            cert=json.loads(Path(CERT).read_text())
            cert['conditional_analytic_interior_edge_crossing_certified']=False
            bogus=folder/'bogus.json';bogus.write_text(json.dumps(cert))
            with self.assertRaisesRegex(ValueError,'CROSSING_CERTIFICATE_NOT_REPRODUCED'):
                audit(ZIP,bogus,folder)


if __name__=='__main__':unittest.main()
