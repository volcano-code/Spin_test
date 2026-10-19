"""W1 M5: real frozen accounting and instrumentation semantics smoke."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from m5_native_call_instrumentation import (
    InclusiveExclusiveLedger, instrument_call, statement_label,
    preflight, native_run, strict_audit, git_blob,
)
from m5_attribution_report import make_report

M4 = HERE/'evidence/m4-baseline-performance.json'


class FakeEvaluator:
    def __call__(self,q):
        value=0
        for i in range(4):
            value+=(q+i)*(q+i)
        if q<0:
            raise ValueError('negative q')
        return dict(value=value, q=q)


class M5Tests(unittest.TestCase):
    def test_original_25point_accounting(self):
        report=make_report(json.loads(M4.read_text()))
        self.assertGreater(report['unattributed_fraction'],0.79)
        self.assertLess(report['ideal_elimination_of_prepared_stage_max_speedup'],1.005)
        self.assertIsNone(report['production_before_after_speedup'])
        self.assertTrue(report['cross_host_unattributed_time_subtraction_forbidden'])

    def test_historical_failure_cannot_be_erased(self):
        r=json.loads(M4.read_text())
        r['archived_25point_status']='PASSED'
        with self.assertRaisesRegex(ValueError,'SCOPE_OR_IDENTITY_DRIFT'):
            make_report(r)

    def test_historical_mixed_run_forbidden(self):
        r=json.loads(M4.read_text())
        r['source_run_id']=39120089309
        with self.assertRaisesRegex(ValueError,'SCOPE_OR_IDENTITY_DRIFT'):
            make_report(r)

    def test_double_count_stage_rejected(self):
        r=json.loads(M4.read_text())
        r['historical_named_stage_seconds']['boolean']+=50
        with self.assertRaisesRegex(ValueError,'LEDGER_NOT_CLOSED'):
            make_report(r)

    def test_replay_ledger_disjoint(self):
        r=json.loads(M4.read_text())
        r['replay_stage_totals_seconds']['fraction_exact_ten']+=20
        with self.assertRaisesRegex(ValueError,'REPLAY_LEDGER_NOT_CLOSED'):
            make_report(r)

    def test_nested_exclusive_accounting_and_fail(self):
        clock=InclusiveExclusiveLedger()
        with clock.span('python:01:source'):
            with clock.span('native:boolean'):
                self.assertEqual(clock.native('source',lambda:42),42)
        with self.assertRaisesRegex(ValueError,'broken'):
            with clock.span('python:02:failure'):
                raise ValueError('broken')
        report=clock.summary()
        self.assertEqual(len(report['exclusive_stages']),4)
        self.assertFalse(report['all_returned'])
        self.assertLessEqual(report['exclusive_ns'],report['wall_ns'])
        with self.assertRaisesRegex(ValueError,'UNKNOWN_NATIVE_STAGE'):
            clock.native('fake_skip_audit',lambda:None)

    def test_instrumented_ast_return_equivalence(self):
        clock=InclusiveExclusiveLedger()
        wrapped,labels=instrument_call(FakeEvaluator.__call__,clock)
        klass=type('BoundTest',(FakeEvaluator,),{'__call__':wrapped})
        self.assertGreaterEqual(len(labels),3)
        for x in (0,1,2,15):
            self.assertEqual(FakeEvaluator()(x),klass()(x))
        out=clock.summary()
        self.assertTrue(out['all_returned'])
        self.assertGreater(out['exclusive_ns'],0)

    def test_instrumented_ast_failure_equivalence(self):
        clock=InclusiveExclusiveLedger()
        wrapped,_=instrument_call(FakeEvaluator.__call__,clock)
        klass=type('BoundTest',(FakeEvaluator,),{'__call__':wrapped})
        with self.assertRaisesRegex(ValueError,'negative q'):
            klass()(-1)
        self.assertFalse(clock.summary()['all_returned'])

    def test_missing_native_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root)
            with self.assertRaises(FileNotFoundError):preflight(root/'missing.zip',root)
            with self.assertRaises(Exception):native_run(root/'missing.zip',root,root/'output')
            fail=json.loads((root/'output/failure.json').read_text())
            self.assertFalse(fail['paper_speed_qualified'])
            self.assertFalse((root/'output/baseline-performance.json').exists())

    def test_strict_exact_audit_gates(self):
        flags={x:True for x in __import__('m5_native_call_instrumentation').AUDIT_TRUE}
        strict_audit(flags)
        flags['self_intersection_free']=False
        with self.assertRaisesRegex(ValueError,'BOUNDARY_REJECTED'):
            strict_audit(flags)
        flags['self_intersection_free']=True
        flags['intersecting_pairs']=[[1,2]]
        with self.assertRaisesRegex(ValueError,'BOUNDARY_REJECTED'):
            strict_audit(flags)

    def test_source_hash_uses_git_blob_frame(self):
        import hashlib
        content=b'hello-world\n'
        self.assertEqual(git_blob(content),hashlib.sha1(b'blob 12\0'+content).hexdigest())

if __name__=='__main__': unittest.main()
