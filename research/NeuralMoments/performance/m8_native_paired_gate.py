"""W1 M8: paired single-q strict native Cherchi candidate gate, isolated W1 only.

No production files or extension ABI are modified. This is a runnable native-
HOST experiment, NOT a claim it was executed on this Python-only host. Fails
closed without pinned source, H8c archive and all three compiled native modules.
A passing pair is NOT a complete Faster/Newton solver, terminal material or
paper-matched speed claim.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import gzip
from hashlib import sha256
import inspect
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time

from m5_native_call_instrumentation import (
    preflight, resource_guard, strict_audit,
    InclusiveExclusiveLedger, instrument_call, sha, dump_new, H8,
    ARCHIVE_SHA, REQUEST_SHA, SOURCE_BLOB, FROZEN,
)
from m8_exact_construction_trial import MAX_CACHED_TOKENS, target_coordinates


def clone_paired_classes(original, old_ledger, new_ledger):
    """Two distinct recompiled diagnostic methods, no global monkeypatching."""
    original_function=original.__call__
    exact=original_function.__globals__.get('exact_fraction')
    if not callable(exact):
        raise ValueError('M8_ORIGINAL_EXACT_PARSER_MISSING')
    old,old_labels=instrument_call(original_function,old_ledger)
    newer,new_labels=instrument_call(original_function,new_ledger)
    if old_labels!=new_labels:
        raise ValueError('M8_INSTRUMENTATION_MISMATCH')
    # Only the candidate's fresh isolated function-global dictionary is changed;
    # original module globals and frozen source remain untouched.
    candidate_exact=lru_cache(maxsize=MAX_CACHED_TOKENS)(exact)
    if newer.__globals__ is original_function.__globals__:
        raise ValueError('M8_CANDIDATE_GLOBAL_LEAK')
    newer.__globals__['exact_fraction']=candidate_exact
    if original_function.__globals__.get('exact_fraction') is not exact:
        raise ValueError('M8_ORIGINAL_PARSER_WAS_MODIFIED')

    def candidate_target_view(self,physical_rational):
        import numpy as np
        values,_=target_coordinates(physical_rational,self.request.target_axes,
            self.request.target_origin,mode='optimized',
            normalization_origin=self.normalization_origin,length=self.length)
        return np.asarray([[float(x) for x in row] for row in values],dtype=float).reshape(-1,3),tuple(values)

    Old=type('W1M8OriginalProfiled',(original,),{'__call__':old})
    Candidate=type('W1M8CandidateProfiled',(original,),
        {'__call__':newer,'_target_view':candidate_target_view})
    return Old,Candidate,old_labels,candidate_exact


def native_pair(archive,root,output):
    root=Path(root).resolve();archive=Path(archive).resolve();output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    a=InclusiveExclusiveLedger();b=InclusiveExclusiveLedger()
    try:
        request_raw=preflight(archive,root)
        limits=resource_guard()
        sys.path.insert(0,str(root/'python'))
        import numpy as np
        import _make_it_stand as native
        import _cherchi_core_boolean as boolean
        import _cherchi_rational_moments as arithmetic
        from make_it_stand.verification.cherchi_inprocess import (
            InProcessCherchiEvaluator,_json_value)
        sys.path.insert(0,str(root/H8/'source'))
        from probe_h8_native_cherchi import initial_ellipsoid_q,request_from_frozen
        from verify_h8_exact_moments import independent_ten_raw_moments
        old_type,new_type,labels,cached=clone_paired_classes(InProcessCherchiEvaluator,a,b)
        with tempfile.TemporaryDirectory(prefix='w1-m8-native-pair-') as tmp:
            request_path=Path(tmp)/'prepared-request.json'
            request_path.write_bytes(request_raw)
            request,settings,evidence=request_from_frozen(request_path)
            if evidence.get('original_author_cad') is not False:
                raise ValueError('M8_SOURCE_CAD_SCOPE_DRIFT')
            q=np.asarray(initial_ellipsoid_q(request.target_origin),dtype=np.float64)
            engines=[]
            for cls,ledger in ((old_type,a),(new_type,b)):
                engine=cls(request,settings,normalization={'origin':[0.,0.,0.],'L':1.},
                    rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',fixed_boundary_reuse=False,
                    integral_profile='EXACT_GMP_V1',branch_identity_policy='SOURCE_FEATURE_BRANCH_V2',
                    stage_observer=ledger.native)
                if not engine.backend_identity.startswith(
                    'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'):
                    raise ValueError('M8_NON_PINNED_CHERCHI_BACKEND')
                engines.append(engine)
            signal.alarm(3600)
            results=[]
            for name,engine,ledger in (('original',engines[0],a),('candidate',engines[1],b)):
                tick=time.perf_counter_ns()
                evaluated=engine(q)
                evaluate_ns=time.perf_counter_ns()-tick
                with ledger.span('audit:same_call_material'):
                    material=engine.material(q)
                    engine.validate_same_call_material(material,q,request)
                with ledger.span('audit:native_exact_rational_boundary'):
                    coords=material['variable_rational_vertices']
                    faces=np.asarray(material['variable_faces'],dtype=np.int32)
                    facts=dict(native.audit_exact_rational_triangle_boundary(coords,faces,'AnyNonzero'))
                    strict_audit(facts)
                with ledger.span('audit:independent_fraction_ten'):
                    ref=np.asarray([float(x) for x in independent_ten_raw_moments(
                        coords,faces.tolist())],dtype=np.float64)
                    ten=np.asarray(evaluated['variable_raw_moments'],dtype=np.float64)
                    jac=np.asarray(evaluated['moment_jacobian'],dtype=np.float64)
                    if (ten.shape!=(10,) or jac.shape!=(10,10) or not np.isfinite(jac).all()
                            or not np.isfinite(ten).all() or not np.isfinite(ref).all()):
                        raise ValueError('M8_INVALID_NATIVE_MOMENT_OR_JACOBIAN')
                    error=float(np.max(np.abs(ten-ref)/np.maximum(1.,np.abs(ref))))
                    if error>1e-10:
                        raise ValueError('M8_INDEPENDENT_TEN_DISAGREEMENT')
                with ledger.span('audit:serialize_same_call_material'):
                    serialized=json.dumps(material,default=_json_value,sort_keys=True,allow_nan=False)
                timing=ledger.summary()
                if not timing['all_returned']:
                    raise ValueError('M8_FAILED_STAGE')
                results.append(dict(mode=name,eval_wall_ns=evaluate_ns,timing=timing,
                    material_json_sha256=sha(serialized.encode()),
                    geometry_hash=evaluated['geometry_hash'],
                    topology_hash=evaluated['topology_hash'],
                    source_identity=material['quadric_source_identity'],
                    input_q=q.tolist(),ten=ten.tolist(),jacobian=jac.tolist(),
                    audit_flags={key:bool(facts.get(key)) for key in (
                        'boundary_valid','closed','edge_manifold','vertex_manifold',
                        'consistently_oriented','component_orientations_valid',
                        'self_intersection_completed','self_intersection_free')},
                    independent_ten_max_scaled_error=error,
                    exact_material_vertices=len(coords),material_triangles=len(faces)))
            first,second=results
            checks=('material_json_sha256','geometry_hash','topology_hash','source_identity',
                'input_q','ten','jacobian','audit_flags','exact_material_vertices','material_triangles')
            if any(first[key]!=second[key] for key in checks):
                raise ValueError('M8_OLD_NEW_SAME_CALL_MATH_OR_MATERIAL_DRIFT')
            report=dict(schema='w1-m8-native-single-q-paired-gate-v1',
                scope='SAME_Q_TWO_FRESH_CHERCHI_CALLS_NOT_COMPLETE_NEWTON',
                frozen_source_commit=FROZEN,production_source_blob=SOURCE_BLOB,
                frozen_input_sha256=REQUEST_SHA,archive_sha256=ARCHIVE_SHA,
                module_binary_sha256={name:sha(Path(module.__file__).read_bytes()) for name,module in (
                    ('native',native),('cherchi',boolean),('arithmetic',arithmetic))},
                stage_labels=labels,old_and_candidate_identical_complete_material=True,
                candidate_parser_cache=cached.cache_info()._asdict(),
                results=results,observed_single_q_evaluator_ratio=first['eval_wall_ns']/second['eval_wall_ns'],
                memory=dict(maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,limits=limits),
                full_solver_speedup=None,terminal_material_verified=False,
                w0_w2_production_admission=False,paper_speed_qualified=False)
            dump_new(output/'baseline-performance.json',report)
            dump_new(output/'before_after.json',dict(schema='w1-m8-before-after-native-v1',
                same_q_full_material_and_jacobian_equal=True,
                observed_single_q_evaluator_ratio=report['observed_single_q_evaluator_ratio'],
                complete_solver_speedup=None,terminal_accepted=False,paper_speed_qualified=False))
            return report
    except BaseException as exc:
        dump_new(output/'failure.json',dict(schema='w1-m8-native-failure-v1',
            status='FAILED_NO_NATIVE_MATH_ADMISSION',error=f'{type(exc).__name__}: {exc}',
            full_solver_speedup=None,paper_speed_qualified=False))
        raise
    finally:
        signal.alarm(0)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=native_pair(args.archive,args.root,args.output)
    print('M8_NATIVE_PAIR',result['observed_single_q_evaluator_ratio'])

if __name__=='__main__':main()
