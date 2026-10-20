"""W1 M14 contract tests; synthetic receipts are never native measurements."""
from __future__ import annotations
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import m10_native_host_runner as m10
import m13_pinned_native_build as m13
import m14_native_build_custody as m14


def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,check=True)
    return p.stdout.strip()


class TestTrackedCheckoutProvenance(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='m14-local-git-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        subprocess.run(['git','init','-q','-b',m10.BRANCH,str(self.root)],check=True)
        git(self.root,'config','user.name','W1 synthetic test')
        git(self.root,'config','user.email','w1-synthetic@example.invalid')
        x=self.root/'src/engine.cpp';x.parent.mkdir()
        x.write_text('int main() {return 0;}\n')
        (self.root/'research/NeuralMoments/performance').mkdir(parents=True)
        git(self.root,'add','.')
        git(self.root,'commit','-q','-m','synthetic freeze')
        self.freeze=git(self.root,'rev-parse','HEAD')
        self.patcher=mock.patch.object(m10,'FREEZE',self.freeze)
        self.patcher.start();self.addCleanup(self.patcher.stop)
        self.identity=mock.patch.object(m10,'_source_identity',return_value={'git_blob_sha1':'synthetic-test-only'})
        self.identity.start();self.addCleanup(self.identity.stop)

    def test_clean_synthetic_w1_checkout_passes(self):
        report=m14.protected_checkout(self.root)
        self.assertTrue(report['tracked_production_tree_clean'])
        self.assertTrue(report['critical_paths_frozen'])

    def test_performance_only_committed_changes_pass(self):
        p=self.root/'research/NeuralMoments/performance/check.py';p.write_text('x=1\n')
        git(self.root,'add','.')
        git(self.root,'commit','-q','-m','W1 internal tool')
        self.assertTrue(m14.protected_checkout(self.root)['critical_paths_frozen'])

    def test_production_commit_drifts_from_freeze(self):
        x=self.root/'src/engine.cpp';x.write_text('int main() {return 1;}\n')
        git(self.root,'add','.')
        git(self.root,'commit','-q','-m','unauthorized production mutation')
        with self.assertRaisesRegex(ValueError,'M14_COMMIT_OUTSIDE_W1_EXCLUSIVE_SCOPE'):
            m14.protected_checkout(self.root)

    def test_other_window_committed_changes_rejected(self):
        p=self.root/'research/NeuralMoments/teacher/teacher.py'
        p.parent.mkdir(parents=True)
        p.write_text('forbidden = True\n')
        git(self.root,'add','.')
        git(self.root,'commit','-q','-m','synthetic accidental W2 edit')
        with self.assertRaisesRegex(ValueError,'M14_COMMIT_OUTSIDE_W1_EXCLUSIVE_SCOPE'):
            m14.protected_checkout(self.root)

    def test_unstaged_production_modified(self):
        (self.root/'src/engine.cpp').write_text('int main() {return 12;}\n')
        with self.assertRaisesRegex(ValueError,'M14_DIRTY_UNSTAGED_PRODUCTION_SOURCE'):
            m14.protected_checkout(self.root)

    def test_staged_production_modified(self):
        (self.root/'src/engine.cpp').write_text('int main() {return 2;}\n')
        git(self.root,'add','src/engine.cpp')
        with self.assertRaisesRegex(ValueError,'M14_DIRTY_STAGED_PRODUCTION_SOURCE'):
            m14.protected_checkout(self.root)

    def test_heartbeat_workflow_dirty_fails(self):
        p=self.root/'.github/workflows/native.yml';p.parent.mkdir(parents=True)
        p.write_text('name: mock\n')
        git(self.root,'add','.')
        git(self.root,'commit','-q','-m','unauthorized workflow')
        with self.assertRaisesRegex(ValueError,'M14_COMMIT_OUTSIDE_W1_EXCLUSIVE_SCOPE'):
            m14.protected_checkout(self.root)


class TestSyntheticBuildCustody(unittest.TestCase):
    """All modules and receipts here are SYNTHETIC bytes; mock native verifier."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='m14-mock-native-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.artifacts=self.root/'m13';self.artifacts.mkdir()
        self.archive=self.root/'auth-h8.zip';self.archive.write_bytes(b'SYNTHETIC NOT REAL H8')
        self.core=self.root/m13.BUILD_CORE_REL;self.cherchi=self.root/m13.BUILD_CHERCHI_REL
        (self.core/'python').mkdir(parents=True);(self.cherchi/'python').mkdir(parents=True)
        self.config={
            'branch':m10.BRANCH,'head':'a'*40,'frozen_ancestor':m10.FREEZE,
            'production_source':{'git_blob_sha1':'synthetic-test'},
            'critical_paths_frozen':True,'tracked_production_tree_clean':True,
        }
        self.sources={'pinned':True,'cherchi_head':m13.CHERCHI_COMMIT,'cgal_head':m13.CGAL_COMMIT}
        self.fake_shas={};self.inventory={}
        for name in m10.NATIVE:
            directory=self.core if name=='_make_it_stand' else self.cherchi
            f=directory/'python'/(name+'.cpython-313-x86_64-linux-gnu.so')
            f.write_bytes(b'SYNTHETIC_UNLOADABLE_TEST_ONLY_'+name.encode())
            self.fake_shas[name]=sha256(f.read_bytes()).hexdigest()
            self.inventory[name]={'path':str(f),'sha256':self.fake_shas[name],'status':'FOUND'}
        (self.core/'build.ninja').write_text('SYNTHETIC NINJA\n')
        logs=[]
        for name in m14.BUILT_STAGES:
            p=self.artifacts/(name+'.log');p.write_text('SYNTHETIC UNIT TEST '+name+'\n')
            if name=='build-core': argv=['cmake','--build',str(self.core),'--target','_make_it_stand','--parallel','2']
            elif name=='build-cherchi': argv=['cmake','--build',str(self.cherchi),'--parallel','2']
            elif name=='configure-core': argv=['cmake','-S',str(self.root),'-B',str(self.core),'-G','Ninja',
                   '-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON',
                   '-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON',
                   '-DMAKE_IT_STAND_BUILD_PYTHON=ON']
            else: argv=['cmake','-S',str(self.root/'bindings/cherchi'),'-B',str(self.cherchi),'-G','Ninja',
                        '-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON']
            logs.append({'stage':name,'exit_code':0,'wall_ns':12345,
                         'log_sha256':sha256(p.read_bytes()).hexdigest(),'argv':argv})
        self.build={'schema':'w1-m13-pinned-native-build-v1','git_branch':m10.BRANCH,
                    'full_solver_speedup':None,'paper_speed_qualified':False,
                    'pinned_revision':self.sources,
                    'compiled_native_import':{'cpp_extensions_imported':True,'validated_modules':3},
                    'build_commands':logs,'actual_compiled_modules':self.fake_shas,
                    'boost_ninja_rewrite':{'host_libraries_untouched':True,
                    'after_sha256':sha256((self.core/'build.ninja').read_bytes()).hexdigest()}}
        self.write('native-build-receipt.json',self.build)
        self.proof={'complete_native_ledger_rows':5,'native_imports_attested_by_m10':True,
                    'reproduced_abba_single_q_ratio':1.1,'synthetic':True}
        self.write('m11/m11-verified-native-receipts.json',self.proof)
        self.summary={'schema':'w1-m11-native-receipt-suite-v1',
            'state':'FIVE_REAL_CHERCHI_EVALUATIONS_AND_SAVED_RECEIPTS_ADMITTED',
            'native_samples':5,
            'admission_document_sha256':sha256((self.artifacts/'m11/m11-verified-native-receipts.json').read_bytes()).hexdigest(),
            'full_solver_speedup':None,'newton_terminal_verified':False}
        self.write('m11/m11-native-validation-summary.json',self.summary)
        self.preflight={'state':'READY_FOR_REAL_NATIVE_ABBA','checks':{
            'git':{'details':{'head':self.config['head']}},
            'archive':{'details':{'zip_sha256':m10.ARCHIVE_SHA}}}}
        self.write('m11/work/preflight.json',self.preflight)
        self._stack=ExitStack();self.addCleanup(self._stack.close)
        self._stack.enter_context(mock.patch.object(m14,'protected_checkout',return_value=self.config))
        self._stack.enter_context(mock.patch.object(m10,'archive_identity',return_value={'passed':True}))
        self._stack.enter_context(mock.patch.object(m13,'_source_check',return_value=self.sources))
        self._stack.enter_context(mock.patch.object(m10,'_swap_guard',return_value=True))
        self._stack.enter_context(mock.patch.object(m10,'_memory_limit',return_value={
             'process_address_space_cap_bytes':8*1024**3}))
        self._stack.enter_context(mock.patch.object(m10,'module_inventory',return_value=self.inventory))
        self._stack.enter_context(mock.patch.object(m14.m11,'verify',return_value=deepcopy(self.proof)))

    def write(self,name,obj):
        p=self.artifacts/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(obj,allow_nan=False),encoding='utf-8')

    def check(self):
        return m14.custody(self.root,self.archive,self.artifacts)

    def test_synthetic_structure_is_accepted_only_under_mock(self):
        x=self.check()
        self.assertEqual(x['certified_scientific_eval_calls'],5)
        self.assertEqual(x['certified_newton_solves'],0)
        self.assertIsNone(x['full_solver_speedup'])
        self.assertFalse(x['paper_speed_qualified'])

    def test_tampered_build_log_fails(self):
        (self.artifacts/'configure-core.log').write_text('altered')
        with self.assertRaisesRegex(ValueError,'M14_BUILD_LOG_OR_EXIT_DRIFT'):
            self.check()

    def test_missing_build_stage_fails(self):
        self.build['build_commands'].pop(1)
        self.write('native-build-receipt.json',self.build)
        with self.assertRaisesRegex(ValueError,'M14_INCOMPLETE_OR_REORDERED_NATIVE_BUILD'):
            self.check()

    def test_five_parallel_compile_workers_rejected(self):
        self.build['build_commands'][1]['argv'][-1]='5'
        self.write('native-build-receipt.json',self.build)
        with self.assertRaisesRegex(ValueError,'M14_MAX_FOUR_NATIVE_BUILD_WORKERS'):
            self.check()

    def test_altered_binary_rejected(self):
        path=Path(self.inventory['_cherchi_core_boolean']['path'])
        path.write_bytes(b'mutated synthetic test only')
        with self.assertRaisesRegex(ValueError,'M14_BUILT_EXTENSION_NOT_OWNED_BY_M13'):
            self.check()

    def test_foreign_binary_not_in_new_build_rejected(self):
        outside=self.root/'foreign_fake_native.so';outside.write_bytes(b'fake')
        self.inventory['_make_it_stand']['path']=str(outside)
        with self.assertRaisesRegex(ValueError,'M14_BUILT_EXTENSION_NOT_OWNED_BY_M13'):
            self.check()

    def test_wrong_original_source_commit_rejected(self):
        self.preflight['checks']['git']['details']['head']='b'*40
        self.write('m11/work/preflight.json',self.preflight)
        with self.assertRaisesRegex(ValueError,'M14_M11_REAL_SOURCE_PROVENANCE_DRIFT'):
            self.check()

    def test_wrong_cgal_provenance_rejected(self):
        self.sources['cgal_head']='deadbeef'
        self.write('native-build-receipt.json',self.build)
        with self.assertRaisesRegex(ValueError,'M14_CHERCHI_OR_CGAL_SOURCE_UNPINNED'):
            self.check()

    def test_missing_m11_material_proof_rejected(self):
        (self.artifacts/'m11/m11-verified-native-receipts.json').unlink()
        with self.assertRaisesRegex(ValueError,'M11_MISSING_OR_OVERSIZED_JSON'):
            self.check()

    def test_m11_proof_changed_and_summary_updated_but_independent_audit_rejects(self):
        self.proof['reproduced_abba_single_q_ratio']=40
        self.write('m11/m11-verified-native-receipts.json',self.proof)
        self.summary['admission_document_sha256']=sha256((self.artifacts/'m11/m11-verified-native-receipts.json').read_bytes()).hexdigest()
        self.write('m11/m11-native-validation-summary.json',self.summary)
        with self.assertRaisesRegex(ValueError,'M14_SAVED_M11_INDEPENDENT_RECEIPT_DRIFT'):
            self.check()

    def test_blocked_without_build_reports_no_success(self):
        self._stack.enter_context(mock.patch.object(m14,'protected_checkout',side_effect=ValueError('NO_REAL_W1_GIT_TREE')))
        out=self.root/'m14-report'
        with self.assertRaisesRegex(ValueError,'NO_REAL_W1_GIT_TREE'):
            m14.execute(self.root,self.archive,self.artifacts,out)
        self.assertTrue((out/'failure.json').exists())
        self.assertFalse((out/'admission.json').exists())
        self.assertEqual(json.loads((out/'failure.json').read_text())['verified_native_calls'],0)
        with self.assertRaises(FileExistsError):
            m14.execute(self.root,self.archive,self.artifacts,out)


if __name__=='__main__':
    unittest.main()
