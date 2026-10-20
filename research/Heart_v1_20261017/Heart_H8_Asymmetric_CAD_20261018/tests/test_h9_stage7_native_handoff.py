"""Stage7 native build handoff: ensure no unpinned builds or pretend Cherchi calls."""
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

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import prepare_h9_pinned_native as build


class H9Stage7NativeHandoffContracts(unittest.TestCase):
    def test_plan_reuses_exact_frozen_reference_pins_and_compiler_flags(self):
        manifest=build.build_plan(Path('/tmp/Spin_test'))
        self.assertEqual(manifest['source_references']['cherchi'],
                         '7bd6c2697695f555f9a15d7e154e084d841316f0')
        self.assertEqual(manifest['source_references']['cgal'],
                         'f7c3c8212b56c0d6dae63787efc99093f4383415')
        self.assertEqual(manifest['historical_h8f_workflow_blob_sha'],
                         'a6dda4d04998f1244ce0a7f80991d6198c037cdb')
        self.assertEqual(manifest['maximum_compiler_parallelism'],2)
        self.assertLess(manifest['max_build_seconds'],3600)
        self.assertEqual(manifest['max_native_job_seconds'],3600)
        self.assertEqual(manifest['boost_abi_policy'],
                         'SHARED_LIB_ONLY_NO_SYSTEM_STATIC_ARCHIVE_MUTATION')
        args=[a for row in manifest['steps'] for a in row['argv']]
        for needed in ('-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON',
                       '-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON',
                       '-DMAKE_IT_STAND_FILTERED_BOUNDARY_KERNEL=ON',
                       '-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON'):
            self.assertIn(needed,args)
        self.assertNotIn('sudo',args)
        self.assertNotIn('main',args)
        self.assertTrue(manifest['no_newton_claim'])

    def test_real_current_container_rejected_before_git_and_compilers(self):
        status=build.check_runtime(Path('/mnt/data/not-a-checkout'))
        self.assertFalse(status['ready'])
        self.assertIn('LESS_THAN_24GIB_EFFECTIVE_MEMORY',status['blocked_reasons'])
        self.assertIn('NOT_FROZEN_W3_BRANCH_OR_ANCESTOR',status['blocked_reasons'])

    def test_wrong_branch_even_on_large_machine_is_rejected(self):
        machine={'effective_memory_bytes':24*1024**3,
                 'physical_swap_bytes':0,'physical_mem_bytes':32*1024**3,
                 'mem_available_bytes':24*1024**3,'container_memory_limit_bytes':24*1024**3}
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td);(repo/'.git').mkdir();(repo/'CMakeLists.txt').write_text('project(p)')
            with patch.object(build,'read_machine_memory',return_value=machine),\
                 patch.object(build,'git_ref',return_value={
                     'branch':'main','head_sha':'bad','frozen_ancestor_is_ancestor':False}),\
                 patch.object(build.shutil,'which',return_value='/usr/bin/tool'):
                self.assertIn('NOT_FROZEN_W3_BRANCH_OR_ANCESTOR',
                              build.check_runtime(repo)['blocked_reasons'])

    def test_python_path_points_to_only_local_builds_and_python_package(self):
        repo=Path('/safe/W3')
        env=build.python_path_env(repo,{'PYTHONPATH':'/trusted/extensions'})
        self.assertEqual(env['PYTHONPATH'].split(os.pathsep)[:3],
            ['/safe/W3/python','/safe/W3/build/h9-w3-core/python',
             '/safe/W3/build/h9-w3-cherchi/python'])
        self.assertTrue(env['PYTHONPATH'].endswith('/trusted/extensions'))
        self.assertEqual(env['OMP_NUM_THREADS'],'1')

    def test_boost_rewrite_only_changes_build_ninja_not_system(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'build.ninja'
            path.write_text('IN /usr/lib/x86_64-linux-gnu/libboost_thread.a '
                            '/usr/lib/x86_64-linux-gnu/libboost_system.a')
            originals=[]
            original_exists=Path.exists
            def mock_exists(p):
                if str(p).endswith('.so'):
                    originals.append(str(p))
                    return True
                return original_exists(p)
            with patch.object(Path,'exists',mock_exists):
                self.assertEqual(build.boost_shared_rewrite(path),2)
            self.assertIn('libboost_system.so',path.read_text())
            self.assertIn('libboost_thread.so',path.read_text())
            self.assertTrue(all(path.startswith('/usr/lib') for path in originals))

    def test_command_runner_rejects_nonzero_without_shell_or_silent_success(self):
        with tempfile.TemporaryDirectory() as td:
            with (Path(td)/'log.txt').open('w') as log:
                with self.assertRaisesRegex(build.BuildBlocked,'BUILD_SUBPROCESS_FAILED:9'):
                    build.run_command([sys.executable,'-c','raise SystemExit(9)'],8,log)
                self.assertIn('EXEC ',(Path(td)/'log.txt').read_text())

    def test_absent_untrusted_build_manifest_cannot_approve_native_launch(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)
            proof=repo/'build.json'
            legitimate={
                'schema':'heart-h9-native-build-evidence-v1',
                'status':'NATIVE_BINARIES_BUILT_AND_IMPORTABLE_NOT_YET_EVALUATED',
                'source_revisions':{'cherchi':build.CHERCHI_COMMIT,'cgal':build.CGAL_COMMIT},
                'pinned_H8f_workflow_blob_sha256':build.H8F_WORKFLOW_BLOB_SHA,
                'head_after_build':'f'*40,
                'module_sha256':{'_make_it_stand':'a'*64}}
            contract={'schema':'heart-h9-clean-source-contract-v1','head_sha':'f'*40,
                      'frozen_workflow_blob_sha':build.H8F_WORKFLOW_BLOB_SHA,
                      'tracked_source_clean':True,'untracked_importable_source_absent':True}
            legitimate['source_contract_before_build']=contract
            legitimate['source_contract_after_build']=contract
            proof.write_text(json.dumps(legitimate))
            with patch.object(build,'git_ref',return_value={'head_sha':'f'*40}),\
                 patch.object(build,'source_contract',return_value=contract):
                self.assertEqual(len(build.verify_build_evidence(repo,proof,legitimate['module_sha256'])),64)
                with self.assertRaisesRegex(build.BuildBlocked,'LOCAL_NATIVE_BUILD_PROVENANCE_OR_BINARY_SHA_DRIFT'):
                    build.verify_build_evidence(repo,proof,{'_make_it_stand':'b'*64})
                forged=copy.deepcopy(legitimate);forged['source_revisions']['cgal']='invalid'
                proof.write_text(json.dumps(forged))
                with self.assertRaisesRegex(build.BuildBlocked,'LOCAL_NATIVE_BUILD_PROVENANCE_OR_BINARY_SHA_DRIFT'):
                    build.verify_build_evidence(repo,proof,legitimate['module_sha256'])

    def test_native_extension_must_originate_from_new_w3_build_and_match_sha(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            paths={
                '_make_it_stand':root/'build/h9-w3-core/python/_make_it_stand.cpython.so',
                '_cherchi_core_boolean':root/'build/h9-w3-cherchi/python/_cherchi_core_boolean.cpython.so',
                '_cherchi_rational_moments':root/'build/h9-w3-cherchi/python/_cherchi_rational_moments.cpython.so',
            }
            for name,path in paths.items():
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(name.encode())
            info={'paths':{k:str(v) for k,v in paths.items()},
                  'sha256':{k:build.sha_file(v) for k,v in paths.items()}}
            self.assertEqual(build.validate_module_locations(root,info),info['sha256'])
            wrong=copy.deepcopy(info)
            foreign=root/'outside/_make_it_stand.cpython.so';foreign.parent.mkdir()
            foreign.write_bytes(b'other compiled extension')
            wrong['paths']['_make_it_stand']=str(foreign)
            wrong['sha256']['_make_it_stand']=build.sha_file(foreign)
            with self.assertRaisesRegex(build.BuildBlocked,
                                       'NATIVE_EXTENSION_LOADED_OUTSIDE_FRESH_W3_BUILD'):
                build.validate_module_locations(root,wrong)
            changed=copy.deepcopy(info)
            changed['sha256']['_cherchi_core_boolean']='a'*64
            with self.assertRaisesRegex(build.BuildBlocked,
                                       'NATIVE_BINARY_HASH_NOT_REPRODUCIBLE'):
                build.validate_module_locations(root,changed)

    def test_build_attempt_in_small_container_returns_two_and_never_builds(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out'
            with patch.object(build,'run_command',side_effect=AssertionError('must not launch')):
                result=build.build('/mnt/data/not-a-checkout',out)
            self.assertEqual(result,2)
            self.assertFalse((out/'build.log').exists())
            self.assertEqual(json.loads((out/'preflight.json').read_text())['ready'],False)
            self.assertFalse((out/'build_evidence.json').exists())

    def test_run_attempt_in_small_container_refuses_without_claimed_native_result(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'out'
            with patch.object(build,'native_module_smoke',side_effect=AssertionError('no native import')):
                code=build.launch('/mnt/data/not-a-checkout',Path(td)/'fake-artifact',
                                  Path(td)/'fake-cert',out,Path(td)/'fake-build.json')
            self.assertEqual(code,2)
            self.assertFalse((out/'launch_result.json').exists())
            self.assertEqual(json.loads((out/'launch_preflight.json').read_text())['status'],
                             'BLOCKED_NO_NATIVE_EVALUATION')

if __name__=='__main__':unittest.main()
