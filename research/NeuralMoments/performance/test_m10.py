"""M10 tests exercise real Git/resource/archive guards; fake .so never counts as native."""
from __future__ import annotations

from hashlib import sha256
import importlib.machinery
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from m10_native_host_runner import (
    ARCHIVE_SHA, BRANCH, MAX_MEMORY, MAX_SECONDS, NATIVE,
    archive_identity, execute, module_inventory, native_import_probe,
    preflight, repo_identity, _child_limits, _memory_limit, _swap_guard,
    _native_job_lock,
)
from m5_native_call_instrumentation import SOURCE_BLOB

ROOT=Path(__file__).resolve().parents[3]
H8C=Path(os.environ.get('W1_M8_H8C_ARCHIVE', '/mnt/data/h8c-reference-39118951636.zip'))


def git(directory,*args):
    r=subprocess.run(['git','-C',str(directory),*args],capture_output=True,
                     text=True,timeout=10,check=True)
    return r.stdout.strip()


class M10Guards(unittest.TestCase):
    def test_actual_archived_material_and_request_pinned(self):
        self.assertTrue(H8C.is_file())
        result=archive_identity(H8C)
        self.assertEqual(result['zip_sha256'],ARCHIVE_SHA)
        self.assertEqual(result['historical_material_vertices'],8455)
        self.assertEqual(result['historical_material_faces'],16910)
        self.assertTrue(result['nonauthor_cad_only'])

    def test_drifted_archive_is_rejected_before_native_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'wrong.zip';p.write_bytes(H8C.read_bytes()[:256])
            with self.assertRaisesRegex(ValueError,'M10_H8C_ARCHIVE_SHA_DRIFT'):
                archive_identity(p)

    def test_git_current_branch_and_ancestor_real_local_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            git(p,'init','-b',BRANCH)
            (p/'example.txt').write_text('example\n')
            git(p,'add','example.txt')
            git(p,'-c','user.email=unit@example.invalid','-c','user.name=W1 Unit',
                'commit','-m','unrelated local mock checkout')
            root_commit=git(p,'rev-parse','HEAD')
            with patch('m10_native_host_runner.FREEZE',root_commit):
                facts=repo_identity(p)
                self.assertEqual(facts['branch'],BRANCH)
                self.assertEqual(facts['head'],root_commit)
            with self.assertRaisesRegex(ValueError,'M10_FROZEN_ANCESTOR_NOT_VERIFIED'):
                repo_identity(p)
            git(p,'checkout','-b','main')
            with patch('m10_native_host_runner.FREEZE',root_commit):
                with self.assertRaisesRegex(ValueError,'M10_W1_ONLY_BRANCH_REQUIRED'):
                    repo_identity(p)

    def test_plain_directory_cannot_claim_w1(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'M10_FULL_GIT_CHECKOUT_REQUIRED'):
                repo_identity(Path(tmp))

    def test_real_native_required_not_python_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);modules=root/'build/heart-cloud-core/python';modules.mkdir(parents=True)
            for n in NATIVE: (modules/(n+'.py')).write_text('def fake():pass\n')
            found=module_inventory(root)
            self.assertTrue(all(info['status']=='NOT_FOUND' for info in found.values()))

    def test_strict_extension_suffix_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);modules=root/'build/heart-cloud-core/python';modules.mkdir(parents=True)
            suffix=importlib.machinery.EXTENSION_SUFFIXES[0]
            for n in NATIVE: (modules/(n+suffix)).write_bytes(b'not an extension')
            found=module_inventory(root)
            self.assertEqual(set(found),set(NATIVE))
            self.assertTrue(all(info['status']=='FOUND' for info in found.values()))
            with self.assertRaisesRegex(RuntimeError,'M10_NATIVE_EXTENSION_LOAD_OR_ABI_FAILURE'):
                native_import_probe(root,[],found,_memory_limit()['process_address_space_cap_bytes'])

    def test_duplicate_compiled_candidates_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for dirname in ('heart-cloud-core','heart-cloud-cherchi'):
                p=root/'build'/dirname/'python';p.mkdir(parents=True)
                (p/('_make_it_stand'+importlib.machinery.EXTENSION_SUFFIXES[0])).write_bytes(b'\x7fELFfake')
            self.assertEqual(module_inventory(root)['_make_it_stand']['status'],'AMBIGUOUS')

    def test_actual_memory_and_swap_contract(self):
        m=_memory_limit()
        self.assertLessEqual(m['process_address_space_cap_bytes'],MAX_MEMORY)
        self.assertGreaterEqual(m['physical_memory_bytes'],m['process_address_space_cap_bytes'])
        self.assertTrue(_swap_guard())

    def test_address_space_guard_never_raises_limit(self):
        # Never change the parent process RLIMITs; child only.
        from unittest.mock import patch
        with patch('m10_native_host_runner.resource.getrlimit',return_value=(resource_unlimited(),resource_unlimited())), \
             patch('m10_native_host_runner.resource.setrlimit') as setlimit:
            _child_limits(MAX_MEMORY*2)
        self.assertEqual(setlimit.call_args[0][1],(MAX_MEMORY,MAX_MEMORY))

    def test_missing_checkout_reports_all_prerequisite_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=preflight(Path(tmp),H8C)
            self.assertEqual(report['state'],'BLOCKED')
            self.assertIn('git',report['blockers'])
            self.assertIn('source',report['blockers'])
            self.assertIn('native_modules',report['blockers'])
            self.assertIn('native_abi_import',report['blockers'])
            self.assertEqual(report['checks']['archive']['status'],'PASS')
            self.assertIsNone(report['full_solver_speedup'])
            self.assertEqual(report['native_boolean_calls'],0)

    def test_real_blocked_execution_does_not_start_any_native_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'run'
            with patch('m10_native_host_runner._execute') as execute_job:
                outcome=execute(root,H8C,output)
            execute_job.assert_not_called()
            self.assertEqual(outcome['state'],'BLOCKED')
            failure=json.loads((output/'failure.json').read_text())
            self.assertFalse(failure['executed_m5'])
            self.assertFalse(failure['executed_m9'])
            self.assertIsNone(failure['full_solver_speedup'])
            self.assertFalse((output/'native_evaluation_summary.json').exists())

    def test_output_is_exclusive_and_prior_failure_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);output=root/'results'
            execute(root,H8C,output)
            with self.assertRaises(FileExistsError): execute(root,H8C,output)

    def test_native_job_lock_blocks_duplicate_w1_process(self):
        with _native_job_lock():
            with self.assertRaisesRegex(RuntimeError,'M10_ANOTHER_W1_NATIVE_JOB_ALREADY_RUNNING'):
                with _native_job_lock(): pass
        with _native_job_lock():
            pass

    def test_native_report_missing_after_success_exit_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ready=dict(state='READY_FOR_REAL_NATIVE_ABBA',
                       checks={'memory':{'status':'PASS','details':{
                           'process_address_space_cap_bytes':MAX_MEMORY}}},blockers=[])
            with patch('m10_native_host_runner.preflight',return_value=ready), \
                 patch('m10_native_host_runner._execute',return_value=0) as launch:
                with self.assertRaisesRegex(RuntimeError,'M10_NATIVE_STAGE_HAS_NO_SCIENTIFIC_REPORT'):
                    execute(root,H8C,root/'missing_report')
            self.assertEqual(launch.call_count,1)
            failure=json.loads((root/'missing_report/failure.json').read_text())
            self.assertEqual(failure['failed_stage'],'m5')
            self.assertFalse((root/'missing_report/native_evaluation_summary.json').exists())

    def test_native_nonzero_exit_stops_second_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ready=dict(state='READY_FOR_REAL_NATIVE_ABBA',
                       checks={'memory':{'status':'PASS','details':{
                           'process_address_space_cap_bytes':MAX_MEMORY}}},blockers=[])
            with patch('m10_native_host_runner.preflight',return_value=ready), \
                 patch('m10_native_host_runner._execute',return_value=13) as launch:
                with self.assertRaisesRegex(RuntimeError,'M10_NATIVE_STAGE_EXIT_NONZERO:m5:13'):
                    execute(root,H8C,root/'native_exit')
            self.assertEqual(launch.call_count,1)
            failure=json.loads((root/'native_exit/failure.json').read_text())
            self.assertEqual(len(failure['jobs']),1)
            self.assertIsNone(failure['complete_solver_speedup'])

    def test_native_lock_conflict_has_failure_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ready=dict(state='READY_FOR_REAL_NATIVE_ABBA',
                       checks={'memory':{'status':'PASS','details':{
                           'process_address_space_cap_bytes':MAX_MEMORY}}},blockers=[])
            with _native_job_lock():
                with patch('m10_native_host_runner.preflight',return_value=ready), \
                     patch('m10_native_host_runner._execute') as launch:
                    with self.assertRaisesRegex(RuntimeError,'ALREADY_RUNNING'):
                        execute(root,H8C,root/'locked')
                    launch.assert_not_called()
            failure=json.loads((root/'locked/failure.json').read_text())
            self.assertEqual(failure['status'],'FAILED_BEFORE_NATIVE_COMPLETION')
            self.assertFalse((root/'locked/native_evaluation_summary.json').exists())

    def test_job_limit_is_one_hour_not_default_to_longer(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'M10_PER_JOB_SECONDS_LIMIT'):
                execute(tmp,H8C,Path(tmp)/'long',max_seconds=3601)
            with self.assertRaisesRegex(ValueError,'M10_PER_JOB_SECONDS_LIMIT'):
                execute(tmp,H8C,Path(tmp)/'fake',max_seconds=1.0)
            self.assertEqual(MAX_SECONDS,3600)


def resource_unlimited():
    import resource
    return resource.RLIM_INFINITY


if __name__=='__main__':
    unittest.main()
