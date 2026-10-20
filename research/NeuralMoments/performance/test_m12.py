"""W1 M12: reject fabricated timings even when old/new material and hashes agree.

All positive M5/M9 fixtures here are synthetic and must NEVER be reported as
executed Cherchi. Original GitHub H8c ZIP is checked separately by M11/M10.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from m9_native_abba_gate import certify_abba
from m11_native_evidence_gate import _bind_m5_timing, _bind_m9_timing, verify
import test_m11 as fixtures


class TimingScopeUnit(unittest.TestCase):
    def test_native_boolean_alone_does_not_replace_independent_audits(self):
        ledger=dict(wall_ns=100, exclusive_stages=[
            dict(name='native:boolean', status='PASS', exclusive_ns=50,
                 inclusive_ns=50)])
        with self.assertRaisesRegex(ValueError,'M11_M9_REQUIRED_STAGE'):
            _bind_m9_timing(dict(eval_wall_ns=60,complete_validation_ns=100,
                                 stage_ledger=ledger))

    def test_exact_m9_timing_accounting(self):
        names=('native:boolean','audit:same_call_material',
               'audit:native_exact_rational_boundary','audit:independent_fraction_ten',
               'audit:exact_material_serialization')
        ledger=dict(wall_ns=200,exclusive_stages=[
            dict(name=n,exclusive_ns=50 if n=='native:boolean' else 5)
            for n in names])
        self.assertEqual(_bind_m9_timing(dict(eval_wall_ns=100,
                         complete_validation_ns=200,stage_ledger=ledger)),200)

    def test_staged_evaluation_cannot_exceed_observed_eval_window(self):
        names=('native:boolean','audit:same_call_material',
               'audit:native_exact_rational_boundary','audit:independent_fraction_ten',
               'audit:exact_material_serialization')
        ledger=dict(wall_ns=200,exclusive_stages=[
            dict(name=n,exclusive_ns=50 if n=='native:boolean' else 5)
            for n in names])
        with self.assertRaisesRegex(ValueError,'M11_M9_EVALUATION_SPANS_EXCEED'):
            _bind_m9_timing(dict(eval_wall_ns=49,complete_validation_ns=200,
                                 stage_ledger=ledger))

    def test_stage_count_does_not_allow_duplicated_audits(self):
        rows=[dict(name=n,exclusive_ns=5) for n in (
              'native:boolean','audit:same_call_material',
              'audit:native_exact_rational_boundary','audit:independent_fraction_ten',
              'audit:exact_material_serialization','audit:exact_material_serialization')]
        with self.assertRaisesRegex(ValueError,'M11_M9_REQUIRED_STAGE'):
            _bind_m9_timing(dict(eval_wall_ns=100,complete_validation_ns=200,
                                 stage_ledger=dict(wall_ns=200,exclusive_stages=rows)))


class SyntheticReceiptBinding(unittest.TestCase):
    """Use a standalone synthetic fixture, never an external native claim."""
    @classmethod
    def setUpClass(cls):
        fixtures.SyntheticReceipt.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.SyntheticReceipt.tearDownClass()

    def run_receipts(self):
        return verify(fixtures.SyntheticReceipt.pref_path,fixtures.SyntheticReceipt.m5,fixtures.SyntheticReceipt.m9)

    def edit(self, edits, match):
        backups={}
        try:
            for path,mutate in edits:
                path=Path(path);backups[path]=path.read_bytes()
                value=json.loads(backups[path]);mutate(value);fixtures.write_json(path,value)
            with self.assertRaisesRegex(ValueError,match):
                self.run_receipts()
        finally:
            for path,original in backups.items():path.write_bytes(original)

    def m9_changed_rows(self, transform):
        """Tamper scientifically identical point rows AND recompute quoted ratio."""
        base=fixtures.SyntheticReceipt.m9/'baseline-performance.json'
        original=json.loads(base.read_text())
        changed=deepcopy(original)
        for row in changed['measurements']:
            transform(row)
        changed['parity_and_timing']=certify_abba(changed['measurements'])
        per_point=[fixtures.SyntheticReceipt.m9/f"point-{r['iteration']:03d}-{r['mode']}.json"
                   for r in changed['measurements']]
        # Check real on-disk M11 semantic gate. Every forged point JSON gets
        # updated too, so the old M11 would have accepted a false timing.
        backups={p:p.read_bytes() for p in [base,*per_point]}
        try:
            fixtures.write_json(base,changed)
            for p,row in zip(per_point,changed['measurements']):fixtures.write_json(p,row)
            return self.run_receipts()
        finally:
            for p,raw in backups.items():p.write_bytes(raw)

    def test_normal_synthetic_contract_still_checks_scoped_timing(self):
        result=self.run_receipts()
        self.assertTrue(result['independent_material_jacobian_and_ten_receipts_match'])
        self.assertFalse(result['fresh_native_execution_independently_proven_by_receipt_alone'])

    def test_forged_fast_candidate_wall_with_self_consistent_ratio_rejected(self):
        def forge(row):
            if row['mode']=='candidate':row['complete_validation_ns']=120
        with self.assertRaisesRegex(ValueError,'M11_M9_COMPLETE_WALL_LEDGER_MISMATCH'):
            self.m9_changed_rows(forge)

    def test_forged_fast_evaluation_wall_even_after_ratio_update_rejected(self):
        def forge(row):
            if row['mode']=='candidate':row['eval_wall_ns']=25
        with self.assertRaisesRegex(ValueError,'M11_M9_EVALUATION_SPANS_EXCEED_EVAL_WALL'):
            self.m9_changed_rows(forge)

    def test_missing_native_geometry_audit_span_rejected(self):
        def forge(row):
            if row['mode']=='candidate':
                spans=row['stage_ledger']['exclusive_stages']
                for event in spans:
                    if event['name']=='audit:native_exact_rational_boundary':
                        event['name']='audit:skipped_geometry'
                totals=row['stage_ledger']['stage_exclusive_totals_ns']
                totals['audit:skipped_geometry']=totals.pop('audit:native_exact_rational_boundary')
        with self.assertRaisesRegex(ValueError,'M11_M9_REQUIRED_STAGE'):
            self.m9_changed_rows(forge)

    def test_m5_sample_wall_requires_actual_parent_ledger_window(self):
        p=fixtures.SyntheticReceipt.m5/'baseline-performance.json'
        self.edit([(p,lambda x:x.update(sample_and_validation_wall_ns=999))],
                  'M11_M5_SAMPLE_AND_VALIDATION_WALL_UNBOUND')

    def test_m5_cannot_omit_fraction_independent_validation(self):
        p=fixtures.SyntheticReceipt.m5/'baseline-performance.json'
        def forge(x):
            for row in x['profiler']['exclusive_stages']:
                if row['name']=='audit:independent_fraction_ten':
                    row['name']='audit:skipped_fraction'
            totals=x['profiler']['stage_exclusive_totals_ns']
            totals['audit:skipped_fraction']=totals.pop('audit:independent_fraction_ten')
        self.edit([(p,forge)],'M11_M5_REQUIRED_STAGE')


if __name__=='__main__': unittest.main()
