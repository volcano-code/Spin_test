"""Stage 8 structural handoff tests (ONLY synthetic fixture files).

No test executes Cherchi. Synthetic success exercises structural verification,
not scientific provenance. Real four-point native execution is still required.
"""
from __future__ import annotations

import copy
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import verify_h9_live_handoff as gate
import prepare_h9_pinned_native as launch

SHA_MAP = {'_make_it_stand': 'a'*64,
           '_cherchi_core_boolean': 'b'*64,
           '_cherchi_rational_moments': 'c'*64}
BINARY_SHA = {'core': 'a'*64,'boolean': 'b'*64,'arithmetic': 'c'*64}
SIDES = ('left-coarse','left-near','right-near','right-coarse')


def write_json(path, object_):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(object_,sort_keys=True,allow_nan=False)+'\n',encoding='utf8')


def build_synthetic_structural_fixture(serial):
    """Self-consistent text: intentionally NOT an actual native execution."""
    serial=Path(serial); native=serial/'native'
    native.mkdir(parents=True,exist_ok=True)
    write_json(serial/'run_status.json',{
        'status':'FOUR_NEW_REAL_NATIVE_POINTS_AND_INDEPENDENT_AUDIT_FINISHED_NO_NEWTON',
        'audit_exit_code':0,'newton_admitted':False})
    (serial/'probe.stdout.txt').write_text(''.join(
        f'H9_REAL_NATIVE_SIDE_PROBE {i} {side} {1 if i<2 else -1} SYNTHETIC_NOT_NATIVE\n'
        for i,side in enumerate(SIDES)))
    (serial/'audit.stdout.txt').write_text(
        'H9_NEW_NATIVE_SIDES_REINTEGRATED_BUT_NEWTON_STILL_DENIED 4\n')
    plan=[{'index':i,'side':side,'c7':float(2.18e-6 + i*1e-8),
           'expected_proxy_event_sign': 1 if i<2 else -1} for i,side in enumerate(SIDES)]
    producer={'schema':'heart-h9-crossing-sides-live-v1',
        'status':'FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED',
        'new_real_native_calls':4,'finished_indices':[0,1,2,3],
        'historical_run_id':39123384402,'historical_run_conclusion':'failure',
        'source_archive_sha256':gate.H8F_SHA256,
        'binary_hashes':BINARY_SHA,
        'native_binary_identical_to_h8f':{'core':False,'boolean':False,'arithmetic':False},
        'newton_admitted':False,'actual_accepted_step':False,
        'actual_smooth_neighborhood_certified':False,'final_heart_obj_produced':False,
        'plan':plan}
    write_json(native/'report.json',producer)
    stats=[]
    for i,side in enumerate(SIDES):
        stem=f'side-{i:02d}-{side}'
        compressed=native/(stem+'.json.gz')
        with gzip.open(compressed,'wb') as stream:
            stream.write(json.dumps({'synthetic':True,'index':i}).encode('utf8'))
        digest=gate.hash_file(compressed)
        write_json(native/(stem+'.json'),{'index':i,'side':side,'c7':plan[i]['c7'],
            'native_event_sign':plan[i]['expected_proxy_event_sign'],
            'agrees_with_analytic_proxy_sign':True,'native_geometry_valid':True,
            'material_sha256':digest,'vertex_count':8455,'face_count':16910})
        stats.append({'index':i,'side':side,'c7':plan[i]['c7'],
            'new_same_call_material_sha256':digest,
            'crossing_sign':plan[i]['expected_proxy_event_sign'],
            'vertex_count':8455,'face_count':16910})
    audit={'schema':'heart-h9-independent-new-side-material-audit-v1',
        'historical_ci_conclusion':'failure','historical_run_id':39123384402,
        'frozen_artifact_sha256':gate.H8F_SHA256,
        'new_native_run_report_sha256':gate.hash_file(native/'report.json'),
        'new_native_samples_reintegrated':4,
        'every_new_side_reproduces_expected_oriented_edge_sign':True,
        'newton_admitted':False,'actual_newton_step_accepted':False,
        'continuous_native_boolean_smooth_stratum_proven':False,
        'final_heart_obj_produced':False,
        'sample_integrity_checked_but_runtime_origin_not_cryptographically_attested':True,
        'original_H8f_binaries_identical_to_new_native':{
            'core':False,'boolean':False,'arithmetic':False},
        'same_binary_across_runs':False,
        'cross_build_same_semantic_baseline_admitted':False,
        'sample_diagnostics':stats,
        'one_sided_independent_moment_jacobian_diagnostics':{
            'schema':'heart-h9-two-sided-finite-jacobian-diagnostics-v1',
            'finite_same_side_pairs':[{'side':'left','indices':[0,1]},
                                      {'side':'right','indices':[2,3]}],
            'newton_admitted':False,
            'continuous_neighborhood_certified':False}}
    write_json(serial/'independent-audit.json',audit)
    return serial


class H9Stage8LiveHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.serial=build_synthetic_structural_fixture(self.root/'serial')

    def verify(self):
        return gate.verify_handoff(self.serial,
           original_archive_sha256=gate.H8F_SHA256,module_sha256=SHA_MAP)

    def test_synthetic_structural_fixture_links_all_four_bytes_but_no_scientific_claim(self):
        result=self.verify()
        self.assertEqual(result['completed_structurally_bound_side_count'],4)
        self.assertTrue(result['structurally_consistent_not_cryptographic_runtime_attestation'])
        self.assertFalse(result['newton_admitted'])
        self.assertFalse(result['accepted_Newton_step_observed'])
        self.assertFalse(result['continuous_neighborhood_proven'])
        self.assertEqual(len(result['materials']),4)

    def test_partial_or_missing_side_is_rejected(self):
        (self.serial/'native/side-02-right-near.json.gz').unlink()
        with self.assertRaisesRegex(gate.HandoffRejected,'MISSING_OR_OVERSIZED_REAL_NATIVE_MATERIAL'):
            self.verify()

    def test_material_byte_mutation_is_rejected_even_when_status_claims_success(self):
        path=self.serial/'native/side-00-left-coarse.json.gz'
        with gzip.open(path,'wb') as stream:
            stream.write(b'{"altered": true}')
        with self.assertRaisesRegex(gate.HandoffRejected,'SIDE_MATERIAL_SHA_EVENT_SIGN_OR_FRAME_NOT_BOUND'):
            self.verify()

    def test_new_report_bytes_must_match_independent_audit_digest(self):
        path=self.serial/'native/report.json'
        data=json.loads(path.read_text())
        data['extra_field']='new data that was not independently verified'
        write_json(path,data)
        with self.assertRaisesRegex(gate.HandoffRejected,'INDEPENDENT_AUDIT_NOT_BOUND_TO_ORIGINAL_RUN_OR_REPORT'):
            self.verify()

    def test_binary_identity_must_match_fresh_build_not_only_producer_report(self):
        different=copy.deepcopy(SHA_MAP);different['_cherchi_core_boolean']='f'*64
        with self.assertRaisesRegex(gate.HandoffRejected,'REAL_NATIVE_PRODUCER_REPORT_NOT_BOUND_TO_W3_BINARIES'):
            gate.verify_handoff(self.serial,original_archive_sha256=gate.H8F_SHA256,
                                module_sha256=different)

    def test_newton_claim_is_never_accepted(self):
        path=self.serial/'independent-audit.json'
        data=json.loads(path.read_text());data['newton_admitted']=True
        write_json(path,data)
        with self.assertRaisesRegex(gate.HandoffRejected,'INDEPENDENT_AUDIT_NOT_BOUND_TO_ORIGINAL_RUN_OR_REPORT'):
            self.verify()

    def test_cross_build_semantic_admission_without_matching_binaries_rejected(self):
        path=self.serial/'independent-audit.json'
        data=json.loads(path.read_text());data['cross_build_same_semantic_baseline_admitted']=True
        write_json(path,data)
        with self.assertRaisesRegex(gate.HandoffRejected,'CROSS_BUILD_BASELINE_EQUIVALENCE_CLAIM_UNSUPPORTED'):
            self.verify()

    def test_side_sign_or_parameter_change_rejected(self):
        path=self.serial/'native/side-03-right-coarse.json'
        data=json.loads(path.read_text());data['native_event_sign']=1
        write_json(path,data)
        with self.assertRaisesRegex(gate.HandoffRejected,'SIDE_MATERIAL_SHA_EVENT_SIGN_OR_FRAME_NOT_BOUND'):
            self.verify()

    def test_corrupted_gzip_crc_is_rejected_even_if_all_checksums_adjusted(self):
        file=self.serial/'native/side-01-left-near.json.gz'
        raw=bytearray(file.read_bytes());raw[-1]^=1
        file.write_bytes(raw)
        digest=gate.hash_file(file)
        meta=self.serial/'native/side-01-left-near.json'
        m=json.loads(meta.read_text());m['material_sha256']=digest;write_json(meta,m)
        audit_file=self.serial/'independent-audit.json'
        a=json.loads(audit_file.read_text());a['sample_diagnostics'][1]['new_same_call_material_sha256']=digest
        write_json(audit_file,a)
        with self.assertRaisesRegex(gate.HandoffRejected,'CORRUPT_NATIVE_GZIP'):
            self.verify()

    def test_missing_execution_stdout_markers_rejected(self):
        (self.serial/'probe.stdout.txt').write_text('FAKE_SUCCESS_WITHOUT_ACTUAL_PROBE_EVENTS\n')
        with self.assertRaisesRegex(gate.HandoffRejected,
                                    'MISSING_REAL_FOUR_SIDE_EXECUTION_AND_INDEPENDENT_AUDIT_LOG_MARKERS'):
            self.verify()

    def test_stage7_launcher_fails_closed_when_child_exits_zero_but_no_artifacts(self):
        out=self.root/'launch'
        artifact=self.root/'artifact';artifact.write_bytes(b'fake artifact for mock test only')
        base={'ready':True,'blocked_reasons':[], 'git_ref':{'head_sha':'0'*40}, 'source_contract':None}
        with patch.object(launch,'check_runtime',return_value=base),\
             patch.object(launch,'sha_file',return_value=launch.HISTORICAL_ARTIFACT_SHA256),\
             patch('h9_frozen_input_gate.validate_pair',return_value={'status':'EXPLICIT_TEST_ONLY_MOCK_NO_BOOLEAN'}),\
             patch.object(launch,'native_module_smoke',return_value=SHA_MAP),\
             patch.object(launch,'verify_build_evidence',return_value='f'*64),\
             patch.object(launch,'source_contract',return_value=None),\
             patch.object(launch,'git_ref',return_value={'head_sha':'0'*40}),\
             patch.object(launch,'run_process_group',return_value=0):
            code=launch.launch(self.root,artifact,self.root/'certificate',out,self.root/'build_evidence')
        self.assertEqual(code,1)
        result=json.loads((out/'launch_result.json').read_text())
        self.assertEqual(result['status'],'FAILED_CLOSED')
        self.assertFalse(result['actual_independent_audit_accepted'])
        self.assertIn('HandoffRejected',result['outer_handoff_error'])
        self.assertFalse(result['newton_admitted'])

    def test_stage7_launcher_calls_crosslink_gate_after_mocked_child(self):
        out=self.root/'launch'
        artifact=self.root/'artifact';artifact.write_bytes(b'fake artifact for mock test only')
        base={'ready':True,'blocked_reasons':[], 'git_ref':{'head_sha':'0'*40}, 'source_contract':None}
        def fake_subprocess(argv,**kwargs):
            # Explicitly synthetic: the child wasn't run; test only verifies
            # that the outer crosslink gate is actually reached.
            build_synthetic_structural_fixture(out/'serial-native')
            return 0
        with patch.object(launch,'check_runtime',return_value=base),\
             patch.object(launch,'sha_file',return_value=launch.HISTORICAL_ARTIFACT_SHA256),\
             patch('h9_frozen_input_gate.validate_pair',return_value={'status':'EXPLICIT_TEST_ONLY_MOCK_NO_BOOLEAN'}),\
             patch.object(launch,'native_module_smoke',return_value=SHA_MAP),\
             patch.object(launch,'verify_build_evidence',return_value='f'*64),\
             patch.object(launch,'source_contract',return_value=None),\
             patch.object(launch,'git_ref',return_value={'head_sha':'0'*40}),\
             patch.object(launch,'run_process_group',side_effect=fake_subprocess):
            code=launch.launch(self.root,artifact,self.root/'certificate',out,self.root/'build_evidence')
        self.assertEqual(code,0)
        result=json.loads((out/'launch_result.json').read_text())
        self.assertTrue(result['actual_independent_audit_accepted'])
        self.assertFalse(result['cryptographic_runtime_origin_attested'])
        self.assertFalse(result['newton_admitted'])
        self.assertEqual(result['outer_handoff']['completed_structurally_bound_side_count'],4)


if __name__ == '__main__':
    unittest.main()
