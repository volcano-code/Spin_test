"""Stage9: real Git worktree state and orphan-free native process timeouts.

No test runs Cherchi, CGAL, or Newton. Real subprocess/grandchild tests are
short and isolated; mock builds exercise ordering/negative admission only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import prepare_h9_pinned_native as build
import run_h9_native_serial as serial
from h9_process_isolation import run_process_group


def call_git(repo,*args):
    return subprocess.run(['git','-C',str(repo),*args],check=True,
                          capture_output=True,text=True).stdout.strip()


class NativeSourceAndTimeoutGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='w3-stage9-')
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)

    def create_minimal_repository(self):
        repo=self.folder/'test-checkout';repo.mkdir()
        call_git(repo,'init','-b',build.BRANCH)
        original=repo/'.github/workflows/heart-h8f-81-point.yml'
        original.parent.mkdir(parents=True)
        original.write_text('name: frozen H8f\non: push\n')
        src=repo/'src/native_demo.cpp'
        src.parent.mkdir();src.write_text('int frozen=1;\n')
        (repo/'CMakeLists.txt').write_text('project(w3)\n')
        call_git(repo,'add','.')
        call_git(repo,'-c','user.email=w3@example.invalid',
                 '-c','user.name=W3 Test','commit','-m','fake W3 checkout (not upstream)')
        frozen_sha=call_git(repo,'hash-object',str(original))
        return repo,original,src,frozen_sha

    def test_real_git_clean_checkout_workflow_identity_and_dirty_source(self):
        repo,wf,src,sha=self.create_minimal_repository()
        with patch.object(build,'H8F_WORKFLOW_BLOB_SHA',sha):
            contract=build.source_contract(repo)
            self.assertEqual(contract['frozen_workflow_blob_sha'],sha)
            self.assertEqual(contract['head_sha'],call_git(repo,'rev-parse','HEAD'))
            (repo/'build/h9-w3-core').mkdir(parents=True)
            (repo/'build/h9-w3-core/build.ninja').write_text('untracked build output\n')
            self.assertEqual(build.source_contract(repo),contract)
            src.write_text('int malicious_local_override=1;\n')
            with self.assertRaisesRegex(build.BuildBlocked,'DIRTY_TRACKED_W3_SOURCE_TREE'):
                build.source_contract(repo)
            call_git(repo,'checkout','--','src/native_demo.cpp')
            self.assertEqual(build.source_contract(repo),contract)
            untracked=repo/'research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/override.py'
            untracked.parent.mkdir(parents=True)
            untracked.write_text('print("unexpected override")\n')
            with self.assertRaisesRegex(build.BuildBlocked,'UNTRACKED_SOURCE_SHADOWING_RISK'):
                build.source_contract(repo)
            untracked.unlink()
            self.assertEqual(build.source_contract(repo),contract)
            wf.write_text('name: modified\n')
            with self.assertRaisesRegex(build.BuildBlocked,'DIRTY_TRACKED_W3_SOURCE_TREE'):
                build.source_contract(repo)
            call_git(repo,'add','.github/workflows/heart-h8f-81-point.yml')
            call_git(repo,'-c','user.email=w3@example.invalid',
                 '-c','user.name=W3 Test','commit','-m','change historical workflow in test repo')
            with self.assertRaisesRegex(build.BuildBlocked,'FROZEN_H8F_WORKFLOW_BLOB_DRIFT'):
                build.source_contract(repo)

    def test_native_preflight_blocks_dirty_source_before_any_compile(self):
        repo,wf,src,sha=self.create_minimal_repository()
        machine={'effective_memory_bytes':32*1024**3,'physical_swap_bytes':0,
                 'physical_mem_bytes':32*1024**3,'mem_available_bytes':31*1024**3}
        eligible_ref={'branch':build.BRANCH,'head_sha':call_git(repo,'rev-parse','HEAD'),
                      'frozen_ancestor_is_ancestor':True}
        with patch.object(build,'H8F_WORKFLOW_BLOB_SHA',sha),\
             patch.object(build,'read_machine_memory',return_value=machine),\
             patch.object(build,'git_ref',return_value=eligible_ref),\
             patch.object(build.shutil,'which',return_value='/usr/bin/verified-tool'):
            self.assertTrue(build.check_runtime(repo)['ready'])
            src.write_text('int dirty_malicious_source=1;\n')
            blocked=build.check_runtime(repo)
            self.assertFalse(blocked['ready'])
            self.assertIn('DIRTY_TRACKED_W3_SOURCE_TREE',blocked['blocked_reasons'])
            with patch.object(build,'run_command',side_effect=AssertionError('NO COMPILE IF DIRTY')):
                code=build.build(repo,self.folder/'blocked-build')
            self.assertEqual(code,2)
            preflight=json.loads((self.folder/'blocked-build/preflight.json').read_text())
            self.assertIsNone(preflight['source_contract'])
            self.assertFalse((self.folder/'blocked-build/build.log').exists())

    def test_outer_success_without_unchanged_source_is_still_rejected(self):
        root=self.folder
        fake_artifact=root/'archive.zip';fake_artifact.write_bytes(b'synthetic only')
        initial={'ready':True,'blocked_reasons':[], 'source_contract':{'head_sha':'a'*40},
                 'git_ref':{'head_sha':'a'*40}}
        with patch.object(build,'check_runtime',return_value=initial),\
             patch.object(build,'sha_file',return_value=build.HISTORICAL_ARTIFACT_SHA256),\
             patch.object(build,'native_module_smoke',return_value={'_make_it_stand':'b'*64}),\
             patch.object(build,'verify_build_evidence',return_value='f'*64),\
             patch.object(build,'run_process_group',return_value=0),\
             patch.object(build,'source_contract',return_value={'head_sha':'unexpected'}) ,\
             patch.object(build,'git_ref',return_value={'head_sha':'a'*40}):
            code=build.launch(root,fake_artifact,root/'cert',root/'run',root/'build')
        self.assertEqual(code,1)
        result=json.loads((root/'run/launch_result.json').read_text())
        self.assertIn('W3_SOURCE_OR_REF_CHANGED_DURING_NATIVE_RUN',result['outer_handoff_error'])
        self.assertFalse(result['actual_independent_audit_accepted'])
        self.assertFalse(result['newton_admitted'])

    def test_verified_manifest_rejects_old_unbound_build_evidence(self):
        root=self.folder
        contract={'schema':'heart-h9-clean-source-contract-v1',
                  'head_sha':'a'*40,'frozen_workflow_blob_sha':build.H8F_WORKFLOW_BLOB_SHA,
                  'tracked_source_clean':True,'untracked_importable_source_absent':True}
        valid={'schema':'heart-h9-native-build-evidence-v1',
               'status':'NATIVE_BINARIES_BUILT_AND_IMPORTABLE_NOT_YET_EVALUATED',
               'source_revisions':{'cherchi':build.CHERCHI_COMMIT,'cgal':build.CGAL_COMMIT},
               'pinned_H8f_workflow_blob_sha256':build.H8F_WORKFLOW_BLOB_SHA,
               'head_after_build':'a'*40, 'module_sha256':{'_make_it_stand':'b'*64}}
        path=root/'build_evidence.json';path.write_text(json.dumps(valid))
        with patch.object(build,'git_ref',return_value={'head_sha':'a'*40}),\
             patch.object(build,'source_contract',return_value=contract):
            with self.assertRaisesRegex(build.BuildBlocked,'LOCAL_NATIVE_BUILD_PROVENANCE_OR_BINARY_SHA_DRIFT'):
                build.verify_build_evidence(root,path,valid['module_sha256'])
            valid['source_contract_before_build']=contract
            valid['source_contract_after_build']=contract
            path.write_text(json.dumps(valid))
            self.assertEqual(len(build.verify_build_evidence(root,path,valid['module_sha256'])),64)
            with patch.object(build,'source_contract',return_value={**contract,'head_sha':'c'*40}):
                with self.assertRaisesRegex(build.BuildBlocked,'LOCAL_NATIVE_BUILD_PROVENANCE_OR_BINARY_SHA_DRIFT'):
                    build.verify_build_evidence(root,path,valid['module_sha256'])

    def test_grouped_native_command_forwards_exit_status(self):
        rc=run_process_group([sys.executable,'-c','raise SystemExit(19)'],timeout=2)
        self.assertEqual(rc,19)
        with self.assertRaisesRegex(ValueError,'INVALID_OR_OVERLONG_NATIVE_SUBPROCESS_TIMEOUT'):
            run_process_group([sys.executable,'-c','pass'],timeout=3601)

    def test_native_timeout_kills_grandchild_before_it_can_write(self):
        marker=self.folder/'orphan_heartbeat.txt'
        script=("import subprocess,sys,time;"
                "subprocess.Popen([sys.executable,'-c',"
                "'import pathlib,time;time.sleep(0.55);pathlib.Path(%r).write_text(\"orphan\")']);"
                "time.sleep(5)" % str(marker))
        with self.assertRaises(subprocess.TimeoutExpired):
            run_process_group([sys.executable,'-c',script],timeout=.12)
        time.sleep(.75)
        self.assertFalse(marker.exists(),'orphan native worker survived parent timeout')

    def test_normal_parent_exit_also_kills_leftover_native_workers(self):
        marker=self.folder/'normal_exit_orphan.txt'
        child=("import pathlib,time;time.sleep(0.5);"
               f"pathlib.Path({str(marker)!r}).write_text('alive')")
        script=f"import subprocess,sys;subprocess.Popen([sys.executable,'-c',{child!r}])"
        self.assertEqual(run_process_group([sys.executable,'-c',script],timeout=3),0)
        time.sleep(.7)
        self.assertFalse(marker.exists(),'native child survived successful parent exit')

    def test_serial_process_cap_is_applied_inside_new_process_session(self):
        with patch.object(serial,'run_process_group',return_value=23) as runner:
            rc=serial.capped_exec([sys.executable,'-c','pass'],3,
                                  self.folder/'stdout.txt',self.folder/'stderr.txt')
        self.assertEqual(rc,23)
        self.assertEqual(runner.call_args.kwargs['timeout'],3)
        self.assertTrue(callable(runner.call_args.kwargs['preexec_fn']))

    def test_outer_launcher_timeout_uses_remaining_time_not_3630s(self):
        root=self.folder
        fake_artifact=root/'archive.zip';fake_artifact.write_bytes(b'synthetic test only')
        ready={'ready':True,'blocked_reasons':[],
               'git_ref':{'head_sha':'a'*40},'source_contract':{'schema':'test'}}
        with patch.object(build,'check_runtime',return_value=ready),\
             patch.object(build,'sha_file',return_value=build.HISTORICAL_ARTIFACT_SHA256),\
             patch.object(build,'native_module_smoke',return_value={'_make_it_stand':'b'*64}),\
             patch.object(build,'verify_build_evidence',return_value='f'*64),\
             patch.object(build,'run_process_group',return_value=17) as grouped:
            code=build.launch(root,fake_artifact,root/'cert',root/'run',root/'build')
        self.assertEqual(code,17)
        passed=grouped.call_args.kwargs['timeout']
        self.assertGreater(passed,0)
        self.assertLessEqual(passed,3600)
        result=json.loads((root/'run/launch_result.json').read_text())
        self.assertFalse(result['newton_admitted'])
        self.assertEqual(result['status'],'FAILED_CLOSED')


if __name__=='__main__':unittest.main()
