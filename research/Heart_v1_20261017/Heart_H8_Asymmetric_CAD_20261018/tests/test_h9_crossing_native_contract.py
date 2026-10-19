"""H9 guarded real-native event probe contract; no synthetic Cherchi returns."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from probe_h9_crossing_sides_live import native_plan,load_native_or_reject,run

ORIGINAL=os.environ.get('H9_EVIDENCE_ZIP')
CERT=os.environ.get('H9_CROSSING_CERTIFICATE')


class NativeCrossingSafetyTests(unittest.TestCase):
    @unittest.skipUnless(CERT,'requires new exact edge-interior certificate')
    def test_points_surround_root_and_are_serial(self):
        cert=json.loads(Path(CERT).read_text())
        plan=native_plan(cert)
        self.assertEqual([p['side'] for p in plan],
                         ['left-coarse','left-near','right-near','right-coarse'])
        self.assertEqual([p['index'] for p in plan],list(range(4)))
        self.assertEqual([p['expected_proxy_event_sign'] for p in plan],[1,1,-1,-1])
        center=cert['surrogate_root_midpoint_display']
        for item in plan:
            self.assertGreater(item['c7'],1.5e-6)
            self.assertLess(item['c7'],3e-6)
        self.assertTrue(all(plan[i]['c7']<center for i in (0,1)))
        self.assertTrue(all(plan[i]['c7']>center for i in (2,3)))

    @unittest.skipUnless(CERT,'requires new exact edge-interior certificate')
    def test_newton_eligible_forgery_denied(self):
        cert=json.loads(Path(CERT).read_text())
        cert['newton_admitted']=True
        with self.assertRaisesRegex(ValueError,'NOT_CERTIFIED_OFFLINE_PROXY_EVENT_CONTRACT'):
            native_plan(cert)
        cert['newton_admitted']=False
        cert['actual_in_between_native_boolean_samples_evaluated']=4
        with self.assertRaisesRegex(ValueError,'NOT_CERTIFIED_OFFLINE_PROXY_EVENT_CONTRACT'):
            native_plan(cert)

    def test_native_backend_missing_cannot_fallback_to_proxy(self):
        with patch.dict(sys.modules, {'_make_it_stand':None}):
            with self.assertRaisesRegex(RuntimeError,'REAL_PINNED_NATIVE_CHERCHI_MISSING_NO_SURROGATE_FALLBACK'):
                load_native_or_reject()

    @unittest.skipUnless(ORIGINAL and CERT,'requires original ZIP and new certificate')
    def test_runtime_failure_records_zero_real_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'native'
            with patch.dict(sys.modules,{'_make_it_stand':None}):
                with self.assertRaisesRegex(RuntimeError,'REAL_PINNED_NATIVE_CHERCHI_MISSING_NO_SURROGATE_FALLBACK'):
                    run(Path(ORIGINAL),Path(CERT),out)
            f=json.loads((out/'failure.json').read_text())
            self.assertEqual(f['new_real_native_calls'],0)
            self.assertEqual(f['status'],'FAILED_NO_NEWTON_ADMISSION')
            self.assertEqual(f['failed_stage'],'IMPORT_REAL_PINNED_NATIVE_CHERCHI')
            self.assertFalse(f['newton_admitted'])
            self.assertFalse((out/'report.json').exists())

    @unittest.skipUnless(ORIGINAL and CERT,'requires original ZIP and new certificate')
    def test_mutated_certificate_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as temp:
            cert=json.loads(Path(CERT).read_text())
            cert['surrogate_root_midpoint_display']+=1e-8
            file=Path(temp)/'fake.json'
            file.write_text(json.dumps(cert))
            out=Path(temp)/'denied'
            with self.assertRaisesRegex(ValueError,'CERTIFICATE_CONTENT_DIFFERS_FROM_RECOMPUTED_REAL_ARCHIVE_PROOF'):
                run(Path(ORIGINAL),file,out)
            result=json.loads((out/'failure.json').read_text())
            self.assertEqual(result['new_real_native_calls'],0)
            self.assertFalse(result['newton_admitted'])


if __name__=='__main__':unittest.main()
