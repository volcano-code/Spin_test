"""W1 V2 M19: profile the EXACT frozen real H8e Cherchi 25-point driver.

The original H8e run/solver source AST statement nodes are not edited; this
source-pinned, W1-only diagnostic adds nested timing contexts around them.
It NEVER makes a historical failure a smooth-stratum, Newton or speed claim.
A missing full native checkout/module makes only a failure receipt (exit 2).
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import signal
import sys
import tempfile
import time

from m5_native_call_instrumentation import (
    ARCHIVE_SHA, REQUEST_SHA, SOURCE_BLOB, git_blob, instrument_call,
)
import m10_native_host_runner as native_host

H8E_SOURCE_REL = Path('research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/probe_h8_jacobian.py')
H8E_SOURCE_BLOB = '0c219e34869c454db655e62f23d18e59ba4db494'
REQUEST_MEMBER = 'artifacts/h8-request/prepared-request.json'
CERT_MEMBER = 'artifacts/h8-cherchi-point/exact-ten-moment-certificate.json'
REFERENCE_MEMBER = 'artifacts/h8-cherchi-point/result.json'
H8C_REFERENCE_SHA = 'dd1d46e765ce6e99e58b340db9de5e30e4f23f1d3967b38fed7a6133e321eeba'
H8C_CERT_SHA = '301ec94084e627b94608d1d904340d9ce9cd1123afffbc42f00611589751541c'
PHASES = ('EVALUATE_INPROCESS_CHERCHI', 'SAME_CALL_MATERIAL_ATTACHMENT',
          'EXACT_NATIVE_MATERIAL_GEOMETRY_AUDIT',
          'INDEPENDENT_FRACTION_MATERIAL_TEN_MOMENTS',
          'WRITE_COMPLETE_SAME_CALL_MATERIAL', 'WRITE_EVIDENCE')
MAX_SAMPLES = 25


def _dump_new(path, obj):
    path=Path(path)
    with path.open('x',encoding='utf-8') as fp:
        json.dump(obj,fp,indent=2,sort_keys=True,allow_nan=False)
        fp.write('\n')


class NestedRealStageLedger:
    """Nested inclusive and disjoint-exclusive monotonic timings per H8 point.

    A point owns phase spans; each phase contains original evaluator statement
    spans and native observer spans. Sum ONLY exclusive, not inclusive, times.
    """
    def __init__(self):
        self.begin=time.monotonic_ns()
        self._stack=[]
        self.rows=[]

    @contextmanager
    def span(self, name: str, point: int | None = None):
        if not (name.startswith(('point:', 'phase:', 'python:', 'native:', 'audit:'))):
            raise ValueError('M19_UNREGISTERED_TIMING_STAGE')
        if point is not None and (type(point) is not int or not 0 <= point < MAX_SAMPLES):
            raise ValueError('M19_INVALID_POINT_INDEX')
        if name.startswith('point:'):
            if self._stack or point is None:
                raise ValueError('M19_POINT_SPAN_NESTING_VIOLATION')
        else:
            if not self._stack:
                raise ValueError('M19_STAGE_WITHOUT_POINT')
            point=self._stack[-1]['point']
        started=time.monotonic_ns()
        frame=dict(name=name,point=point,start=started,children_ns=0)
        self._stack.append(frame)
        status='PASS'
        try:
            yield
        except BaseException:
            status='FAIL'
            raise
        finally:
            if not self._stack or self._stack[-1] is not frame:
                raise RuntimeError('M19_STAGE_STACK_CORRUPTED')
            elapsed=time.monotonic_ns()-started
            exclusive=elapsed-frame['children_ns']
            if exclusive<0:
                raise RuntimeError('M19_NEGATIVE_EXCLUSIVE_DURATION')
            self._stack.pop()
            if self._stack:
                self._stack[-1]['children_ns']+=elapsed
            self.rows.append(dict(point=point,name=name,status=status,
                                  inclusive_ns=elapsed,exclusive_ns=exclusive))

    def native(self,name,operation):
        if name not in ('source','physical_source_boundary','boolean',
                        'intersection_motion','prepare_arithmetic_boundary',
                        'derivative','integration','material_attachment_serialization'):
            raise ValueError('M19_UNKNOWN_NATIVE_STAGE:'+str(name))
        with self.span('native:'+name):
            return operation()

    def summarize(self, *, expected_points: int | None=None):
        if self._stack:
            raise ValueError('M19_OPEN_TIMING_STACK')
        elapsed=time.monotonic_ns()-self.begin
        roots=[r for r in self.rows if r['name'].startswith('point:')]
        indexes=[r['point'] for r in roots]
        if len(set(indexes))!=len(indexes) or sorted(indexes)!=list(range(len(indexes))):
            raise ValueError('M19_DUPLICATE_OR_NONCONSECUTIVE_POINTS')
        if expected_points is not None and len(indexes)!=expected_points:
            raise ValueError('M19_POINT_COUNT_INCOMPLETE')
        if sum(r['inclusive_ns'] for r in roots)>elapsed:
            raise ValueError('M19_POINT_WALL_OVERLAP')
        per_point=[]
        for root in sorted(roots,key=lambda r:r['point']):
            index=root['point']
            group=[r for r in self.rows if r['point']==index]
            if sum(r['exclusive_ns'] for r in group)!=root['inclusive_ns']:
                raise ValueError('M19_PER_POINT_EXCLUSIVE_LEDGER_NOT_CLOSED')
            spans=[r for r in group if r['name'].startswith('phase:')]
            if root['status']=='PASS':
                if [r['name'] for r in sorted(spans,key=lambda r:PHASES.index(r['name'][6:]))] != [
                        'phase:'+p for p in PHASES]:
                    raise ValueError('M19_REQUIRED_PHASE_MISSING_OR_DUPLICATE')
            phases={r['name'][6:]:r['inclusive_ns'] for r in spans}
            stages={}
            for r in group:
                if r is root:
                    continue
                stages[r['name']]=stages.get(r['name'],0)+r['exclusive_ns']
            stages['unwrapped_point_overhead']=root['exclusive_ns']
            per_point.append(dict(index=index,status=root['status'],
                point_wall_ns=root['inclusive_ns'],phase_inclusive_ns=phases,
                disjoint_stage_exclusive_ns=stages,
                exclusive_sum_ns=sum(stages.values())))
        return dict(schema='w1-m19-pinned-real-h8e-hierarchical-ledger-v1',
            scope='FRESH_FROZEN_H8E_HIERARCHICAL_PROFILE_NOT_OPTIMIZED_ABBA',
            wall_ns=elapsed,points=len(roots),
            point_wall_sum_ns=sum(r['inclusive_ns'] for r in roots),
            outside_point_ns=elapsed-sum(r['inclusive_ns'] for r in roots),
            all_completed=all(r['status']=='PASS' for r in roots),
            per_point=per_point,rows=self.rows,
            newton_solver_calls=0,full_solver_speedup=None,
            production_speedup_admitted=False,paper_speed_qualified=False)


def _is_stage_assign(node):
    if not isinstance(node,ast.Assign) or len(node.targets)!=1:
        return None
    if not isinstance(node.targets[0],ast.Name) or node.targets[0].id!='stage':
        return None
    if not isinstance(node.value,ast.Constant) or not isinstance(node.value.value,str):
        return None
    return node.value.value


def _context(name,body,at,point=False):
    args=[ast.Constant(name)] + ([ast.Name(id='i',ctx=ast.Load())] if point else [])
    expr=ast.Call(func=ast.Attribute(value=ast.Name(id='__w1_m19_ledger',ctx=ast.Load()),
                    attr='span',ctx=ast.Load()),args=args,keywords=[])
    statement=ast.With(items=[ast.withitem(context_expr=expr,optional_vars=None)],
                       body=body,type_comment=None)
    return ast.copy_location(statement,at)


def rewrite_frozen_run(source: str, *, source_blob: str = H8E_SOURCE_BLOB,
                       check_pin: bool=True):
    """Wrap original AST nodes without altering their operands or expressions.

    Fail closed on a different frozen H8e driver structure. The only injected
    evaluator change is timing observers; no bypassed check or altered q.
    """
    if check_pin and git_blob(source.encode())!=source_blob:
        raise ValueError('M19_FROZEN_H8E_SOURCE_GIT_BLOB_MISMATCH')
    tree=ast.parse(source)
    run=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run']
    if len(run)!=1 or run[0].decorator_list:
        raise ValueError('M19_FROZEN_H8E_RUN_STRUCTURE_DRIFT')
    fn=run[0]
    relevant=[]
    for node in ast.walk(fn):
        if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple) and len(node.target.elts)==2:
            names=[x.id if isinstance(x,ast.Name) else None for x in node.target.elts]
            if names==['i','coefficients']:
                relevant.append(node)
    if len(relevant)!=1:
        raise ValueError('M19_ORIGINAL_H8E_POINT_LOOP_NOT_UNIQUE')
    point_loop=relevant[0]
    idx=[j for j,node in enumerate(point_loop.body) if isinstance(node,ast.Try)]
    if len(idx)!=1:
        raise ValueError('M19_ORIGINAL_H8E_TRY_NOT_UNIQUE')
    guarded=point_loop.body[idx[0]]
    if not any(_is_stage_assign(n)=='EVALUATE_INPROCESS_CHERCHI' for n in point_loop.body[:idx[0]]):
        raise ValueError('M19_ORIGINAL_INITIAL_EVALUATION_PHASE_ABSENT')
    new_body=[]; pending=[];current=PHASES[0]; transitions=[]
    def flush():
        nonlocal pending
        if pending:
            new_body.append(_context('phase:'+current,pending,pending[0]))
            pending=[]
    for node in guarded.body:
        state=_is_stage_assign(node)
        if state is not None:
            flush()
            if state not in PHASES[1:] or state in transitions:
                raise ValueError('M19_UNEXPECTED_OR_DUPLICATE_PHASE:'+str(state))
            transitions.append(state)
            current=state
            new_body.append(node)  # original exception diagnostics unchanged
        else:
            pending.append(node)
    flush()
    if transitions!=list(PHASES[1:]) or len(new_body)!=len(PHASES)*2-1:
        raise ValueError('M19_ORIGINAL_H8E_PHASE_LAYOUT_DRIFT')
    guarded.body=new_body
    point_loop.body=[_context('point:all',point_loop.body,point_loop,point=True)]
    # Replace only the locally imported evaluator by an instrumented subclass.
    # The import and all source AST computations are unchanged.
    found=0; remap=[]
    for node in fn.body:
        remap.append(node)
        if (isinstance(node,ast.ImportFrom) and
            node.module=='make_it_stand.verification.cherchi_inprocess' and
            len(node.names)==1 and node.names[0].name=='InProcessCherchiEvaluator'):
            expr=ast.Assign(targets=[ast.Name(id='InProcessCherchiEvaluator',ctx=ast.Store())],
                 value=ast.Call(func=ast.Name(id='__w1_m19_rebind',ctx=ast.Load()),
                                args=[ast.Name(id='InProcessCherchiEvaluator',ctx=ast.Load()),
                                      ast.Name(id='__w1_m19_ledger',ctx=ast.Load())],keywords=[]))
            remap.append(ast.copy_location(expr,node));found+=1
    if found!=1:
        raise ValueError('M19_FROZEN_EVALUATOR_IMPORT_DRIFT')
    fn.body=remap
    ast.fix_missing_locations(fn)
    return ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),tuple(PHASES)


def make_timed_class(cls,ledger):
    import inspect
    original_file=Path(inspect.getfile(cls)).read_bytes()
    if git_blob(original_file)!=SOURCE_BLOB:
        raise ValueError('M19_PRODUCTION_EVALUATOR_HASH_MISMATCH')
    transformed,labels=instrument_call(cls.__call__,ledger)
    if not labels:
        raise ValueError('M19_MISSING_EVALUATOR_STATEMENT_LABELS')
    def observed_call(self, *args, **kwargs):
        # Observer is temporarily active ONLY inside the original __call__.
        # Thus the actual frozen _stage body, arguments and return values stay
        # unchanged while nested C++/Python stages become disjointly timed.
        before=self.stage_observer
        if before is not None:
            raise ValueError('M19_EXISTING_STAGE_OBSERVER_MUST_NOT_BE_REPLACED')
        self.stage_observer=ledger.native
        try:
            return transformed(self,*args,**kwargs)
        finally:
            self.stage_observer=before
    return type('W1M19FrozenDiagnosticEvaluator',(cls,),{'__call__':observed_call})


def build_profiled_function(original_globals,source,ledger, *, rebind=make_timed_class,
                            check_pin=True):
    ast_run,phases=rewrite_frozen_run(source,check_pin=check_pin)
    namespace=dict(original_globals)
    namespace['__w1_m19_ledger']=ledger
    namespace['__w1_m19_rebind']=rebind
    local={}
    exec(compile(ast_run,namespace.get('__file__','<H8e-run>')+'[W1M19]','exec'),namespace,local)
    fn=local['run']
    return fn,phases


def _read_member(archive, member, limit):
    matches=[m for m in archive.infolist() if m.filename==member]
    if len(matches)!=1 or not 0<matches[0].file_size<=limit:
        raise ValueError('M19_H8C_MEMBER_ABSENT_DUPLICATE_OR_OVERSIZED:'+member)
    return archive.read(matches[0])


def prepare_h8c_inputs(archive,tmp):
    from zipfile import ZipFile
    if sha256(Path(archive).read_bytes()).hexdigest()!=ARCHIVE_SHA:
        raise ValueError('M19_PINNED_H8C_ZIP_SHA_MISMATCH')
    mapping={REQUEST_MEMBER:'request.json',CERT_MEMBER:'certificate.json',REFERENCE_MEMBER:'reference.json'}
    outputs={}
    with ZipFile(archive) as z:
        for member,filename in mapping.items():
            target=Path(tmp)/filename
            target.write_bytes(_read_member(z,member,7_000_000 if member==REQUEST_MEMBER else 500_000))
            outputs[member]=target
    return outputs


def cross_build_reference_authority(inputs, source_module_sha256):
    """Identify a *different binary* run and authenticate the original H8c proof.

    Never describe different compiled module bytes as reproduction of the
    cloud build. The historical reference remains a numeric anchor, not a
    cross-build material/Jacobian bitwise identity certificate.
    """
    if set(source_module_sha256) != {'_make_it_stand', '_cherchi_core_boolean',
                                       '_cherchi_rational_moments'}:
        raise ValueError('M19_FRESH_NATIVE_BINARY_PROVENANCE_INCOMPLETE')
    reference_bytes=Path(inputs[REFERENCE_MEMBER]).read_bytes()
    certificate_bytes=Path(inputs[CERT_MEMBER]).read_bytes()
    request_bytes=Path(inputs[REQUEST_MEMBER]).read_bytes()
    ref=json.loads(reference_bytes)
    cert=json.loads(certificate_bytes)
    if (sha256(reference_bytes).hexdigest()!=H8C_REFERENCE_SHA or
        sha256(certificate_bytes).hexdigest()!=H8C_CERT_SHA or
        sha256(request_bytes).hexdigest()!=REQUEST_SHA or
        ref.get('status')!='ACTUAL_CHERCHI_ONE_POINT_RATIONAL_BOUNDARY_PASSED_NOT_OPTIMIZED' or
        cert.get('schema')!='h8c-exact-ten-mass-moment-double-implementation-v1' or
        cert.get('frozen_request_sha256')!=REQUEST_SHA or
        cert.get('verified_actual_packet_sha256')!=ref.get('actual_packet_archive_sha256') or
        cert.get('exact_ten_moments_independently_reproduced') is not True or
        cert.get('full_jacobian_passed') is not False or
        not all(isinstance(ref.get(key),str) and len(ref[key])==64 for key in
                ('native_sha256','cherchi_sha256')) or
        ref.get('material_vertices')!=8455 or ref.get('material_faces')!=16910):
        raise ValueError('M19_FRESH_NATIVE_ARCHIVED_AUTHORITY_INVALID')
    original={'_make_it_stand':ref['native_sha256'],
              '_cherchi_core_boolean':ref['cherchi_sha256']}
    if all(source_module_sha256[k]==original[k] for k in original):
        raise ValueError('M19_FRESH_NATIVE_NO_BINARY_DIFFERENCE_USE_STRICT_MODE')
    return dict(
        mode='FRESH_NATIVE_DIFFERENT_ELF_BINARY_SAME_PINNED_SOURCE',
        archived_reference_sha256=sha256(reference_bytes).hexdigest(),
        archived_certificate_sha256=sha256(certificate_bytes).hexdigest(),
        frozen_request_sha256=REQUEST_SHA,
        archived_binary_sha256=original,
        local_binary_sha256=dict(source_module_sha256),
        same_binary_as_archived=False,
        archived_jacobian_admitted=False,
        cross_build_full_material_sha_identical=None,
        historical_numeric_anchor_allowed_only_after_first_point_check=True,
        archived_ten=cert.get('variable_raw_ten_moments_normalized'),
        archived_q=ref.get('exploratory_q'))


def cross_build_first_point_audit(authority, point, request, frozen_module):
    """Check the fresh same-input point against the historic 10 moments.

    The frozen H8e already compares this same model-to-target moment formula
    at 1e-10, but its prior mode also requires literal old compiled .so bytes.
    We keep the *numerical* anchor while honestly distinguishing the binaries.
    """
    import numpy as np
    from probe_h8_native_cherchi import initial_ellipsoid_q
    q=np.asarray(initial_ellipsoid_q(np.asarray(request.target_origin,dtype=np.float64)))
    historical_q=np.asarray(authority['archived_q'],dtype=np.float64)
    archived_ten=np.asarray(authority['archived_ten'],dtype=np.float64)
    observed=np.asarray(point.get('independent_variable_raw_moments'),dtype=np.float64)
    if (q.shape!=(10,) or historical_q.shape!=(10,) or not np.array_equal(q,historical_q)
            or archived_ten.shape!=(10,) or observed.shape!=(10,) or
            not np.isfinite(archived_ten).all() or not np.isfinite(observed).all()):
        raise ValueError('M19_FRESH_NATIVE_REFERENCE_Q_OR_TEN_INVALID')
    mapped=frozen_module.model_to_target_raw_ten_moments(
        archived_ten,request.target_origin,request.target_axes)
    if point.get('vertex_count')!=8455 or point.get('triangle_count')!=16910:
        raise ValueError('M19_FRESH_NATIVE_HISTORICAL_BASE_MESH_COUNT_DIFFERENCE')
    err=float(np.max(np.abs(mapped-observed)))
    if not np.isfinite(err) or err>1e-10:
        raise ValueError('M19_FRESH_NATIVE_HISTORICAL_TEN_MOMENT_DIFFERENCE')
    return dict(status='PASS_HISTORICAL_TEN_MOMENT_ANCHOR_ONLY',
                max_abs_model_to_target_ten_error=err,
                accepted_max_abs_error=1e-10,
                first_point_vertex_count=point['vertex_count'],
                first_point_triangle_count=point['triangle_count'],
                exact_same_call_validation_from_frozen_run=True,
                historical_binary_sha_parity=False,
                historical_jacobian_bitwise_parity_not_tested=True,
                full_newton_solves=0)


def environment_preflight(root,archive,module_dirs):
    root,archive=Path(root).resolve(),Path(archive).resolve()
    result=native_host.preflight(root,archive,module_dirs)
    source=root/H8E_SOURCE_REL
    try:
        if git_blob(source.read_bytes())!=H8E_SOURCE_BLOB:
            raise ValueError('M19_FROZEN_H8E_SOURCE_NOT_PRESENT_OR_PINNED')
        result['checks']['h8e_original_source']=dict(status='PASS',blob=H8E_SOURCE_BLOB)
    except (OSError,ValueError) as exc:
        result['checks']['h8e_original_source']=dict(status='BLOCKED',reason=str(exc))
        result['blockers'].append('h8e_original_source')
    memory=result['checks'].get('memory',{})
    available=memory.get('details',{}).get('process_address_space_cap_bytes',0)
    if available<6*1024**3:
        result['checks']['M19_conservative_memory']=dict(status='BLOCKED',
            reason='M19_H8E_HOST_BELOW_6_GIB_VIRTUAL_MEMORY_CAP')
        result['blockers'].append('M19_conservative_memory')
    else:
        result['checks']['M19_conservative_memory']=dict(status='PASS',cap=available)
    result['state']='BLOCKED' if result['blockers'] else 'READY_FOR_REAL_H8E_PROFILING'
    return result


def require_zero_swap_for_native():
    """Recheck zero swap at execution using the M10 preflight's exact rule.

    Linux /proc/swaps headers vary in whitespace across kernels; comparing
    header bytes (tabs/spaces) produces false failures on swap-free hosts.
    M10 deliberately checks the *number of lines* rather than header bytes.
    Active swap, a missing swap table and other M10 guard failures stay fatal.
    """
    native_host._swap_guard()


def run_native(root,archive,output,*,module_dirs=(),baseline_mode='strict'):
    if baseline_mode not in ('strict','fresh-native'):
        raise ValueError('M19_INVALID_BASELINE_MODE')
    root,archive,output=Path(root).resolve(),Path(archive).resolve(),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    checks=environment_preflight(root,archive,module_dirs)
    _dump_new(output/'preflight.json',checks)
    if checks['state']!='READY_FOR_REAL_H8E_PROFILING':
        _dump_new(output/'failure.json',dict(schema='w1-m19-native-preflight-blocked-v1',
            status='BLOCKED_NO_BOOLEAN_EVALUATIONS',blockers=checks['blockers'],
            fresh_native_cherchi_calls=0,full_solver_speedup=None))
        return dict(state='BLOCKED',blockers=checks['blockers'])
    memory=checks['checks']['memory']['details']['process_address_space_cap_bytes']
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS,(min(memory,soft if soft!=resource.RLIM_INFINITY else memory),hard))
    require_zero_swap_for_native()
    from m10_native_host_runner import _native_job_lock
    import importlib.util
    paths=[root/'python',root/H8E_SOURCE_REL.parent,*native_host.module_roots(root,module_dirs)]
    for path in reversed(paths):
        if str(path) not in sys.path:sys.path.insert(0,str(path))
    stage='BEFORE_REAL_EVALUATION'
    ledger=NestedRealStageLedger()
    prev=signal.getsignal(signal.SIGALRM)
    try:
        with _native_job_lock(), tempfile.TemporaryDirectory(prefix='w1-m19-real-h8e-') as td:
            manifest=prepare_h8c_inputs(archive,td)
            spec=importlib.util.spec_from_file_location('w1_m19_pinned_h8e_original',root/H8E_SOURCE_REL)
            if spec is None or spec.loader is None:raise ImportError('M19_CANNOT_IMPORT_FROZEN_H8E')
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            timed,phases=build_profiled_function(vars(module),(root/H8E_SOURCE_REL).read_text(),ledger)
            def timeout(signum,frame):
                raise TimeoutError('M19_H8E_3600_SECONDS_EXCEEDED')
            signal.signal(signal.SIGALRM,timeout)
            signal.alarm(3600)
            stage='REAL_H8E_25_POINT_CHERCHI'
            orig_output=output/'actual-frozen-h8e'
            authority=None
            if baseline_mode=='fresh-native':
                modules=checks['checks']['native_modules']['modules']
                provenance={key:modules[key]['sha256'] for key in native_host.NATIVE}
                authority=cross_build_reference_authority(manifest,provenance)
                # Explicit *different-binary* experiment: the unchanged
                # frozen H8e runner performs ALL original native/math checks,
                # but cannot claim the archived ELF byte identity. The
                # historic first point is checked independently below.
                report=timed(manifest[REQUEST_MEMBER],orig_output,'0,4,8',None,None)
                import numpy as np
                from probe_h8_native_cherchi import request_from_frozen
                request,_,_=request_from_frozen(manifest[REQUEST_MEMBER])
                anchor=json.loads((orig_output/'point-000.json').read_text())
                authority['first_point_audit']=cross_build_first_point_audit(
                    authority,anchor,request,module)
                # Never put a cross-build result under the historical same-ELF
                # name or silently mark historical source feature stability.
                _dump_new(output/'fresh-native-cross-build-authority.json',authority)
            else:
                report=timed(manifest[REQUEST_MEMBER],orig_output,'0,4,8',
                             manifest[CERT_MEMBER],manifest[REFERENCE_MEMBER])
            science_pass=(report.get('completed_samples')==25 and
                          report.get('all_numerical_checks_passed') is True)
            times=ledger.summarize(expected_points=25)
            if not science_pass or not times['all_completed']:
                raise ValueError('M19_NATIVE_H8E_25POINT_NOT_COMPLETE')
            receipt=dict(schema='w1-m19-fresh-native-h8e-stage-profile-v1',
                scope='FRESH_FROZEN_H8E_25POINT_NOT_NEWTON_NOT_W1_OPTIMIZED_ABBA',
                original_driver_source_git_blob=H8E_SOURCE_BLOB,
                original_evaluator_source_git_blob=SOURCE_BLOB,
                archive_sha256=ARCHIVE_SHA,profile=times,
                original_h8e_report_file='actual-frozen-h8e/report.json',
                original_numerical_fd_passed=True,
                original_changed_feature_hash_points=report['changed_feature_hash_points'],
                source_branch_stable=report.get('all_tested_stencils_same_feature_hash') is True,
                valid_neighborhood_certified=False,actual_faster_newton_runs=0,
                optimized_cherchi_abba_runs=0,full_solver_speedup=None,
                paper_speed_qualified=False,platform=platform.platform(),
                baseline_mode=baseline_mode,
                cross_build_reference_audit=(authority['first_point_audit']
                     if authority is not None else None),
                historical_same_binary_identity=(authority is None),
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            _dump_new(output/'baseline-performance.json',receipt)
            if receipt['source_branch_stable'] is False:
                # Preserve the original H8e failure; timing still complete.
                _dump_new(output/'failure.json',dict(schema='w1-m19-h8e-branch-drift-v1',
                    status='NATIVE_TIMING_COMPLETE_BUT_SMOOTH_ADMISSION_FAILED',
                    changed_feature_hash_points=receipt['original_changed_feature_hash_points'],
                    full_solver_speedup=None))
                return dict(state='NATIVE_TIMING_COMPLETE_SMOOTH_BRANCH_FAILED',
                            native_calls=25,full_solver_speedup=None)
            return dict(state='NATIVE_TIMING_COMPLETE_NOT_NEWTON',native_calls=25,
                        full_solver_speedup=None)
    except BaseException as error:
        # A mid-run native exception MUST NOT discard the genuine timing spans.
        # Save them separately, clearly labeled partial and never as baseline.
        if ledger.rows and not (output/'partial-stage-ledger.json').exists():
            try:
                partial=ledger.summarize()
                partial['status']='PARTIAL_OR_FAILED_NOT_SCIENTIFICALLY_ADMITTED'
                _dump_new(output/'partial-stage-ledger.json',partial)
            except BaseException:
                pass  # the original exception remains the authoritative failure
        if not (output/'failure.json').exists():
            _dump_new(output/'failure.json',dict(schema='w1-m19-native-failure-v1',
                status='FAILED_CLOSED',stage=stage,
                error=f'{type(error).__name__}: {error}',
                complete_points=sum(r['name'].startswith('point:') for r in ledger.rows),
                full_solver_speedup=None))
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM,prev)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--archive',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--module-dir',type=Path,action='append',default=[])
    ap.add_argument('--preflight-only',action='store_true')
    ap.add_argument('--baseline-mode',choices=('strict','fresh-native'),default='strict',
        help='strict: same archived native binaries; fresh-native: explicit new-build '             '25-point profiling with independent historic first-point ten-moment audit')
    a=ap.parse_args()
    if a.preflight_only:
        if a.output.exists():raise FileExistsError('M19_OUTPUT_EXISTS')
        a.output.mkdir(parents=True)
        report=environment_preflight(a.root,a.archive,a.module_dir)
        _dump_new(a.output/'preflight.json',report)
        if report['state']!='READY_FOR_REAL_H8E_PROFILING':
            _dump_new(a.output/'failure.json',dict(status='BLOCKED',
                blockers=report['blockers'],fresh_native_cherchi_calls=0))
            print(json.dumps({'status':'BLOCKED','blockers':report['blockers']}))
            raise SystemExit(2)
        print('READY_FOR_REAL_H8E_PROFILE_ONLY')
        return
    result=run_native(a.root,a.archive,a.output,module_dirs=a.module_dir,
                      baseline_mode=a.baseline_mode)
    print(json.dumps(result,sort_keys=True))
    if result['state'] not in ('NATIVE_TIMING_COMPLETE_NOT_NEWTON',):
        raise SystemExit(2)


if __name__=='__main__':main()
