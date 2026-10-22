"""M23: real H8e CAD input identity plus fail-closed genuine native runner."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

import numpy as np

import m23_real_newton_abba as m23

REAL=Path('/mnt/data/h8e-25point-39121571756.zip')


class TestH8NativeNewton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REAL.is_file():
            raise RuntimeError('M23_REQUIRES_REAL_CI_H8E_ARTIFACT_NO_SYNTHETIC_SUBSTITUTION')
        cls.data=m23.frozen_meshes(REAL)

    def test_authenticated_original_archive(self):
        m,d,c,a=m23._archive_data(REAL)
        self.assertEqual(d['request']['mode'],'SPINNING_TOP')
        self.assertFalse(d['evidence']['newton_converged'])
        self.assertFalse(a['formal_newton_qualified'])
        self.assertFalse(c['faster_newton_converged'])
        self.assertEqual(m23._sha(m[m23.REQUEST_PATH]),m23.H8_REQUEST_SHA)

    def test_all_four_real_cad_meshes_authenticated(self):
        d=self.data['arrays']
        self.assertEqual(len(d),4)
        self.assertEqual([(len(d[k][0]),len(d[k][1])) for k in
           ('initial_top','fixed_shell','design_domain','shaft')],
           [(15646,31288),(28768,57532),(13122,26244),(1580,3156)])

    def test_original_geometry_matches_frozen_request(self):
        import zipfile
        with zipfile.ZipFile(REAL) as z:
            r=json.loads(z.read(m23.REQUEST_PATH))['request']
        for name,tag in [('initial_top','outer'),('design_domain','design')]:
            v,f=self.data['arrays'][name]
            self.assertTrue(np.array_equal(v/self.data['scale_mm'],np.asarray(r[tag+'_vertices'])))
            self.assertTrue(np.array_equal(f,np.asarray(r[tag+'_faces'])))

    def test_real_physical_units_not_silent_fake_request(self):
        d=self.data
        self.assertEqual(d['scale_mm'],25.)
        self.assertAlmostEqual(d['density_g_mm3'],0.001187)
        self.assertGreater(d['minimum_outer_wall_mm'],0)
        self.assertAlmostEqual(d['target_origin_mm'][2],-2.874999612569809,places=10)
        self.assertIn('NOT_IDENTICAL_NATIVE_H8C_REQUEST',d['scope'])

    def test_original_author_cad_not_claimed(self):
        self.assertIn('RECONSTRUCTED',self.data['scope'])
        self.assertEqual(self.data['archive_sha256'],m23.ARCHIVE_SHA)

    def test_bad_zip_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'tampered.zip'
            path.write_bytes(REAL.read_bytes()+b'garbage')
            with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA_MISMATCH'):
                m23._archive_data(path)

    def test_missing_archive_rejected(self):
        with self.assertRaisesRegex(ValueError,'ARCHIVE_SHA_MISMATCH'):
            m23._archive_data('/not/a/real/CI.zip')

    def test_memory_guard_still_detects_4gib(self):
        self.assertLess(m23._memory_limit(),6*1024**3)

    def test_missing_original_checkout_and_modules_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            receipt=m23.preflight(t,REAL,())
            self.assertEqual(receipt['status'],'BLOCKED')
            self.assertIn('M23_FULL_W1_GIT_CHECKOUT_REQUIRED',receipt['blockers'])
            self.assertEqual(receipt['archive_sha256'],m23.ARCHIVE_SHA)
            self.assertTrue(any('M23_NATIVE_MODULE_NOT_UNIQUELY_PRESENT' in x
                           for x in receipt['blockers']))

    def test_blocked_real_run_writes_failure_and_zero_calls(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/'output'
            r=m23.run_four(root,REAL,out,())
            self.assertEqual(r['state'],'BLOCKED')
            self.assertTrue((out/'preflight.json').is_file())
            failure=json.loads((out/'failure.json').read_text())
            self.assertEqual(failure['solver_calls'],0)
            self.assertIsNone(failure['full_solver_speedup'])
            self.assertFalse((out/'diagnostic.json').exists())

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'has-evidence';p.mkdir()
            with self.assertRaisesRegex(FileExistsError,'OUTPUT_ALREADY_EXISTS'):
                m23.run_four(t,REAL,p)

    def test_bad_timeout_rejected_without_output(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'out'
            with self.assertRaisesRegex(ValueError,'AT_MOST_ONE_HOUR'):
                m23.run_four(t,REAL,p,max_seconds=3601)
            self.assertFalse(p.exists())

    def test_frozen_4_call_order(self):
        self.assertEqual(m23.ORDER,('original','candidate','candidate','original'))
        self.assertEqual(m23.MAX_RUN_SECONDS,3600)

    def test_python_cli_exit2_on_actual_host(self):
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'run'
            proc=subprocess.run([sys.executable,m23.__file__,'--root',t,
                 '--archive',str(REAL),'--output',str(out)],
                 capture_output=True,text=True,timeout=20)
            self.assertEqual(proc.returncode,2,proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['state'],'BLOCKED')
            self.assertFalse((out/'diagnostic.json').exists())

    def test_independent_run_isolation(self):
        import inspect
        source=inspect.getsource(m23._one_worker)
        self.assertIn('start_new_session=True',source)
        self.assertIn('subprocess.Popen',source)
        self.assertIn('os.killpg',source)
        self.assertNotIn('shell=True',source)

    def _journal_fixture(self,folder):
        path=Path(folder); path.mkdir(parents=True,exist_ok=True)
        material={'geometry_hash':'pin-geometry','topology_hash':'pin-topology',
                  'quadric_coefficients':[1.]+[0.]*9,
                  'variable_raw_moments':[1.]+[0.]*9,
                  'raw_moments':[2.]+[0.]*9,
                  'quadric_source_identity':'pin-source',
                  'moment_jacobian':[[float(i==j) for j in range(10)] for i in range(10)]}
        packet='evaluation-000001.json'
        (path/packet).write_text(json.dumps(material,sort_keys=True))
        row=dict(kind='MAP_SAVED',evaluation=1,evaluation_file=packet,
             sha256=m23._sha((path/packet).read_bytes()),
             coefficients=material['quadric_coefficients'],geometry_hash='pin-geometry')
        (path/'events.jsonl').write_text(json.dumps(row)+'\n'+json.dumps(
            dict(kind='NEWTON_EVENT',event={'accepted':True,'iteration':0}))+'\n'+
            json.dumps(dict(kind='RUN_TERMINATED',status='CONVERGED',evaluation_count=1))+'\n')
        for filename in ('complete.json','result.json','record-verification.json',
                         'terminal-complement.json','terminal-material-reference.json',
                         'timing-scope.json','recording-costs.json'):
            val={'complete':True,'status':'CONVERGED','evaluation_count':1} if filename=='complete.json' else (
                {'status':'CONVERGED','scientific_digest':'pin-science'} if filename=='result.json' else (
                dict(record_integrity_valid=True,saved_materials=1,accepted_updates=1,
                     rejected_evaluations=0,core_admission=False)
                if filename=='record-verification.json' else {}))
            (path/filename).write_text(json.dumps(val))
        return path

    def test_real_journal_sha_and_newton_trace_audit_fixture(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            receipt=m23.audit_saved_newton_events(path)
            self.assertEqual(receipt['evaluation_count'],1)
            self.assertEqual(receipt['newton_event_count'],1)
            self.assertEqual(receipt['scientific_digest'],'pin-science')

    def test_altered_material_rejected_not_speedup(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            with (path/'evaluation-000001.json').open('a') as f:f.write(' ')
            with self.assertRaisesRegex(ValueError,'EVALUATION_SHA_MISMATCH'):
                m23.audit_saved_newton_events(path)

    def test_false_completed_terminal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            (path/'complete.json').write_text('{'+'"complete":false'+'}')
            with self.assertRaisesRegex(ValueError,'INCOMPLETE_OR_NONCONVERGED'):
                m23.audit_saved_newton_events(path)

    def test_missing_original_saved_geometry_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            (path/'evaluation-000001.json').unlink()
            with self.assertRaisesRegex(ValueError,'EVALUATION_SHA_MISMATCH'):
                m23.audit_saved_newton_events(path)

    def test_production_solver_and_partition_are_real(self):
        import inspect
        source=inspect.getsource(m23._child)
        self.assertIn('SpinArtifactProblem(',source)
        self.assertIn('solve_cherchi_inprocess_and_seal_faster',source)
        self.assertIn('make_candidate_solver(',source)
        self.assertNotIn('Mock',source)

    def _edit_fixture_material(self, folder, edit):
        path=Path(folder)/'evaluation-000001.json'
        content=json.loads(path.read_text())
        edit(content)
        path.write_text(json.dumps(content,sort_keys=True))
        # Keep the self-reported event SHA internally consistent to ensure
        # independent field checks really detect the invalid attachment.
        events=Path(folder)/'events.jsonl'
        lines=[json.loads(s) for s in events.read_text().splitlines()]
        lines[0]['sha256']=m23._sha(path.read_bytes())
        events.write_text(''.join(json.dumps(x)+'\n' for x in lines))

    def test_missing_full_jacobian_fails_even_with_recomputed_sha(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            self._edit_fixture_material(path,lambda material:material.pop('moment_jacobian'))
            with self.assertRaisesRegex(ValueError,'FULL_JACOBIAN_MISSING_OR_NONFINITE'):
                m23.audit_saved_newton_events(path)

    def test_nan_jacobian_fails_even_with_recomputed_sha(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            self._edit_fixture_material(path,lambda material: material['moment_jacobian'][0].__setitem__(0,float('nan')))
            with self.assertRaisesRegex(ValueError,'FULL_JACOBIAN_MISSING_OR_NONFINITE'):
                m23.audit_saved_newton_events(path)

    def test_short_jacobian_fails_even_with_recomputed_sha(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            self._edit_fixture_material(path,lambda material: material['moment_jacobian'].pop())
            with self.assertRaisesRegex(ValueError,'FULL_JACOBIAN_MISSING_OR_NONFINITE'):
                m23.audit_saved_newton_events(path)

    def test_missing_one_ten_moment_fails(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            self._edit_fixture_material(path,lambda material: material['variable_raw_moments'].pop())
            with self.assertRaisesRegex(ValueError,'TEN_MOMENTS_MISSING_OR_NONFINITE'):
                m23.audit_saved_newton_events(path)

    def test_rejected_record_verifier_false_green_flag(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            proof=path/'record-verification.json'
            data=json.loads(proof.read_text())
            data['record_integrity_valid']=False
            proof.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'PRODUCTION_RECORD_PROOF_MISSING'):
                m23.audit_saved_newton_events(path)

    def test_rejected_record_verifier_wrong_saved_material_count(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            proof=path/'record-verification.json'
            data=json.loads(proof.read_text());data['saved_materials']=0
            proof.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'PRODUCTION_RECORD_PROOF_MISSING'):
                m23.audit_saved_newton_events(path)

    def test_missing_terminal_event_cannot_qualify_as_newton(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            journal=path/'events.jsonl'
            journal.write_text('\n'.join(journal.read_text().splitlines()[:-1])+'\n')
            with self.assertRaisesRegex(ValueError,'MISSING_SUCCESSFUL_NEWTON_TERMINAL_EVENT'):
                m23.audit_saved_newton_events(path)

    def test_cli_nonconverged_status_is_nonzero(self):
        with patch.object(m23,'run_four',return_value={'state':'FAILED_NONCONVERGED','completed':[]}):
            with patch.object(sys,'argv',[m23.__file__,'--root','/tmp','--archive','/tmp','--output','/tmp/w1-nonconverged']):
                with redirect_stdout(StringIO()):
                    with self.assertRaises(SystemExit) as result:
                        m23.main()
                    self.assertEqual(result.exception.code,2)

    def test_cli_unexpected_status_is_nonzero(self):
        with patch.object(m23,'run_four',return_value={'state':'UNKNOWN_STATE'}):
            with patch.object(sys,'argv',[m23.__file__,'--root','/tmp','--archive','/tmp','--output','/tmp/w1-unknown']):
                with redirect_stdout(StringIO()):
                    with self.assertRaises(SystemExit) as result:
                        m23.main()
                    self.assertEqual(result.exception.code,2)

    def test_cli_accepted_diagnostic_status_is_zero_but_not_production_release(self):
        with patch.object(m23,'run_four',return_value={'state':'FOUR_NATIVE_RUNS_SAME_SCIENTIFIC_DIGEST_NOT_W0_W2_ADMITTED'}):
            with patch.object(sys,'argv',[m23.__file__,'--root','/tmp','--archive','/tmp','--output','/tmp/w1-accepted']):
                with redirect_stdout(StringIO()):
                    self.assertIsNone(m23.main())

    def test_four_nonconverged_children_fail_closed_not_diagnostic(self):
        # Fully synthetic worker outputs; tests parent failure propagation only.
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            def fake_worker(script,worktree,archive,output,mode,module_dirs,max_seconds,memory):
                (output/'worker.json').write_text(json.dumps(dict(
                    locked_problem_digest='same-locked-problem',
                    solver_status='MAX_ITERATIONS',scientific_digest='same-synthetic-digest',
                    mode=mode,wall_solver_ns=1000)))
                return 0
            fake_pre=dict(status='READY_TO_RUN_FOUR_INDEPENDENT_SOLVER_PROCESSES',
                module_sha256={},native_binary_candidates={})
            with patch.object(m23,'preflight',return_value=fake_pre), \
                 patch.object(m23,'_one_worker',side_effect=fake_worker), \
                 patch.object(m23,'_memory_limit',return_value=8*1024**3):
                actual=m23.run_four(root,REAL,root/'newton',module_dirs=())
            self.assertEqual(actual['state'],'FAILED_NONCONVERGED')
            self.assertEqual(len(actual['completed']),4)
            self.assertFalse((root/'newton'/'diagnostic.json').exists())
            failure=json.loads((root/'newton'/'failure.json').read_text())
            self.assertEqual(failure['status'],'M23_FOUR_SOLVERS_RETURNED_NONCONVERGED')
            self.assertIsNone(failure['full_solver_speedup'])

    def test_missing_accepted_updates_denied_even_with_saved_complete(self):
        with tempfile.TemporaryDirectory() as t:
            path=self._journal_fixture(Path(t)/'run')
            proof=path/'record-verification.json'
            data=json.loads(proof.read_text());data['accepted_updates']=0
            proof.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'PRODUCTION_RECORD_PROOF_MISSING'):
                m23.audit_saved_newton_events(path)

if __name__=='__main__':unittest.main()
