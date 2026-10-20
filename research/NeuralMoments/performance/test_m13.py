"""M13 native build/provisioner safety tests: never fabricate an actual solver run."""
from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest import mock

import m13_pinned_native_build as m13


class TestM13(unittest.TestCase):
    def test_frozen_dependencies_explicit(self):
        self.assertEqual(m13.CHERCHI_COMMIT, '7bd6c2697695f555f9a15d7e154e084d841316f0')
        self.assertEqual(m13.CGAL_COMMIT, 'f7c3c8212b56c0d6dae63787efc99093f4383415')
        self.assertEqual(m13.MAX_WORKERS, 4)
        self.assertEqual(m13.MAX_STAGE_SECONDS, 3600)

    def test_core_build_matches_native_workflow(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            shared={n:root/f'libboost_{n}.so' for n in ('thread','system')}
            flags=m13._core_args(root,root/'build/core','/usr/bin/python3.13',shared)
            text=' '.join(flags)
            for flag in ('-DMAKE_IT_STAND_BUILD_PYTHON=ON',
                         '-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON',
                         '-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON',
                         '-DMAKE_IT_STAND_FILTERED_BOUNDARY_KERNEL=ON',
                         '-DBoost_USE_STATIC_LIBS=OFF',
                         '-DMAKE_IT_STAND_BUILD_VIEWER=OFF'):
                self.assertIn(flag,text)
            self.assertEqual(flags[0],'cmake')

    def test_cherchi_arithmetic_required(self):
        x=m13._cherchi_args(Path('/tmp/repo'),Path('/tmp/build'),'/usr/bin/python3.13')
        self.assertIn('-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON',x)
        self.assertIn('-DCMAKE_BUILD_TYPE=Release',x)

    def test_no_nonpic_static_boost_after_patch(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            libs={k:p/f'libboost_{k}.so' for k in ('thread','system')}
            for lib in libs.values():lib.write_bytes(b'ELF')
            ninja=p/'build.ninja'
            before=f'LINK = {str(libs["thread"])[:-3]}.a {str(libs["system"])[:-3]}.a\n'
            ninja.write_text(before)
            fact=m13._fix_boost_ninja(ninja,libs)
            self.assertNotIn('libboost_thread.a',ninja.read_text())
            self.assertNotIn('libboost_system.a',ninja.read_text())
            self.assertIn('libboost_thread.so',ninja.read_text())
            self.assertEqual(fact['replaced_static_boost_references'],{'thread':1,'system':1})
            self.assertTrue(fact['host_libraries_untouched'])
            self.assertEqual(libs['thread'].read_bytes(),b'ELF')
            again=m13._fix_boost_ninja(ninja,libs)
            self.assertEqual(again['replaced_static_boost_references'],{'thread':0,'system':0})
            self.assertEqual(again['before_sha256'],again['after_sha256'])

    def test_absent_boost_shared_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            ninja=p/'build.ninja';ninja.write_text('a\n')
            with self.assertRaisesRegex(ValueError,'BOOST_SHARED_LIBRARY_MISSING'):
                m13._fix_boost_ninja(ninja,{'thread':p/'missing.so','system':p/'missing.so'})
            self.assertEqual(ninja.read_text(),'a\n')

    def test_preflight_is_failsafe_on_unsupported_host(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            record=m13.preflight(p,Path('/mnt/data/h8c-reference-39118951636.zip'))
            self.assertEqual(record['state'],'BLOCKED')
            self.assertIn('git',record['blockers'])
            self.assertIn('source',record['blockers'])
            self.assertEqual(record['native_boolean_calls'],0)
            self.assertIsNone(record['full_solver_speedup'])
            self.assertFalse(record['paper_speed_qualified'])
            self.assertEqual(record['checks']['swap']['status'],'PASS')
            self.assertEqual(record['checks']['archive']['status'],'PASS')

    def test_missing_pinned_sources_only_fetch_after_explicit_optin(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            checks={'git':{'status':'PASS'},'source':{'status':'PASS'},
                    'archive':{'status':'PASS'},'memory':{'status':'PASS'},
                    'swap':{'status':'PASS'},'toolchain':{'status':'PASS'}}
            libs={n:p/f'libboost_{n}.so' for n in ('thread','system')}
            for path in libs.values():path.touch()
            with mock.patch.object(m13,'_environment_check',return_value=checks), \
                 mock.patch.object(m13,'_boost_libraries',return_value=libs):
                orig=m13.preflight(p,p/'h8.zip')
                self.assertIn('pinned_sources',orig['blockers'])
                self.assertEqual(orig['state'],'BLOCKED')
                explicit=m13.preflight(p,p/'h8.zip',allow_source_fetch=True)
                self.assertEqual(explicit['state'],'READY_TO_BUILD')
                self.assertEqual(explicit['checks']['pinned_sources']['status'],'NEEDS_PINNED_FETCH')

    def test_empty_placeholder_sources_can_be_fetched_explicitly(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/m13.CHERCHI_REL).mkdir(parents=True)
            (p/m13.CGAL_REL).mkdir(parents=True)
            checks={key:{'status':'PASS'} for key in
                    ('git','source','archive','memory','swap','toolchain')}
            libs={n:p/f'libboost_{n}.so' for n in ('thread','system')}
            for path in libs.values():path.touch()
            with mock.patch.object(m13,'_environment_check',return_value=checks), \
                 mock.patch.object(m13,'_boost_libraries',return_value=libs):
                result=m13.preflight(p,p/'h8.zip',allow_source_fetch=True)
                self.assertEqual(result['state'],'READY_TO_BUILD')
                self.assertEqual(result['checks']['pinned_sources']['status'],'NEEDS_PINNED_FETCH')
                (p/m13.CGAL_REL/'existing-research.cpp').write_text('do not delete')
                refused=m13.preflight(p,p/'h8.zip',allow_source_fetch=True)
                self.assertEqual(refused['state'],'BLOCKED')
                self.assertIn('pinned_sources',refused['blockers'])

    def test_dirty_pinned_source_refuses_fetch_even_at_correct_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            r={'pinned':False,'cherchi_head':m13.CHERCHI_COMMIT,
               'cherchi_tracked_clean':False,'cherchi_header_found':True,
               'cgal_head':None,'cgal_tracked_clean':False,'cgal_header_found':False}
            checks={k:{'status':'PASS'} for k in
                    ('git','source','archive','memory','swap','toolchain')}
            libs={n:root/f'libboost_{n}.so' for n in ('thread','system')}
            for f in libs.values():f.touch()
            with mock.patch.object(m13,'_environment_check',return_value=checks), \
                 mock.patch.object(m13,'_boost_libraries',return_value=libs), \
                 mock.patch.object(m13,'_source_check',return_value=r):
                out=m13.preflight(root,root/'archive',allow_source_fetch=True)
            self.assertEqual(out['state'],'BLOCKED')
            self.assertIn('PINNED_SOURCE_DIRTY',out['checks']['pinned_sources']['error'])

    def test_wrong_existing_source_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/m13.CHERCHI_REL).mkdir(parents=True)
            (p/m13.CHERCHI_REL/'existing-file.cpp').write_text('preserve')
            with mock.patch.object(m13,'_environment_check',return_value={}), \
                 mock.patch.object(m13,'_boost_libraries',return_value={n:p/f'libboost_{n}.so' for n in ('thread','system')}):
                r=m13.preflight(p,p/'h8.zip',allow_source_fetch=True)
                self.assertEqual(r['state'],'BLOCKED')
                self.assertIn('pinned_sources',r['blockers'])
                self.assertIn('M13_EXISTING_WRONG_SOURCE',r['checks']['pinned_sources']['error'])

    def test_do_not_write_existing_build_dir(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            with self.assertRaisesRegex(FileExistsError,'REFUSES_TO_OVERWRITE'):
                m13._need_empty_target(p)

    def test_build_worker_ceiling_is_strict_integer(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for v in (0,5,-1,True,2.0):
                with self.subTest(v=v), self.assertRaisesRegex(ValueError,'MAX_FOUR_COMPILERS'):
                    m13.execute(root,root/'h8.zip',root/'out',workers=v)
            self.assertFalse((root/'out').exists())

    def test_non_native_preflight_writes_only_blocked_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            report=m13.execute(root,Path('/mnt/data/h8c-reference-39118951636.zip'),
                               root/'out',allow_fetch=False)
            self.assertEqual(report['state'],'BLOCKED')
            out=root/'out'
            self.assertEqual(json.loads((out/'failure.json').read_text())['status'],
                             'BLOCKED_BEFORE_NATIVE_BUILD')
            self.assertFalse((out/'native-build-receipt.json').exists())
            self.assertFalse((out/'m11').exists())
            with self.assertRaises(FileExistsError):
                m13.execute(root,Path('/mnt/data/h8c-reference-39118951636.zip'),out)

    def test_nonzero_build_exits_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            fake_env={key:{'status':'PASS'} for key in ('git','source','archive','swap','toolchain')}
            fake_env['memory']={'status':'PASS','detail':{'process_address_space_cap_bytes':8*1024**3}}
            libraries={n:p/f'libboost_{n}.so' for n in ('thread','system')}
            for lib in libraries.values():lib.touch()
            pinned=dict(pinned=True)
            with mock.patch.object(m13,'_environment_check',return_value=fake_env), \
                 mock.patch.object(m13,'_source_check',return_value=pinned), \
                 mock.patch.object(m13,'_boost_libraries',return_value=libraries), \
                 mock.patch.object(m13,'_subprocess',side_effect=RuntimeError('BUILD_FAILED')):
                with self.assertRaisesRegex(RuntimeError,'BUILD_FAILED'):
                    m13.execute(p,p/'archive.zip',p/'out',run_m11=False)
            f=json.loads((p/'out/failure.json').read_text())
            self.assertEqual(f['status'],'FAILED_CLOSED')
            self.assertEqual(f['stage'],'configure-core')
            self.assertFalse((p/'out/native-build-receipt.json').exists())

    def test_only_m11_coordinator_may_run_two_serial_hour_limited_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'ONLY_M11'):
                m13._subprocess(['python','not_m11.py'],cwd=td,
                    log=Path(td)/'log',memory_bytes=8*1024**3,
                    timeout_seconds=7200,coordinator=True)
            with self.assertRaisesRegex(ValueError,'TIMEOUT_EXCEEDS_60_MINUTES'):
                m13._subprocess(['python','m11_native_host_runner.py'],cwd=td,
                    log=Path(td)/'log',memory_bytes=8*1024**3,
                    timeout_seconds=7400,coordinator=True)

    def test_stage_timeout_cannot_exceed_60min(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'TIMEOUT_EXCEEDS_60_MINUTES'):
                m13._subprocess(['python','-V'],cwd=td,
                                log=Path(td)/'log',memory_bytes=1_000_000_000,
                                timeout_seconds=3601)

    def test_native_build_worker_not_rerouted_to_other_branch(self):
        self.assertTrue(str(m13.BUILD_CORE_REL).startswith('build/w1-m13-'))
        self.assertTrue(str(m13.BUILD_CHERCHI_REL).startswith('build/w1-m13-'))
        self.assertFalse('sudo' in ' '.join(m13._core_args(Path('/repo'),Path('/build'),
                      '/usr/bin/python3.13',{'thread':'t','system':'s'})))

    def test_compiler_and_source_hash_scope_no_production_math_claim(self):
        import inspect
        s=inspect.getsource(m13)
        self.assertIn('full_solver_speedup=None',s)
        self.assertIn('paper_speed_qualified=False',s)
        self.assertIn('preflight(',s)
        self.assertIn('_fetch_pinned_sources(',s)
        self.assertNotIn("git', 'checkout', 'main'",s)

    def test_pinned_source_rejects_modified_tracked_code(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            env = os.environ.copy()
            env.update(GIT_AUTHOR_NAME='W1 Test', GIT_AUTHOR_EMAIL='test@example.invalid',
                       GIT_COMMITTER_NAME='W1 Test', GIT_COMMITTER_EMAIL='test@example.invalid')
            subprocess.run(['git','init','-q',str(path)],check=True,env=env)
            file = path/'code.cpp';file.write_text('pinned bytes')
            subprocess.run(['git','-C',str(path),'add','code.cpp'],check=True,env=env)
            subprocess.run(['git','-C',str(path),'commit','-q','-m','test'],check=True,env=env)
            self.assertTrue(m13._tracked_source_clean(path))
            file.write_text('tampered bytes')
            self.assertFalse(m13._tracked_source_clean(path))

    def test_corrupt_real_h8_archive_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            bad=p/'fake.zip';bad.write_bytes(b'not original archive')
            result=m13.preflight(p,bad)
            self.assertEqual(result['checks']['archive']['status'],'BLOCKED')
            self.assertIn('archive',result['blockers'])

    def test_source_check_requires_both_revisions_and_headers(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cherchi=root/m13.CHERCHI_REL; cgal=root/m13.CGAL_REL
            (cherchi/'code').mkdir(parents=True)
            (cgal/'Number_types/include/CGAL').mkdir(parents=True)
            (cherchi/'code/booleans.h').touch()
            (cgal/'Number_types/include/CGAL/Gmpq.h').touch()
            with mock.patch.object(m13,'_git_revision',side_effect=[m13.CHERCHI_COMMIT,m13.CGAL_COMMIT]), \
                 mock.patch.object(m13,'_tracked_source_clean',return_value=True):
                result=m13._source_check(root)
            self.assertTrue(result['pinned'])
            with mock.patch.object(m13,'_git_revision',side_effect=['bad',m13.CGAL_COMMIT]):
                self.assertFalse(m13._source_check(root)['pinned'])


if __name__=='__main__': unittest.main()
