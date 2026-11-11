"""Build-evidence recovery for W3; never dispatches a Boolean or Newton step.

Default: validate plan/cache and run quarterpoint tests, then stop. --build also
calls the existing pinned incremental build procedure, with a new output leaf.
The extra MemAvailable/disk floors below are conservative operational guards,
not claims about measured compiler peak memory or build-space requirements.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile

BRANCH = 'research/neuralmoments-w3-heart-h9-20261019'
H9 = Path('research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018')
PLAN_REL = 'Research/W3_H9_Results/m21-6d-plan-20261108T110852Z-3084537/quarterpoint-plan.json'
PLAN_SHA = 'dbed9b42b77a8d7df942613d7b9f111386ff7b00dcadde60f0b5a0912373965b'
MODULES = {'core': ('h9-w3-core', '_make_it_stand'),
           'boolean': ('h9-w3-cherchi', '_cherchi_core_boolean'),
           'arithmetic': ('h9-w3-cherchi', '_cherchi_rational_moments')}
GIB = 1024 ** 3
MIN_AVAILABLE = 24 * GIB
MIN_DISK_FREE = 4 * GIB


class Blocked(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise Blocked(reason)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def meminfo(text):
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            values[parts[0].rstrip(':')] = int(parts[1]) * 1024
    require('MemAvailable' in values and 'SwapTotal' in values, 'MEMINFO_INCOMPLETE')
    return {'available_bytes': values['MemAvailable'], 'swap_bytes': values['SwapTotal']}


def resource_reasons(memory, free_bytes):
    reasons = []
    if memory['available_bytes'] < MIN_AVAILABLE:
        reasons.append('AVAILABLE_RAM_BELOW_24_GIB')
    if memory['swap_bytes'] != 0:
        reasons.append('SWAP_MUST_BE_ZERO')
    if any(value < MIN_DISK_FREE for value in free_bytes):
        reasons.append('DISK_FREE_BELOW_OPERATIONAL_4_GIB_FLOOR')
    return reasons


def load_plan(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'PLAN_FILE_MISSING_OR_SYMLINK')
    require(digest(path) == PLAN_SHA, 'PINNED_PLAN_SHA_MISMATCH')
    plan = json.loads(path.read_bytes())
    require(plan.get('schema') == 'heart-h9-m21-6d-four-quarterpoint-plan-v1'
            and plan.get('status') == 'FOUR_REAL_QUARTERPOINTS_PREDECLARED_NOT_EXECUTED'
            and plan.get('point_count') == 4 and plan.get('newton_admitted') is False,
            'PLAN_SCOPE_CHANGED')
    require(plan.get('new_boolean_calls_executed') == 0
            and plan.get('new_native_source_calls_executed') == 0, 'PLAN_ALREADY_EXECUTED_CLAIM')
    return plan


def cache_hashes(repo):
    hashes = {}
    for key, (directory, module) in MODULES.items():
        paths = list((Path(repo) / 'build' / directory / 'python').glob(module + '*.so'))
        require(len(paths) == 1 and paths[0].is_file() and not paths[0].is_symlink(),
                'MISSING_OR_AMBIGUOUS_CACHED_MODULE:' + module)
        hashes[key] = digest(paths[0])
    return hashes


def verify_evidence(evidence, head, hashes):
    expected = {module: hashes[key] for key, (_, module) in MODULES.items()}
    require(evidence.get('status') == 'NATIVE_BINARIES_BUILT_AND_IMPORTABLE_NOT_YET_EVALUATED',
            'BUILD_NOT_SUCCESSFUL')
    require(evidence.get('head_after_build') == head, 'BUILD_HEAD_MISMATCH')
    require(evidence.get('module_sha256') == expected, 'BUILD_MODULE_SHA_MISMATCH')
    require(evidence.get('newton_admitted') is False, 'UNSAFE_BUILD_NEWTON_CLAIM')
    return expected


def clean_env(python_path, stdcxx, tmpdir, environ=None):
    env = dict(os.environ if environ is None else environ)
    for key in ('CONDA_PREFIX', 'LD_LIBRARY_PATH', 'LIBRARY_PATH', 'CMAKE_PREFIX_PATH',
                'PYTHONPATH', 'PYTHONHOME', 'BOOST_ROOT', 'Boost_ROOT', 'Boost_DIR', 'PKG_CONFIG_PATH'):
        env.pop(key, None)
    require(Path(python_path).is_file() and os.access(python_path, os.X_OK), 'PYTHON_NOT_EXECUTABLE')
    require(Path(stdcxx).is_file(), 'SYSTEM_LIBSTDCXX_MISSING')
    env.update(PATH=str(Path(python_path).absolute().parent) + ':/usr/local/bin:/usr/bin:/bin',
               LD_PRELOAD=str(Path(stdcxx).resolve()), TMPDIR=str(tmpdir),
               PYTHONINTMAXSTRDIGITS='100000', PYTHONUNBUFFERED='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    return env


def new_session(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='m21-6d-build-recovery-', dir=root))
    output = folder / 'build-output'
    require(not os.path.lexists(output), 'BUILD_OUTPUT_MUST_NOT_EXIST')
    return folder, output


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    require(result.returncode == 0, 'GIT_FAILED:' + result.stderr.strip())
    return result.stdout.strip()


def logged_run(command, log, env, cwd, timeout):
    """Bound the child process group and retain output on failure/timeout."""
    with Path(log).open('x') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   cwd=cwd, env=env, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()


def tail(path):
    with Path(path).open('rb') as stream:
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(max(0, size - 16000))
        print(stream.read().decode('utf8', errors='replace'), flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path('/data/xvxinyao1/Spin_test-W3'))
    parser.add_argument('--plan', type=Path, default=Path.home() / PLAN_REL)
    parser.add_argument('--output-root', type=Path, default=Path('/data/xvxinyao1/W3_H9_Results'))
    parser.add_argument('--build', action='store_true', help='Run pinned build after tests and resource checks')
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    record = None
    state = {'schema': 'heart-h9-m21-6d-build-recovery-v1', 'status': 'CHECKING',
             'new_boolean_calls': 0, 'new_source_motion_calls': 0, 'newton_admitted': False}
    try:
        require(sys.version_info[:2] == (3, 13), 'REQUIRES_PYTHON_3_13')
        require(git(repo, 'branch', '--show-current') == BRANCH, 'WRONG_W3_BRANCH')
        require(not git(repo, 'status', '--porcelain', '--untracked-files=no'), 'TRACKED_FILES_DIRTY')
        head = git(repo, 'rev-parse', 'HEAD')
        source = repo / H9 / 'source'
        plan = load_plan(args.plan)
        before = cache_hashes(repo)
        require(before == plan.get('native_binary_sha256'), 'CACHED_MODULES_DIFFER_FROM_PLAN')
        record, output = new_session(args.output_root)
        tmpdir = record / 'tmp'
        tmpdir.mkdir()
        env = clean_env(sys.executable, '/usr/lib/x86_64-linux-gnu/libstdc++.so.6', tmpdir)
        state.update(head_sha=head, plan_sha256=PLAN_SHA, cached_module_sha256=before,
                     build_output=str(output), record_dir=str(record))
        print('RECOVERY_RECORD=' + str(record), flush=True)
        # Ignore untracked external/ dependencies; the original builder still
        # performs its stricter importable-source and frozen-workflow checks.
        with (repo / 'build' / '.w3-m21-6d-build.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Blocked('ANOTHER_SAFE_BUILD_IS_RUNNING') from error
            test_log = record / 'quarterpoint-tests.log'
            code = logged_run([sys.executable, '-m', 'unittest', 'discover',
                               '-s', str(repo / H9 / 'tests'),
                               '-p', 'test_h9_m21_6d_quarterpoint*.py', '-v'],
                              test_log, env, repo, 120)
            state['test_exit_code'] = code
            tail(test_log)
            require(code == 0, 'QUARTERPOINT_TESTS_FAILED_NO_BUILD')
            memory = meminfo(Path('/proc/meminfo').read_text())
            free = [shutil.disk_usage(repo / 'build').free, shutil.disk_usage(record).free]
            reasons = resource_reasons(memory, free)
            state.update(memory=memory, disk_free_bytes=free, operational_blockers=reasons)
            print('MEM_AVAILABLE_GIB=%.2f' % (memory['available_bytes'] / GIB), flush=True)
            if not args.build:
                state['status'] = 'CHECKED_NO_BUILD_NO_BOOLEAN'
                return 0
            require(not reasons, ';'.join(reasons))
            require(git(repo, 'rev-parse', 'HEAD') == head, 'HEAD_CHANGED_BEFORE_BUILD')
            require(not os.path.lexists(output), 'BUILD_OUTPUT_MUST_NOT_EXIST')
            build_log = record / 'build-console.log'
            code = logged_run([sys.executable, '-u', str(source / 'prepare_h9_pinned_native.py'),
                               '--phase', 'build', '--repo', str(repo), '--output', str(output)],
                              build_log, env, repo, 3600)
            state['build_exit_code'] = code
            tail(build_log)
            require(code == 0, 'PINNED_BUILD_FAILED_OR_TIMED_OUT')
            evidence_path = output / 'build_evidence.json'
            require(evidence_path.is_file(), 'BUILD_EVIDENCE_NOT_PRODUCED')
            evidence = json.loads(evidence_path.read_bytes())
            require(git(repo, 'rev-parse', 'HEAD') == head, 'HEAD_CHANGED_DURING_BUILD')
            after = cache_hashes(repo)
            require(after == before, 'MODULE_SHA_CHANGED_DO_NOT_RUN_BOOLEAN')
            module_hashes = verify_evidence(evidence, head, after)
            sys.path.insert(0, str(source))
            from prepare_h9_pinned_native import verify_build_evidence
            verify_build_evidence(repo, evidence_path, module_hashes)
            state.update(status='BUILD_EVIDENCE_VERIFIED_NO_BOOLEAN',
                         build_evidence=str(evidence_path), build_evidence_sha256=digest(evidence_path))
            print('BUILD_EVIDENCE=' + str(evidence_path), flush=True)
            print('BUILD_EVIDENCE_SHA256=' + digest(evidence_path), flush=True)
            return 0
    except Exception as error:
        state.update(status='BLOCKED_NO_BOOLEAN', error=f'{type(error).__name__}: {error}')
        print(state['error'], file=sys.stderr, flush=True)
        return 2
    finally:
        if record is not None:
            path = record / 'recovery-result.json'
            with path.open('x') as stream:
                json.dump(state, stream, indent=2, sort_keys=True)
                stream.write('\n')
            print('RECOVERY_RESULT=' + str(path), flush=True)
        print('NO_BOOLEAN_WAS_DISPATCHED_BY_THIS_WRAPPER', flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
