"""W1 M9 local proof of per-call cache lifecycle and fail-closed native ABBA."""
from __future__ import annotations
import copy
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from m5_native_call_instrumentation import InclusiveExclusiveLedger
from m8_native_paired_gate import clone_paired_classes, MAX_CACHED_TOKENS
from m9_native_abba_gate import (ORDER, historic_h8c_anchor,
    model_to_target_identity_ten, certify_abba, run, CHERCHI_ID)
from test_m8_native_paired import MimicOriginalEvaluator

H8C=Path(os.environ.get('W1_M8_H8C_ARCHIVE','/mnt/data/h8c-reference-39118951636.zip'))
H8E=Path(os.environ.get('W1_M8_H8E_ARCHIVE','/mnt/data/h8e-25point-39121571756.zip'))


def fixture():
    core=dict(material_sha256='f'*64,geometry_hash='g',topology_hash='t',
              source_identity='s',backend_identity=CHERCHI_ID+'real-binary',
              q=[1.]+[0.]*9,ten=[float(i+1) for i in range(10)],
              jacobian=[[float(i==j) for j in range(10)] for i in range(10)],
              boundary_flags={x:True for x in ('boundary_valid','closed','edge_manifold',
                 'vertex_manifold','consistently_oriented','component_orientations_valid',
                 'self_intersection_completed','self_intersection_free')},
              vertices=8455,faces=16910,native_sha256='a'*64,
              cherchi_sha256='b'*64,gmp_sha256='c'*64,
              setup_ns=10,eval_wall_ns=20,complete_validation_ns=30,
              same_call_passed=True,exact_geometry_audit_passed=True,
              independent_ten_max_scaled_error=0.,historical_ten_max_abs_error=0.)
    return [dict(mode=name,**copy.deepcopy(core)) for name in ORDER]


class TestM9CacheLifecycle(unittest.TestCase):
    def setUp(self):
        self.saved=MimicOriginalEvaluator.__call__.__globals__['exact_fraction']
        self.old_ledger=InclusiveExclusiveLedger()
        self.new_ledger=InclusiveExclusiveLedger()
        self.Original,self.Candidate,_,self.stats=clone_paired_classes(
            MimicOriginalEvaluator,self.old_ledger,self.new_ledger)
        self.points=[['0b100/0b11','0b100/0b11','0/1'] for _ in range(6)]

    def test_fresh_lru_on_each_q_call(self):
        a=self.Candidate()
        for _ in range(3):
            x=a(self.points)
            y=self.Original()(self.points)
            self.assertEqual(x[1],y[1])
            self.assertEqual(x[0].tobytes(),y[0].tobytes())
        self.assertEqual(len(self.stats.calls),3)
        self.assertEqual([row['misses'] for row in self.stats.calls],[2,2,2])
        self.assertEqual([row['hits'] for row in self.stats.calls],[16,16,16])
        self.assertEqual(self.stats.cache_info().misses,6)
        self.assertEqual(self.stats.cache_info().hits,48)
        self.assertEqual(self.stats.cache_info().currsize,0)
        self.assertEqual(self.stats.cache_info().maxsize,MAX_CACHED_TOKENS)
        self.assertIs(self.saved,MimicOriginalEvaluator.__call__.__globals__['exact_fraction'])

    def test_same_class_two_instances_no_shared_fraction_values(self):
        self.Candidate()(self.points)
        self.Candidate()(self.points)
        self.assertEqual([c['misses'] for c in self.stats.calls],[2,2])
        self.assertEqual(self.stats.cache_info().currsize,0)

    def test_exception_always_clears_cache_and_restores_globals(self):
        with self.assertRaises((ValueError,ZeroDivisionError)):
            self.Candidate()([['8/11','8/11','1/0']])
        self.assertEqual(len(self.stats.calls),1)
        self.assertEqual(self.stats.cache_info().currsize,0)
        self.Candidate()(self.points)
        self.assertEqual(self.stats.calls[-1]['misses'],2)
        self.assertIs(self.saved,MimicOriginalEvaluator.__call__.__globals__['exact_fraction'])

    def test_two_distinct_real_h8_material_tokens_do_not_reuse_cache(self):
        """Two actually archived 8455-vertex source packets, same candidate class."""
        import gzip
        self.assertTrue(H8E.is_file())
        with ZipFile(H8E) as z:
            names=['artifacts/h8e-jacobian-cols0-4-8/point-000-material.json.gz',
                   'artifacts/h8e-jacobian-cols0-4-8/point-012-material.json.gz']
            packets=[json.loads(gzip.decompress(z.read(name))) for name in names]
        old=self.Original(); candidate=self.Candidate()
        for packet in packets:
            tokens=packet['material_proof']['exact_vertices']
            a=old(tokens);b=candidate(tokens)
            self.assertEqual(a[1],b[1]);self.assertEqual(a[0].tobytes(),b[0].tobytes())
        self.assertEqual(len(self.stats.calls),2)
        self.assertTrue(all(info['misses']>0 for info in self.stats.calls))
        self.assertEqual(self.stats.cache_info().currsize,0)
        self.assertIs(self.saved,MimicOriginalEvaluator.__call__.__globals__['exact_fraction'])

    def test_nonidentity_axes_falls_back_exactly(self):
        source=self.Original(); candidate=self.Candidate()
        axes=[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]
        source.request.target_axes=axes
        candidate.request.target_axes=axes
        a=source(self.points);b=candidate(self.points)
        self.assertEqual(a[1],b[1]);self.assertEqual(a[0].tobytes(),b[0].tobytes())


class TestM9ABBAContract(unittest.TestCase):
    def test_four_identical_rows_are_only_single_q_diagnostic(self):
        report=certify_abba(fixture())
        self.assertTrue(report['pass_all_four_material_and_jacobian_parity'])
        self.assertEqual(report['single_q_evaluator_old_over_candidate'],1.0)
        self.assertIsNone(report['full_solver_speedup'])
        self.assertFalse(report['formal_derivative_admission'])

    def test_reordered_runs_rejected(self):
        rows=fixture();rows[0]['mode']='candidate'
        with self.assertRaisesRegex(ValueError,'ORDER_MUST_BE_ABBA'):
            certify_abba(rows)

    def test_mutated_saved_full_material_rejected(self):
        rows=fixture();rows[2]['material_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'SCIENTIFIC_OUTPUT_DRIFT'):
            certify_abba(rows)

    def test_nonunit_quadric_rejected(self):
        rows=fixture()
        for row in rows:row['q']=[.1]*10
        with self.assertRaisesRegex(ValueError,'INVALID_NATIVE_UNIT_COEFFICIENTS'):
            certify_abba(rows)

    def test_nan_jacobian_rejected(self):
        rows=fixture()
        for row in rows:row['jacobian'][1][2]=float('nan')
        with self.assertRaisesRegex(ValueError,'WRONG_TEN_JACOBIAN'):
            certify_abba(rows)

    def test_mutated_jacobian_rejected(self):
        rows=fixture();rows[3]['jacobian'][0][9]=.002
        with self.assertRaisesRegex(ValueError,'SCIENTIFIC_OUTPUT_DRIFT'):
            certify_abba(rows)

    def test_unverified_geometry_or_ten_rejected(self):
        for change in ({'boundary_flags':{'boundary_valid':True}},
                       {'same_call_passed':False},
                       {'independent_ten_max_scaled_error':1e-4},
                       {'native_sha256':'e'*64},
                       {'eval_wall_ns':0}):
            rows=fixture();rows[1].update(change)
            with self.assertRaises(ValueError):
                certify_abba(rows)

    def test_wrong_mesh_or_missing_native_identity_rejected(self):
        for change in ({'vertices':2},{'faces':0},
                       {'backend_identity':'cgal-silent-fallback'},
                       {'jacobian':[[0.0]*10]*9}):
            rows=fixture();rows[0].update(change)
            with self.assertRaises(ValueError):certify_abba(rows)

    def test_archived_h8c_q_and_full_reference_are_immutable(self):
        self.assertTrue(H8C.is_file())
        h=historic_h8c_anchor(H8C)
        self.assertEqual(h['vertices'],8455);self.assertEqual(h['faces'],16910)
        self.assertEqual(len(h['q']),10);self.assertEqual(len(h['model_moments']),10)
        with self.assertRaisesRegex(ValueError,'FROZEN_QUADRIC_CHANGED'):
            historic_h8c_anchor(H8C,expected_q=[0.0]*10)

    def test_h8c_target_frame_matches_h8e_true_point_zero(self):
        self.assertTrue(H8E.is_file())
        with ZipFile(H8E) as z:
            req=json.loads(z.read('artifacts/h8-request/prepared-request.json'))
            observed=json.loads(z.read('artifacts/h8e-jacobian-cols0-4-8/point-000.json'))
        base=historic_h8c_anchor(H8C)
        expected=model_to_target_identity_ten(base['model_moments'],
                    req['request']['target_origin'],req['request']['target_axes'])
        self.assertLess(max(abs(x-y) for x,y in zip(expected,
                        observed['independent_variable_raw_moments'])),1e-12)
        self.assertEqual(base['q'],observed['coefficients'])

    def test_nonidentity_frame_cannot_claim_h8c_reference(self):
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_OR_MALFORMED'):
            model_to_target_identity_ten([1.0]*10,[0.,0.,0.],[[0.,1.,0.],[1.,0.,0.],[0.,0.,1.]])

    def test_native_missing_production_checkout_fails_closed(self):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            with self.assertRaisesRegex(ValueError,'M5_PRODUCTION_SOURCE_UNPINNED'):
                run(H8C,root,root/'result')
            failure=json.loads((root/'result/failure.json').read_text())
            self.assertEqual(failure['status'],'BLOCKED_OR_FAILED_NO_NATIVE_ABBA_CERTIFICATE')
            self.assertEqual(failure['completed_points'],0)
            self.assertFalse((root/'result/baseline-performance.json').exists())
            self.assertIsNone(failure['old_new_full_solver_speedup'])


if __name__=='__main__':
    unittest.main()
