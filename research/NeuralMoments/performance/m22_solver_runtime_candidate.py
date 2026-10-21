"""W1 M22: source-pinned opt-in *real Faster solver* evaluator variant.

This does NOT patch shared production globals, change math, skip a material
validator, override Newton settings or pronounce a speedup. Instead it creates
an independently scoped function object with unchanged production solver
bytecode, replacing only the *constructor* of InProcessCherchiEvaluator with
an isolated subclass. The subclass uses a fresh exact Fraction cache PER
__call__ and the previously verified identity-axis exact target-frame path.

The candidate is NOT W0/W2-admitted. A frozen native host is required to run
and independently audit complete old/candidate Newton trajectories.
"""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha1, sha256
from inspect import getfile
from pathlib import Path
from types import FunctionType

from m8_exact_construction_trial import MAX_CACHED_TOKENS, target_coordinates

SOURCE_BLOB = 'f9fa539f699df8baf8b8d30729048269a26ecb3c'
M8_EXACT_PATH_BLOB = 'd85ea23f6db394d13ec7410ec487ec40ab981eb2'
CANDIDATE_LABEL = 'W1_M22_EXACT_PER_EVALUATION_FRACTION_AND_IDENTITY_FRAME_V1'


def git_blob(source: bytes) -> str:
    return sha1(b'blob ' + str(len(source)).encode() + b'\0' + source).hexdigest()


def _pin_original(evaluator_type, solver, *, enforce=True):
    if not isinstance(evaluator_type, type) or not callable(solver):
        raise TypeError('M22_EVALUATOR_AND_SOLVER_REQUIRED')
    original_constructor = solver.__globals__.get('InProcessCherchiEvaluator')
    if original_constructor is not evaluator_type:
        raise ValueError('M22_SOLVER_CONSTRUCTOR_MISMATCH')
    call = evaluator_type.__dict__.get('__call__')
    if not isinstance(call, FunctionType):
        raise ValueError('M22_EXPECTS_ORIGINAL_DIRECT_CALL')
    exact = call.__globals__.get('exact_fraction')
    if not callable(exact):
        raise ValueError('M22_ORIGINAL_EXACT_PARSER_MISSING')
    if not isinstance(evaluator_type.__dict__.get('_target_view'), FunctionType):
        raise ValueError('M22_EXPECTS_ORIGINAL_TARGET_VIEW')
    if enforce:
        # Both original evaluator and complete Faster/Newton entrypoint are
        # defined by the same frozen production file; no guessed source ABI.
        files = (Path(getfile(call)), Path(getfile(solver)))
        if files[0].resolve() != files[1].resolve():
            raise ValueError('M22_PRODUCTION_SOLVER_AND_EVALUATOR_SOURCE_DIFFER')
        if git_blob(files[0].read_bytes()) != SOURCE_BLOB:
            raise ValueError('M22_FROZEN_PRODUCTION_SOURCE_BLOB_MISMATCH')
        if git_blob(Path(getfile(target_coordinates)).read_bytes()) != M8_EXACT_PATH_BLOB:
            raise ValueError('M22_M8_EXACT_COORDINATE_IMPLEMENTATION_CHANGED')
    return call, exact


def make_candidate_solver(evaluator_type, solver, *, enforce_source_pin=True):
    """Return (solver_function, evaluator_subclass), without global mutation.

    The copied solver has IDENTICAL code, defaults, closure and arguments. The
    only substituted global is the evaluator constructor. The scoped Fraction
    parser is discarded and cleared on every native q, even on exceptions.
    """
    original_call, original_parser = _pin_original(
        evaluator_type, solver, enforce=enforce_source_pin)
    if type(MAX_CACHED_TOKENS) is not int or not 0 < MAX_CACHED_TOKENS <= 65536:
        raise ValueError('M22_INVALID_CACHE_BOUND')

    def scoped_call(self, *args, **kwargs):
        parser = lru_cache(maxsize=MAX_CACHED_TOKENS)(original_parser)
        local = dict(original_call.__globals__)
        local['exact_fraction'] = parser
        isolated = FunctionType(original_call.__code__, local,
            original_call.__name__, original_call.__defaults__,
            original_call.__closure__)
        isolated.__kwdefaults__ = original_call.__kwdefaults__
        try:
            return isolated(self, *args, **kwargs)
        finally:
            parser.cache_clear()

    def specialized_target(self, physical_rational):
        import numpy as np
        rows, _ = target_coordinates(
            physical_rational, self.request.target_axes,
            self.request.target_origin, mode='optimized',
            normalization_origin=self.normalization_origin,
            length=self.length)
        return (np.asarray([[float(x) for x in row] for row in rows],
                           dtype=np.float64).reshape(-1, 3), tuple(rows))

    Candidate = type('W1M22FrozenNativeSolverCandidate', (evaluator_type,), {
        '__call__': scoped_call,
        '_target_view': specialized_target,
        'w1_candidate_label': CANDIDATE_LABEL,
    })
    globals_copy = dict(solver.__globals__)
    globals_copy['InProcessCherchiEvaluator'] = Candidate
    scoped_solver = FunctionType(solver.__code__, globals_copy,
        solver.__name__, solver.__defaults__, solver.__closure__)
    scoped_solver.__kwdefaults__ = solver.__kwdefaults__
    scoped_solver.__annotations__ = dict(solver.__annotations__)
    scoped_solver.__module__ = solver.__module__
    if scoped_solver.__code__ is not solver.__code__:
        raise AssertionError('M22_UNEXPECTED_SOLVER_BYTECODE_CHANGE')
    if solver.__globals__.get('InProcessCherchiEvaluator') is not evaluator_type:
        raise AssertionError('M22_MUTATED_PRODUCTION_MODULE_GLOBAL')
    return scoped_solver, Candidate


def explain_admission():
    return dict(schema='w1-m22-production-entrypoint-candidate-v1',
        frozen_evaluator_git_blob=SOURCE_BLOB,
        exact_path_git_blob=M8_EXACT_PATH_BLOB,
        candidate_label=CANDIDATE_LABEL,
        original_solver_bytecode_preserved=True,
        source_boolean_unchanged=True,
        exact_fraction_cache_scope='SINGLE_EVALUATION_CLEARED_ON_RETURN_OR_EXCEPTION',
        exact_source_material_jacobian_checks_not_disabled=True,
        native_boolean_executed_here=False,
        full_newton_solver_speedup=None,
        w0_w2_production_admitted=False,
        candidate_is_reversible_without_production_source_edit=True)
