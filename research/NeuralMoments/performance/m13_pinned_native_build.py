"""W1 M13: provision pinned native SOURCES, build isolated modules, run M11.

No sudo, apt mutation, branch switches, production-code edits or CI claims.
Default is a read-only preflight. --execute requires an explicitly prepared
native host and optionally --fetch-pinned-sources. Only the actual M11 run may
attest real Cherchi evaluations; this launcher never manufactures those data.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

import m10_native_host_runner as m10

CHERCHI_COMMIT = '7bd6c2697695f555f9a15d7e154e084d841316f0'
CGAL_COMMIT = 'f7c3c8212b56c0d6dae63787efc99093f4383415'
CHERCHI_URL = 'https://github.com/gcherchi/InteractiveAndRobustMeshBooleans.git'
CGAL_URL = 'https://github.com/CGAL/cgal.git'
CHERCHI_REL = Path('external/reference-sources-20260917/sources') / (
    'InteractiveAndRobustMeshBooleans-' + CHERCHI_COMMIT)
CGAL_REL = Path('libigl/external/cgal')
BUILD_CORE_REL = Path('build/w1-m13-core')
BUILD_CHERCHI_REL = Path('build/w1-m13-cherchi')
MIN_BUILD_MEMORY = 6 * 1024**3
MAX_WORKERS = 4
MAX_STAGE_SECONDS = 3600


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def _git_revision(path):
    if not path.is_dir():
        return None
    proc = subprocess.run(['git', '-C', str(path), 'rev-parse', '--verify', 'HEAD'],
                          capture_output=True, text=True, timeout=15, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _tracked_source_clean(path):
    if not Path(path).is_dir():
        return False
    p = subprocess.run(['git', '-C', str(path), 'status', '--porcelain',
                        '--untracked-files=no'], capture_output=True,
                       text=True, timeout=15, check=False)
    return p.returncode == 0 and not p.stdout.strip()


def _source_check(root):
    cherchi = root / CHERCHI_REL
    cgal = root / CGAL_REL
    observations = {
        'cherchi_path': str(CHERCHI_REL),
        'cherchi_head': _git_revision(cherchi),
        'cherchi_expected': CHERCHI_COMMIT,
        'cgal_path': str(CGAL_REL),
        'cgal_head': _git_revision(cgal),
        'cgal_expected': CGAL_COMMIT,
    }
    observations['cherchi_tracked_clean'] = (observations['cherchi_head'] == CHERCHI_COMMIT
                                            and _tracked_source_clean(cherchi))
    observations['cgal_tracked_clean'] = (observations['cgal_head'] == CGAL_COMMIT
                                         and _tracked_source_clean(cgal))
    observations['cherchi_header_found'] = (cherchi / 'code/booleans.h').is_file()
    observations['cgal_header_found'] = (cgal / 'Number_types/include/CGAL/Gmpq.h').is_file()
    observations['pinned'] = (
        observations['cherchi_tracked_clean'] and
        observations['cgal_tracked_clean'] and
        observations['cherchi_header_found'] and observations['cgal_header_found'])
    return observations


def _toolchain_check():
    tools = {name: shutil.which(name) for name in
             ('git', 'cmake', 'ninja', 'g++', 'pkg-config')}
    result = {'executables': tools}
    try:
        pybind = importlib.metadata.version('pybind11')
    except importlib.metadata.PackageNotFoundError:
        pybind = None
    result['pybind11_version'] = pybind
    result['python_version'] = platform.python_version()
    pkg = {}
    for name in ('gmp', 'mpfr'):
        if not tools['pkg-config']:
            pkg[name] = None
            continue
        p = subprocess.run(['pkg-config', '--modversion', name],
                           capture_output=True, text=True, timeout=15, check=False)
        pkg[name] = p.stdout.strip() if p.returncode == 0 else None
    result['pkg_config_versions'] = pkg
    result['ready'] = (
        all(tools.values()) and pybind == '3.0.1' and
        sys.version_info[:2] == (3, 13) and all(pkg.values()))
    return result


def _boost_libraries():
    base = Path('/usr/lib/x86_64-linux-gnu')
    return {name: base / ('libboost_' + name + '.so')
            for name in ('system', 'thread')}


def _environment_check(root, archive):
    checks = {}
    for name, fn in (
        ('git', lambda: m10.repo_identity(root)),
        ('source', lambda: m10._source_identity(root)),
        ('archive', lambda: m10.archive_identity(archive)),
        ('memory', m10._memory_limit),
        ('swap', m10._swap_guard),
        ('toolchain', _toolchain_check),
    ):
        try:
            value = fn()
            if name == 'memory' and value['process_address_space_cap_bytes'] < MIN_BUILD_MEMORY:
                raise RuntimeError('M13_BUILD_HOST_BELOW_6_GIB_MEMORY_CEILING')
            if name == 'toolchain' and not value['ready']:
                raise RuntimeError('M13_PINNED_BUILD_DEPENDENCIES_UNAVAILABLE')
            checks[name] = {'status': 'PASS', 'detail': value}
        except (ValueError, RuntimeError, FileNotFoundError, OSError,
                subprocess.SubprocessError) as exc:
            checks[name] = {'status': 'BLOCKED',
                            'error': type(exc).__name__ + ': ' + str(exc)}
    return checks


def _empty_directory_or_absent(path):
    path = Path(path)
    return not path.exists() or (path.is_dir() and not any(path.iterdir()))


def preflight(root, archive, *, allow_source_fetch=False):
    root, archive = Path(root).resolve(), Path(archive).resolve()
    checks = _environment_check(root, archive)
    sources = _source_check(root)
    checks['pinned_sources'] = {'status': 'PASS' if sources['pinned'] else 'BLOCKED',
                                'detail': sources}
    if allow_source_fetch and not sources['pinned']:
        dirty_pinned = any((sources[what + '_head'] == expected and
                            (not sources[what + '_tracked_clean'] or
                             not sources[what + '_header_found']))
                           for what, expected in (
                               ('cherchi', CHERCHI_COMMIT), ('cgal', CGAL_COMMIT)))
        conflicting = any((not _empty_directory_or_absent(root / relative) and
                           sources[what + '_head'] != expected)
                          for what, relative, expected in (
                              ('cherchi', CHERCHI_REL, CHERCHI_COMMIT),
                              ('cgal', CGAL_REL, CGAL_COMMIT)))
        if dirty_pinned:
            checks['pinned_sources']['error'] = 'M13_PINNED_SOURCE_DIRTY_OR_INCOMPLETE'
        elif conflicting:
            checks['pinned_sources']['error'] = 'M13_EXISTING_WRONG_SOURCE_MUST_NOT_BE_OVERWRITTEN'
        else:
            checks['pinned_sources']['status'] = 'NEEDS_PINNED_FETCH'
    blockers = [k for k, v in checks.items() if v['status'] == 'BLOCKED']
    boost = _boost_libraries()
    if any(not p.is_file() for p in boost.values()):
        blockers.append('boost_shared_libraries')
    return dict(schema='w1-m13-native-build-preflight-v1',
                scope='PINNED_BUILD_PRECHECK_NOT_A_BOOLEAN_OR_NEWTON_RESULT',
                state='READY_TO_BUILD' if not blockers else 'BLOCKED',
                checks=checks, blockers=blockers,
                boost_shared={name: str(p) if p.is_file() else None
                              for name,p in boost.items()},
                memory_budget_bytes=m10.MAX_MEMORY,
                max_compile_parallelism=MAX_WORKERS,
                max_single_stage_seconds=MAX_STAGE_SECONDS,
                fetch_requires_explicit_opt_in=True,
                native_boolean_calls=0, full_solver_speedup=None,
                w0_w2_admitted=False, paper_speed_qualified=False)


def _limits(memory_ceiling):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    bound = min(x for x in (m10.MAX_MEMORY, memory_ceiling, soft, hard)
                if x != resource.RLIM_INFINITY)
    resource.setrlimit(resource.RLIMIT_AS, (bound, bound))


def _subprocess(command, *, cwd, log, memory_bytes, timeout_seconds=MAX_STAGE_SECONDS,
                coordinator=False):
    """Run one bounded foreground process; return its recorded exit status."""
    allowed = (2*MAX_STAGE_SECONDS + 120) if coordinator else MAX_STAGE_SECONDS
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= allowed:
        raise ValueError('M13_STAGE_TIMEOUT_EXCEEDS_60_MINUTES')
    if coordinator and (len(command)<2 or Path(str(command[1])).name != 'm11_native_host_runner.py'):
        raise ValueError('M13_ONLY_M11_CAN_COORDINATE_TWO_BOUNDED_JOBS')
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    with Path(log).open('x', encoding='utf-8') as output:
        proc = subprocess.Popen(list(map(str,command)), cwd=cwd, env=env,
                                stdout=output, stderr=subprocess.STDOUT,
                                start_new_session=True,
                                preexec_fn=lambda: _limits(memory_bytes))
        try:
            returncode = proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise TimeoutError('M13_STAGE_TIMEOUT_60_MINUTES') from exc
    if returncode != 0:
        raise RuntimeError('M13_BUILD_STAGE_FAILED_EXIT_' + str(returncode) + ':' + Path(log).name)
    return {'exit_code': 0, 'log_sha256': _sha(log)}


def _need_empty_target(path):
    if path.exists():
        raise FileExistsError('M13_REFUSES_TO_OVERWRITE_EXISTING_BUILD_TARGET:' + str(path))


def _fetch_pinned_sources(root, stage_dir, memory_bytes):
    """Explicit opt-in only; never run git checkout on main or another branch."""
    cherchi, cgal = root / CHERCHI_REL, root / CGAL_REL
    if _empty_directory_or_absent(cherchi):
        cherchi.parent.mkdir(parents=True, exist_ok=True)
        _subprocess(['git', 'clone', CHERCHI_URL, str(cherchi)], cwd=root,
                    log=stage_dir/'fetch-cherchi.log', memory_bytes=memory_bytes)
        _subprocess(['git','-C',str(cherchi),'checkout','--detach', CHERCHI_COMMIT],
                    cwd=root,log=stage_dir/'pin-cherchi.log',memory_bytes=memory_bytes)
    if _empty_directory_or_absent(cgal):
        cgal.parent.mkdir(parents=True, exist_ok=True)
        cgal.mkdir(exist_ok=True)
        _subprocess(['git','-C',str(cgal),'init'],cwd=root,
                    log=stage_dir/'init-cgal.log',memory_bytes=memory_bytes)
        _subprocess(['git','-C',str(cgal),'fetch','--depth=1','--filter=blob:none',
                     CGAL_URL, CGAL_COMMIT],cwd=root,
                    log=stage_dir/'fetch-cgal.log',memory_bytes=memory_bytes)
        _subprocess(['git','-C',str(cgal),'checkout','--detach','FETCH_HEAD'],cwd=root,
                    log=stage_dir/'pin-cgal.log',memory_bytes=memory_bytes)
    result = _source_check(root)
    if not result['pinned']:
        raise ValueError('M13_PINNED_SOURCE_REVISIONS_OR_HEADERS_FAILED')
    return result


def _core_args(root, out, python_executable, boost):
    args = [
        'cmake','-S',str(root),'-B',str(out),'-G','Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DMAKE_IT_STAND_BUILD_VIEWER=OFF',
        '-DMAKE_IT_STAND_BUILD_REACHABILITY=OFF',
        '-DMAKE_IT_STAND_BUILD_SPIN_IT_2014=OFF',
        '-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON',
        '-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON',
        '-DMAKE_IT_STAND_BUILD_PYTHON=ON',
        '-DMAKE_IT_STAND_FILTERED_BOUNDARY_KERNEL=ON',
        '-DBUILD_TESTING=OFF','-DBoost_USE_STATIC_LIBS=OFF',
        '-DBoost_THREAD_LIBRARY_RELEASE='+str(boost['thread']),
        '-DBoost_SYSTEM_LIBRARY_RELEASE='+str(boost['system']),
        '-DPython_EXECUTABLE='+str(python_executable),
        '-DPython3_EXECUTABLE='+str(python_executable),
    ]
    return args


def _cherchi_args(root, out, python_executable):
    return ['cmake','-S',str(root/'bindings/cherchi'),'-B',str(out),
            '-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
            '-DPython_EXECUTABLE='+str(python_executable),
            '-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON']


def _fix_boost_ninja(build_ninja, boost):
    """Patch ONLY the generated Ninja graph; never sudo-move system libraries."""
    path = Path(build_ninja)
    original = path.read_text()
    updated = original
    count = {}
    for name in ('thread', 'system'):
        shared = str(boost[name])
        if not Path(shared).is_file():
            raise ValueError('M13_BOOST_SHARED_LIBRARY_MISSING:' + name)
        static = shared[:-3] + '.a'
        count[name] = updated.count(static)
        updated = updated.replace(static, shared)
    if re.search(r'libboost_(?:thread|system)\.a', updated):
        raise ValueError('M13_STATIC_NONPIC_BOOST_REMAINING')
    if updated != original:
        tmp = path.with_name(path.name + '.m13-tmp')
        _need_empty_target(tmp)
        tmp.write_text(updated)
        tmp.replace(path)
    return dict(before_sha256=sha256(original.encode()).hexdigest(),
                after_sha256=sha256(updated.encode()).hexdigest(),
                replaced_static_boost_references=count,
                host_libraries_untouched=True)


@contextmanager
def _build_lock():
    import fcntl
    path = Path('/tmp/spin_test_w1_m13_native_build.lock')
    with path.open('a+', encoding='utf-8') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('M13_ANOTHER_W1_BUILD_ALREADY_RUNNING') from exc
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def execute(root, archive, output, *, allow_fetch=False, workers=2, run_m11=True):
    """Build isolated pinned extensions and optionally launch existing M11 gate."""
    if type(workers) is not int or not 1 <= workers <= MAX_WORKERS:
        raise ValueError('M13_MAX_FOUR_COMPILERS')
    root, archive, output = Path(root).resolve(), Path(archive).resolve(), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    checked = preflight(root, archive, allow_source_fetch=allow_fetch)
    _write_new(output/'preflight.json', checked)
    if checked['state'] != 'READY_TO_BUILD':
        _write_new(output/'failure.json', dict(status='BLOCKED_BEFORE_NATIVE_BUILD',
            blockers=checked['blockers'], math_executions=0, full_solver_speedup=None))
        return checked
    resource_bytes = checked['checks']['memory']['detail']['process_address_space_cap_bytes']
    boost = _boost_libraries()
    current_stage = 'VERIFY_SOURCES'
    try:
        with _build_lock():
            if not checked['checks']['pinned_sources']['detail']['pinned']:
                if not allow_fetch:
                    raise ValueError('M13_FETCH_REQUIRES_EXPLICIT_OPT_IN')
                _fetch_pinned_sources(root, output, resource_bytes)
            if not _source_check(root)['pinned']:
                raise ValueError('M13_SOURCE_REVISION_CHANGED_BEFORE_BUILD')
            core, cherchi = root/BUILD_CORE_REL, root/BUILD_CHERCHI_REL
            _need_empty_target(core)
            _need_empty_target(cherchi)
            record = []
            def stage(name, argv):
                nonlocal current_stage
                current_stage = name
                t0 = time.monotonic_ns()
                details = _subprocess(argv, cwd=root, log=output/(name+'.log'),
                         memory_bytes=resource_bytes)
                record.append(dict(stage=name, argv=list(map(str,argv)),
                                   wall_ns=time.monotonic_ns()-t0, **details))
            stage('configure-core', _core_args(root, core, sys.executable, boost))
            rewrite = _fix_boost_ninja(core/'build.ninja', boost)
            stage('build-core', ['cmake','--build',str(core),'--target',
                                 '_make_it_stand','--parallel',str(workers)])
            stage('configure-cherchi', _cherchi_args(root, cherchi, sys.executable))
            stage('build-cherchi', ['cmake','--build',str(cherchi),
                                    '--parallel',str(workers)])
            current_stage = 'VERIFY_COMPILED_ABI'
            inventory = m10.module_inventory(root, [core/'python', cherchi/'python'])
            if any(inventory[name]['status'] != 'FOUND' for name in m10.NATIVE):
                raise RuntimeError('M13_MISSING_COMPILED_EXTENSION_AFTER_BUILD')
            import_check = m10.native_import_probe(root,[core/'python',cherchi/'python'],
                                                   inventory,resource_bytes)
            build_receipt = dict(schema='w1-m13-pinned-native-build-v1',
                actual_compiled_modules={name:inventory[name]['sha256'] for name in m10.NATIVE},
                pinned_revision=_source_check(root),boost_ninja_rewrite=rewrite,
                build_commands=record,compiled_native_import=import_check,
                git_branch=m10.repo_identity(root)['branch'],
                full_solver_speedup=None, paper_speed_qualified=False)
            _write_new(output/'native-build-receipt.json', build_receipt)
        # The build lock is intentionally released before M11: M10 owns its
        # *separate* exclusive native runtime lock; do not deadlock the child.
        if not run_m11:
            return dict(state='NATIVE_COMPILED_ONLY_NOT_SCIENTIFICALLY_ADMITTED',
                        native_boolean_calls=0,full_solver_speedup=None)
        current_stage = 'SERIAL_M5_M9_M11'
        runner = root/'research/NeuralMoments/performance/m11_native_host_runner.py'
        stage_call = [sys.executable,str(runner),'--root',str(root),
                      '--archive',str(archive),'--output',str(output/'m11'),
                      '--module-dir',str(core/'python'),
                      '--module-dir',str(cherchi/'python'),
                      '--max-seconds',str(MAX_STAGE_SECONDS)]
        # M11 runs two native jobs sequentially, each individually capped at 1h.
        res = _subprocess(stage_call,cwd=root,log=output/'m11.log',
                          memory_bytes=resource_bytes,
                          timeout_seconds=2*MAX_STAGE_SECONDS + 120,coordinator=True)
        receipt_path = output/'m11/m11-native-validation-summary.json'
        if not receipt_path.is_file():
            raise RuntimeError('M13_M11_SCIENCE_RECEIPT_MISSING')
        receipt = json.loads(receipt_path.read_text())
        if (receipt.get('state') != 'FIVE_REAL_CHERCHI_EVALUATIONS_AND_SAVED_RECEIPTS_ADMITTED' or
                receipt.get('native_samples') != 5 or
                receipt.get('full_solver_speedup') is not None):
            raise ValueError('M13_M11_NOT_INDEPENDENTLY_ADMITTED')
        return dict(schema='w1-m13-native-build-and-gate-v1',
                    state='FIVE_REAL_SAME_Q_SCIENCE_RECEIPTS_ADMITTED_NOT_NEWTON',
                    m11_receipt_sha256=_sha(receipt_path),
                    build_receipt_sha256=_sha(output/'native-build-receipt.json'),
                    newton_terminal_admitted=False,full_solver_speedup=None,
                    paper_speed_qualified=False)
    except BaseException as exc:
        _write_new(output/'failure.json', dict(schema='w1-m13-native-build-failure-v1',
            stage=current_stage,status='FAILED_CLOSED',
            error=type(exc).__name__+': '+str(exc),
            native_science_admitted=False,full_solver_speedup=None))
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',required=True,type=Path)
    ap.add_argument('--archive',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--execute',action='store_true',help='Actually build; default preflight is read-only')
    ap.add_argument('--fetch-pinned-sources',action='store_true',
                    help='Explicit permission to fetch ONLY the pinned Cherchi/CGAL revisions')
    ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--build-only',action='store_true',
                    help='No scientific admission; compile and ABI-check without M11')
    a = ap.parse_args()
    if not a.execute:
        result = preflight(a.root,a.archive,allow_source_fetch=a.fetch_pinned_sources)
        if a.output.exists(): raise FileExistsError('M13_OUTPUT_ALREADY_EXISTS')
        a.output.mkdir(parents=True)
        _write_new(a.output/'preflight.json',result)
        if result['state']=='BLOCKED':
            _write_new(a.output/'failure.json', dict(status='BLOCKED',
                      blockers=result['blockers'],full_solver_speedup=None))
        print(json.dumps({'status': result['state'], 'blockers':result['blockers']}))
        if result['state']=='BLOCKED': raise SystemExit(2)
        return
    result = execute(a.root,a.archive,a.output,
                     allow_fetch=a.fetch_pinned_sources, workers=a.workers,
                     run_m11=not a.build_only)
    print(json.dumps({'status':result.get('state'),
                      'full_solver_speedup':None},sort_keys=True))
    if result.get('state') == 'BLOCKED': raise SystemExit(2)


if __name__=='__main__':
    main()
