"""W3 stage8 fail-closed smoke; these are NOT real new Cherchi evaluations."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import prepare_h9_pinned_native as launcher
import verify_h9_live_handoff as gate
import audit_h9_new_native_sides as auditor

class H9Stage8HandoffContracts(unittest.TestCase):
    def test_unverified_archive_not_accepted_as_new_native(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(gate.HandoffRejected,'HISTORICAL_H8F_SHA_CHANGED'):
                gate.verify_handoff(root,original_archive_sha256='f'*64,
                     module_sha256={'_make_it_stand':'a'*64,
                         '_cherchi_core_boolean':'b'*64,
                         '_cherchi_rational_moments':'c'*64})

    def test_missing_serial_result_never_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(gate.HandoffRejected,'MISSING_OR_OVERSIZED_EVIDENCE'):
                gate.verify_handoff(root,original_archive_sha256=gate.H8F,
                     module_sha256={'_make_it_stand':'a'*64,
                         '_cherchi_core_boolean':'b'*64,
                         '_cherchi_rational_moments':'c'*64})

    def test_independent_audit_fast_fails_before_old_81_point_replay(self):
        with tempfile.TemporaryDirectory() as tmp,\
             patch.object(auditor,'archival_data',side_effect=AssertionError('not touched')):
            with self.assertRaisesRegex(ValueError,'NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT'):
                auditor.audit(Path(tmp)/'unreadable-old.zip',Path(tmp)/'missing-cert.json',Path(tmp))

    def test_child_exit_zero_without_material_must_be_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            artifact=tmp/'test-only-archive';artifact.write_bytes(b'synthetic')
            preflight={'ready':True,'blocked_reasons':[],'source_contract':None,'git_ref':{'head_sha':'0'*40}}
            hashes={'_make_it_stand':'a'*64,'_cherchi_core_boolean':'b'*64,
                    '_cherchi_rational_moments':'c'*64}
            with patch.object(launcher,'check_runtime',return_value=preflight),\
                 patch.object(launcher,'sha_file',return_value=launcher.HISTORICAL_ARTIFACT_SHA256),\
                 patch('h9_frozen_input_gate.validate_pair',return_value={'status':'EXPLICIT_TEST_ONLY_MOCK_NO_BOOLEAN'}),\
             patch.object(launcher,'native_module_smoke',return_value=hashes),\
                 patch.object(launcher,'verify_build_evidence',return_value='e'*64),\
                 patch.object(launcher,'source_contract',return_value=None),\
                 patch.object(launcher,'git_ref',return_value={'head_sha':'0'*40}),\
                 patch.object(launcher,'run_process_group',return_value=0):
                code=launcher.launch(tmp,artifact,tmp/'cert',tmp/'output',tmp/'build.json')
            result=json.loads((tmp/'output/launch_result.json').read_text())
            self.assertEqual(code,1)
            self.assertEqual(result['status'],'FAILED_CLOSED')
            self.assertFalse(result['actual_independent_audit_accepted'])
            self.assertFalse(result['newton_admitted'])
            self.assertFalse(result['cryptographic_runtime_origin_attested'])

if __name__=='__main__':unittest.main()
