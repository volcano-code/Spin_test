"""Stage10 real historical archive / conditional certificate gate regression.

Mocks are explicitly control-flow-only; no synthetic packet is a Cherchi sample.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import h9_frozen_input_gate as gate
import prepare_h9_pinned_native as handoff

ARCHIVE = Path(os.getenv('H9_EVIDENCE_ZIP', '/mnt/data/w3-h8f-evidence-12135528290.zip'))
CERT = Path(os.getenv('H9_CROSSING_CERTIFICATE',
                       '/mnt/data/w3h9_stage4/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json'))



class H9FrozenInputPurePythonContracts(unittest.TestCase):
    def test_duplicate_keys_are_never_silently_overwritten(self):
        with self.assertRaisesRegex(gate.FrozenInputRejected, 'DUPLICATE_CERTIFICATE_JSON_KEY'):
            json.loads('{"run_id":39123384402,"run_id":999}',object_pairs_hook=gate.unique_keys)

    def test_nonfinite_json_constants_are_never_accepted(self):
        with self.assertRaisesRegex(gate.FrozenInputRejected, 'NON_FINITE_CERTIFICATE_JSON_CONSTANT'):
            json.loads('{"newton_admitted":NaN}',parse_constant=gate.finite_json_constant)

    def test_fake_short_archive_rejected_before_any_material_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            fake=Path(folder)/'fake.zip'; fake.write_bytes(b'fabricated')
            with patch.object(gate,'solve',side_effect=AssertionError('must not replay')):
                with self.assertRaisesRegex(gate.FrozenInputRejected,
                                            'ABSENT_OR_UNEXPECTED_SIZE_H8F_SOURCE_ARCHIVE'):
                    gate.validate_pair(fake,Path(folder)/'missing-cert.json')

    def test_fake_input_emits_fail_closed_evidence_without_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); fake=root/'fabricated.zip'; fake.write_bytes(b'not historical')
            code=gate.run_inputs(fake,root/'fake-cert.json',root/'out')
            self.assertEqual(code,2)
            self.assertFalse((root/'out/input_gate.json').exists())
            failure=json.loads((root/'out/failure.json').read_text())
            self.assertEqual(failure['new_real_native_calls'],0)
            self.assertFalse(failure['newton_admitted'])


@unittest.skipUnless(ARCHIVE.is_file() and CERT.is_file(),
                     'requires original immutable H8f Actions ZIP and H9 certificate')
class H9FrozenInputAdmissionTests(unittest.TestCase):
    def test_01_real_81_point_archive_replay_and_four_c7_values(self):
        report = gate.validate_pair(ARCHIVE, CERT)
        self.assertEqual(report['historical_run_conclusion'], 'failure')
        self.assertEqual(report['source_artifact_sha256'], gate.ZIP_SHA)
        self.assertTrue(report['certificate_recomputed_from_frozen_actual_material'])
        pts = report['four_new_native_probe_plan']
        self.assertEqual([p['side'] for p in pts],
                         ['left-coarse','left-near','right-near','right-coarse'])
        self.assertEqual([p['expected_proxy_event_sign'] for p in pts],[1,1,-1,-1])
        self.assertTrue(all(1.5e-6 < p['c7'] < 3e-6 for p in pts))
        self.assertEqual(report['four_new_native_calls_completed_by_this_gate'], 0)
        self.assertFalse(report['newton_admitted'])

    def test_02_tampered_cert_claiming_newton_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder)/'forged.json'
            payload = json.loads(CERT.read_text())
            payload['newton_admitted'] = True
            fake.write_text(json.dumps(payload))
            with self.assertRaisesRegex(gate.FrozenInputRejected,
                                        'CERTIFICATE_DOES_NOT_MATCH_REAL_H8F_REPLAY'):
                gate.validate_pair(ARCHIVE,fake)

    def test_03_duplicate_key_certificate_rejected_even_if_values_match(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder)/'duplicate.json'
            payload = CERT.read_text().strip()
            self.assertTrue(payload.startswith('{'))
            fake.write_text('{"schema":"first",' + payload[1:])
            with self.assertRaisesRegex(gate.FrozenInputRejected,
                                        'DUPLICATE_CERTIFICATE_JSON_KEY'):
                gate.validate_pair(ARCHIVE,fake)

    def test_04_modified_original_zip_is_rejected_before_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder)/'edited.zip'
            data = ARCHIVE.read_bytes()
            fake.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
            with patch.object(gate, 'solve', side_effect=AssertionError('no expensive replay')):
                with self.assertRaisesRegex(gate.FrozenInputRejected,
                                            'FROZEN_H8F_ARCHIVE_SHA256_CHANGED'):
                    gate.validate_pair(fake,CERT)

    def test_05_cli_inputs_phase_writes_reproducible_success_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'input-evidence'
            command = [sys.executable, str(Path(handoff.__file__)),
                       '--phase','inputs','--artifact',str(ARCHIVE),
                       '--certificate',str(CERT),'--output',str(output)]
            proc = subprocess.run(command,capture_output=True,text=True,timeout=25)
            self.assertEqual(proc.returncode,0,proc.stderr)
            result = json.loads((output/'input_gate.json').read_text())
            self.assertEqual(result['status'],'FROZEN_INPUT_READY_FOR_NATIVE_ATTEMPT_ONLY')
            self.assertFalse((output/'failure.json').exists())
            self.assertFalse(result['actual_native_boolean_result_available'])

    def test_06_bad_certificate_produces_only_failure_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder)/'broken.json'
            bad.write_text(CERT.read_text().replace('\"newton_admitted\": false', '\"newton_admitted\": NaN'))
            output = Path(folder)/'blocked'
            self.assertEqual(gate.run_inputs(ARCHIVE,bad,output),2)
            report=json.loads((output/'failure.json').read_text())
            self.assertIn('NON_FINITE_CERTIFICATE_JSON_CONSTANT',report['error'])
            self.assertEqual(report['new_real_native_calls'],0)
            self.assertFalse((output/'input_gate.json').exists())

    def test_07_outer_launcher_rejects_bad_certificate_before_native_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'launch'
            bad=root/'invalid.json'
            payload=json.loads(CERT.read_text());payload['newton_admitted']=True
            bad.write_text(json.dumps(payload))
            state={'ready':True,'blocked_reasons':[],
                   'source_contract':{'head_sha':'a'*40},'git_ref':{'head_sha':'a'*40}}
            with patch.object(handoff,'check_runtime',return_value=state),\
                 patch.object(handoff,'native_module_smoke',
                              side_effect=AssertionError('never import native on bad certificate')):
                status=handoff.launch(root,ARCHIVE,bad,out,root/'fake-build.json')
            self.assertEqual(status,2)
            decision=json.loads((out/'launch_preflight.json').read_text())
            self.assertEqual(decision['status'],'FROZEN_INPUT_GATE_REJECTED')
            self.assertFalse(decision['newton_admitted'])
            self.assertFalse((out/'serial-native').exists())

    def test_08_valid_inputs_survive_to_real_native_dependency_barrier(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);out=root/'launch'
            state={'ready':True,'blocked_reasons':[],
                   'source_contract':{'head_sha':'a'*40},'git_ref':{'head_sha':'a'*40}}
            with patch.object(handoff,'check_runtime',return_value=state),\
                 patch.object(handoff,'native_module_smoke',
                              side_effect=handoff.BuildBlocked('NO_REAL_NATIVE_EXTENSIONS')):
                status=handoff.launch(root,ARCHIVE,CERT,out,root/'fake-build.json')
            self.assertEqual(status,2)
            decision=json.loads((out/'launch_preflight.json').read_text())
            self.assertEqual(decision['status'],'NATIVE_BINARY_NOT_IMPORTABLE')
            self.assertTrue(decision['verified_input_gate']['certificate_recomputed_from_frozen_actual_material'])
            self.assertEqual(decision['verified_input_gate']['four_new_native_calls_completed_by_this_gate'],0)
            self.assertFalse((out/'serial-native').exists())


if __name__=='__main__':
    unittest.main()
