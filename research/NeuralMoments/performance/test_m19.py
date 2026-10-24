"""W1 M19: real frozen-driver AST and accounting regression, not native proof."""
import ast
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import m19_real_h8e_profiler as p

FROZEN_SHAPE='''\
def run(request_file, output, columns, base_certificate=None, base_reference=None):
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    engine=InProcessCherchiEvaluator()
    points=[]
    samples=(1,2,3)
    with (output/'events.jsonl').open('x') as journal:
        for i,coefficients in enumerate(samples):
            stage='EVALUATE_INPROCESS_CHERCHI'
            tick=time.monotonic()
            try:
                previous=engine.calls
                value=engine(coefficients)
                stage='SAME_CALL_MATERIAL_ATTACHMENT'
                material=engine.material(coefficients)
                engine.validate(material)
                stage='EXACT_NATIVE_MATERIAL_GEOMETRY_AUDIT'
                facts=dict(boundary_valid=True)
                if facts['boundary_valid'] is not True:
                    raise ValueError('NO_PROOF')
                stage='INDEPENDENT_FRACTION_MATERIAL_TEN_MOMENTS'
                independent=value
                if independent != material['value']:
                    raise ValueError('WRONG_MOMENT')
                stage='WRITE_COMPLETE_SAME_CALL_MATERIAL'
                with (output/f'packet-{i}.json').open('x') as file:
                    json.dump(material,file,sort_keys=True)
                stage='WRITE_EVIDENCE'
                points.append((i,value,material['value']))
                journal.write(f'{i}|{value}\\n')
            except Exception as error:
                journal.write(f'FAILED:{stage}:{error}\\n')
                raise
    return points
'''


class FakeEngine:
    fail_on=None
    def __init__(self):
        self.calls=0
        self.stage_observer=None
    def __call__(self,x):
        self.calls+=1
        if x==self.fail_on:raise RuntimeError('FAKE_CHERCHI_TEST_EXCEPTION')
        if self.stage_observer is not None:
            return self.stage_observer('source',lambda:x*x)
        return x*x
    def material(self,x):
        return dict(value=x*x)
    def validate(self,material):
        if material['value']<0:raise RuntimeError('FAKE_NEGATIVE_MATERIAL')


@contextmanager
def module_stub():
    keys=['make_it_stand','make_it_stand.verification',
          'make_it_stand.verification.cherchi_inprocess']
    mods=[types.ModuleType(n) for n in keys]
    mods[0].__path__=[];mods[1].__path__=[]
    mods[-1].InProcessCherchiEvaluator=FakeEngine
    with patch.dict(sys.modules,dict(zip(keys,mods))):
        yield


def source_function(ledger=None,source=FROZEN_SHAPE):
    globals_={'time':time,'json':json,'__file__':'fake-h8e-driver.py'}
    if ledger is None:
        ns={};exec(compile(ast.parse(source),'fake.py','exec'),globals_,ns)
        return ns['run']
    return p.build_profiled_function(globals_,source,ledger,
        rebind=lambda engine,observed:engine,check_pin=False)[0]


class TestM19(unittest.TestCase):
    def test_source_is_pinned_by_default(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_GIT_BLOB_MISMATCH'):
            p.rewrite_frozen_run(FROZEN_SHAPE)

    def test_six_strict_phases_preserved(self):
        tree, phases=p.rewrite_frozen_run(FROZEN_SHAPE,check_pin=False)
        self.assertEqual(phases,p.PHASES)
        self.assertEqual(len([x for x in ast.walk(tree) if isinstance(x,ast.With)]),9)

    def test_original_vs_wrapped_return_and_bytes(self):
        with module_stub(),tempfile.TemporaryDirectory() as td:
            root=Path(td);old=root/'original';new=root/'profiled'
            old.mkdir();new.mkdir()
            l=p.NestedRealStageLedger()
            self.assertEqual(source_function()(None,old,'0'),
                             source_function(l)(None,new,'0'))
            self.assertEqual({x.name:x.read_bytes() for x in old.iterdir()},
                             {x.name:x.read_bytes() for x in new.iterdir()})
            rows=l.summarize(expected_points=3)
            self.assertEqual(rows['points'],3)
            self.assertTrue(rows['all_completed'])
            for point in rows['per_point']:
                self.assertEqual(set(point['phase_inclusive_ns']),set(p.PHASES))
                self.assertEqual(point['point_wall_ns'],point['exclusive_sum_ns'])

    def test_exception_behavior_preserved(self):
        with module_stub(),tempfile.TemporaryDirectory() as td:
            with patch.object(FakeEngine,'fail_on',2):
                outputs=[]
                for which,fn in [('original',source_function()),
                                 ('profiled',source_function(p.NestedRealStageLedger()))]:
                    dest=Path(td)/which;dest.mkdir()
                    with self.assertRaisesRegex(RuntimeError,'FAKE_CHERCHI_TEST_EXCEPTION'):
                        fn(None,dest,'0')
                    outputs.append({x.name:x.read_bytes() for x in dest.iterdir()})
                self.assertEqual(*outputs)

    def test_actual_instrument_call_native_observer_restoration(self):
        import inspect
        ledger=p.NestedRealStageLedger()
        # Fixture's own checked source, NOT the production source pin.
        fixture_blob=p.git_blob(Path(inspect.getfile(FakeEngine)).read_bytes())
        with patch.object(p,'SOURCE_BLOB',fixture_blob):
            cls=p.make_timed_class(FakeEngine,ledger)
        engine=cls()
        with ledger.span('point:all',0):
            for phase in p.PHASES:
                with ledger.span('phase:'+phase):
                    if phase==p.PHASES[0]:
                        self.assertEqual(engine(2),4)
        self.assertIsNone(engine.stage_observer)
        result=ledger.summarize(expected_points=1)
        self.assertEqual(result['per_point'][0]['point_wall_ns'],
                         result['per_point'][0]['exclusive_sum_ns'])
        names={r['name'] for r in result['rows']}
        self.assertIn('native:source',names)
        self.assertTrue(any(n.startswith('python:') for n in names))

    def test_production_evaluator_pin_rejects_fake(self):
        with self.assertRaisesRegex(ValueError,'PRODUCTION_EVALUATOR_HASH_MISMATCH'):
            p.make_timed_class(FakeEngine,p.NestedRealStageLedger())

    def test_missing_real_stage_rejected(self):
        altered=FROZEN_SHAPE.replace('WRITE_COMPLETE_SAME_CALL_MATERIAL','WRITE_FAKE_STAGE')
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_OR_DUPLICATE_PHASE'):
            p.rewrite_frozen_run(altered,check_pin=False)

    def test_duplicate_stage_rejected(self):
        altered=FROZEN_SHAPE.replace("stage='WRITE_COMPLETE_SAME_CALL_MATERIAL'",
            "stage='INDEPENDENT_FRACTION_MATERIAL_TEN_MOMENTS'")
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_OR_DUPLICATE_PHASE'):
            p.rewrite_frozen_run(altered,check_pin=False)

    def test_duplicate_point_loop_rejected(self):
        altered=FROZEN_SHAPE.replace('    return points',
                '    for i,coefficients in enumerate(samples):\n        pass\n    return points')
        with self.assertRaisesRegex(ValueError,'POINT_LOOP_NOT_UNIQUE'):
            p.rewrite_frozen_run(altered,check_pin=False)

    def test_missing_evaluator_import_rejected(self):
        altered=FROZEN_SHAPE.replace('from make_it_stand.verification.cherchi_inprocess',
                                    'from fake_pkg.verification.cherchi_inprocess')
        with self.assertRaisesRegex(ValueError,'EVALUATOR_IMPORT_DRIFT'):
            p.rewrite_frozen_run(altered,check_pin=False)

    def test_nested_exclusivity(self):
        l=p.NestedRealStageLedger()
        with l.span('point:all',0):
            for phase in p.PHASES:
                with l.span('phase:'+phase):
                    if phase==p.PHASES[0]:
                        with l.span('python:00:test'):
                            time.sleep(0.001)
        result=l.summarize(expected_points=1)
        self.assertEqual(result['per_point'][0]['point_wall_ns'],result['per_point'][0]['exclusive_sum_ns'])
        self.assertEqual(result['points'],1)

    def test_dangling_nested_stage_rejected(self):
        l=p.NestedRealStageLedger()
        with self.assertRaisesRegex(ValueError,'STAGE_WITHOUT_POINT'):
            with l.span('native:boolean'):
                pass

    def test_unregistered_stage_rejected(self):
        l=p.NestedRealStageLedger()
        with self.assertRaisesRegex(ValueError,'UNREGISTERED'):
            with l.span('UNKNOWN_STAGE'):
                pass

    def test_unknown_native_stage_fails_closed(self):
        l=p.NestedRealStageLedger()
        with l.span('point:all',0):
            with self.assertRaisesRegex(ValueError,'UNKNOWN_NATIVE_STAGE'):
                l.native('skipped_exact_audit',lambda:True)

    def test_exception_failing_span_recorded(self):
        l=p.NestedRealStageLedger()
        with self.assertRaisesRegex(RuntimeError,'intentional'):
            with l.span('point:all',0):
                with l.span('phase:EVALUATE_INPROCESS_CHERCHI'):
                    raise RuntimeError('intentional')
        report=l.summarize(expected_points=1)
        self.assertFalse(report['all_completed'])
        self.assertTrue(any(row['status']=='FAIL' for row in report['rows']))

    def test_duplicate_index_rejected(self):
        l=p.NestedRealStageLedger()
        for _ in range(2):
            with l.span('point:all',0):
                pass
        with self.assertRaisesRegex(ValueError,'DUPLICATE_OR_NONCONSECUTIVE'):
            l.summarize()

    def test_expected_25_required(self):
        l=p.NestedRealStageLedger()
        with l.span('point:all',0):pass
        with self.assertRaisesRegex(ValueError,'POINT_COUNT_INCOMPLETE'):
            l.summarize(expected_points=25)

    def test_cloud_template_is_diagnostic_only_and_in_scope(self):
        template=Path(__file__).with_name('m19-w1-real-h8e-stage-profile.workflow.template.yml')
        body=template.read_text()
        self.assertTrue(template.is_file())
        self.assertIn('workflow_dispatch:',body)
        self.assertIn('research/neuralmoments-w1-native-20261019',body)
        self.assertIn('m13_pinned_native_build.py',body)
        self.assertIn('--build-only',body)
        self.assertIn('m19_real_h8e_profiler.py',body)
        self.assertIn('if: always()',body)
        self.assertNotIn('push:\n',body)
        self.assertIn('INACTIVE TEMPLATE',body)

    def test_partial_rows_do_not_count_as_full_25(self):
        l=p.NestedRealStageLedger()
        with l.span('point:all',0):
            for phase in p.PHASES:
                with l.span('phase:'+phase):
                    pass
        with self.assertRaisesRegex(ValueError,'POINT_COUNT_INCOMPLETE'):
            l.summarize(expected_points=25)
        partial=l.summarize()
        self.assertEqual(partial['points'],1)
        self.assertFalse(partial['production_speedup_admitted'])

    def test_native_zero_swap_recheck_delegates_to_preflight_guard(self):
        # False negatives caused by Linux /proc/swaps header spacing must not
        # stop a legitimate native run after a successful M10 preflight.
        with patch.object(p.native_host, '_swap_guard', return_value=True) as guard:
            self.assertIsNone(p.require_zero_swap_for_native())
            guard.assert_called_once_with()
        with patch.object(p.native_host, '_swap_guard',
                          side_effect=RuntimeError('M10_REQUIRES_ZERO_SWAP')):
            with self.assertRaisesRegex(RuntimeError, 'REQUIRES_ZERO_SWAP'):
                p.require_zero_swap_for_native()

    def test_zero_swap_header_whitespace_and_actual_swap(self):
        # Simulates the user-host header, which contains extra tabs but NO
        # swap device rows. Test the *real M10 predicate* under mocked procfs.
        for header in (
                'Filename\tType\tSize\tUsed\tPriority\n',
                'Filename\t\t\t\tType\t\tSize\t\tUsed\t\tPriority\n',
                'Filename    Type    Size    Used    Priority\n'):
            with self.subTest(header=header):
                with patch.object(p.native_host, 'Path') as proc:
                    proc.return_value.is_file.return_value = True
                    proc.return_value.read_text.return_value = header
                    self.assertIs(p.native_host._swap_guard(), True)
        with patch.object(p.native_host, 'Path') as proc:
            proc.return_value.is_file.return_value = True
            proc.return_value.read_text.return_value = (
                'Filename\tType\tSize\tUsed\tPriority\n'
                '/swapfile\tfile\t1048576\t0\t-2\n')
            with self.assertRaisesRegex(RuntimeError, 'REQUIRES_ZERO_SWAP'):
                p.native_host._swap_guard()

    def test_runtime_source_no_longer_compares_proc_header_bytes(self):
        import inspect
        source=inspect.getsource(p.run_native)
        self.assertIn('require_zero_swap_for_native()',source)
        self.assertNotIn(".strip()!='Filename",source)

    def test_real_host_preflight_failure_not_success(self):
        archive=Path('/mnt/data/h8c-reference-39118951636.zip')
        if not archive.is_file():self.skipTest('explicitly unavailable genuine archive')
        result=p.environment_preflight(Path('/mnt/data/W1_M19_dev'),archive,())
        self.assertEqual(result['state'],'BLOCKED')
        self.assertIn('native_modules',result['blockers'])
        self.assertIn('h8e_original_source',result['blockers'])
        self.assertIn('M19_conservative_memory',result['blockers'])


if __name__=='__main__':unittest.main()
