"""M22 fail-closed tests: candidate reaches true solver code, no shared patches."""
import inspect
import json
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from m22_solver_runtime_candidate import (make_candidate_solver, explain_admission,
    git_blob, M8_EXACT_PATH_BLOB)
from m8_exact_construction_trial import target_coordinates

calls=[]

def exact_fraction(token):
    calls.append(token)
    return Fraction(token)

class FakeEngine:
    def __init__(self, request, **kwargs):
        self.request=request
        self.normalization_origin=(0.,0.,0.)
        self.length=1.
        self.kwargs=kwargs

    def _target_view(self, physical_rational):
        values, _=target_coordinates(physical_rational,
             self.request.target_axes,self.request.target_origin,
             mode='original', normalization_origin=self.normalization_origin,
             length=self.length)
        return (np.asarray([[float(x) for x in row] for row in values]),tuple(values))

    def __call__(self, q):
        if q=='explode':
            exact_fraction('1/2')
            raise RuntimeError('ORIGINAL_GEOMETRY_EXCEPTION')
        if q=='different':
            tokens=('2/3','2/3','3/5')
        else:
            tokens=('1/2','1/2','1/3')
        results=[exact_fraction(x) for x in tokens]
        xyz=(tuple(results),tuple(results),tuple(results))
        view,exact=self._target_view(xyz)
        return dict(values=[str(x) for x in results],
                    exact=[[str(x) for x in row] for row in exact],
                    binary64=view.tobytes().hex(), kwargs=self.kwargs)

InProcessCherchiEvaluator=FakeEngine

def original_solver(request, q, *, switches=None):
    evaluator=InProcessCherchiEvaluator(request, switches=switches)
    return dict(result=evaluator(q), trace=[{'accepted':True}, {'accepted':False}],
                seal='FAKE_NOT_NATIVE')

class Request:
    target_origin=(0.,0.,0.)
    target_axes=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))

class NontrivialRequest:
    target_origin=(0.1,0.2,0.3)
    target_axes=((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.))

class TestSolverOverlay(unittest.TestCase):
    def setUp(self):
        calls.clear()
        self.wrapper,self.Candidate=make_candidate_solver(
            FakeEngine,original_solver,enforce_source_pin=False)

    def test_solver_bytecode_and_global_identity(self):
        self.assertIs(self.wrapper.__code__,original_solver.__code__)
        self.assertIs(original_solver.__globals__['InProcessCherchiEvaluator'],FakeEngine)
        self.assertIs(self.wrapper.__globals__['InProcessCherchiEvaluator'],self.Candidate)
        self.assertIsNot(self.wrapper.__globals__,original_solver.__globals__)

    def test_identity_exact_solver_trace(self):
        original=original_solver(Request(),'one',switches='test')
        candidate=self.wrapper(Request(),'one',switches='test')
        self.assertEqual(original,candidate)
        self.assertEqual(candidate['trace'],[{'accepted':True},{'accepted':False}])

    def test_affine_frame_not_approximated(self):
        self.assertEqual(original_solver(NontrivialRequest(),'one'),
                         self.wrapper(NontrivialRequest(),'one'))

    def test_cache_per_q_no_cross_call_leak(self):
        calls.clear()
        self.wrapper(Request(),'one')
        self.assertEqual(calls,['1/2','1/3'])
        self.wrapper(Request(),'one')
        self.assertEqual(calls,['1/2','1/3','1/2','1/3'])
        self.wrapper(Request(),'different')
        self.assertEqual(calls[-2:],['2/3','3/5'])

    def test_errors_and_restore(self):
        with self.assertRaisesRegex(RuntimeError,'ORIGINAL_GEOMETRY_EXCEPTION'):
            self.wrapper(Request(),'explode')
        self.assertEqual(original_solver(Request(),'one'), self.wrapper(Request(),'one'))
        self.assertIs(original_solver.__globals__['InProcessCherchiEvaluator'],FakeEngine)

    def test_pin_rejects_fake_source(self):
        with self.assertRaisesRegex(ValueError,'FROZEN_PRODUCTION_SOURCE_BLOB_MISMATCH'):
            make_candidate_solver(FakeEngine,original_solver,enforce_source_pin=True)

    def test_different_evaluator_rejected(self):
        class Other(FakeEngine): pass
        with self.assertRaisesRegex(ValueError,'SOLVER_CONSTRUCTOR_MISMATCH'):
            make_candidate_solver(Other,original_solver,enforce_source_pin=False)

    def test_missing_direct_original_call_rejected(self):
        class Other(FakeEngine): pass
        globals2=dict(original_solver.__globals__,InProcessCherchiEvaluator=Other)
        from types import FunctionType
        altered=FunctionType(original_solver.__code__,globals2,original_solver.__name__)
        with self.assertRaisesRegex(ValueError,'EXPECTS_ORIGINAL_DIRECT_CALL'):
            make_candidate_solver(Other,altered,enforce_source_pin=False)

    def test_missing_parser_rejected(self):
        saved=original_solver.__globals__['exact_fraction']
        with patch.dict(original_solver.__globals__, {'exact_fraction': None}):
            with self.assertRaisesRegex(ValueError,'ORIGINAL_EXACT_PARSER_MISSING'):
                make_candidate_solver(FakeEngine, original_solver,enforce_source_pin=False)
        self.assertIs(original_solver.__globals__['exact_fraction'],saved)

    def test_bounded_fraction_cache(self):
        import m22_solver_runtime_candidate as m22
        with patch.object(m22,'MAX_CACHED_TOKENS',-1):
            with self.assertRaisesRegex(ValueError,'INVALID_CACHE_BOUND'):
                make_candidate_solver(FakeEngine,original_solver,enforce_source_pin=False)

    def test_m8_coordinate_helper_matches_pinned_W1_blob(self):
        from m8_exact_construction_trial import target_coordinates
        from inspect import getfile
        self.assertEqual(git_blob(Path(getfile(target_coordinates)).read_bytes()),
                         M8_EXACT_PATH_BLOB)

    def test_candidate_returns_identical_scaled_offset_coordinates(self):
        points=((Fraction(1,3),Fraction(2,7),Fraction(11,13)),
                (Fraction(-17,31),Fraction(3,2),Fraction(9,16)))
        base=FakeEngine(NontrivialRequest())
        alt=self.Candidate(NontrivialRequest())
        for obj in (base,alt):
            obj.length=2.
            obj.normalization_origin=(0.5,-1.,0.25)
        lhs=base._target_view(points)
        rhs=alt._target_view(points)
        self.assertEqual(lhs[1],rhs[1])
        self.assertEqual(lhs[0].tobytes(),rhs[0].tobytes())

    def test_metadata_does_not_claim_native(self):
        d=explain_admission()
        self.assertFalse(d['native_boolean_executed_here'])
        self.assertIsNone(d['full_newton_solver_speedup'])
        self.assertFalse(d['w0_w2_production_admitted'])

if __name__=='__main__':unittest.main()
