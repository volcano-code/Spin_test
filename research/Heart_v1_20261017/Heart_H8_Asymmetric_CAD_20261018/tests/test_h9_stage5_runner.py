"""Stage-5 serial runner resource gates and fail-closed invocation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SRC=Path(__file__).resolve().parents[1]/'source'
sys.path.insert(0,str(SRC))
from run_h9_native_serial import preflight,run_once,BRANCH,MAX_AS_BYTES,MAX_SECONDS

ORIGINAL=os.environ.get('H9_EVIDENCE_ZIP')
CERT=os.environ.get('H9_CROSSING_CERTIFICATE')

class SafeNativeJobTests(unittest.TestCase):
    def test_this_container_is_not_allowed_to_pretend_native_succeeded(self):
        result=preflight(Path('/mnt/data/w3h9_stage5'))
        self.assertEqual(result['status'],'BLOCKED_NO_NATIVE_EVALUATION')
        self.assertEqual(result['max_total_wall_seconds'],3600)
        self.assertEqual(result['process_virtual_memory_cap_bytes'],24*1024**3)
        self.assertIn('PINNED_NATIVE_EXTENSIONS_UNAVAILABLE',result['blockers'])
        self.assertFalse(result['newton_admitted'])

    def test_policy_must_check_branch_and_mem_even_when_extensions_exist(self):
        machine={'effective_memory_bytes':30*1024**3,'physical_swap_bytes':0,
                 'physical_mem_bytes':30*1024**3,'mem_available_bytes':25*1024**3,
                 'container_memory_limit_bytes':None}
        with patch('run_h9_native_serial.read_machine_memory',return_value=machine),\
             patch('run_h9_native_serial.git_ref',return_value={
                 'branch':'main','head_sha':'bad','frozen_ancestor_is_ancestor':False}),\
             patch('run_h9_native_serial.importlib.util.find_spec',return_value=object()):
            result=preflight('/tmp/repo')
        self.assertIn('NOT_A_FROZEN_W3_GIT_CHECKOUT',result['blockers'])
        self.assertFalse(result['newton_admitted'])

    def test_resource_swap_policy_is_fail_closed(self):
        machine={'effective_memory_bytes':32*1024**3,'physical_swap_bytes':1024,
                 'physical_mem_bytes':32*1024**3,'mem_available_bytes':20*1024**3,
                 'container_memory_limit_bytes':None}
        with patch('run_h9_native_serial.read_machine_memory',return_value=machine),\
             patch('run_h9_native_serial.git_ref',return_value={
                 'branch':BRANCH,'head_sha':'x','frozen_ancestor_is_ancestor':True}),\
             patch('run_h9_native_serial.importlib.util.find_spec',return_value=object()):
            result=preflight('/tmp/repo')
        self.assertIn('SWAP_ZERO_RESOURCE_PROTOCOL_VIOLATED',result['blockers'])

    @unittest.skipUnless(ORIGINAL and CERT,'requires actual archive and conditional certificate')
    def test_actual_run_once_writes_blocker_not_fake_material(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'probe'
            code=run_once(ORIGINAL,CERT,output)
            self.assertEqual(code,2)
            data=json.loads((output/'preflight.json').read_text())
            self.assertEqual(data['status'],'BLOCKED_NO_NATIVE_EVALUATION')
            self.assertFalse((output/'native').exists())
            self.assertFalse((output/'independent-audit.json').exists())
            self.assertFalse(data['newton_admitted'])

if __name__=='__main__':unittest.main()
