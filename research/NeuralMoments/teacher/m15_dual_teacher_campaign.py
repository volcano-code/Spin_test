"""W2 M15: serial, source-frozen Heart and Noodles Cherchi teacher admission.

No simulated native calls. Requires genuinely compiled modules for runtime.
The archived Heart H8f material is historical (upstream Actions failure),
while the frozen Noodles V7 final OBJ is a different, output-only asset.
"""
from __future__ import annotations

import argparse
import hashlib
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

import numpy as np

HEART_ZIP_SHA256 = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
HEART_REQUEST_SHA256 = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
HEART_RUN_ID, HEART_ARTIFACT_ID = 39123384402, 12135528290
HEART_ORIGINAL_SHA = '0bcc187b3005478baa586a6d6f450e73811ca342'
NOODLES_V7_COMMIT = '053756f5091ab3e07d6bd29c40baab146e910121'
NOODLES_FINAL_OBJ_SHA256 = 'e979bd3980a5efaf9b03d047c4e19e9296ddb426267a7322ff4e1a4b954fe80a'
NOODLES_FINAL_OBJ_GIT_BLOB = 'f803c45274d7721b854cfd19a5173e4b43e79af1'
NOODLES_STATUS_GIT_BLOB = '7233e25162f287c9584b68bea447095deca4549'
NOODLES_SOLVER_GIT_BLOB = '2ae059052d28893afc3d289944551e4eaa857f11'
NOODLES_REQUEST_GIT_BLOB = 'fac1fd017a95846d8a918a924395fbe546404f42'
NOODLES_EXPECTED_TEN = [
    .985807721802751, 4.3883919715881344e-14, -9.798289587100347e-16,
    .9939894479131947, .21042996239210696, .15175169536911137,
    1.0318556681301232, -3.799175222714742e-16,
    4.028558731079101e-14, 1.1886815084125177e-05,
]
NOODLES_MOMENT_PREDECLARED_TOLERANCE = 1e-10
HEART_PARTITION_PREDECLARED_TOLERANCE = 1e-9  # frozen prepare_h8_solver_request.py
MIN_NATIVE_MEMORY = 24 * 1024**3
PAIR_ORDER = ((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, allow_nan=False, sort_keys=True,
                      separators=(',', ':'))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def parse_obj_bytes(data: bytes):
    """Read indexed static OBJ with all vertices before faces; no silent repair."""
    v, f = [], []
    for n, raw in enumerate(data.decode('utf-8-sig').splitlines(), 1):
        line = raw.partition('#')[0].strip()
        if not line:
            continue
        parts = line.split()
        if parts[0] == 'v':
            require(len(parts) == 4, 'OBJ_BAD_VERTEX_LINE')
            try:
                vertex = tuple(float(x) for x in parts[1:])
            except ValueError as exc:
                raise ValueError('OBJ_BAD_FLOAT') from exc
            require(all(math.isfinite(x) for x in vertex), 'OBJ_NONFINITE')
            v.append(vertex)
        elif parts[0] == 'f':
            require(len(parts) == 4, 'OBJ_NONTRIANGLE')
            require(all(t.isdigit() and int(t) > 0 for t in parts[1:]),
                    'OBJ_INDEX_NOT_POSITIVE_INTEGER')
            face = tuple(int(t)-1 for t in parts[1:])
            require(len(set(face)) == 3 and max(face) < len(v), 'OBJ_BAD_FACE_INDEX')
            f.append(face)
        else:
            require(parts[0] in ('vn', 'vt', 'o', 'g', 's', 'usemtl', 'mtllib'),
                    'UNSUPPORTED_OBJ_RECORD')
    require(len(v) >= 4 and len(f) >= 4, 'OBJ_EMPTY_OR_OPEN')
    return np.asarray(v, dtype='<f8'), np.asarray(f, dtype='<i4')


def integrate_raw_ten(vertices, faces):
    """Independent signed tetra integration in a *single explicitly stated* frame."""
    faces = np.asarray(faces, dtype=np.int64)
    require(faces.ndim == 2 and faces.shape[1] == 3, 'INVALID_FACE_SHAPE')
    pts = np.asarray(vertices, dtype=np.float64)
    require(pts.ndim == 2 and pts.shape[1] == 3 and np.isfinite(pts).all(),
            'INVALID_VERTEX_SHAPE')
    require(np.all(faces >= 0) and np.all(faces < len(pts)), 'INVALID_FACE_INDEX')
    t = pts[faces]
    a, b, c = t[:, 0, :], t[:, 1, :], t[:, 2, :]
    volume = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6
    axes = t.sum(axis=1)
    r = np.zeros(10)
    r[0] = math.fsum(volume.tolist())
    r[1:4] = [math.fsum((volume * axes[:, k] / 4).tolist()) for k in range(3)]
    for k, (i, j) in enumerate(PAIR_ORDER):
        terms = volume * (axes[:, i] * axes[:, j] +
                          np.sum(t[:, :, i]*t[:, :, j], axis=1)) / 20
        r[4+k] = math.fsum(terms.tolist())
    require(np.isfinite(r).all(), 'INVALID_INTEGRATED_MOMENTS')
    return r


def read_cgroup_memory():
    for name in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        p = Path(name)
        if p.is_file():
            s = p.read_text().strip()
            if s != 'max':
                return int(s)
    return None


def require_native_resources():
    limit = read_cgroup_memory()
    require(limit is not None and limit >= MIN_NATIVE_MEMORY,
            'NATIVE_REQUIRES_AT_LEAST_24GIB_EFFECTIVE_MEMORY')
    # Check host swap, not just cgroup effective swap.
    total_swap = 0
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('SwapTotal:'):
            total_swap = int(line.split()[1]) * 1024
    require(total_swap == 0, 'NATIVE_REQUIRES_SWAP0')
    return {'cgroup_memory_bytes': limit, 'swap_bytes': total_swap}


def _member(z, name):
    info = z.getinfo(name)
    require(info.file_size <= 9_000_000, 'ZIP_MEMBER_TOO_LARGE')
    return z.read(info)


def _assert_mesh_link(source, request_v, request_f, *, unit_length_mm=25):
    vertices, faces = parse_obj_bytes(source)
    expected_v = np.asarray(request_v, dtype='<f8')
    expected_f = np.asarray(request_f, dtype='<i4')
    require(vertices.shape == expected_v.shape and faces.shape == expected_f.shape,
            'FROZEN_REQUEST_MESH_SHAPE_MISMATCH')
    require((vertices / unit_length_mm).tobytes() == expected_v.tobytes(),
            'FROZEN_REQUEST_MESH_VERTEX_BINARY64_MISMATCH')
    require(faces.tobytes() == expected_f.tobytes(),
            'FROZEN_REQUEST_MESH_FACE_BINARY64_MISMATCH')
    return vertices, faces


def verify_frozen_heart(archive_path):
    start = time.monotonic()
    require(file_sha256(archive_path) == HEART_ZIP_SHA256, 'NOT_H8F_FROZEN_ARCHIVE')
    with ZipFile(archive_path) as z:
        raw = _member(z, 'artifacts/h8-request/prepared-request.json')
        require(sha256(raw) == HEART_REQUEST_SHA256, 'FROZEN_H8_REQUEST_SHA_DRIFT')
        prep = json.loads(raw)
        require(prep['schema'] == 'spin-heart-h8-faster-preparation-v1',
                'FROZEN_H8_REQUEST_SCHEMA_MISMATCH')
        evidence = prep['evidence']
        require(evidence['scope'] == 'H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED'
                and evidence['original_author_cad'] is False,
                'ORIGINAL_CAD_CLAIM_NOT_ALLOWED')
        source = {}
        for name in ('initial_top.obj', 'fixed_shell.obj', 'design_domain.obj'):
            data = _member(z, 'artifacts/h8-input/'+name)
            require(sha256(data) == evidence['source_sha256'][name],
                    'H8_FROZEN_SOURCE_SHA_DRIFT:'+name)
            source[name] = data
        request = prep['request']
        input_audit = json.loads(_member(z, 'artifacts/h8-input/H8_INDEPENDENT_AUDIT.json'))
        cad_audit = json.loads(_member(z, 'artifacts/h8-input/H8_CAD_AUDIT.json'))
        require(input_audit['success'] is True and
                input_audit['original_author_cad_qualified'] is False and
                cad_audit['classification'] ==
                'PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED',
                'H8_FROZEN_INDEPENDENT_INPUT_AUDIT_REJECTED')
        scale_mm = float(evidence['normalized_scale_mm_per_unit'])
        require(scale_mm == 25 and float(request['original_units_per_normalized_unit']) == .025,
                'H8_MM_AND_M_UNIT_SCALE_MISMATCH')
        outer_v, outer_f = _assert_mesh_link(source['initial_top.obj'],
                                             request['outer_vertices'], request['outer_faces'],
                                             unit_length_mm=scale_mm)
        design_v, design_f = _assert_mesh_link(source['design_domain.obj'],
                                               request['design_vertices'], request['design_faces'],
                                               unit_length_mm=scale_mm)
        fixed_v, fixed_f = parse_obj_bytes(source['fixed_shell.obj'])
        start_integration = time.monotonic()
        outer_r = integrate_raw_ten(outer_v/scale_mm, outer_f)
        design_r = integrate_raw_ten(design_v/scale_mm, design_f)
        fixed_r = integrate_raw_ten(fixed_v/scale_mm, fixed_f)
        registered_f = np.asarray(request['fixed_shell_moments'], dtype=np.float64)
        fixed_error = float(np.max(np.abs(fixed_r-registered_f)))
        partition_error = float(np.max(np.abs(outer_r - fixed_r - design_r)))
        require(fixed_error <= HEART_PARTITION_PREDECLARED_TOLERANCE,
                'H8_FIXED_MOMENT_REFERENCE_DISAGREES')
        require(partition_error <= HEART_PARTITION_PREDECLARED_TOLERANCE,
                'H8_FROZEN_F_D_PARTITION_DISAGREES')
        point0 = json.loads(_member(z, 'artifacts/h8f-all81-points/point-000.json'))
        c = point0['coefficients']
        require(len(c) == 10 and all(math.isfinite(float(x)) for x in c),
                'H8_BAD_FROZEN_NATIVE_C')
    return {
        'schema': 'w2-m15-heart-frozen-input-preflight-v1',
        'status': 'FROZEN_H8_OUTER_DESIGN_FIXED_INPUT_VERIFIED',
        'source': {'run_id': HEART_RUN_ID, 'artifact_id': HEART_ARTIFACT_ID,
                   'source_commit_sha': HEART_ORIGINAL_SHA,
                   'original_workflow_conclusion': 'failure',
                   'archive_sha256': HEART_ZIP_SHA256,
                   'request_sha256': HEART_REQUEST_SHA256,
                   'mesh_file_sha256': {name: sha256(data) for name, data in source.items()}},
        'outer_vertices': len(outer_v), 'outer_faces': len(outer_f),
        'design_vertices': len(design_v), 'design_faces': len(design_f),
        'fixed_vertices': len(fixed_v), 'fixed_faces': len(fixed_f),
        'physical_obj_mm_per_normalized_unit': scale_mm,
        'request_m_per_normalized_unit': request['original_units_per_normalized_unit'],
        'frozen_initial_native_c': c,
        'frozen_initial_native_c_sha256': sha256(canonical(c).encode()),
        'fixed_r_vs_registered_max_abs_error': fixed_error,
        'F_plus_D_vs_outer_max_abs_error': partition_error,
        'predeclared_per_case_moment_absolute_threshold': HEART_PARTITION_PREDECLARED_TOLERANCE,
        'geometry_reference_elapsed_seconds': time.monotonic() - start_integration,
        'preflight_elapsed_seconds': time.monotonic() - start,
        'independent_archived_input_audit_passed': True,
        'source_3D_boolean_exact_recertified_here': False,
        'new_native_calls': 0, 'training_admitted': False,
        '_prepared_request': prep,
    }


def create_normalized_obj(request, destination, source_sha):
    """Deterministic W2 native-view file, not a replacement for original CAD."""
    path = Path(destination)
    with path.open('x', encoding='utf-8') as f:
        f.write('# W2 M15 normalized view of frozen physical H8 OBJ; not author CAD\n')
        f.write('# original_frozen_source_sha256='+source_sha+'\n')
        for x, y, z in request['outer_vertices']:
            f.write(f'v {repr(float(x))} {repr(float(y))} {repr(float(z))}\n')
        for a, b, c in request['outer_faces']:
            f.write(f'f {a+1} {b+1} {c+1}\n')
    v, faces = parse_obj_bytes(path.read_bytes())
    assert v.tobytes() == np.asarray(request['outer_vertices'], dtype='<f8').tobytes()
    assert faces.tobytes() == np.asarray(request['outer_faces'], dtype='<i4').tobytes()
    return {'path': str(path), 'sha256': file_sha256(path),
            'is_original_source_file': False, 'original_source_sha256': source_sha}


def audit_exported_noodles_obj(path):
    """Standalone secondary audit of *optimized final OBJ*, not a native input."""
    require(file_sha256(path) == NOODLES_FINAL_OBJ_SHA256,
            'UNRECOGNIZED_NOODLES_V7_FINAL_OBJ_SHA')
    v, f = parse_obj_bytes(Path(path).read_bytes())
    require((len(v), len(f)) == (42932, 86076), 'NOODLES_FINAL_FACE_COUNT_CHANGED')
    # The old V7 raw-moment evidence uses the tip at z=-4 mm as target origin.
    target = v.copy();target[:, 2] += 4
    raw = integrate_raw_ten(target/25., f)
    error = float(np.max(np.abs(raw - np.asarray(NOODLES_EXPECTED_TEN))))
    require(error <= NOODLES_MOMENT_PREDECLARED_TOLERANCE,
            'NOODLES_TERMINAL_REFERENCE_TEN_MOMENTS_MISMATCH')
    return {'status': 'HISTORICAL_OPTIMIZED_OBJ_TEN_MOMENTS_RECOMPUTED',
            'source_commit_sha': NOODLES_V7_COMMIT,
            'final_obj_sha256': NOODLES_FINAL_OBJ_SHA256,
            'vertex_count': len(v), 'face_count': len(f),
            'coordinate_frame': 'normalized_xyz=(x_mm/25,y_mm/25,(z_mm+4)/25)',
            'ten_raw_moments': raw.tolist(), 'ten_raw_moments_max_abs_error': error,
            'mass_g_at_density_1200_kg_m3': float(raw[0]*25**3*0.0012),
            'native_cherchi_eval_performed_now': False,
            'can_substitute_frozen_F_D_teacher_input': False}


def describe_noodles(*, final_obj_path=None, frozen_request_path=None):
    source = {'commit_sha': NOODLES_V7_COMMIT,
       'historical_numeric_solver_source': 'OLD_B0A13E3_NOT_FRESHLY_RECOMPILED_A17FF49',
       'final_obj_sha256': NOODLES_FINAL_OBJ_SHA256,
       'final_obj_git_blob_sha1': NOODLES_FINAL_OBJ_GIT_BLOB,
       'frozen_status_git_blob_sha1': NOODLES_STATUS_GIT_BLOB,
       'historical_solver_git_blob_sha1': NOODLES_SOLVER_GIT_BLOB,
       'historical_request_summary_git_blob_sha1': NOODLES_REQUEST_GIT_BLOB,
       'frozen_F_D_A_binary64_partition_proved': False}
    result = {'schema': 'w2-m15-noodles-real-asset-preflight-v1',
              'source': source, 'new_native_calls': 0, 'training_admitted': False,
              'source_model_scope': 'PHOTO_GUIDED_RECONSTRUCTION_NOT_AUTHOR_CAD'}
    if final_obj_path is not None:
        result['terminal_obj_audit'] = audit_exported_noodles_obj(final_obj_path)
    else:
        result['terminal_obj_audit'] = None
    # A summary of an old solver request lacks native outer/design vertices and
    # F material. A full new request must be explicitly supplied and validated.
    if frozen_request_path is None:
        result.update(status='BLOCKED_FROZEN_NOODLES_NATIVE_F_D_INPUT_ABSENT',
                      native_teacher_preflight_passed=False,
                      missing=['FULL_NATIVE_OUTER_AND_DESIGN_VERTICES_AND_FACES',
                               'FROZEN_FIXED_MATERIAL_IN_TARGET_FRAME',
                               'FROZEN_SOURCE_MESHES_WITH_MATCHING_SHA'])
    else:
        row = json.loads(Path(frozen_request_path).read_text())
        req = row.get('request', {})
        require(all(k in req for k in ('outer_vertices', 'outer_faces', 'design_vertices',
                 'design_faces', 'fixed_shell_moments')), 'NOODLES_NOT_A_FULL_FROZEN_REQUEST')
        # Requested inputs are not authenticated merely by existing as JSON.
        result.update(status='NOODLES_REQUEST_PRESENT_BUT_NOT_INDEPENDENTLY_CERTIFIED',
                      native_teacher_preflight_passed=False,
                      missing=['INDEPENDENT_SOURCE_F_D_A_SHA_BINDING_NOT_VERIFIED'])
    return result


def run_campaign(archive, output_dir, *, native_module=None, execute_native=False,
                 noodles_final_obj=None, noodles_full_request=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result_file = output_dir/'M15_CAMPAIGN_RESULT.json'
    require(not result_file.exists(), 'REFUSE_OVERWRITE_CAMPAIGN_RESULT')
    heart = verify_frozen_heart(archive)
    prep = heart.pop('_prepared_request')
    request = prep['request']
    normalized = create_normalized_obj(request, output_dir/'M15_HEART_NORMALIZED_VIEW.obj',
                                       heart['source']['mesh_file_sha256']['initial_top.obj'])
    heart['normalized_model_view'] = normalized
    heart['status'] = 'FROZEN_HEART_INPUT_READY_NATIVE_BLOCKED'
    noodles = describe_noodles(final_obj_path=noodles_final_obj,
                               frozen_request_path=noodles_full_request)
    module_sha = file_sha256(native_module) if native_module is not None and Path(native_module).is_file() else None
    heart['native_module_sha256'] = module_sha
    heart['native_attempt_requested'] = bool(execute_native)
    heart['effective_cgroup_memory_bytes'] = read_cgroup_memory()
    if execute_native:
        if module_sha is None:
            heart['status'] = 'BLOCKED_COMPILED_NATIVE_MODULE_FILE_ABSENT'
            heart['native_preflight_reason'] = 'COMPILED_NATIVE_MODULE_FILE_ABSENT'
        else:
            try:
                resources = require_native_resources()
                # The native binary identity is pinned, not invented or cached.
                spec = {'schema':'w2-one-cherchi-request-v3',
                        'source_sha':HEART_ORIGINAL_SHA,
                        'model_path':str(Path(normalized['path']).resolve()),
                        'expected_model_sha256':normalized['sha256'],
                        'expected_native_module_sha256':module_sha,
                        'request': request, 'evaluator_settings':prep['evaluator_settings'],
                        'native_c':heart['frozen_initial_native_c'],
                        'expected_native_c_sha256':heart['frozen_initial_native_c_sha256'],
                        'model_geometry_binding':{'mode':'OBJ_IS_INPUT_NORMALIZED_OUTER_V1'},
                        'reference_absolute_tolerances':[HEART_PARTITION_PREDECLARED_TOLERANCE]*10,
                        'geometry':{'frozen_original_obj_sha256':heart['source']['mesh_file_sha256']['initial_top.obj'],
                                    'frozen_design_obj_sha256':heart['source']['mesh_file_sha256']['design_domain.obj'],
                                    'frozen_fixed_obj_sha256':heart['source']['mesh_file_sha256']['fixed_shell.obj'],
                                    'frozen_request_sha256':HEART_REQUEST_SHA256,
                                    'normalized_view_sha256':normalized['sha256'],
                                    'model_scope':'H8_RECONSTRUCTED_NOT_AUTHOR_CAD'},
                        'frame':{'kind':'INPUT_NORMALIZED_TARGET_V1',
                                 'target_origin':request['target_origin'],
                                 'target_axes':request['target_axes']},
                        'derivative_contract':None}
                spec_path = output_dir/'M15_HEART_FROZEN_NATIVE_SPEC.json'
                with spec_path.open('x', encoding='utf8') as stream:
                    json.dump(spec, stream, sort_keys=True, allow_nan=False)
                env = dict(os.environ)
                # Explicit command remains serial, <=60 min; RLIMIT_AS=24GiB.
                script = Path(__file__).with_name('run_native_smoke.py')
                cmd = [sys.executable, str(script), '--spec', str(spec_path),
                       '--output', str(output_dir/'M15_HEART_NATIVE_TEACHER.json')]
                def cap():
                    resource.setrlimit(resource.RLIMIT_AS, (MIN_NATIVE_MEMORY, MIN_NATIVE_MEMORY))
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE, text=True, env=env,
                  start_new_session=True, preexec_fn=cap)
                try:
                    out, err = process.communicate(timeout=3590)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    raise
                finally:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                heart['native_runner_exit_code'] = process.returncode
                heart['native_runner_stdout'] = out[-1500:]
                heart['native_runner_stderr'] = err[-1500:]
                heart['native_preflight_resource'] = resources
                if process.returncode == 0:
                    from native_cherchi_teacher import load
                    frozen = load(output_dir/'M15_HEART_NATIVE_TEACHER.json',
                      expected_q=spec['native_c'],
                      expected_model_sha256=spec['expected_model_sha256'],
                      expected_native_module_sha256=spec['expected_native_module_sha256'])
                    proof = frozen['exact_proof']
                    require(proof['native_cherchi'] is True and
                      proof['independent_ten_moment_audit']['comparison']['within_tolerance'] is True
                      and proof['same_call_attachment'] is not None and
                      frozen['J_D'] is None and frozen['split'] == 'excluded',
                      'NATIVE_LABEL_NOT_EXACTLY_CERTIFIED')
                    heart['status'] = 'ONE_ACTUAL_NATIVE_HEART_MATERIAL_RECORDED_JACOBIAN_EXCLUDED'
                    heart['one_new_native_verified'] = True
                    heart['native_label_sha256'] = file_sha256(output_dir/'M15_HEART_NATIVE_TEACHER.json')
                    heart['native_stage_seconds'] = frozen['stage_seconds']
                    heart['native_peak_rss_process_lifetime_bytes'] = frozen['peak_rss_bytes']
                else:
                    heart['status'] = 'NATIVE_RUN_FAILED_EVIDENCE_RETAINED'
                    heart['one_new_native_verified'] = False
            except ValueError as exc:
                heart['native_preflight_reason'] = str(exc)
                heart['status'] = 'BLOCKED_NATIVE_RESOURCE_OR_IDENTITY_PREFLIGHT'
            except subprocess.TimeoutExpired:
                heart['native_preflight_reason'] = 'NATIVE_ONE_CALL_TIME_LIMIT_EXCEEDED_3590S'
                heart['status'] = 'NATIVE_TIMEOUT_EVIDENCE_RETAINED'
    else:
        heart['native_preflight_reason'] = 'NATIVE_EXECUTION_NOT_REQUESTED'
    verified_native = int(heart.get('one_new_native_verified') is True)
    report = {'schema':'w2-m15-serial-dual-teacher-campaign-v1',
              'heart':heart,'noodles':noodles,'new_native_calls_verified':verified_native,
              'new_verified_J_D':0,'training_admitted':0,
              'historical_H8f_workflow_failure_preserved':True,
              'newton_not_required_for_teacher_preflight':True}
    with result_file.open('x',encoding='utf8') as stream:
        json.dump(report, stream, sort_keys=True, allow_nan=False, indent=2)
        stream.write('\n')
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--heart-archive', required=True)
    ap.add_argument('--output-dir', required=True)
    ap.add_argument('--native-module')
    ap.add_argument('--execute-native', action='store_true')
    ap.add_argument('--noodles-final-obj')
    ap.add_argument('--noodles-full-request')
    a = ap.parse_args(argv)
    report = run_campaign(a.heart_archive, a.output_dir,
                          native_module=a.native_module, execute_native=a.execute_native,
                          noodles_final_obj=a.noodles_final_obj,
                          noodles_full_request=a.noodles_full_request)
    print(canonical({'heart_status':report['heart']['status'],
                     'noodles_status':report['noodles']['status'],
                     'new_native_verified':report['new_native_calls_verified'],
                     'training_admitted':0}))
    # A requested native evaluation that could not run must never exit success.
    return 0 if (not a.execute_native or report['new_native_calls_verified']==1) else 2


if __name__ == '__main__':
    sys.exit(main())
