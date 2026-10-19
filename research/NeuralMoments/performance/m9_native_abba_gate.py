"""W1 M9: pinned H8c true-native ABBA material+Jacobian parity admission gate.

Only executable on a FULL matching Cherchi build. No production ABI or
acceptance policy changes. A successful *four-call* single-q trial is not a
Newton solve, a smooth-stratum proof, or evidence of paper-matched speed.
When prerequisites are absent, write ONLY failure.json and exit nonzero.
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import inspect
import json
import math
from pathlib import Path
import platform
import resource
import signal
from statistics import median
import sys
import tempfile
import time
from zipfile import ZipFile

from m5_native_call_instrumentation import (
    preflight, resource_guard, strict_audit, git_blob, sha, dump_new,
    InclusiveExclusiveLedger, H8, SOURCE_BLOB, REQUEST_SHA, ARCHIVE_SHA, FROZEN,
    AUDIT_TRUE,
)
from m8_native_paired_gate import clone_paired_classes

ORDER = ('original', 'candidate', 'candidate', 'original')
H8C_PACKET = 'artifacts/h8-cherchi-point/actual-cherchi-packet.json.gz'
H8C_CERT = 'artifacts/h8-cherchi-point/exact-ten-moment-certificate.json'
H8C_PACKET_SHA = 'ba47a6d6f9fad2dce2569434bf9340252cceaeaf99c14a82df02b637092b6464'
CHERCHI_ID = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'


def _archive_member(z: ZipFile, name: str, limit: int) -> bytes:
    rows = [f for f in z.infolist() if f.filename == name]
    if len(rows) != 1 or not 0 < rows[0].file_size <= limit:
        raise ValueError('M9_MISSING_DUPLICATE_OR_OVERSIZED_ARCHIVE_MEMBER:' + name)
    return z.read(rows[0])


def historic_h8c_anchor(archive, *, expected_q=None):
    """Read frozen model-frame ten-moment ground truth, not an optimizer output."""
    archive=Path(archive)
    if sha(archive.read_bytes()) != ARCHIVE_SHA:
        raise ValueError('M9_ARCHIVE_SHA_MISMATCH')
    with ZipFile(archive) as z:
        packet_data = _archive_member(z,H8C_PACKET,4_000_000)
        cert = json.loads(_archive_member(z,H8C_CERT,200_000))
        if sha(packet_data) != H8C_PACKET_SHA:
            raise ValueError('M9_ORIGINAL_CHERCHI_PACKET_SHA_MISMATCH')
        packet=json.loads(gzip.decompress(packet_data))
        if (cert.get('verified_actual_packet_sha256') != H8C_PACKET_SHA
                or cert.get('pure_python_fraction_vs_native_gmp_max_ulp') != 0
                or cert.get('exact_ten_moments_independently_reproduced') is not True
                or cert.get('newton_converged') is not False
                or len(packet.get('exact_vertices',[])) != 8455
                or len(packet.get('faces',[])) != 16910
                or len(packet.get('quadric_coefficients',[])) != 10):
            raise ValueError('M9_HISTORICAL_H8C_MOMENT_PROOF_INCOMPLETE')
        q=packet['quadric_coefficients']
        if expected_q is not None and list(expected_q)!=q:
            raise ValueError('M9_FROZEN_QUADRIC_CHANGED')
        moments=cert['variable_raw_ten_moments_normalized']
        if len(moments)!=10 or not all(type(x) in (float,int) and math.isfinite(x) for x in moments):
            raise ValueError('M9_HISTORICAL_TEN_VECTOR_MALFORMED')
        return dict(q=q,model_moments=moments,packet_sha256=H8C_PACKET_SHA,
                    vertices=8455,faces=16910,
                    scope='NONAUTHOR_RECONSTRUCTED_H8C_ARCHIVED_REFERENCE_ONLY')


def model_to_target_identity_ten(m,origin,axes):
    """Specialization valid ONLY for H8's original, exactly identity axes."""
    if (axes != [[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]]
            or len(origin)!=3 or len(m)!=10
            or any(type(x) not in (int,float) or not math.isfinite(x) for x in origin)):
        raise ValueError('M9_UNSUPPORTED_OR_MALFORMED_H8_FRAME')
    x,y,z=origin
    M,Lx,Ly,Lz,xx,yy,zz,yz,xz,xy=m
    return [M, Lx-x*M, Ly-y*M, Lz-z*M,
            xx-2*x*Lx+x*x*M,yy-2*y*Ly+y*y*M,zz-2*z*Lz+z*z*M,
            yz-y*Lz-z*Ly+y*z*M,xz-x*Lz-z*Lx+x*z*M,
            xy-x*Ly-y*Lx+x*y*M]


def certify_abba(rows):
    """Pure fail-closed reducer; does NOT create evidence of native execution."""
    if len(rows)!=4 or tuple(x.get('mode') for x in rows)!=ORDER:
        raise ValueError('M9_ORDER_MUST_BE_ABBA')
    must_match=('material_sha256','geometry_hash','topology_hash','source_identity',
                'backend_identity','q','ten','jacobian','boundary_flags',
                'vertices','faces','native_sha256','cherchi_sha256','gmp_sha256')
    reference=rows[0]
    q=reference.get('q',[])
    if (len(q)!=10 or any(type(v) not in (int,float) or not math.isfinite(v) for v in q)
            or abs(sum(v*v for v in q)-1)>1e-12):
        raise ValueError('M9_ABBA_INVALID_NATIVE_UNIT_COEFFICIENTS')
    if any(reference.get(k) is None for k in must_match):
        raise ValueError('M9_ABBA_MISSING_SCIENTIFIC_IDENTITY')
    for i,row in enumerate(rows):
        if not row.get('same_call_passed') or not row.get('exact_geometry_audit_passed'):
            raise ValueError('M9_ABBA_UNVERIFIED_MATERIAL')
        if (row.get('independent_ten_max_scaled_error',1)>1e-10 or
                row.get('historical_ten_max_abs_error',1)>1e-10):
            raise ValueError('M9_ABBA_INDEPENDENT_OR_FROZEN_TEN_CHANGED')
        if (row.get('vertices') != 8455 or row.get('faces') != 16910 or
                len(row.get('ten',[]))!=10 or len(row.get('jacobian',[]))!=10 or
                any(len(line)!=10 for line in row['jacobian']) or
                any(type(v) not in (int,float) or not math.isfinite(v)
                    for v in row['ten']) or
                any(type(v) not in (int,float) or not math.isfinite(v)
                    for line in row['jacobian'] for v in line)):

            raise ValueError('M9_ABBA_WRONG_TEN_JACOBIAN_OR_MESH_SIZE')
        if any(type(row.get(t)) is not int or row[t]<0 for t in
               ('setup_ns','eval_wall_ns','complete_validation_ns')):
            raise ValueError('M9_ABBA_INVALID_TIMER')
        if row['eval_wall_ns']==0 or row['complete_validation_ns']==0:
            raise ValueError('M9_ABBA_ZERO_WALL')
        if not row['backend_identity'].startswith(CHERCHI_ID):
            raise ValueError('M9_ABBA_NON_CHERCHI_BACKEND')
        if any(row.get(k)!=reference[k] for k in must_match):
            raise ValueError('M9_ABBA_SCIENTIFIC_OUTPUT_DRIFT_AT_'+str(i))
        if set(row.get('boundary_flags',{})) != set(AUDIT_TRUE) or not all(
                row['boundary_flags'].get(k) is True for k in AUDIT_TRUE):
            raise ValueError('M9_ABBA_BOUNDARY_FLAGS_INCOMPLETE')
    old=median(x['eval_wall_ns'] for x in rows if x['mode']=='original')
    new=median(x['eval_wall_ns'] for x in rows if x['mode']=='candidate')
    old_whole=median(x['complete_validation_ns'] for x in rows if x['mode']=='original')
    new_whole=median(x['complete_validation_ns'] for x in rows if x['mode']=='candidate')
    return dict(pass_all_four_material_and_jacobian_parity=True,
        single_q_evaluator_old_over_candidate=old/new,
        single_q_with_same_call_audits_old_over_candidate=old_whole/new_whole,
        original_median_eval_ns=old, candidate_median_eval_ns=new,
        original_median_complete_ns=old_whole,candidate_median_complete_ns=new_whole,
        four_samples=4,full_solver_speedup=None,formal_derivative_admission=False)


def run(archive,root,output):
    """ABBA one-q real native experiment; all four material proofs are compulsory."""
    root=Path(root).resolve();archive=Path(archive).resolve();output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    stage='PREFLIGHT'; completed=[]
    prior_handler=None
    try:
        frozen=preflight(archive,root)
        historic=historic_h8c_anchor(archive)
        stage='RESOURCE_LIMIT'
        limits=resource_guard()
        import numpy as np
        import _make_it_stand as native
        import _cherchi_core_boolean as boolean
        import _cherchi_rational_moments as arithmetic
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator,_json_value
        src=Path(inspect.getfile(InProcessCherchiEvaluator))
        if git_blob(src.read_bytes())!=SOURCE_BLOB:
            raise ValueError('M9_IMPORTED_PRODUCTION_SOURCE_DRIFT')
        sys.path.insert(0,str(root/H8/'source'))
        from probe_h8_native_cherchi import initial_ellipsoid_q, request_from_frozen
        from verify_h8_exact_moments import independent_ten_raw_moments
        with tempfile.TemporaryDirectory(prefix='w1-m9-h8c-') as temp:
            request_path=Path(temp)/'prepared-request.json';request_path.write_bytes(frozen)
            request,settings,evidence=request_from_frozen(request_path)
            if evidence.get('original_author_cad') is not False:
                raise ValueError('M9_RECONSTRUCTED_CAD_SCOPE_DRIFT')
            q=np.asarray(initial_ellipsoid_q(request.target_origin),dtype=np.float64)
            historic=historic_h8c_anchor(archive,expected_q=q.tolist())
            expected=model_to_target_identity_ten(historic['model_moments'],
                request.target_origin,request.target_axes)
            old_ledger=InclusiveExclusiveLedger();new_ledger=InclusiveExclusiveLedger()
            Old,Candidate,labels,caches=clone_paired_classes(
                InProcessCherchiEvaluator,old_ledger,new_ledger)

            def timeout_handler(signum, frame):
                raise TimeoutError('M9_NATIVE_ABBA_3600_SECOND_LIMIT')
            prior_handler=signal.signal(signal.SIGALRM,timeout_handler)
            signal.alarm(3600)
            stage='REAL_CHERCHI_ABBA'
            modules=dict(native_sha256=sha(Path(native.__file__).read_bytes()),
                cherchi_sha256=sha(Path(boolean.__file__).read_bytes()),
                gmp_sha256=sha(Path(arithmetic.__file__).read_bytes()))
            for iteration,mode in enumerate(ORDER):
                ledger=old_ledger if mode=='original' else new_ledger
                cls=Old if mode=='original' else Candidate
                began=time.monotonic_ns()
                engine=cls(request,settings,normalization={'origin':[0.,0.,0.],'L':1.},
                    branch_identity_policy='SOURCE_FEATURE_BRANCH_V2',
                    rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
                    fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1',
                    stage_observer=ledger.native)
                setup_ns=time.monotonic_ns()-began
                if not engine.backend_identity.startswith(CHERCHI_ID):
                    raise ValueError('M9_NON_PINNED_CHERCHI_BACKEND')
                start_stage=len(ledger.rows)
                began=time.monotonic_ns()
                evaluated=engine(q)
                eval_ns=time.monotonic_ns()-began
                with ledger.span('audit:same_call_material'):
                    material=engine.material(q)
                    engine.validate_same_call_material(material,q,request)
                with ledger.span('audit:native_exact_rational_boundary'):
                    coords=material['variable_rational_vertices']
                    faces=np.asarray(material['variable_faces'],dtype=np.int32)
                    flags=dict(native.audit_exact_rational_triangle_boundary(coords,faces,'AnyNonzero'))
                    strict_audit(flags)
                with ledger.span('audit:independent_fraction_ten'):
                    independent=np.asarray([float(v) for v in independent_ten_raw_moments(
                        coords,faces.tolist())],dtype=np.float64)
                    ten=np.asarray(evaluated['variable_raw_moments'],dtype=np.float64)
                    jac=np.asarray(evaluated['moment_jacobian'],dtype=np.float64)
                    total=np.asarray(evaluated['raw_moments'],dtype=np.float64)
                    if (ten.shape!=(10,) or jac.shape!=(10,10) or total.shape!=(10,)
                            or not np.isfinite(ten).all() or not np.isfinite(jac).all()
                            or not np.isfinite(total).all() or not np.isfinite(independent).all()):
                        raise ValueError('M9_NATIVE_TEN_OR_JACOBIAN_INVALID')
                    scaled=float(np.max(np.abs(independent-ten)/np.maximum(1.,np.abs(independent))))
                    if scaled>1e-10:
                        raise ValueError('M9_NATIVE_INDEPENDENT_MOMENTS_DIFFER')
                    fixed=np.asarray(engine.fixed,dtype=np.float64)
                    if (fixed.shape!=(10,) or
                            np.max(np.abs(total-(ten+fixed)))>1e-10):
                        raise ValueError('M9_DOUBLE_COUNTED_OR_CHANGED_FIXED_MOMENT')
                    old_ref=float(np.max(np.abs(ten-np.asarray(expected))))
                    if old_ref>1e-10:
                        raise ValueError('M9_HISTORICAL_MODEL_TO_TARGET_REFERENCE_CHANGED')
                with ledger.span('audit:exact_material_serialization'):
                    snapshot=json.dumps(material,default=_json_value,sort_keys=True,allow_nan=False)
                    snap_sha=sha(snapshot.encode())
                    with gzip.open(output/f'point-{iteration:03d}-{mode}.json.gz','wt',encoding='utf-8',compresslevel=5) as stream:
                        stream.write(snapshot)
                finished=time.monotonic_ns()-began
                # The ledger instance is reused for the A...A or B..B arms.
                # Slice strictly at this invocation so earlier same-arm stages
                # never leak into the current call's accounting.
                entries=[dict(e) for e in ledger.rows[start_stage:]]
                exclusive=sum(e['exclusive_ns'] for e in entries)
                if (exclusive>finished or any(e['status']!='PASS' for e in entries)):
                    raise ValueError('M9_PER_CALL_TIMING_DID_NOT_CLOSE')
                actual=dict(wall_ns=finished,exclusive_ns=exclusive,
                    unattributed_ns=finished-exclusive,exclusive_stages=entries,
                    all_returned=True)
                row=dict(iteration=iteration,mode=mode,**modules,setup_ns=setup_ns,
                    eval_wall_ns=eval_ns,complete_validation_ns=finished,
                    material_sha256=snap_sha,geometry_hash=evaluated['geometry_hash'],
                    topology_hash=evaluated['topology_hash'],source_identity=material['quadric_source_identity'],
                    backend_identity=evaluated['boolean_backend_identity'],q=q.tolist(),
                    ten=ten.tolist(),jacobian=jac.tolist(),vertices=len(coords),faces=len(faces),
                    boundary_flags={k:flags[k] for k in AUDIT_TRUE},
                    exact_geometry_audit_passed=True,same_call_passed=True,
                    independent_ten_max_scaled_error=scaled,historical_ten_max_abs_error=old_ref,
                    stage_ledger=actual)
                completed.append(row)
                dump_new(output/f'point-{iteration:03d}-{mode}.json',row)
            checks=certify_abba(completed)
            if len(caches.calls)!=2 or any(x['misses']==0 for x in caches.calls) or caches.cache_info().currsize!=0:
                raise ValueError('M9_PARSER_CACHE_SCOPE_NOT_PER_CALL')
            report=dict(schema='w1-m9-native-h8c-abba-v1',
                scope='FOUR_REAL_H8C_SINGLE_Q_CHERCHI_MATERIALS_NOT_FULL_NEWTON',
                freeze_source_commit=FROZEN,production_source_blob=SOURCE_BLOB,
                request_sha256=REQUEST_SHA,archive_sha256=ARCHIVE_SHA,historical=historic,
                module_binary_sha256=modules,order=ORDER,statement_labels=labels,
                parity_and_timing=checks,measurements=completed,
                parser_cache_scope='PER_Q_CALL_CLEARED_EVEN_ON_EXCEPTION',
                candidate_parser_caches_by_call=caches.calls,
                process_rss_peak_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                platform=platform.platform(),limits=limits,
                native_cherchi_calls=4,real_newton_solves=0,
                full_solver_speedup=None,accepted_terminal_material=None,
                w0_w2_production_admission=False,paper_speed_qualified=False)
            dump_new(output/'baseline-performance.json',report)
            dump_new(output/'before_after.json',dict(schema='w1-m9-before-after-v1',
                candidate_applied_to_production=False,matched_input_and_archived_reference=True,
                full_material_and_jacobian_parity=True,
                single_q_evaluator_ratio=checks['single_q_evaluator_old_over_candidate'],
                single_q_with_audit_ratio=checks['single_q_with_same_call_audits_old_over_candidate'],
                full_solver_speedup=None,newton_and_terminal_parity=None,
                mathematically_admissible_for_merging=False,paper_speed_qualified=False))
            return report
    except BaseException as exc:
        dump_new(output/'failure.json',dict(schema='w1-m9-fail-closed-v1',
            status='BLOCKED_OR_FAILED_NO_NATIVE_ABBA_CERTIFICATE',stage=stage,
            error=f'{type(exc).__name__}: {exc}',completed_points=len(completed),
            old_new_full_solver_speedup=None,paper_speed_qualified=False))
        raise
    finally:
        signal.alarm(0)
        if prior_handler is not None:
            signal.signal(signal.SIGALRM,prior_handler)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report=run(args.archive,args.root,args.output)
    print(json.dumps({'scope':report['scope'],'parity':report['parity_and_timing']},sort_keys=True))


if __name__=='__main__':
    main()
