"""Bounded native M/F/D preparation, explicitly separate from formal W0 M6.

The worker constructs actual immutable native material regions, authenticates
M=F+D, prepares the unchanged core request and a fresh Cherchi evaluator, and
observes six real pins.  It never calls the evaluator or any M6 entry point.
The 6 GiB / 900 s cap is for this limited preparation only; it does not lower
the formal M6 physical/effective-memory floor or grant scientific admission.
"""
from __future__ import annotations

import argparse
import fcntl
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time

from p20_native_factory import ADMISSION, BASE, load_request, observed_pins, prepare_context, recheck_inputs


SCHEMA = 'W4_P20_BOUNDED_OWNED_MATERIAL_PREPARATION_V1'
MAX_ADDRESS_BYTES = 6 * 1024**3
MAX_SECONDS = 900
LOCK_PATH = Path('/tmp/spin_test_w0_m5_cherchi_job.lock')


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _new_json(path, value):
    path = Path(path)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def resource_observation():
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
            memory[key + '_bytes'] = int(value.split()[0]) * 1024
    cgroup = {}
    for name in ('memory.max', 'memory.current', 'memory.peak', 'memory.swap.max', 'memory.swap.current'):
        path = Path('/sys/fs/cgroup') / name
        cgroup[name] = path.read_text().strip() if path.exists() else None
    return {'physical': memory, 'visible_cgroup_v2': cgroup,
            'worker_address_space_limit_bytes': MAX_ADDRESS_BYTES,
            'maximum_wall_seconds': MAX_SECONDS,
            'formal_M6_resource_preflight_satisfied_by_this_probe': False}


def _worker(worker_output):
    resource.setrlimit(resource.RLIMIT_AS, (MAX_ADDRESS_BYTES, MAX_ADDRESS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_SECONDS, MAX_SECONDS + 1))
    def observe(row):
        print(json.dumps(row, sort_keys=True, allow_nan=False), flush=True)
    started = time.monotonic()
    bundle = prepare_context(observer=observe)
    import numpy as np
    from p16_exact_binary64_chain import NAMES, exact_ten
    from p20_physical_contract import (build_contract_report, fraction_from_payload,
        fraction_payload, raw10_original_to_target, raw10_target_to_original,
        raw10_reference_to_si)

    contract = build_contract_report(bundle['frame'], core_source_root=bundle['source_root'],
        p19_case_root=BASE/'P19_material_case',
        p19_report_path=BASE/'P19_CANONICAL_SOURCE_COMPLETE_REPORT.json')
    regions, raw10 = {}, {}
    observe({'event': 'start', 'stage': 'owned_boundary_and_independent_exact_moments'})
    for name in ('M', 'F', 'D'):
        snapshot = bundle['snapshots'][name]
        region = snapshot.exact_region()
        facts = dict(region.facts)
        actual = region.rational_boundary
        source_vertices, source_faces = bundle['raw_meshes'][name]
        expected_rational = tuple(tuple(Fraction.from_float(x) for x in row) for row in source_vertices)
        actual_rational = tuple(tuple(Fraction(x) for x in row) for row in actual['vertices'])
        if actual_rational != expected_rational or not np.array_equal(actual['faces'], source_faces):
            raise ValueError('P20_OWNED_BOUNDARY_DIFFERS_FROM_FROZEN_SOURCE_' + name)
        if not region.matches_rational_boundary(actual['vertices'], np.asarray(source_faces, dtype=np.int32)):
            raise ValueError('P20_NATIVE_BOUNDARY_AUTHENTICATION_FAILED_' + name)
        if region.boundary_coordinate_policy != 'BINARY64_INDEXED':
            raise ValueError('P20_UNEXPECTED_NATIVE_BOUNDARY_COORDINATE_POLICY_' + name)
        raw10[name] = exact_ten(source_vertices, source_faces)
        historical = tuple(fraction_from_payload(x) for x in
            contract['physical_replay']['materials'][name]['reference_raw10_exact'])
        if raw10[name] != historical:
            raise ValueError('P20_FRESH_GEOMETRY_INTEGRAL_DIFFERS_FROM_P19_' + name)
        target = raw10_original_to_target(raw10[name], bundle['frame'])
        if raw10_target_to_original(target, bundle['frame']) != raw10[name]:
            raise ValueError('P20_EXACT_RAW10_FRAME_ROUNDTRIP_FAILED_' + name)
        regions[name] = dict(native_owned_region_facts=facts,
            original_indexed_binary64_input_preserved=True,
            owned_rational_boundary_equals_exact_frozen_binary64_input=True,
            native_matches_rational_boundary=True,
            raw10_order=list(NAMES), reference_raw10_exact=[fraction_payload(x) for x in raw10[name]],
            target_raw10_exact=[fraction_payload(x) for x in target],
            si_raw10_exact=[fraction_payload(x) for x in raw10_reference_to_si(raw10[name])],
            fresh_geometry_reintegration_matches_frozen_P19=True,
            exact_target_to_original_roundtrip=True)
    residual = tuple(m-f-d for m, f, d in zip(raw10['M'], raw10['F'], raw10['D']))
    if any(residual):
        raise ValueError('P20_EXACT_TEN_MOMENT_ADDITIVITY_FAILED')
    observe({'event': 'completed', 'stage': 'owned_boundary_and_independent_exact_moments'})

    exact_fixed = raw10_original_to_target(raw10['F'], bundle['frame'])
    actual_fixed = tuple(float(x) for x in bundle['evaluator'].fixed)
    fixed_difference = tuple(Fraction.from_float(x)-y for x, y in zip(actual_fixed, exact_fixed))
    pins = observed_pins(bundle)
    problem = bundle['problem']
    partition = problem.identity['partition']
    if not (partition['completed'] is True and partition['complete_partition'] is True
            and partition['union_equals_whole'] is True and partition['no_positive_volume_overlap'] is True
            and partition['missing_whole_content'] is False and partition['excess_union_content'] is False
            and all(partition['part_subset_whole'])
            and partition['part_digests'] == [regions[n]['native_owned_region_facts']['region_digest'] for n in ('F', 'D')]
            and partition['whole_digest'] == regions['M']['native_owned_region_facts']['region_digest']):
        raise ValueError('P20_NATIVE_MFD_PARTITION_INCOMPLETE_OR_UNBOUND')
    if bundle['evaluator'].call_counts != {'source': 0, 'boolean': 0, 'integration': 0, 'derivative': 0}:
        raise ValueError('P20_PREPARATION_UNEXPECTED_NATIVE_EVALUATION')
    recheck_inputs(bundle['input_identity'])
    result = {
        'schema': SCHEMA, 'status': 'P20_OWNED_MFD_AND_FRESH_FACTORY_PREPARATION_PASS',
        'completed': True, 'input_identity': bundle['input_identity'],
        'native_regions': regions, 'native_M_equals_F_plus_D_partition': partition,
        'native_problem_input_digest': problem.input_digest,
        'native_problem_identity': problem.identity,
        'runtime_python_git_blobs': bundle['runtime_python_git_blobs'],
        'exact_raw10_M_minus_F_minus_D': [fraction_payload(x) for x in residual],
        'all_ten_exact_additivity_residuals_zero': True,
        'region_partition_proof_does_not_rely_on_moment_equality': True,
        'native_geometry_construction_in_this_probe': False,
        'native_owned_set_checker': 'EXISTING_CGAL_NEF_INDEPENDENT_VERIFICATION_OF_P19_CHERCHI_INPUTS',
        'P19_Cherchi_outputs_unchanged': True,
        'factory_fresh_call_counts': dict(bundle['evaluator'].call_counts),
        'native_fixed_shell_integration_executed': True,
        'evaluator_settings': bundle['evaluator_settings'], 'solver_settings': bundle['solver_settings'],
        'prepared_run_identity': json.loads(bundle['prepared'].identity_json),
        'physical_and_frame_contract': contract,
        'native_fixed_moment_diagnostic': {
            'meaning': 'Core request integrates the rounded normalized F, then changes target frame in binary64.',
            'is_exact_affine_image_of_frozen_F_moments': not any(fixed_difference),
            'exact_affine_target_F_raw10': [fraction_payload(x) for x in exact_fixed],
            'actual_evaluator_fixed_raw10': list(actual_fixed),
            'actual_minus_exact_target_F': [fraction_payload(x) for x in fixed_difference],
            'max_absolute_difference': max(float(abs(x)) for x in fixed_difference),
            'diagnostic_does_not_grant_W0_moment_gate_admission': True,
        },
        'observed_six_pins': pins,
        'loaded_native_files': {
            'native': str(Path(bundle['evaluator'].native.__file__).resolve()),
            'bridge': str(Path(bundle['evaluator'].bridge.__file__).resolve()),
            'arithmetic': str(Path(bundle['evaluator'].arithmetic.__file__).resolve()),
        },
        'native_arithmetic_identity': dict(bundle['evaluator'].arithmetic_identity),
        'stage_seconds': bundle['timings'], 'total_worker_seconds': time.monotonic()-started,
        'worker_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'admission': dict(ADMISSION),
        'remaining_formal_M6': ['One real source generation at registered unit c',
            'Retained and complement from exactly the same saved source',
            'Owned D=retained+cavity and M=F+retained+cavity',
            'W0 actual cross-oracle ten-moment comparisons and same-call 10x10 Jc binding',
            'Formal resource-compliant isolated launch and receipt'],
    }
    _new_json(worker_output, result)


def run_owned_preparation(output, *, pins_output=None, seconds=MAX_SECONDS):
    if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
        raise ValueError('P20_INVALID_BOUNDED_PREPARATION_TIME_LIMIT')
    output = Path(output).absolute()
    worker_output = output.with_name(output.stem + '.worker.json')
    progress = output.with_name(output.stem + '.progress.jsonl')
    for path in (output, worker_output, progress, *((Path(pins_output).absolute(),) if pins_output else ())):
        if path.exists() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('P20_NO_OVERWRITE_OR_SYMLINK_OUTPUT:' + str(path))
    before = resource_observation()
    report = {'schema': SCHEMA, 'status': 'P20_BOUNDED_PREPARATION_NOT_COMPLETED',
              'completed': False, 'resource_before': before, 'admission': dict(ADMISSION)}
    started = time.monotonic()
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    command = [sys.executable, str(Path(__file__).resolve()), '--owned-worker', str(worker_output)]
    report['command'] = command
    try:
        if before['physical']['SwapTotal_bytes'] != 0:
            raise ValueError('P20_BOUNDED_PREPARATION_REQUIRES_SWAP_ZERO')
        _, original_inputs = load_request()
        with tempfile.TemporaryDirectory(prefix='w4-p20-owned-pycache-') as cache_dir, LOCK_PATH.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            env['PYTHONPYCACHEPREFIX'] = cache_dir
            env['PYTHONDONTWRITEBYTECODE'] = '1'
            with progress.open('xb') as stream:
                child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                         env=env, start_new_session=True)
                try:
                    code = child.wait(timeout=seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    code = child.wait()
                    report['timeout'] = True
            report['worker_exit_code'] = code
            recheck_inputs(original_inputs)
            if code == 0 and worker_output.is_file():
                worker = json.loads(worker_output.read_text())
                if worker.get('schema') != SCHEMA or worker.get('completed') is not True or worker.get('admission') != ADMISSION:
                    raise ValueError('P20_WORKER_RESULT_SCHEMA_OR_ADMISSION_MISMATCH')
                report.update(status=worker['status'], completed=True, worker_completed=True, result=worker)
                if pins_output:
                    _new_json(pins_output, worker['observed_six_pins'])
                    report['pins_file'] = {'path': str(Path(pins_output).absolute()), 'sha256': _sha(pins_output)}
            else:
                report['status'] = 'P20_BOUNDED_PREPARATION_WORKER_FAILED'
    except Exception as error:
        report.update(status='P20_BOUNDED_PREPARATION_BLOCKED', completed=False,
                      error_type=type(error).__name__, error=str(error))
    report['elapsed_seconds'] = time.monotonic()-started
    report['resource_after'] = resource_observation()
    if progress.is_file():
        report['progress_log'] = {'path': str(progress), 'sha256': _sha(progress), 'bytes': progress.stat().st_size}
    if worker_output.is_file():
        report['worker_output'] = {'path': str(worker_output), 'sha256': _sha(worker_output)}
    _new_json(output, report)
    return (0 if report['completed'] else 2), report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--pins-output')
    parser.add_argument('--seconds', type=int, default=MAX_SECONDS)
    parser.add_argument('--owned-worker', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.owned_worker:
        _worker(Path(args.owned_worker))
        return 0
    if not args.output:
        parser.error('--output required')
    code, report = run_owned_preparation(args.output, pins_output=args.pins_output, seconds=args.seconds)
    print(json.dumps({'status': report['status'], 'completed': report['completed'],
                      'formal_M6_passed': False, 'output': args.output}, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
