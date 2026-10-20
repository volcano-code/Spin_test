"""W1 M10: pinned native-host admission and serial M5/M9 execution.

This is a *runner*, not a Cherchi implementation. It cannot synthesize missing
native modules or turn a saved material into a new Boolean evaluation.
Only genuine compiled Python extension modules pass the preflight. It leaves
production src/, bindings/, and other window branches entirely untouched.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
from hashlib import sha256
import importlib.machinery
import json
import os
from pathlib import Path
import platform
import re
import resource
import signal
import subprocess
import sys
from time import monotonic_ns
from zipfile import ZipFile

from m5_native_call_instrumentation import (
    ARCHIVE_SHA, REQUEST_MEMBER, REQUEST_SHA, SOURCE_BLOB, git_blob,
)
from m9_native_abba_gate import historic_h8c_anchor

BRANCH = 'research/neuralmoments-w1-native-20261019'
FREEZE = '0bcc187b3005478baa586a6d6f450e73811ca342'
NATIVE = ('_make_it_stand', '_cherchi_core_boolean', '_cherchi_rational_moments')
MAX_MEMORY = 24 * 1024**3
MAX_SECONDS = 3600


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                       text=True, timeout=10, check=False)
    return p.returncode, p.stdout.strip()


def repo_identity(root):
    """Require W1 HEAD descending from the frozen baseline, never main."""
    if not (root / '.git').exists():
        raise ValueError('M10_FULL_GIT_CHECKOUT_REQUIRED')
    exitcode, top = _git(root, 'rev-parse', '--show-toplevel')
    if exitcode or Path(top).resolve() != root.resolve():
        raise ValueError('M10_INVALID_REPOSITORY_ROOT')
    exitcode, branch = _git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    if exitcode or branch != BRANCH:
        raise ValueError('M10_W1_ONLY_BRANCH_REQUIRED')
    exitcode, head = _git(root, 'rev-parse', '--verify', 'HEAD')
    if exitcode or not re.fullmatch('[0-9a-f]{40}', head):
        raise ValueError('M10_INVALID_HEAD_SHA')
    code, _ = _git(root, 'merge-base', '--is-ancestor', FREEZE, 'HEAD')
    if code:
        raise ValueError('M10_FROZEN_ANCESTOR_NOT_VERIFIED')
    return dict(branch=branch, head=head, frozen_ancestor=FREEZE)


def archive_identity(path):
    """Pin the entire historical H8c ZIP and the embedded request/proof."""
    if not path.is_file():
        raise FileNotFoundError('M10_H8C_ARCHIVE_REQUIRED')
    archive_sha = _sha(path)
    if archive_sha != ARCHIVE_SHA:
        raise ValueError('M10_H8C_ARCHIVE_SHA_DRIFT')
    with ZipFile(path) as z:
        entries = [x for x in z.infolist() if x.filename == REQUEST_MEMBER]
        if len(entries) != 1 or not 0 < entries[0].file_size <= 7_000_000:
            raise ValueError('M10_ARCHIVED_REQUEST_NOT_UNIQUE')
        raw = z.read(entries[0])
        if sha256(raw).hexdigest() != REQUEST_SHA:
            raise ValueError('M10_H8C_REQUEST_SHA_DRIFT')
    historical = historic_h8c_anchor(path)
    return dict(zip_sha256=archive_sha, request_sha256=REQUEST_SHA,
                historical_material_sha256=historical['packet_sha256'],
                archived_q=historical['q'], historical_material_vertices=historical['vertices'],
                historical_material_faces=historical['faces'],
                nonauthor_cad_only=True)


def _source_identity(root):
    src = root/'python/make_it_stand/verification/cherchi_inprocess.py'
    if not src.is_file():
        raise FileNotFoundError('M10_PINNED_PRODUCTION_SOURCE_ABSENT')
    actual = git_blob(src.read_bytes())
    if actual != SOURCE_BLOB:
        raise ValueError('M10_PINNED_PRODUCTION_SOURCE_DRIFT')
    return dict(path='python/make_it_stand/verification/cherchi_inprocess.py',
                git_blob_sha1=actual)


def module_roots(root, extras=()):
    defaults = (root/'build/heart-cloud-core/python',
                root/'build/heart-cloud-cherchi/python')
    paths = [*(Path(p).resolve() for p in extras), *defaults]
    unique=[]
    for p in paths:
        if p not in unique: unique.append(p)
    return unique


def module_inventory(root, extras=()):
    """Only real CPython extension suffixes, not .py mocks or bare library names."""
    roots = module_roots(root, extras)
    result={}
    for name in NATIVE:
        candidates=[]
        for directory in roots:
            if not directory.is_dir():
                continue
            for suffix in importlib.machinery.EXTENSION_SUFFIXES:
                path=directory/(name+suffix)
                if path.is_file(): candidates.append(path.resolve())
        candidates=sorted(set(candidates))
        if len(candidates) != 1:
            result[name]=dict(status='NOT_FOUND' if not candidates else 'AMBIGUOUS',
                              candidate_count=len(candidates))
        else:
            path=candidates[0]
            result[name]=dict(status='FOUND',path=str(path),sha256=_sha(path),
                              bytes=path.stat().st_size)
    return result


def native_import_probe(root, extras, inventory, memory_ceiling):
    """Import the real ELF/Python modules in an isolated, capped subprocess.

    A filename or ``find_spec`` alone is not a valid native execution proof.
    The probe checks exact on-disk module provenance and the required ABI
    entrypoints without performing a Cherchi Boolean computation.
    """
    if any(inventory[n]['status'] != 'FOUND' for n in NATIVE):
        raise RuntimeError('M10_NATIVE_BINARIES_MISSING_OR_AMBIGUOUS')
    expected={name:inventory[name]['path'] for name in NATIVE}
    env=os.environ.copy()
    search_paths=[str(root/'python'),*(str(p) for p in module_roots(root,extras))]
    if env.get('PYTHONPATH'):
        search_paths.append(env['PYTHONPATH'])
    env['PYTHONPATH']=os.pathsep.join(search_paths)
    env['OPENBLAS_NUM_THREADS']='1'
    env['OMP_NUM_THREADS']='1'
    code = r"""
import importlib, json, pathlib, sys
paths=json.loads(sys.argv[1]); modules={}
for name, expected in paths.items():
    mod=importlib.import_module(name)
    if str(pathlib.Path(mod.__file__).resolve())!=expected:
        raise ValueError('M10_LOADED_AN_UNEXPECTED_NATIVE_MODULE:'+name)
    modules[name]=mod
native=modules['_make_it_stand']
cherchi=modules['_cherchi_core_boolean']
gmp=modules['_cherchi_rational_moments']
if not all(hasattr(native,n) for n in ('audit_exact_rational_triangle_boundary',
                                      'evaluate_spin_it_faster_source_motion')):
    raise ValueError('M10_NATIVE_ABI_MISSING_EXACT_AUDIT_OR_SOURCE')
if not hasattr(cherchi,'boolean'):
    raise ValueError('M10_CHERCHI_BOOLEAN_ABI_MISSING')
if (not hasattr(gmp,'PreparedBoundary') or
        getattr(gmp,'arithmetic_identity',None)!=
        'DIV_SURFACE_V1_REYNOLDS_V1_GMP_BINARY64_NEAREST_EVEN_V1'):
    raise ValueError('M10_GMP_MOMENT_ABI_MISMATCH')
print('M10_PINNED_EXTENSIONS_LOADED_OK')
"""
    result=subprocess.run([sys.executable,'-c',code,json.dumps(expected)],
        cwd=root,env=env,capture_output=True,text=True,timeout=40,
        preexec_fn=lambda:_child_limits(memory_ceiling))
    if result.returncode or 'M10_PINNED_EXTENSIONS_LOADED_OK' not in result.stdout:
        raise RuntimeError('M10_NATIVE_EXTENSION_LOAD_OR_ABI_FAILURE')
    return dict(validated_modules=len(expected),cpp_extensions_imported=True,
                native_entrypoints_valid=True,math_executions=0)


def _memory_limit():
    """Physical/cgroup ceiling is a safety limit, not a promise of free memory."""
    total=None
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemTotal:'):
            total=int(line.split()[1])*1024
            break
    if total is None or total <= 0:
        raise ValueError('M10_MEMORY_CAP_UNAVAILABLE')
    group=Path('/sys/fs/cgroup/memory.max')
    cg=None
    if group.is_file():
        value=group.read_text().strip()
        if value!='max':
            cg=int(value)
            if cg<=0: raise ValueError('M10_INVALID_CGROUP_MEMORY')
    ceiling=min(x for x in (MAX_MEMORY,total,cg) if x is not None)
    # Reserve 512 MiB of virtual address space for the execution environment.
    if ceiling < (1024**3):
        raise ValueError('M10_NATIVE_MEMORY_TOO_LOW')
    return dict(physical_memory_bytes=total,cgroup_memory_ceiling_bytes=cg,
                process_address_space_cap_bytes=ceiling,
                resource_cap_bytes=MAX_MEMORY)


def _swap_guard():
    table=Path('/proc/swaps')
    if not table.is_file() or len(table.read_text().splitlines()) != 1:
        raise RuntimeError('M10_REQUIRES_ZERO_SWAP')
    return True


def preflight(root, archive, extra_modules=()):
    """Check all dependencies independently; no native work or success report."""
    root,archive=Path(root).resolve(),Path(archive).resolve()
    checks={}; blockers=[]
    for name,callback in (
        ('git',lambda:repo_identity(root)),
        ('source',lambda:_source_identity(root)),
        ('archive',lambda:archive_identity(archive)),
        ('memory',_memory_limit),
        ('swap_disabled',_swap_guard),
    ):
        try: checks[name]=dict(status='PASS',details=callback())
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            checks[name]=dict(status='BLOCKED',reason=f'{type(error).__name__}: {error}')
            blockers.append(name)
    modules=module_inventory(root,extra_modules)
    checks['native_modules']=dict(status='PASS' if all(
        item['status']=='FOUND' for item in modules.values()) else 'BLOCKED',
        modules=modules)
    if checks['native_modules']['status'] != 'PASS': blockers.append('native_modules')
    if checks['native_modules']['status']=='PASS' and checks['memory']['status']=='PASS':
        try:
            checks['native_abi_import']=dict(status='PASS',details=native_import_probe(
                root,extra_modules,modules,
                checks['memory']['details']['process_address_space_cap_bytes']))
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:
            checks['native_abi_import']=dict(status='BLOCKED',
                                              reason=f'{type(error).__name__}: {error}')
            blockers.append('native_abi_import')
    else:
        checks['native_abi_import']=dict(status='BLOCKED',
                                        reason='M10_MODULE_OR_MEMORY_PREREQUISITE_MISSING')
        blockers.append('native_abi_import')
    return dict(schema='w1-m10-native-host-preflight-v1',
        state='READY_FOR_REAL_NATIVE_ABBA' if not blockers else 'BLOCKED',
        tested_branch=BRANCH, freeze=FREEZE, checks=checks, blockers=blockers,
        machine=dict(platform=platform.platform(),python=platform.python_version()),
        native_boolean_calls=0,full_newton_solves=0,full_solver_speedup=None,
        w0_w2_production_admitted=False,paper_speed_qualified=False)


def _new_json(path,obj):
    with Path(path).open('x',encoding='utf-8') as out:
        json.dump(obj,out,indent=2,sort_keys=True,allow_nan=False)
        out.write('\n')


def _child_limits(max_memory):
    # Both the old and new evaluation run under the same conservative cap.
    soft,hard=resource.getrlimit(resource.RLIMIT_AS)
    allowed=min(v for v in (max_memory,MAX_MEMORY,soft,hard)
                if v!=resource.RLIM_INFINITY)
    resource.setrlimit(resource.RLIMIT_AS,(allowed,allowed))


def _execute(cmd, *, cwd, environment, log, memory_ceiling, timeout_seconds):
    with Path(log).open('x',encoding='utf-8') as out:
        process=subprocess.Popen(cmd,cwd=cwd,env=environment,stdout=out,
            stderr=subprocess.STDOUT,start_new_session=True,
            preexec_fn=lambda:_child_limits(memory_ceiling))
        try:
            return process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait()
            raise TimeoutError('M10_NATIVE_JOB_TIME_LIMIT')


@contextmanager
def _native_job_lock():
    """Keep simultaneous W1 M10 invocations off the same native host.

    Cross-window W3 processes must separately coordinate their large jobs;
    this lock only covers cooperating W1 launches.
    """
    path=Path('/tmp/spin_test_w1_native_job.lock')
    with path.open('a+') as stream:
        try:
            fcntl.flock(stream,fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('M10_ANOTHER_W1_NATIVE_JOB_ALREADY_RUNNING') from error
        try:
            yield
        finally:
            fcntl.flock(stream,fcntl.LOCK_UN)


def execute(root, archive, output, *, extra_modules=(), max_seconds=MAX_SECONDS):
    """Actually run M5 then M9 *serially* only after all native guards pass."""
    root,archive,output=Path(root).resolve(),Path(archive).resolve(),Path(output)
    if type(max_seconds) is not int or not 1<=max_seconds<=MAX_SECONDS:
        raise ValueError('M10_PER_JOB_SECONDS_LIMIT')
    output.mkdir(parents=True,exist_ok=False)
    ready=preflight(root,archive,extra_modules)
    _new_json(output/'preflight.json',ready)
    if ready['state']!='READY_FOR_REAL_NATIVE_ABBA':
        _new_json(output/'failure.json',dict(schema='w1-m10-not-run-v1',
            status='BLOCKED_NATIVE_PREFLIGHT',blockers=ready['blockers'],
            executed_m5=False,executed_m9=False,full_solver_speedup=None))
        return ready
    roots=module_roots(root,extra_modules)
    env=os.environ.copy()
    paths=[str(root/'python'),*(str(x) for x in roots),
           *(env.get('PYTHONPATH','').split(os.pathsep) if env.get('PYTHONPATH') else [])]
    env['PYTHONPATH']=os.pathsep.join(paths)
    env['OMP_NUM_THREADS']='1';env['OPENBLAS_NUM_THREADS']='1'
    memory=ready['checks']['memory']['details']['process_address_space_cap_bytes']
    job_results=[]
    try:
        with _native_job_lock():
            for label,script in (('m5','m5_native_call_instrumentation.py'),
                                 ('m9','m9_native_abba_gate.py')):
                subprocess_output=output/label
                command=[sys.executable,str(root/'research/NeuralMoments/performance'/script),
                         '--archive',str(archive),'--root',str(root),'--output',str(subprocess_output)]
                start=monotonic_ns()
                try:
                    status=_execute(command,cwd=root,environment=env,
                            log=output/f'{label}.log',memory_ceiling=memory,
                            timeout_seconds=max_seconds)
                    record=dict(stage=label,returncode=status,wall_ns=monotonic_ns()-start)
                    job_results.append(record)
                    if status!=0:
                        raise RuntimeError('M10_NATIVE_STAGE_EXIT_NONZERO:'+label+':'+str(status))
                    path=subprocess_output/'baseline-performance.json'
                    if not path.is_file():
                        raise RuntimeError('M10_NATIVE_STAGE_HAS_NO_SCIENTIFIC_REPORT:'+label)
                    report=json.loads(path.read_text())
                    required_schema= 'w1-m5-native-h8-instrumented-sample-v1' if label=='m5' else 'w1-m9-native-h8c-abba-v1'
                    calls=1 if label=='m5' else 4
                    if report.get('schema')!=required_schema or report.get(
                            'fresh_boolean_calls' if label=='m5' else 'native_cherchi_calls')!=calls:
                        raise ValueError('M10_NATIVE_STAGE_REPORT_WRONG_SCOPE:'+label)
                except BaseException as exc:
                    _new_json(output/'failure.json',dict(schema='w1-m10-native-job-failure-v1',
                        status='FAILED_NO_COMPLETE_NATIVE_CERTIFICATION',failed_stage=label,
                        error=f'{type(exc).__name__}: {exc}',jobs=job_results,
                        complete_solver_speedup=None,paper_speed_qualified=False))
                    raise
    except BaseException as exc:
        if not (output/'failure.json').exists():
            _new_json(output/'failure.json',dict(schema='w1-m10-lock-or-launch-failure-v1',
                status='FAILED_BEFORE_NATIVE_COMPLETION',
                error=f'{type(exc).__name__}: {exc}',jobs=job_results,
                full_solver_speedup=None,paper_speed_qualified=False))
        raise
    # Still NOT a whole-solver comparison. This only declares 1+4 real calls.
    success=dict(schema='w1-m10-fresh-native-evaluation-complete-v1',
        scope='M5_SINGLE_Q_PLUS_M9_ABBA_NOT_FULL_NEWTON',jobs=job_results,
        fresh_boolean_calls=5,full_solver_speedup=None,
        full_solver_terminal_verified=False,paper_speed_qualified=False)
    _new_json(output/'native_evaluation_summary.json',success)
    return success


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--module-dir',action='append',type=Path,default=[])
    parser.add_argument('--max-seconds',type=int,default=3600)
    args=parser.parse_args()
    result=execute(args.root,args.archive,args.output,
                   extra_modules=args.module_dir,max_seconds=args.max_seconds)
    print(json.dumps({'status':result.get('state',result.get('scope')),
                      'blockers':result.get('blockers',[])},sort_keys=True))
    if result.get('state')=='BLOCKED': raise SystemExit(2)


if __name__=='__main__':
    main()
