"""W1 M23: four isolated original/candidate *full Faster solver* invocations.

The child always invokes the authentic source-pinned production solver; the
candidate only substitutes the M22 per-call exact evaluator subclass.  An
actual signed scientific admission requires an independent W0/W2 review.

The archived H8e CAD is reconstructed research geometry, NOT author CAD. Its
single-q request must NOT be substituted for a SpinArtifactProblem. Instead
we construct/validate the independent original + fixed F + design D partition
in the native library and record its own locked input digest.  Both A/B jobs
must use that same locked problem definition and the original solver settings.

No production module/branch modifications, no fake success on a missing native
host, and no relaxation of exact boundary/terminal verification.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
from zipfile import ZipFile

ARCHIVE_SHA = '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
H8_REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
CAD_PREFIX = 'artifacts/h8-input/'
REQUEST_PATH = 'artifacts/h8-request/prepared-request.json'
ORDER = ('original', 'candidate', 'candidate', 'original')
NATIVE = ('_make_it_stand','_cherchi_core_boolean','_cherchi_rational_moments')
MAX_MEMORY = 24 * 1024**3
MAX_RUN_SECONDS = 3600
FROZEN_BRANCH = 'research/neuralmoments-w1-native-20261019'
FROZEN_ANCESTOR = '0bcc187b3005478baa586a6d6f450e73811ca342'
PRODUCTION_SOURCE_BLOB = 'f9fa539f699df8baf8b8d30729048269a26ecb3c'
M22_SOURCE_BLOB = '4fc02d1161441460291bac38f75d3ef1ffe2c156'
M8_SOURCE_BLOB = 'd85ea23f6db394d13ec7410ec487ec40ab981eb2'


def _sha(data):
    return sha256(data).hexdigest()


def _git_blob(data):
    from hashlib import sha1
    return sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def _write_new(path, obj):
    with Path(path).open('x',encoding='utf-8') as fp:
        json.dump(obj,fp,indent=2,sort_keys=True,allow_nan=False)
        fp.write('\n')


def _archive_data(archive):
    """Use the exact REAL H8e CI ZIP; reject any reassembled substitutes."""
    archive=Path(archive)
    if not archive.is_file() or _sha(archive.read_bytes())!=ARCHIVE_SHA:
        raise ValueError('M23_REAL_H8E_ARCHIVE_SHA_MISMATCH')
    with ZipFile(archive) as z:
        required=[REQUEST_PATH,CAD_PREFIX+'H8_CAD_AUDIT.json',
                  CAD_PREFIX+'H8_INDEPENDENT_AUDIT.json']+[
                  CAD_PREFIX+x+'.obj' for x in ('initial_top','fixed_shell','design_domain','shaft')]
        members={}
        for path in required:
            found=[x for x in z.infolist() if x.filename==path]
            if len(found)!=1 or not 0<found[0].file_size<=7_000_000:
                raise ValueError('M23_MISSING_DUPLICATE_OR_OVERSIZED_H8_MEMBER:'+path)
            members[path]=z.read(found[0])
    if _sha(members[REQUEST_PATH])!=H8_REQUEST_SHA:
        raise ValueError('M23_H8_REQUEST_SHA_MISMATCH')
    doc=json.loads(members[REQUEST_PATH]);cad=json.loads(members[CAD_PREFIX+'H8_CAD_AUDIT.json'])
    audit=json.loads(members[CAD_PREFIX+'H8_INDEPENDENT_AUDIT.json'])
    if (doc.get('schema')!='spin-heart-h8-faster-preparation-v1' or
        doc.get('evidence',{}).get('scope')!='H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED' or
        doc['evidence'].get('newton_converged') is not False or
        cad.get('classification')!='PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED' or
        cad.get('faster_newton_converged') is not False or
        audit.get('success') is not True or
        audit.get('formal_newton_qualified') is not False or
        _sha(members[CAD_PREFIX+'H8_CAD_AUDIT.json'])!=audit.get('original_data_sha256')):
        raise ValueError('M23_H8_RECONSTRUCTED_SCOPE_OR_INPUT_AUDIT_FAILED')
    for key in ('initial_top','fixed_shell','design_domain','shaft'):
        path=CAD_PREFIX+key+'.obj'
        if (_sha(members[path])!=cad['sha256'].get(key+'.obj') or
            _sha(members[path])!=audit['exported_file_sha256'].get(key)):
            raise ValueError('M23_H8_OBJ_SHA_MISMATCH:'+key)
    return members,doc,cad,audit


def frozen_meshes(archive):
    """Validate real CAD and original request mesh bitwise; no Boolean claims."""
    import numpy as np
    import trimesh
    members,doc,cad,audit=_archive_data(archive)
    scale=float(cad['parameters']['length_mm'])
    density=float(cad['parameters']['density_kg_m3'])*1e-6  # g/mm^3
    if not math.isfinite(scale) or scale<=0 or not math.isfinite(density) or density<=0:
        raise ValueError('M23_INVALID_H8_UNITS')
    request=doc['request']
    arrays={}
    for key in ('initial_top','fixed_shell','design_domain','shaft'):
        mesh=trimesh.load(io.BytesIO(members[CAD_PREFIX+key+'.obj']),
                          file_type='obj',force='mesh',process=False)
        v=np.asarray(mesh.vertices,dtype='<f8');f=np.asarray(mesh.faces,dtype='<i4')
        if (v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3 or
            not np.isfinite(v).all() or not mesh.is_watertight or
            not mesh.is_winding_consistent or mesh.volume<=0 or
            len(v)!=cad['all_meshes'][key]['vertices'] or
            len(f)!=cad['all_meshes'][key]['faces']):
            raise ValueError('M23_H8_CAD_MESH_INVALID:'+key)
        arrays[key]=(v,f)
    for key,req in [('initial_top','outer'),('design_domain','design')]:
        vertices,faces=arrays[key]
        if (not np.array_equal(vertices/scale,np.asarray(request[req+'_vertices'],dtype='<f8'))
                or not np.array_equal(faces,np.asarray(request[req+'_faces'],dtype='<i4'))):
            raise ValueError('M23_H8_HISTORIC_MESH_REQUEST_DIFFERENCE:'+key)
    shaft_min=float(arrays['shaft'][0][:,2].min())
    origin=np.asarray(request['target_origin'],dtype='<f8')
    if (origin.shape!=(3,) or origin[0]!=0 or origin[1]!=0 or
        not np.array_equal(np.asarray(request['target_axes']),np.eye(3)) or
        abs(origin[2]-shaft_min/scale)>1e-12):
        raise ValueError('M23_H8_FROZEN_TARGET_FRAME_MISMATCH')
    wall=float(audit['conservative_all_triangle_pair_distance_lower_bound_mm'])
    if wall<=0 or not math.isfinite(wall):
        raise ValueError('M23_H8_INVALID_CONSERVATIVE_WALL')
    return dict(arrays=arrays,scale_mm=scale,density_g_mm3=density,
                target_origin_mm=[0.,0.,shaft_min],minimum_outer_wall_mm=wall,
                evaluator_settings=doc['evaluator_settings'],
                solver_settings=request['settings'],
                archive_sha256=ARCHIVE_SHA,request_sha256=H8_REQUEST_SHA,
                scope='RECONSTRUCTED_CAD_NEW_LOCKED_PROBLEM_NOT_IDENTICAL_NATIVE_H8C_REQUEST')


def _memory_limit():
    try:
        p=Path('/sys/fs/cgroup/memory.max')
        raw=p.read_text().strip()
        limit=int(raw) if raw!='max' else None
    except (OSError,ValueError):
        limit=None
    physical=os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_PHYS_PAGES')
    return min(x for x in (physical,limit,MAX_MEMORY) if x is not None)


def preflight(root,archive,module_dirs):
    """Strictly classify LOCAL native readiness; archive validation is real."""
    import importlib.util
    status={'schema':'w1-m23-native-newton-preflight-v1','status':'BLOCKED',
            'archive_sha256':None,'blockers':[],
            'full_solver_speedup':None,'w0_w2_admitted':False}
    root=Path(root).resolve()
    try:
        frozen_meshes(archive)
        status['archive_sha256']=ARCHIVE_SHA
    except Exception as exc:
        status['blockers'].append('archive:'+type(exc).__name__+':'+str(exc))
    check=subprocess.run(['git','-C',str(root),'symbolic-ref','--short','HEAD'],
                         capture_output=True,text=True,check=False)
    if check.returncode!=0 or check.stdout.strip()!=FROZEN_BRANCH:
        status['blockers'].append('M23_FULL_W1_GIT_CHECKOUT_REQUIRED')
    else:
        ancestry=subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',
                                 FROZEN_ANCESTOR,'HEAD'],capture_output=True,check=False)
        if ancestry.returncode!=0:
            status['blockers'].append('M23_FROZEN_ANCESTRY_MISSING')
        paths={
            'python/make_it_stand/verification/cherchi_inprocess.py':PRODUCTION_SOURCE_BLOB,
            'research/NeuralMoments/performance/m22_solver_runtime_candidate.py':M22_SOURCE_BLOB,
            'research/NeuralMoments/performance/m8_exact_construction_trial.py':M8_SOURCE_BLOB}
        for rel,expected in paths.items():
            p=root/rel
            if not p.is_file() or _git_blob(p.read_bytes())!=expected:
                status['blockers'].append('M23_FROZEN_SOURCE_CHANGED:'+rel)
    if _memory_limit()<6*1024**3:
        status['blockers'].append('M23_NATIVE_HOST_BELOW_6_GIB')
    if Path('/proc/swaps').is_file():
        swaps=Path('/proc/swaps').read_text().splitlines()
        if len(swaps)>1:
            status['blockers'].append('M23_SWAP_MUST_BE_ZERO')
    search=[Path(d).resolve() for d in module_dirs]
    inventory={}
    for mod in NATIVE:
        paths=[p for folder in search for p in folder.glob(mod+'*.so') if p.is_file()]
        inventory[mod]=[str(p) for p in paths]
        if len(paths)!=1:
            status['blockers'].append('M23_NATIVE_MODULE_NOT_UNIQUELY_PRESENT:'+mod)
    status['native_binary_candidates']=inventory
    status['module_sha256']={k:_sha(Path(paths[0]).read_bytes())
        for k,paths in inventory.items() if len(paths)==1}
    if not status['blockers']:
        status['status']='READY_TO_RUN_FOUR_INDEPENDENT_SOLVER_PROCESSES'
    return status


def _child(root,archive,output,mode,module_dirs):
    """One completely isolated genuine original/candidate native run."""
    # Must run only after parent authenticates source, module paths and inputs.
    for d in reversed(module_dirs):
        sys.path.insert(0,str(Path(d).resolve()))
    sys.path.insert(0,str(Path(root)/'python'))
    sys.path.insert(0,str(Path(root)/'research/NeuralMoments/performance'))
    import _make_it_stand as native
    import _cherchi_core_boolean as boolean
    import _cherchi_rational_moments as arithmetic
    import make_it_stand.spin as spin
    from make_it_stand.verification.spin_problem import SpinArtifactProblem
    from make_it_stand.verification.cherchi_inprocess import (
        InProcessCherchiEvaluator, solve_cherchi_inprocess_and_seal_faster)
    from m22_solver_runtime_candidate import make_candidate_solver
    actual={name:_sha(Path(obj.__file__).read_bytes()) for name,obj in
            zip(NATIVE,(native,boolean,arithmetic))}
    if any(Path(obj.__file__).resolve().parent not in [Path(d).resolve() for d in module_dirs]
           for obj in (native,boolean,arithmetic)):
        raise RuntimeError('M23_NATIVE_BINARY_IMPORTED_OUTSIDE_EXCLUSIVE_BUILD_DIR')
    data=frozen_meshes(archive)
    meshes=data['arrays'];density=data['density_g_mm3']
    target=dict(mode='SPINNING_TOP',axis=[0.,0.,1.],
                origin=data['target_origin_mm'],support_points=[])
    # Native constructor checks EXACT original=F+D physical partition.
    problem=SpinArtifactProblem(
        original=meshes['initial_top'],
        fixed_regions=[('H8_FIXED',meshes['fixed_shell'],density)],
        design_regions=[('H8_DESIGN',meshes['design_domain'],density)],
        length_unit='mm',mass_unit='g',target=target,
        minimum_outer_wall=data['minimum_outer_wall_mm'])
    settings=spin.SpinEvaluatorConfig(**data['evaluator_settings'])
    solver_settings=spin.SpinSolverConfig(**data['solver_settings'])
    solver=solve_cherchi_inprocess_and_seal_faster
    if mode=='candidate':
        solver,_=make_candidate_solver(InProcessCherchiEvaluator,solver)
    else:
        if mode!='original':raise ValueError('M23_INVALID_SOLVER_VARIANT')
    (Path(output)/'native-source-pins.json').write_text(json.dumps(dict(
        mode=mode,problem_digest=problem.input_digest,
        native_module_sha256=actual,archive_sha256=ARCHIVE_SHA,
        production_solver_python_sha256=_sha(Path(sys.modules[
            'make_it_stand.verification.cherchi_inprocess'].__file__).read_bytes()),
        candidate_source_sha256=_sha(Path(sys.modules[
            'm22_solver_runtime_candidate'].__file__).read_bytes()),
        scope='ISOLATED_RECONSTRUCTED_H8_NATIVE_SOLVE_NOT_RELEASED'),indent=2)+'\n')
    started=time.monotonic_ns()
    try:
        result=solver(problem,evaluator_settings=settings,solver_settings=solver_settings,
                      output_directory=Path(output)/'run',
                      rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
                      integral_profile='EXACT_GMP_V1')
        _write_new(Path(output)/'worker.json',dict(
            schema='w1-m23-native-worker-v1',mode=mode,
            wall_solver_ns=time.monotonic_ns()-started,
            solver_status=result.status,scientific_digest=result.scientific_digest,
            locked_problem_digest=problem.input_digest,
            full_solver_speedup=None,terminal_admitted=False,
            w0_w2_admitted=False))
    except BaseException as exc:
        _write_new(Path(output)/'failure.json',dict(
            schema='w1-m23-native-worker-failure-v1',mode=mode,
            error=type(exc).__name__+':'+str(exc),
            wall_solver_ns=time.monotonic_ns()-started,
            solver_speedup=None, w0_w2_admitted=False))
        raise


def _limit(address_space):
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    cap=min([address_space, MAX_MEMORY]+[v for v in (soft,hard) if v!=resource.RLIM_INFINITY])
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap))


def _one_worker(script,root,archive,output,mode,module_dirs,max_seconds,memory):
    command=[sys.executable,str(script),'--worker','--root',str(root),
             '--archive',str(archive),'--output',str(output),
             '--mode',mode]
    for d in module_dirs:command.extend(['--module-dir',str(d)])
    with (output/'console.log').open('x') as fp:
        child=subprocess.Popen(command,stdout=fp,stderr=subprocess.STDOUT,
                               cwd=root,start_new_session=True,
                               preexec_fn=lambda:_limit(memory))
        try:
            code=child.wait(timeout=max_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid,signal.SIGKILL)
            child.wait()
            code=124
    return code



def audit_saved_newton_events(run_dir):
    """Rehash every *actual* saved evaluation, not producer self-assertions.

    Raw events and material identities are required before a diagnostic wall
    comparison. This is not a proof of independent physical containment.
    """
    run_dir=Path(run_dir)
    events=run_dir/'events.jsonl'
    if not events.is_file():
        raise ValueError('M23_RUN_EVENTS_MISSING')
    rows=[]
    for text in events.read_text().splitlines():
        if not text.strip():continue
        event=json.loads(text)
        if not isinstance(event,dict):raise ValueError('M23_NONOBJECT_JOURNAL_ENTRY')
        rows.append(event)
    # A merely present terminal receipt is not scientific evidence.  The
    # production verifier's own record-integrity proof must be checked below.
    maps=[];newton=[]
    for event in rows:
        if event.get('kind')=='MAP_SAVED':
            index=event.get('evaluation')
            filename=event.get('evaluation_file')
            if type(index) is not int or index!=len(maps)+1 or filename!=f'evaluation-{index:06d}.json':
                raise ValueError('M23_MISSING_OR_REORDERED_EVALUATION_MATERIAL')
            p=run_dir/filename
            if not p.is_file() or p.is_symlink() or _sha(p.read_bytes())!=event.get('sha256'):
                raise ValueError('M23_EVALUATION_SHA_MISMATCH:'+filename)
            material=json.loads(p.read_text())
            if material.get('geometry_hash')!=event.get('geometry_hash'):
                raise ValueError('M23_SAVED_GEOMETRY_HASH_MISMATCH:'+filename)
            if material.get('quadric_coefficients')!=event.get('coefficients'):
                raise ValueError('M23_SAVED_Q_AND_JOURNAL_DISAGREE:'+filename)
            # Full 10x10 derivative must be attached to EVERY saved material,
            # not just claimed by the worker's scientific digest.  Strict
            # equality in four-call admission remains fail-closed pending W0
            # approval of an independent comparison rule.
            jacobian=material.get('moment_jacobian')
            if (type(jacobian) is not list or len(jacobian)!=10 or any(
                    type(row) is not list or len(row)!=10 or any(
                        type(x) not in (int,float) or not math.isfinite(x)
                        for x in row) for row in jacobian)):
                raise ValueError('M23_SAVED_FULL_JACOBIAN_MISSING_OR_NONFINITE:'+filename)
            for field in ('variable_raw_moments','raw_moments'):
                values=material.get(field)
                if (type(values) is not list or len(values)!=10 or any(
                        type(x) not in (int,float) or not math.isfinite(x)
                        for x in values)):
                    raise ValueError('M23_SAVED_TEN_MOMENTS_MISSING_OR_NONFINITE:'+filename+':'+field)
            maps.append(dict(coefficients=event['coefficients'],
                             geometry_hash=event['geometry_hash'],
                             topology_hash=material.get('topology_hash'),
                             variable_raw_moments=material['variable_raw_moments'],
                             raw_moments=material['raw_moments'],
                             moment_jacobian=jacobian,
                             source_identity=material.get('quadric_source_identity')))
        elif event.get('kind')=='NEWTON_EVENT':
            if not isinstance(event.get('event'),dict):
                raise ValueError('M23_INVALID_NATIVE_NEWTON_EVENT')
            newton.append(event['event'])
    if not maps:
        raise ValueError('M23_NO_SAVED_GENUINE_EVALUATIONS')
    for name in ('complete.json','result.json','record-verification.json',
                 'terminal-complement.json','terminal-material-reference.json',
                 'timing-scope.json','recording-costs.json'):
        if not (run_dir/name).is_file():
            raise ValueError('M23_MISSING_TERMINAL_OR_TIMING_EVIDENCE:'+name)
    complete=json.loads((run_dir/'complete.json').read_text())
    result=json.loads((run_dir/'result.json').read_text())
    verification=json.loads((run_dir/'record-verification.json').read_text())
    rejected=sum(event.get('kind')=='MAP_REJECTED' for event in rows)
    if (verification.get('record_integrity_valid') is not True or
            verification.get('saved_materials')!=len(maps) or
            type(verification.get('accepted_updates')) is not int or
            verification['accepted_updates']<=0 or
            verification.get('rejected_evaluations')!=rejected or
            verification.get('core_admission') is not False):
        raise ValueError('M23_INDEPENDENT_PRODUCTION_RECORD_PROOF_MISSING_OR_INCONSISTENT')
    if not rows or rows[-1].get('kind')!='RUN_TERMINATED' or rows[-1].get('status')!='CONVERGED':
        raise ValueError('M23_MISSING_SUCCESSFUL_NEWTON_TERMINAL_EVENT')
    if (complete.get('complete') is not True or
        complete.get('status')!='CONVERGED' or
        complete.get('evaluation_count')!=len(maps) or
        result.get('status')!='CONVERGED'):
        raise ValueError('M23_INCOMPLETE_OR_NONCONVERGED_TERMINAL')
    return dict(evaluation_count=len(maps),newton_event_count=len(newton),
                maps=maps,newton_events=newton,
                scientific_digest=result.get('scientific_digest'))


def run_four(root,archive,output,module_dirs=(),max_seconds=MAX_RUN_SECONDS):
    """Old–new–new–old, with a fresh process and frozen real CAD every time."""
    if type(max_seconds) is not int or not 1<=max_seconds<=MAX_RUN_SECONDS:
        raise ValueError('M23_EACH_SOLVER_RUN_MUST_BE_AT_MOST_ONE_HOUR')
    root,archive,output=Path(root).resolve(),Path(archive).resolve(),Path(output)
    if output.exists():raise FileExistsError('M23_OUTPUT_ALREADY_EXISTS')
    output.mkdir(parents=True)
    pre=preflight(root,archive,module_dirs)
    _write_new(output/'preflight.json',pre)
    if pre['status']!='READY_TO_RUN_FOUR_INDEPENDENT_SOLVER_PROCESSES':
        _write_new(output/'failure.json',dict(status='BLOCKED_BEFORE_NATIVE',
                 blockers=pre['blockers'],solver_calls=0,full_solver_speedup=None))
        return dict(state='BLOCKED',blockers=pre['blockers'])
    status=[]
    for index,mode in enumerate(ORDER):
        place=output/f'{index:02d}-{mode}'
        place.mkdir()
        code=_one_worker(Path(__file__).resolve(),root,archive,place,mode,module_dirs,
                         max_seconds,_memory_limit())
        observed_modules={k:_sha(Path(paths[0]).read_bytes())
            for k,paths in pre['native_binary_candidates'].items() if len(paths)==1}
        status.append(dict(index=index,mode=mode,exit_code=code,
                           worker_sha256=_sha((place/'worker.json').read_bytes())
                             if (place/'worker.json').is_file() else None))
        if observed_modules!=pre['module_sha256']:
            _write_new(output/'failure.json',dict(status='NATIVE_MODULE_CHANGED_BETWEEN_ABBA_CALLS',
                      at=index,completed=status,full_solver_speedup=None))
            return dict(state='FAILED',completed=status)
        if code!=0:
            _write_new(output/'failure.json',dict(
                schema='w1-m23-four-full-solver-failed-v1',status='FAILED_CLOSED',
                completed=status,at=index,reason='REAL_NATIVE_CHILD_REJECTED_OR_TIMED_OUT',
                full_solver_speedup=None, w0_w2_admitted=False))
            return dict(state='FAILED',completed=status)
    try:
        summaries=[json.loads((output/f'{i:02d}-{mode}'/'worker.json').read_text())
                   for i,mode in enumerate(ORDER)]
        digests=[x['locked_problem_digest'] for x in summaries]
        if len(set(digests))!=1 or len(set(x['solver_status'] for x in summaries))!=1:
            raise ValueError('M23_NATIVE_INPUT_OR_SOLVER_STATUS_DIFFERENT')
        if len(set(x['scientific_digest'] for x in summaries))!=1:
            raise ValueError('M23_FULL_NEWTON_OR_TERMINAL_SCIENTIFIC_DIGEST_DRIFT')
        # Only a genuine all-four CONVERGED run with authentic saved independent
        # verification may be considered a complete-solver performance diagnostic.
        if summaries[0]['solver_status']!='CONVERGED':
            _write_new(output/'failure.json',dict(status='M23_FOUR_SOLVERS_RETURNED_NONCONVERGED',
                       solver_status=summaries[0]['solver_status'],completed=status,
                       full_solver_speedup=None,w0_w2_admitted=False))
            return dict(state='FAILED_NONCONVERGED',completed=status)
        for i,mode in enumerate(ORDER):
            saved=output/f'{i:02d}-{mode}'/'run'
            for name in ('complete.json','result.json','record-verification.json',
                         'terminal-complement.json','terminal-material-reference.json'):
                if not (saved/name).is_file():
                    raise ValueError('M23_MISSING_INDEPENDENT_TERMINAL_EVIDENCE:'+str(i)+':'+name)
            if json.loads((saved/'complete.json').read_text()).get('complete') is not True:
                raise ValueError('M23_NONCOMPLETE_JOURNAL:'+str(i))
        # Rehash all same-call journal material and require truly identical native
        # Newton accept/reject events before calculating a complete-solver ratio.
        event_receipts=[audit_saved_newton_events(
            output/f'{i:02d}-{mode}'/'run') for i,mode in enumerate(ORDER)]
        if any(event_receipts[i]['maps']!=event_receipts[0]['maps'] or
               event_receipts[i]['newton_events']!=event_receipts[0]['newton_events'] or
               event_receipts[i]['scientific_digest']!=summaries[i]['scientific_digest']
               for i in range(4)):
            raise ValueError('M23_NATIVE_ACCEPT_REJECT_OR_SAVED_MATERIAL_DRIFT')
        # A solver call's wall is not itself a formal full physical seal.
        from statistics import median
        original=median(x['wall_solver_ns'] for x in summaries if x['mode']=='original')
        candidate=median(x['wall_solver_ns'] for x in summaries if x['mode']=='candidate')
        receipt=dict(schema='w1-m23-reconstructed-h8-four-native-solve-diagnostic-v1',
                     state='FOUR_NATIVE_RUNS_SAME_SCIENTIFIC_DIGEST_NOT_W0_W2_ADMITTED',
                     order=list(ORDER),locked_problem_digest=digests[0],
                     solver_status=summaries[0]['solver_status'],
                     observed_solver_wall_original_over_candidate=original/candidate,
                     solver_stages_included=True,formal_jacobian_acceptance=False,
                     independent_terminal_seal_approval=False,
                     w0_w2_admitted=False,paper_speed_qualified=False,
                     real_native_4_runs=True,complete=status,
                     evaluated_materials_per_run=event_receipts[0]['evaluation_count'],
                     native_newton_events_per_run=event_receipts[0]['newton_event_count'])
        _write_new(output/'diagnostic.json',receipt)
        return receipt
    except BaseException as exc:
        if not (output/'failure.json').exists():
            _write_new(output/'failure.json',dict(
                status='FAILED_CLOSED_INDEPENDENT_NEWTON_EVIDENCE',
                error=type(exc).__name__+':'+str(exc),
                completed=status,full_solver_speedup=None,w0_w2_admitted=False))
        return dict(state='FAILED',completed=status)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--archive',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--module-dir',type=Path,action='append',default=[])
    ap.add_argument('--max-seconds',type=int,default=MAX_RUN_SECONDS)
    ap.add_argument('--worker',action='store_true')
    ap.add_argument('--mode',choices=ORDER)
    args=ap.parse_args()
    if args.worker:
        if not args.mode:raise ValueError('M23_WORKER_MODE_REQUIRED')
        try:
            _child(args.root,args.archive,args.output,args.mode,args.module_dir)
        except BaseException as exc:
            f=Path(args.output)/'failure.json'
            if not f.exists():
                _write_new(f,dict(status='FAILED_CLOSED_BEFORE_OR_DURING_NEWTON',
                    error=type(exc).__name__+':'+str(exc),
                    full_solver_speedup=None,w0_w2_admitted=False))
            raise
    else:
        result=run_four(args.root,args.archive,args.output,
                        args.module_dir,args.max_seconds)
        print(json.dumps({k:v for k,v in result.items() if k in
                          ('state','blockers','observed_solver_wall_original_over_candidate')},
                         sort_keys=True))
        # Zero exit is reserved for the ONE evidence-admitted diagnostic state.
        # In particular FAILED_NONCONVERGED must never silently turn a real
        # scientific failure into a green GitHub Actions job.
        if result.get('state') != 'FOUR_NATIVE_RUNS_SAME_SCIENTIFIC_DIGEST_NOT_W0_W2_ADMITTED':
            raise SystemExit(2)

if __name__=='__main__': main()
