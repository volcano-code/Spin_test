"""W1 M5: scope-preserving, source-pinned Cherchi call attribution.

Wrap individual top-level Python statements of the ORIGINAL production
InProcessCherchiEvaluator.__call__, and reuse its existing native _stage
observer. Intervals are hierarchically exclusive (nested native time is
subtracted from its surrounding Python statement).

This is DIAGNOSTIC instrumentation, not an optimized evaluation or benchmark.
It does not edit or copy any production src/bindings file on disk.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import gzip
from hashlib import sha1, sha256
import importlib.util
import inspect
import json
from pathlib import Path
import os
import platform
import resource
import signal
import tempfile
import textwrap
import time
from zipfile import ZipFile

FROZEN = '0bcc187b3005478baa586a6d6f450e73811ca342'
SOURCE_BLOB = 'f9fa539f699df8baf8b8d30729048269a26ecb3c'
REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
ARCHIVE_SHA = '78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7'
REQUEST_MEMBER = 'artifacts/h8-request/prepared-request.json'
H8 = 'research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018'
NATIVE_NAMES = frozenset((
    'source','physical_source_boundary','boolean','intersection_motion',
    'prepare_arithmetic_boundary','derivative','integration',
    'material_attachment_serialization',
))
AUDIT_TRUE = (
    'boundary_valid','closed','edge_manifold','vertex_manifold',
    'consistently_oriented','component_orientations_valid',
    'self_intersection_completed','self_intersection_free',
)


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


class InclusiveExclusiveLedger:
    """LIFO hierarchical nested timings, without counting a child twice."""
    def __init__(self):
        self._start = time.monotonic_ns()
        self._stack = []
        self.rows = []

    @contextmanager
    def span(self, name: str):
        if not name or (not name.startswith('python:') and
                        not name.startswith('native:') and
                        not name.startswith('audit:')):
            raise ValueError('M5_UNREGISTERED_STAGE')
        frame = dict(name=name, start=time.monotonic_ns(), children_ns=0)
        self._stack.append(frame)
        status='PASS'
        try:
            yield
        except BaseException:
            status='FAIL'
            raise
        finally:
            if not self._stack or self._stack[-1] is not frame:
                raise RuntimeError('M5_TIMER_STACK_CORRUPTION')
            elapsed=time.monotonic_ns()-frame['start']
            exclusive=elapsed-frame['children_ns']
            if exclusive < 0:
                raise RuntimeError('M5_NEGATIVE_EXCLUSIVE_TIME')
            self._stack.pop()
            if self._stack:
                self._stack[-1]['children_ns'] += elapsed
            self.rows.append(dict(name=name, inclusive_ns=elapsed,
                                  exclusive_ns=exclusive, status=status))

    def native(self, name, op):
        if name not in NATIVE_NAMES:
            raise ValueError('M5_UNKNOWN_NATIVE_STAGE:'+str(name))
        with self.span('native:'+name):
            return op()

    def summary(self):
        if self._stack:
            raise ValueError('M5_UNFINISHED_TIMING_STACK')
        wall=time.monotonic_ns()-self._start
        total=sum(row['exclusive_ns'] for row in self.rows)
        if total>wall:
            raise ValueError('M5_EXCLUSIVE_SUM_EXCEEDS_WALL')
        totals={}
        for row in self.rows:
            totals[row['name']]=totals.get(row['name'],0)+row['exclusive_ns']
        return dict(wall_ns=wall, exclusive_ns=total, unattributed_ns=wall-total,
                    exclusive_stages=self.rows, stage_exclusive_totals_ns=totals,
                    all_returned=all(row['status']=='PASS' for row in self.rows))


def statement_label(node, index):
    # Stable independent of source line-offset: sequence index and target name.
    target='statement'
    if isinstance(node, (ast.Assign,ast.AnnAssign)):
        try:
            t=node.targets[0] if isinstance(node,ast.Assign) else node.target
            target=ast.unparse(t).replace(' ','')[:45]
        except Exception:
            target='assignment'
    elif isinstance(node,ast.For):
        target='for_'+ast.unparse(node.target).replace(' ','')[:25]
    elif isinstance(node,ast.If):
        target='condition'
    elif isinstance(node,ast.Return):
        target='return'
    return 'python:'+f'{index:02d}:'+target


def instrument_call(original, ledger):
    """Recompile __call__ with with-spans; never change mathematical AST nodes.

    The original source file hash must be pinned by the invoking native runner.
    A standalone fake evaluator can use this in tests to prove return/error
    equivalence. A fresh native end-to-end run is necessary for full parity.
    """
    source=textwrap.dedent(inspect.getsource(original))
    tree=ast.parse(source)
    if len(tree.body)!=1 or not isinstance(tree.body[0],(ast.FunctionDef,ast.AsyncFunctionDef)):
        raise ValueError('M5_UNEXPECTED_CALL_STRUCTURE')
    method=tree.body[0]
    if (isinstance(method,ast.AsyncFunctionDef) or method.decorator_list or
            method.args.vararg or method.args.kwarg or
            any(isinstance(n,(ast.Yield,ast.YieldFrom,ast.Await)) for n in ast.walk(method)) or
            any(isinstance(n,ast.Name) and n.id=='__w1_m5_probe' for n in ast.walk(method))):
        raise ValueError('M5_UNSUPPORTED_CALL_SEMANTICS')
    # Preserve a Python docstring if one exists.
    original_body=list(method.body)
    labels=[]
    body=[]
    for index, statement in enumerate(original_body):
        if (index==0 and isinstance(statement,ast.Expr) and
                isinstance(statement.value,ast.Constant) and isinstance(statement.value.value,str)):
            body.append(statement)
            continue
        label=statement_label(statement,index)
        labels.append(label)
        stage=ast.Call(func=ast.Attribute(value=ast.Name(id='__w1_m5_probe',ctx=ast.Load()),
                                        attr='span',ctx=ast.Load()),
                       args=[ast.Constant(value=label)],keywords=[])
        wrapper=ast.With(items=[ast.withitem(context_expr=stage,optional_vars=None)],
                         body=[statement],type_comment=None)
        ast.copy_location(wrapper,statement)
        body.append(wrapper)
    if not labels:
        raise ValueError('M5_EMPTY_CALL')
    method.body=body
    ast.fix_missing_locations(tree)
    namespace=dict(original.__globals__)
    namespace['__w1_m5_probe']=ledger
    compiled={}
    exec(compile(tree,original.__code__.co_filename+'[W1M5]',mode='exec'),namespace,compiled)
    wrapped=compiled[method.name]
    if (wrapped.__code__.co_argcount!=original.__code__.co_argcount or
            wrapped.__code__.co_kwonlyargcount!=original.__code__.co_kwonlyargcount):
        raise ValueError('M5_CALL_SIGNATURE_DRIFT')
    return wrapped,labels


def resource_guard():
    swap=Path('/proc/swaps')
    if not swap.is_file() or len(swap.read_text().splitlines())!=1:
        raise RuntimeError('M5_REQUIRES_SWAP_ZERO')
    budget=24*1024**3
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    bound=min([budget]+[value for value in (soft,hard) if value!=resource.RLIM_INFINITY])
    resource.setrlimit(resource.RLIMIT_AS,(bound,hard))
    return dict(address_space_bytes=bound,swap_enabled=False,
                wall_timeout_seconds=3600,compile_workers_max=4)


def strict_audit(facts):
    if (any(facts.get(k) is not True for k in AUDIT_TRUE) or
            facts.get('intersecting_pairs') or facts.get('degenerate_faces') or
            facts.get('intersection_error')):
        raise ValueError('M5_REAL_EXACT_BOUNDARY_REJECTED')


def dump_new(path, contents):
    path=Path(path)
    with path.open('x',encoding='utf-8') as f:
        json.dump(contents,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')


def preflight(archive: Path, root: Path):
    """Refuse mismatched input, unpinned production source, missing native libs."""
    archive=Path(archive)
    if sha(archive.read_bytes())!=ARCHIVE_SHA:
        raise ValueError('M5_ARCHIVE_HASH_DRIFT')
    src=root/'python/make_it_stand/verification/cherchi_inprocess.py'
    if not src.is_file() or git_blob(src.read_bytes())!=SOURCE_BLOB:
        raise ValueError('M5_PRODUCTION_SOURCE_UNPINNED')
    with ZipFile(archive) as z:
        members=[x for x in z.infolist() if x.filename==REQUEST_MEMBER]
        if len(members)!=1 or members[0].file_size>7_000_000:
            raise ValueError('M5_REQUEST_MEMBER_INVALID')
        raw=z.read(members[0])
        if sha(raw)!=REQUEST_SHA:
            raise ValueError('M5_REQUEST_HASH_DRIFT')
        request=json.loads(raw)
        if (request.get('schema')!='spin-heart-h8-faster-preparation-v1' or
                request.get('evidence',{}).get('original_author_cad') is not False):
            raise ValueError('M5_H8_RECONSTRUCTED_SCOPE_DRIFT')
    missing=[name for name in ('_make_it_stand','_cherchi_core_boolean','_cherchi_rational_moments')
             if importlib.util.find_spec(name) is None]
    if missing:
        raise RuntimeError('M5_NATIVE_MODULES_UNAVAILABLE:'+','.join(missing))
    return raw


def native_run(archive, root, output):
    """One SAME-CALL full Cherchi evaluation+required checks, NOT Newton solve."""
    root=Path(root).resolve();output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    ledger=InclusiveExclusiveLedger()
    try:
        raw=preflight(Path(archive),root)
        limits=resource_guard()
        import sys
        sys.path.insert(0,str(root/'python'))
        import numpy as np
        import _make_it_stand as native
        import _cherchi_core_boolean as cherchi
        import _cherchi_rational_moments as gmp
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
        from make_it_stand.verification.cherchi_inprocess import _json_value
        sys.path.insert(0,str(root/H8/'source'))
        from probe_h8_native_cherchi import initial_ellipsoid_q,request_from_frozen
        from verify_h8_exact_moments import independent_ten_raw_moments
        if git_blob(Path(inspect.getfile(InProcessCherchiEvaluator)).read_bytes())!=SOURCE_BLOB:
            raise ValueError('M5_IMPORTED_SOURCE_NOT_PINNED')
        wrapped,labels=instrument_call(InProcessCherchiEvaluator.__call__,ledger)
        Profiled=type('W1DiagnosticEvaluator',(InProcessCherchiEvaluator,),{'__call__':wrapped})
        with tempfile.TemporaryDirectory(prefix='w1-m5-h8-') as tmp:
            frozen=Path(tmp)/'prepared-request.json';frozen.write_bytes(raw)
            request,settings,evidence=request_from_frozen(frozen)
            q=np.asarray(initial_ellipsoid_q(request.target_origin),dtype=np.float64)
            profiler=Profiled(request,settings,normalization={'origin':[0.,0.,0.],'L':1.},
                rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
                fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1',
                branch_identity_policy='SOURCE_FEATURE_BRANCH_V2',stage_observer=ledger.native)
            if not profiler.backend_identity.startswith('cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'):
                raise ValueError('M5_NON_CHERCHI_BACKEND')
            signal.alarm(3600)
            eval_start=time.monotonic_ns()
            result=profiler(q)
            with ledger.span('audit:same_call_material'):
                material=profiler.material(q)
                profiler.validate_same_call_material(material,q,request)
            with ledger.span('audit:native_exact_rational_boundary'):
                vertices=material['variable_rational_vertices']
                faces=np.asarray(material['variable_faces'],dtype=np.int32)
                facts=dict(native.audit_exact_rational_triangle_boundary(vertices,faces,'AnyNonzero'))
                strict_audit(facts)
            with ledger.span('audit:independent_fraction_ten'):
                reference=np.asarray([float(x) for x in independent_ten_raw_moments(
                    vertices,faces.tolist())],dtype=np.float64)
                produced=np.asarray(result['variable_raw_moments'],dtype=np.float64)
                jac=np.asarray(result['moment_jacobian'],dtype=np.float64)
                if (produced.shape!=(10,) or reference.shape!=(10,) or jac.shape!=(10,10)
                        or not np.isfinite(jac).all() or
                        not np.isfinite(reference).all() or not np.isfinite(produced).all()):
                    raise ValueError('M5_INVALID_JACOBIAN_OR_MOMENTS')
                parity=float(np.max(np.abs(produced-reference)/np.maximum(1.,np.abs(reference))))
                if parity>1e-10:
                    raise ValueError('M5_INDEPENDENT_MOMENTS_MISMATCH')
            with ledger.span('audit:complete_material_snapshot'):
                with gzip.open(output/'same-call-material.json.gz','wt',encoding='utf-8',compresslevel=5) as fp:
                    json.dump(material,fp,sort_keys=True,allow_nan=False,default=_json_value)
            wall=time.monotonic_ns()-eval_start
            prof=ledger.summary()
            if not prof['all_returned']:
                raise ValueError('M5_INCOMPLETE_STAGE_RECORD')
            report=dict(schema='w1-m5-native-h8-instrumented-sample-v1',
                scope='FRESH_H8_RECONSTRUCTED_SINGLE_Q_NOT_FULL_SOLVER',
                fresh_boolean_calls=1,input_request_sha256=REQUEST_SHA,
                root_source_sha=FROZEN,source_git_blob=SOURCE_BLOB,
                archive_sha256=ARCHIVE_SHA,
                native_binary_sha256=sha(Path(native.__file__).read_bytes()),
                cherchi_binary_sha256=sha(Path(cherchi.__file__).read_bytes()),
                gmp_binary_sha256=sha(Path(gmp.__file__).read_bytes()),
                geometry_hash=result['geometry_hash'],topology_hash=result['topology_hash'],
                ten_moment_max_scaled_error=parity,
                jacobian_shape=[10,10], material_vertices=len(vertices),
                material_faces=len(faces),q=q.tolist(),
                all_boundary_proof_flags={name:facts[name] for name in AUDIT_TRUE},
                instrumented_statement_labels=labels,profiler=prof,
                sample_and_validation_wall_ns=wall,
                memory=dict(process_rss_hwm_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                            platform=platform.platform(),limits=limits),
                full_solver_measured=False,terminal_material_accepted=False,
                w0_w2_admission_confirmed=False,paper_speed_qualified=False)
            dump_new(output/'baseline-performance.json',report)
            dump_new(output/'before_after.json',dict(schema='w1-m5-before-after-v1',
                paired_old_new_full_solver_runs=0,full_solver_speedup=None,
                proof_of_production_optimization=False,paper_speed_qualified=False))
            return report
    except BaseException as ex:
        dump_new(output/'failure.json',dict(schema='w1-m5-fail-closed-v1',
            status='FAILED_NO_FRESH_NATIVE_CERTIFICATION',error=f'{type(ex).__name__}: {ex}',
            timing=ledger.summary(),paper_speed_qualified=False))
        raise
    finally:
        signal.alarm(0)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=native_run(args.archive,args.root,args.output)
    print('W1_M5_REAL_NATIVE_H8',result['scope'],flush=True)


if __name__=='__main__':
    main()
