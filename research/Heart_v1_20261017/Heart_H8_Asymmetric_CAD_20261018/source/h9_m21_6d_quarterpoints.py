"""W3 M21.6D-P1: one real Cherchi quarter-point + source-motion probe per run.

Each --phase run --index N executes exactly one fresh Cherchi Boolean same-call
material, one native source-motion replay, exact boundary/moment checks, H7
branch identity checks, and an independent second-process audit. Runs are
serialized; each is capped below one hour and 24 GiB address space. Newton is
never dispatched and finite samples never certify a continuous neighborhood.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from types import SimpleNamespace

from h9_stage19_multiscale import file_hash, read_json
from h9_m21_6d_quarterpoint_plan import (
    M21_6C_SHA, SCHEMA as PLAN_SCHEMA, STATUS as PLAN_STATUS,
    build_plan, make_quarterpoint_plan,
)
from h9_m21_layered_replay import (
    BINARY_SHA, LEDGER_SHA, bind_file, frozen_request, load_ledger, load_six,
    source_pair, source_snapshot,
)
from h9_m21_3_lpi import read_motion, source_rows
from h9_m21_6b_moment_layers import BOUNDARY_SHA, LPI_SHA, strict_json
from h9_m21_motion_math import (
    compare_vectors, material_state, moment_tangent, motion_pair,
)
from h9_same_call_capture import _sync_directory, same_binary64_coefficients
from h9_stage19_multiscale import M19Rejected
from probe_h9_crossing_sides_live import BACKEND_PREFIX, EXACT_AUDIT_REQUIRED, load_native_or_reject
from audit_h9_new_native_sides import h7_observe, validate_native_packet_provenance
from audit_h9_branch_decision import load_point
from certify_h9_interior_edge_crossing import DESIGN_IDS, SOURCE_IDS, exact_line_witness, qvec

MAX_SECONDS = 3600
MAX_AS_BYTES = 24 * 1024**3
WORKER_SECONDS = 3200
AUDIT_SECONDS = 330
SAME = 'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
EXPECTED_CAPTURE_PREFIX = 'quarterpoint-'


class QuarterpointRejected(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise QuarterpointRejected(reason)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def token(value):
    return f'{value.numerator}/{value.denominator}'


def strict_json(path, expected_sha=None):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size < 128 * 1024**2,
         'MISSING_OR_UNSAFE_JSON:' + str(path))

    if expected_sha is not None:
        need(file_hash(path) == expected_sha, 'JSON_SHA_MISMATCH:' + path.name)

    def unique(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, 'DUPLICATE_JSON_KEY:' + key)
            out[key] = value
        return out

    def reject_constant(value):
        raise QuarterpointRejected('NONFINITE_JSON_CONSTANT:' + str(value))

    return json.loads(path.read_bytes(), object_pairs_hook=unique, parse_constant=reject_constant)


def capture_stem(point):
    need(type(point.get('index')) is int and 0 <= point['index'] < 4,
         'QUARTERPOINT_INDEX_INVALID')
    interval = point.get('interval')
    need(interval in (
        'left-coarse-to-mid', 'left-mid-to-near',
        'right-near-to-mid', 'right-mid-to-coarse',
    ), 'QUARTERPOINT_INTERVAL_INVALID')
    return f"q{point['index']:02d}-{interval}"


def validate_point_contract(plan, index):
    need(plan.get('schema') == PLAN_SCHEMA and plan.get('status') == PLAN_STATUS,
         'QUARTERPOINT_PLAN_NOT_QUALIFIED')
    points = plan.get('points')
    need(type(points) is list and len(points) == 4, 'FOUR_QUARTERPOINTS_REQUIRED')
    need(type(index) is int and 0 <= index < 4, 'QUARTERPOINT_INDEX_OUT_OF_RANGE')
    point = points[index]

    specs = (
        ('left', 'left-coarse-to-mid', 'side-00-left-coarse',
         'm19-mid-00-left-mid', 0.25, 1, 'H8F_SAMPLE_059'),
        ('left', 'left-mid-to-near', 'm19-mid-00-left-mid',
         'side-01-left-near', 0.75, 1, 'H8F_SAMPLE_059'),
        ('right', 'right-near-to-mid', 'side-02-right-near',
         'm19-mid-01-right-mid', 0.25, -1, 'H8F_SAMPLE_060'),
        ('right', 'right-mid-to-coarse', 'm19-mid-01-right-mid',
         'side-03-right-coarse', 0.75, -1, 'H8F_SAMPLE_060'),
    )
    side, interval, from_stem, to_stem, fraction, sign, anchor = specs[index]
    need(point.get('index') == index and point.get('side') == side
         and point.get('interval') == interval
         and point.get('from_stem') == from_stem and point.get('to_stem') == to_stem
         and point.get('fraction_of_original_full_interval') == fraction
         and point.get('expected_proxy_event_sign') == sign
         and point.get('expected_same_side_anchor') == anchor,
         'QUARTERPOINT_PLAN_ROW_IDENTITY_CHANGED')

    q = point.get('q')
    need(type(q) is list and len(q) == 10
         and all(type(x) in (int, float) and math.isfinite(float(x)) for x in q),
         'QUARTERPOINT_Q_INVALID')
    need(type(point.get('c7')) in (int, float) and math.isfinite(point['c7'])
         and float(q[7]) == float(point['c7']),
         'QUARTERPOINT_C7_Q_MISMATCH')
    need(point.get('native_boolean_call_required') is True
         and point.get('same_side_finite_probe_only') is True,
         'QUARTERPOINT_EXECUTION_SCOPE_CHANGED')
    need(plan.get('newton_admitted') is False
         and plan.get('continuous_neighborhood_certified') is False,
         'QUARTERPOINT_PLAN_UNSAFE_ADMISSION_FLAG')
    return point


def branch_status_is_valid(side, left_status, right_status):
    if side == 'left':
        return left_status == SAME and right_status != SAME
    if side == 'right':
        return right_status == SAME and left_status != SAME
    return False


def source_signature_matches(new_signature, from_signature, to_signature):
    return new_signature == from_signature == to_signature


def _exclusive_file(folder, name, payload):
    """Publish a new file atomically without following or overwriting a path."""
    folder = Path(folder)
    destination = folder / name
    need(not os.path.lexists(destination), 'DESTINATION_EXISTS_DO_NOT_OVERWRITE:' + name)
    temporary = None
    try:
        import tempfile as _tempfile
        with _tempfile.NamedTemporaryFile(mode='wb', dir=folder, prefix='.qpt-',
                                          suffix='.partial', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
        _sync_directory(folder)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def _gzip_bytes(payload):
    import io
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0, compresslevel=5) as zipped:
        zipped.write(payload)
    return stream.getvalue()


def _verify_plan(args):
    supplied = strict_json(args.plan)
    with tempfile.TemporaryDirectory(prefix='h9-m21-6d-plan-recheck-') as temporary:
        expected_args = SimpleNamespace(
            precision_ledger=args.precision_ledger,
            artifact=args.artifact,
            stage17_native_dir=args.stage17_native_dir,
            m19_run=args.m19_run,
            source_run=args.source_run,
            boundary_report=args.boundary_report,
            moment_layers=args.moment_layers,
            certificate=args.certificate,
            stage18_audit=args.stage18_audit,
            output=Path(temporary) / 'recomputed-plan.json',
        )
        expected = build_plan(expected_args)
    need(supplied == expected, 'QUARTERPOINT_PLAN_OR_ANY_FROZEN_INPUT_CHANGED')
    need(supplied.get('new_boolean_calls_executed') == 0
         and supplied.get('new_native_source_calls_executed') == 0,
         'PLANNER_MUST_NOT_HAVE_EXECUTED_NATIVE_CALLS')
    return supplied


def _load_context(args):
    plan = _verify_plan(args)
    ledger = load_ledger(args.precision_ledger)
    loaded, m19_plan, _ = load_six(args, ledger)
    request_doc = frozen_request(args.artifact)
    request = request_doc['request']

    core_sha = m19_plan['stage17_current_binary_sha256']['core']
    need(core_sha == BINARY_SHA, 'FROZEN_CORE_BINARY_CHANGED')

    source_root = Path(args.source_run)
    summary_path = source_root / 'layered-report.json'
    summary = strict_json(summary_path, file_hash(summary_path))
    worker = source_root / 'worker'
    worker_report_path = worker / 'layered-report.json'
    worker_report = strict_json(worker_report_path, summary['worker_report_sha256'])
    rows = source_rows(worker_report, core_sha)

    materials = {}
    states = {}
    velocities = {}
    signatures = {}
    observations = {}

    for (material, metadata, evidence), row in zip(loaded, rows):
        stem = evidence['stem']
        need(row['stem'] == stem, 'SOURCE_MOTION_ROW_ORDER_CHANGED:' + stem)
        velocity = read_motion(worker, row, evidence, core_sha)
        attachment_path = worker / (stem + '.source-motion.json')
        attachment = strict_json(attachment_path, row['source_motion_attachment_sha256'])
        state = material_state(material, request, velocity)
        need(state['motion'] is not None and len(state['positions']) == 8455
             and len(state['source']) == 162
             and state['kinds'] == {'EXPLICIT3D': 7671, 'LPI': 784},
             'EXISTING_SIX_SAMPLE_STATE_INVALID:' + stem)
        materials[stem] = material
        states[stem] = state
        velocities[stem] = velocity
        signatures[stem] = attachment['discrete_source_signature']
        observations[stem] = h7_observe(material, request)

    with zipfile.ZipFile(args.artifact) as archive:
        _, historical_left, left_obs = load_point(archive, 59, request)
        _, historical_right, right_obs = load_point(archive, 60, request)
        old_report = json.loads(archive.read('artifacts/h8f-all81-points/report.json'))

    need(tuple(materials) == (
        'side-00-left-coarse', 'side-01-left-near', 'side-02-right-near',
        'side-03-right-coarse', 'm19-mid-00-left-mid', 'm19-mid-01-right-mid',
    ), 'EXISTING_SIX_MATERIAL_ORDER_CHANGED')

    return {
        'plan': plan,
        'ledger': ledger,
        'loaded': loaded,
        'm19_plan': m19_plan,
        'request_doc': request_doc,
        'request': request,
        'old_report': old_report,
        'materials': materials,
        'states': states,
        'velocities': velocities,
        'signatures': signatures,
        'observations': observations,
        'historical_left': historical_left,
        'historical_right': historical_right,
        'left_obs': left_obs,
        'right_obs': right_obs,
        'source_summary_sha256': file_hash(summary_path),
        'source_worker_report_sha256': summary['worker_report_sha256'],
        'core_sha': core_sha,
    }


def _observe_new(material, request, observe_packet):
    proof = material['material_proof']
    need(proof.get('schema') == 'cherchi-same-call-material-v1',
         'NEW_MATERIAL_PROOF_MISSING')
    packet = {
        'backend': 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
        'exact_vertices': proof['exact_vertices'],
        'faces': material['variable_faces'],
        'construction_records': proof['construction_records'],
    }
    return observe_packet(
        packet, request['design_vertices'], request['design_faces'],
        material['quadric_source_vertices'], material['quadric_source_faces'],
    )


def _capture_unverified(folder, point, q, material, backend_identity, plan_sha):
    stem = capture_stem(point)
    need(same_binary64_coefficients(q, material.get('quadric_coefficients')),
         'QPT_SAME_CALL_Q_MISMATCH')
    need(type(backend_identity) is str and backend_identity.startswith(BACKEND_PREFIX)
         and material.get('boolean_backend_identity') == backend_identity
         and material.get('material_proof', {}).get('schema') == 'cherchi-same-call-material-v1',
         'QPT_SAME_CALL_BACKEND_OR_PROOF_MISMATCH')

    payload = json.dumps(material, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf8')
    packed = _gzip_bytes(payload)
    raw_name = 'unverified-' + stem + '.json.gz'
    manifest_name = 'unverified-' + stem + '.json'
    raw_path = _exclusive_file(folder, raw_name, packed)
    proof = {
        'schema': 'heart-h9-m21-6d-quarterpoint-unverified-v1',
        'index': point['index'],
        'interval': point['interval'],
        'c7': point['c7'],
        'q': q,
        'plan_sha256': plan_sha,
        'archive_sha256': file_hash(raw_path),
        'material_json_sha256': sha_bytes(payload),
        'status': 'UNVERIFIED_REAL_SAME_CALL_PACKET_PRESERVED',
        'newton_admitted': False,
        'continuous_neighborhood_certified': False,
    }
    manifest_path = _exclusive_file(
        folder, manifest_name,
        (json.dumps(proof, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8'),
    )
    proof['manifest_sha256'] = file_hash(manifest_path)
    return proof, raw_path


def _promote_verified(folder, point, capture, metadata):
    stem = capture_stem(point)
    raw_path = Path(folder) / ('unverified-' + stem + '.json.gz')
    final_path = Path(folder) / ('quarterpoint-' + stem + '.json.gz')
    need(file_hash(raw_path) == capture['archive_sha256'], 'QPT_CAPTURE_SHA_CHANGED')
    need(not os.path.lexists(final_path), 'QPT_FINAL_ARCHIVE_EXISTS')
    os.link(raw_path, final_path)
    _sync_directory(folder)
    metadata = dict(metadata)
    metadata['material_sha256'] = file_hash(final_path)
    metadata_path = _exclusive_file(
        folder, 'quarterpoint-' + stem + '.json',
        (json.dumps(metadata, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8'),
    )
    return final_path, metadata_path


def _load_native():
    return load_native_or_reject()


def _binary_manifest(native, boolean, arithmetic):
    return {
        'core': sha_bytes(Path(native.__file__).read_bytes()),
        'boolean': sha_bytes(Path(boolean.__file__).read_bytes()),
        'arithmetic': sha_bytes(Path(arithmetic.__file__).read_bytes()),
    }


def _make_settings(args, request_from_frozen):
    temporary = tempfile.TemporaryDirectory(prefix='h9-m21-6d-request-')
    try:
        with zipfile.ZipFile(args.artifact) as archive:
            raw = archive.read('artifacts/h8-request/prepared-request.json')
        path = Path(temporary.name) / 'prepared-request.json'
        path.write_bytes(raw)
        prepared_request, settings, _ = request_from_frozen(path)
        return prepared_request, settings, temporary
    except Exception:
        temporary.cleanup()
        raise


def work_one(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    report = {
        'schema': 'heart-h9-m21-6d-quarterpoint-worker-v1',
        'status': 'INCOMPLETE_NO_NEWTON',
        'index': args.index,
        'new_boolean_calls_attempted': 0,
        'new_boolean_calls_completed': 0,
        'new_native_source_calls_attempted': 0,
        'new_native_source_calls_completed': 0,
        'newton_admitted': False,
        'continuous_neighborhood_certified': False,
        'final_heart_obj_produced': False,
    }
    stage = 'REVERIFY_PLAN_AND_SIX_FROZEN_INPUTS'
    request_temporary = None
    try:
        context = _load_context(args)
        plan = context['plan']
        point = validate_point_contract(plan, args.index)
        plan_sha = file_hash(args.plan)

        from prepare_h9_pinned_native import check_runtime, source_contract
        machine = check_runtime(Path(args.repo).resolve())
        need(machine['ready'], 'QPT_NATIVE_HOST_PREFLIGHT_BLOCKED:' + repr(machine['blocked_reasons']))
        contract = source_contract(Path(args.repo).resolve())
        resource.setrlimit(resource.RLIMIT_AS, (MAX_AS_BYTES, MAX_AS_BYTES))

        stage = 'IMPORT_PINNED_CHERCHI_AND_CORE'
        (np, native, boolean, arithmetic, Engine, request_from_frozen,
         independent_ten_raw_moments, load_point_fn, compare_observations,
         observe_packet) = _load_native()
        binary = _binary_manifest(native, boolean, arithmetic)
        need(binary == plan['native_binary_sha256'], 'QPT_NATIVE_BINARY_SHA_DRIFT')
        need(Path(native.__file__).resolve().parent ==
             (Path(args.repo).resolve() / 'build/h9-w3-core/python').resolve(),
             'QPT_NATIVE_CORE_MODULE_FROM_WRONG_BUILD')

        prepared_request, settings, request_temporary = _make_settings(args, request_from_frozen)
        engine = Engine(
            prepared_request, settings,
            normalization={'origin': [0., 0., 0.], 'L': 1.},
            rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
            fixed_boundary_reuse=False,
            integral_profile='EXACT_GMP_V1',
            branch_identity_policy='SOURCE_FEATURE_BRANCH_V2',
        )
        need(engine.backend_identity == BACKEND_PREFIX + binary['boolean'],
             'QPT_CHERCHI_BACKEND_IDENTITY_CHANGED')

        q = np.asarray(point['q'], dtype=np.float64)
        base_q = np.asarray(context['old_report']['target_q'], dtype=np.float64)
        need(q.shape == base_q.shape == (10,) and np.isfinite(q).all()
             and same_binary64_coefficients(point['q'], q.tolist()),
             'QPT_COEFFICIENT_VECTOR_INVALID')
        need(all(float(q[k]) == float(base_q[k]) for k in range(10) if k != 7),
             'QPT_NON_C7_COEFFICIENT_CHANGED')
        need(float(q[7]) == float(point['c7']), 'QPT_C7_VALUE_CHANGED')

        stage = 'REAL_CHERCHI_BOOLEAN_CALL'
        report['new_boolean_calls_attempted'] = 1
        value = engine(q)
        material = engine.material(q)
        engine.validate_same_call_material(material, q, prepared_request)
        need(value.get('boolean_backend_identity') == engine.backend_identity,
             'QPT_VALUE_ENGINE_BACKEND_IDENTITY_MISMATCH')
        report['new_boolean_calls_completed'] = 1

        stage = 'PRESERVE_UNVERIFIED_SAME_CALL_MATERIAL'
        capture, raw_path = _capture_unverified(
            output, point, q.tolist(), material, value['boolean_backend_identity'], plan_sha,
        )

        stage = 'PINNED_NATIVE_PROVENANCE_AND_EVALUATION_MAP'
        need(material.get('evaluation_map_identity') == plan['evaluation_map_identity'],
             'QPT_EVALUATION_MAP_IDENTITY_CHANGED')
        endpoint_material = context['materials'][point['from_stem']]
        validate_native_packet_provenance(
            material, endpoint_material, binary['arithmetic'],
            boolean_sha=binary['boolean'],
            expected_map_identity=plan['evaluation_map_identity'],
        )

        stage = 'STRICT_EXACT_NATIVE_BOUNDARY'
        coordinates = material['variable_rational_vertices']
        faces = np.asarray(material['variable_faces'], dtype=np.int32)
        facts = dict(native.audit_exact_rational_triangle_boundary(coordinates, faces, 'AnyNonzero'))
        need(all(facts.get(key) is True for key in EXACT_AUDIT_REQUIRED)
             and not facts.get('intersecting_pairs')
             and not facts.get('degenerate_faces')
             and not facts.get('intersection_error'),
             'QPT_STRICT_EXACT_BOUNDARY_FAILED')

        stage = 'INDEPENDENT_EXACT_TEN_MOMENTS'
        exact_moments = independent_ten_raw_moments(coordinates, faces.tolist())
        independent_float = np.asarray([float(x) for x in exact_moments], dtype=np.float64)
        reported_moments = np.asarray(value['variable_raw_moments'], dtype=np.float64)
        jacobian = np.asarray(value['moment_jacobian'], dtype=np.float64)
        material_jacobian = np.asarray(material.get('moment_jacobian'), dtype=np.float64)
        need(independent_float.shape == reported_moments.shape == (10,)
             and jacobian.shape == material_jacobian.shape == (10, 10)
             and np.array_equal(jacobian, material_jacobian)
             and np.isfinite(independent_float).all()
             and np.isfinite(reported_moments).all()
             and np.isfinite(jacobian).all(),
             'QPT_MOMENT_OR_JACOBIAN_SHAPE_INVALID')
        moment_error = float(np.max(
            np.abs(independent_float - reported_moments) /
            np.maximum(1., np.abs(reported_moments))
        ))
        need(moment_error <= 1e-10, 'QPT_INDEPENDENT_TEN_MOMENT_DISAGREEMENT')

        stage = 'EXACT_H7_BRANCH_AND_ORIENTED_EVENT'
        observation = _observe_new(material, context['request'], observe_packet)
        left_status = compare_observations(context['left_obs'], observation)
        right_status = compare_observations(context['right_obs'], observation)
        from_status = compare_observations(
            context['observations'][point['from_stem']], observation)
        to_status = compare_observations(
            context['observations'][point['to_stem']], observation)
        need(branch_status_is_valid(point['side'], left_status['status'], right_status['status']),
             'QPT_WRONG_H8F_CONSTRUCTION_SIDE')
        need(from_status['status'] == SAME and to_status['status'] == SAME,
             'QPT_INTERVAL_ENDPOINT_SEMANTIC_IDENTITY_CHANGED')

        design = [qvec(context['request']['design_vertices'][i]) for i in DESIGN_IDS]
        source = [qvec(material['quadric_source_vertices'][i]) for i in SOURCE_IDS]
        witness = exact_line_witness(*source, *design)
        need(0 < witness['source_segment_parameter'] < 1
             and 0 < witness['design_segment_parameter'] < 1,
             'QPT_EXACT_EDGE_INTERSECTION_NOT_INTERIOR')
        event_sign = (witness['determinant'] > 0) - (witness['determinant'] < 0)
        need(event_sign == point['expected_proxy_event_sign'],
             'QPT_REAL_ORIENTED_EVENT_SIGN_DISAGREES')

        stage = 'REAL_NATIVE_SOURCE_MOTION_REPLAY'
        report['new_native_source_calls_attempted'] = 1
        velocity, signature = source_snapshot(
            native, np, settings, context['request'], material)
        report['new_native_source_calls_completed'] = 1
        need(source_signature_matches(
            signature,
            context['signatures'][point['from_stem']],
            context['signatures'][point['to_stem']],
        ), 'QPT_SOURCE_DISCRETE_SIGNATURE_CHANGED')

        stage = 'EXACT_RETAINED_CONSTRAINT_AND_J7_CHAIN_REPLAY'
        state = material_state(material, context['request'], velocity)
        need(len(state['positions']) == 8455 and len(state['source']) == 162
             and state['kinds'] == {'EXPLICIT3D': 7671, 'LPI': 784},
             'QPT_RETAINED_CONSTRUCTION_COUNTS_CHANGED')
        independent_j7, active_faces = moment_tangent(
            state, context['request']['material_density'])
        native_j7 = [row[7] for row in value['moment_jacobian']]
        chain_comparison = compare_vectors(independent_j7, native_j7)
        need(chain_comparison['max_scaled_difference'] <= 1e-10,
             'QPT_INDEPENDENT_SOURCE_CHAIN_J7_DISAGREEMENT')

        from_stem, to_stem = point['from_stem'], point['to_stem']
        pair_from = motion_pair(context['states'][from_stem], state)
        pair_to = motion_pair(state, context['states'][to_stem])
        need(pair_from.get('same_retained_constraints_and_oriented_triangles') is True
             and pair_to.get('same_retained_constraints_and_oriented_triangles') is True,
             'QPT_RETAINED_BOUNDARY_SEMANTICS_CHANGED')
        source_pair_from = source_pair(
            context['states'][from_stem], state,
            context['velocities'][from_stem], velocity)
        source_pair_to = source_pair(
            state, context['states'][to_stem],
            velocity, context['velocities'][to_stem])

        stage = 'PUBLISH_SOURCE_MOTION_AND_VERIFIED_PACKET'
        attachment = {
            'schema': 'heart-h9-m21-source-only-motion-v1',
            'material_sha256': capture['archive_sha256'],
            'native_core_sha256': binary['core'],
            'physical_source_velocity_column7': velocity,
            'discrete_source_signature': signature,
            'boolean_calls': 0,
            'newton_admitted': False,
        }
        attachment_path = _exclusive_file(
            output, 'quarterpoint-' + capture_stem(point) + '.source-motion.json',
            (json.dumps(attachment, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8'),
        )
        metadata = {
            'schema': 'heart-h9-m21-6d-quarterpoint-native-material-v1',
            'status': 'ONE_REAL_QUARTERPOINT_PRODUCED_PENDING_INDEPENDENT_AUDIT',
            'index': point['index'],
            'side': point['side'],
            'interval': point['interval'],
            'from_stem': from_stem,
            'to_stem': to_stem,
            'c7': point['c7'],
            'q': point['q'],
            'plan_sha256': plan_sha,
            'capture_archive_sha256': capture['archive_sha256'],
            'capture_manifest_sha256': capture['manifest_sha256'],
            'native_binary_sha256': binary,
            'evaluation_map_identity': material['evaluation_map_identity'],
            'native_event_sign': event_sign,
            'source_segment_parameter': float(witness['source_segment_parameter']),
            'design_segment_parameter': float(witness['design_segment_parameter']),
            'native_geometry_valid': True,
            'vertex_count': len(coordinates),
            'face_count': len(faces),
            'source_vertex_count': len(material['quadric_source_vertices']),
            'exact_ten_moments': [token(x) for x in exact_moments],
            'independent_scaled_moment_error': moment_error,
            'native_moment_jacobian_column7': [float(x) for x in native_j7],
            'independent_exact_chain_j7': [token(x) for x in independent_j7],
            'independent_chain_vs_native_j7_max_scaled': chain_comparison['max_scaled_difference'],
            'active_tangent_faces': active_faces,
            'source_motion_attachment': attachment_path.name,
            'source_motion_attachment_sha256': file_hash(attachment_path),
            'source_geometry_bitwise_matched': True,
            'source_discrete_signature_matches_both_interval_endpoints': True,
            'h7_match_left_anchor': left_status,
            'h7_match_right_anchor': right_status,
            'h7_match_from_endpoint': from_status,
            'h7_match_to_endpoint': to_status,
            'motion_pair_from_endpoint': pair_from,
            'motion_pair_to_endpoint': pair_to,
            'source_pair_from_endpoint': source_pair_from,
            'source_pair_to_endpoint': source_pair_to,
            'new_boolean_calls_this_run': 1,
            'new_native_source_calls_this_run': 1,
            'root_cause_determined': False,
            'continuous_neighborhood_certified': False,
            'asymptotic_order_certified': False,
            'newton_admitted': False,
            'final_heart_obj_produced': False,
            'native_runtime_origin_cryptographically_attested': False,
        }
        final_path, metadata_path = _promote_verified(output, point, capture, metadata)
        report.update(
            status='ONE_REAL_QUARTERPOINT_PRODUCED_PENDING_INDEPENDENT_AUDIT',
            finished_indices=[point['index']],
            point_stem=capture_stem(point),
            capture_archive_sha256=capture['archive_sha256'],
            final_archive_sha256=file_hash(final_path),
            metadata_sha256=file_hash(metadata_path),
            source_motion_attachment_sha256=file_hash(attachment_path),
            newton_admitted=False,
        )
        _exclusive_file(
            output, 'worker-report.json',
            (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8'),
        )
        print('M21_6D_REAL_QUARTERPOINT', point['index'], point['interval'], event_sign, flush=True)
        print('M21_6D_BOOLEAN_CALLS', 1, flush=True)
        print('M21_6D_SOURCE_MOTION_CALLS', 1, flush=True)
        print('M21_6D_NEWTON', False, flush=True)
        return report
    except Exception as error:
        report.update(
            status='FAILED_CLOSED_NO_NEWTON',
            failed_stage=stage,
            error=f'{type(error).__name__}: {error}',
            traceback=traceback.format_exc(),
            newton_admitted=False,
        )
        _exclusive_file(
            output, 'failure.json',
            (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf8'),
        )
        raise
    finally:
        if request_temporary is not None:
            request_temporary.cleanup()


def audit_one(args):
    context = _load_context(args)
    plan = context['plan']
    point = validate_point_contract(plan, args.index)
    worker_dir = Path(args.worker_dir)
    worker_report_path = worker_dir / 'worker-report.json'
    worker_report = strict_json(worker_report_path, file_hash(worker_report_path))
    need(worker_report.get('status') == 'ONE_REAL_QUARTERPOINT_PRODUCED_PENDING_INDEPENDENT_AUDIT'
         and worker_report.get('finished_indices') == [args.index]
         and worker_report.get('new_boolean_calls_completed') == 1
         and worker_report.get('new_native_source_calls_completed') == 1
         and worker_report.get('newton_admitted') is False,
         'QPT_WORKER_REPORT_INCOMPLETE')

    stem = capture_stem(point)
    archive_path = worker_dir / ('quarterpoint-' + stem + '.json.gz')
    metadata_path = worker_dir / ('quarterpoint-' + stem + '.json')
    metadata = strict_json(metadata_path, worker_report['metadata_sha256'])
    need(file_hash(archive_path) == metadata.get('material_sha256')
         == metadata.get('capture_archive_sha256')
         == worker_report.get('final_archive_sha256'),
         'QPT_PROMOTED_MATERIAL_SHA_MISMATCH')
    raw_bytes = archive_path.read_bytes()
    material_bytes = gzip.decompress(raw_bytes)

    def unique(pairs):
        out = {}
        for key, value in pairs:
            need(key not in out, 'QPT_DUPLICATE_MATERIAL_JSON_KEY:' + key)
            out[key] = value
        return out

    material = json.loads(material_bytes, object_pairs_hook=unique)
    need(same_binary64_coefficients(point['q'], material.get('quadric_coefficients')),
         'QPT_AUDIT_Q_MISMATCH')
    need(metadata.get('plan_sha256') == file_hash(args.plan)
         and metadata.get('index') == args.index
         and metadata.get('interval') == point['interval']
         and metadata.get('newton_admitted') is False,
         'QPT_AUDIT_PLAN_OR_METADATA_MISMATCH')

    attachment_path = worker_dir / metadata['source_motion_attachment']
    attachment = strict_json(
        attachment_path, metadata['source_motion_attachment_sha256'])
    need(attachment.get('schema') == 'heart-h9-m21-source-only-motion-v1'
         and attachment.get('material_sha256') == metadata['material_sha256']
         and attachment.get('native_core_sha256') == metadata['native_binary_sha256']['core']
         and attachment.get('boolean_calls') == 0
         and attachment.get('newton_admitted') is False,
         'QPT_SOURCE_MOTION_ATTACHMENT_INVALID')

    (np, native, boolean, arithmetic, Engine, request_from_frozen,
     independent_ten_raw_moments, load_point_fn, compare_observations,
     observe_packet) = _load_native()
    binary = _binary_manifest(native, boolean, arithmetic)
    need(binary == metadata['native_binary_sha256'] == plan['native_binary_sha256'],
         'QPT_AUDIT_NATIVE_BINARY_CHANGED')

    endpoint_material = context['materials'][point['from_stem']]
    validate_native_packet_provenance(
        material, endpoint_material, binary['arithmetic'],
        boolean_sha=binary['boolean'],
        expected_map_identity=plan['evaluation_map_identity'],
    )
    need(material.get('evaluation_map_identity') == plan['evaluation_map_identity'],
         'QPT_AUDIT_EVALUATION_MAP_CHANGED')

    coordinates = material['variable_rational_vertices']
    faces = np.asarray(material['variable_faces'], dtype=np.int32)
    facts = dict(native.audit_exact_rational_triangle_boundary(coordinates, faces, 'AnyNonzero'))
    need(all(facts.get(key) is True for key in EXACT_AUDIT_REQUIRED)
         and not facts.get('intersecting_pairs')
         and not facts.get('degenerate_faces')
         and not facts.get('intersection_error'),
         'QPT_AUDIT_STRICT_BOUNDARY_FAILED')

    exact_moments = independent_ten_raw_moments(coordinates, faces.tolist())
    exact_tokens = [token(x) for x in exact_moments]
    need(exact_tokens == metadata.get('exact_ten_moments'),
         'QPT_AUDIT_EXACT_TEN_MOMENTS_CHANGED')
    reported = np.asarray(material['variable_raw_moments'], dtype=np.float64)
    independent_float = np.asarray([float(x) for x in exact_moments], dtype=np.float64)
    moment_error = float(np.max(
        np.abs(independent_float - reported) / np.maximum(1., np.abs(reported))))
    need(moment_error <= 1e-10
         and moment_error == metadata.get('independent_scaled_moment_error'),
         'QPT_AUDIT_MOMENT_REINTEGRATION_FAILED')

    observation = _observe_new(material, context['request'], observe_packet)
    left_status = compare_observations(context['left_obs'], observation)
    right_status = compare_observations(context['right_obs'], observation)
    from_status = compare_observations(
        context['observations'][point['from_stem']], observation)
    to_status = compare_observations(
        context['observations'][point['to_stem']], observation)
    need(branch_status_is_valid(point['side'], left_status['status'], right_status['status'])
         and from_status['status'] == SAME and to_status['status'] == SAME,
         'QPT_AUDIT_H7_BRANCH_IDENTITY_FAILED')

    design = [qvec(context['request']['design_vertices'][i]) for i in DESIGN_IDS]
    source = [qvec(material['quadric_source_vertices'][i]) for i in SOURCE_IDS]
    witness = exact_line_witness(*source, *design)
    sign = (witness['determinant'] > 0) - (witness['determinant'] < 0)
    need(0 < witness['source_segment_parameter'] < 1
         and 0 < witness['design_segment_parameter'] < 1
         and sign == point['expected_proxy_event_sign'] == metadata['native_event_sign'],
         'QPT_AUDIT_EXACT_EVENT_WITNESS_FAILED')

    velocity = attachment['physical_source_velocity_column7']
    need(source_signature_matches(
        attachment['discrete_source_signature'],
        context['signatures'][point['from_stem']],
        context['signatures'][point['to_stem']],
    ), 'QPT_AUDIT_SOURCE_SIGNATURE_MISMATCH')
    state = material_state(material, context['request'], velocity)
    independent_j7, active_faces = moment_tangent(
        state, context['request']['material_density'])
    need([token(x) for x in independent_j7] == metadata['independent_exact_chain_j7'],
         'QPT_AUDIT_EXACT_CHAIN_J7_CHANGED')
    native_jacobian = material.get('moment_jacobian')
    need(type(native_jacobian) is list and len(native_jacobian) == 10
         and all(type(row) is list and len(row) == 10 for row in native_jacobian),
         'QPT_AUDIT_NATIVE_JACOBIAN_INVALID')
    native_j7 = [row[7] for row in native_jacobian]
    need(same_binary64_coefficients(
        metadata['native_moment_jacobian_column7'], native_j7),
        'QPT_AUDIT_NATIVE_J7_METADATA_MISMATCH')
    comparison = compare_vectors(independent_j7, native_j7)
    need(comparison['max_scaled_difference'] <= 1e-10
         and comparison['max_scaled_difference'] == metadata['independent_chain_vs_native_j7_max_scaled']
         and active_faces == metadata['active_tangent_faces'],
         'QPT_AUDIT_CHAIN_J7_COMPARISON_FAILED')

    from_stem, to_stem = point['from_stem'], point['to_stem']
    pair_from = motion_pair(context['states'][from_stem], state)
    pair_to = motion_pair(state, context['states'][to_stem])
    need(pair_from.get('same_retained_constraints_and_oriented_triangles') is True
         and pair_to.get('same_retained_constraints_and_oriented_triangles') is True,
         'QPT_AUDIT_RETAINED_BOUNDARY_CHANGED')
    source_pair_from = source_pair(
        context['states'][from_stem], state,
        context['velocities'][from_stem], velocity)
    source_pair_to = source_pair(
        state, context['states'][to_stem],
        velocity, context['velocities'][to_stem])

    result = {
        'schema': 'heart-h9-m21-6d-quarterpoint-independent-audit-v1',
        'status': 'ONE_QUARTERPOINT_INDEPENDENTLY_REVERIFIED_NOT_SMOOTH_OR_NEWTON_CERTIFIED',
        'index': args.index,
        'interval': point['interval'],
        'side': point['side'],
        'c7': point['c7'],
        'q': point['q'],
        'plan_sha256': file_hash(args.plan),
        'material_sha256': file_hash(archive_path),
        'source_motion_attachment_sha256': file_hash(attachment_path),
        'native_binary_sha256': binary,
        'evaluation_map_identity': material['evaluation_map_identity'],
        'strict_exact_boundary_reverified': True,
        'independent_exact_ten_moments_reverified': True,
        'independent_scaled_moment_error': moment_error,
        'exact_chain_j7_reverified': True,
        'independent_chain_vs_native_j7_max_scaled': comparison['max_scaled_difference'],
        'active_tangent_faces': active_faces,
        'source_geometry_bitwise_match_was_recorded_by_worker': metadata['source_geometry_bitwise_matched'],
        'source_discrete_signature_matches_both_interval_endpoints': True,
        'h7_match_left_anchor': left_status,
        'h7_match_right_anchor': right_status,
        'h7_match_from_endpoint': from_status,
        'h7_match_to_endpoint': to_status,
        'motion_pair_from_endpoint': pair_from,
        'motion_pair_to_endpoint': pair_to,
        'source_pair_from_endpoint': source_pair_from,
        'source_pair_to_endpoint': source_pair_to,
        'new_boolean_calls_this_run': 1,
        'new_native_source_calls_this_run': 1,
        'runtime_origin_cryptographically_attested': False,
        'root_cause_determined': False,
        'continuous_neighborhood_certified': False,
        'asymptotic_order_certified': False,
        'newton_admitted': False,
        'actual_accepted_step': False,
        'final_heart_obj_produced': False,
    }
    return result


def _worker_cap():
    resource.setrlimit(resource.RLIMIT_AS, (MAX_AS_BYTES, MAX_AS_BYTES))


def _clean_worker_env(repo):
    from prepare_h9_pinned_native import python_path_env
    env = dict(os.environ)
    for key in (
        'CONDA_PREFIX', 'LD_LIBRARY_PATH', 'LIBRARY_PATH', 'CMAKE_PREFIX_PATH',
        'PYTHONPATH', 'PYTHONHOME', 'BOOST_ROOT', 'Boost_ROOT', 'Boost_DIR',
        'PKG_CONFIG_PATH',
    ):
        env.pop(key, None)
    env['PATH'] = str(Path(sys.executable).resolve().parent) + ':/usr/local/bin:/usr/bin:/bin'
    stdcxx = Path(env.get('W3_STDCXX', '/usr/lib/x86_64-linux-gnu/libstdc++.so.6')).resolve()
    need(stdcxx.is_file(), 'SYSTEM_LIBSTDCXX_NOT_FOUND')
    env['LD_PRELOAD'] = str(stdcxx)
    return python_path_env(repo, environ=env)


def parent_run(args):
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    status = {
        'schema': 'heart-h9-m21-6d-quarterpoint-launch-v1',
        'status': 'BLOCKED_NO_NEW_QUARTERPOINT',
        'index': args.index,
        'new_qualified_quarterpoints': 0,
        'new_boolean_calls': 0,
        'new_native_source_calls': 0,
        'newton_admitted': False,
    }
    try:
        repo = Path(args.repo).resolve()
        from prepare_h9_pinned_native import (
            check_runtime, source_contract, native_module_smoke,
            verify_build_evidence,
        )
        machine = check_runtime(repo)
        need(machine['ready'], 'QPT_NATIVE_HOST_PREFLIGHT_BLOCKED:' + repr(machine['blocked_reasons']))
        contract = source_contract(repo)
        plan = _verify_plan(args)
        point = validate_point_contract(plan, args.index)

        hashes = native_module_smoke(repo)
        binary = {
            'core': hashes['_make_it_stand'],
            'boolean': hashes['_cherchi_core_boolean'],
            'arithmetic': hashes['_cherchi_rational_moments'],
        }
        need(binary == plan['native_binary_sha256'], 'QPT_PINNED_BINARY_MANIFEST_CHANGED')
        status['build_evidence_sha256'] = verify_build_evidence(
            repo, args.build_evidence, hashes)

        env = _clean_worker_env(repo)
        worker_dir = output / 'worker'
        audit_path = output / 'independent-audit.json'

        common = [
            '--repo', str(repo),
            '--precision-ledger', str(args.precision_ledger),
            '--artifact', str(args.artifact),
            '--stage17-native-dir', str(args.stage17_native_dir),
            '--m19-run', str(args.m19_run),
            '--source-run', str(args.source_run),
            '--boundary-report', str(args.boundary_report),
            '--moment-layers', str(args.moment_layers),
            '--certificate', str(args.certificate),
            '--stage18-audit', str(args.stage18_audit),
            '--plan', str(args.plan),
            '--index', str(args.index),
        ]

        worker_cmd = [sys.executable, str(Path(__file__).resolve()),
                      '--phase', 'worker', '--output', str(worker_dir), *common]
        with (output / 'worker.stdout.txt').open('x') as stdout,              (output / 'worker.stderr.txt').open('x') as stderr:
            try:
                worker_code = subprocess_code = None
                from h9_process_isolation import run_process_group
                worker_code = run_process_group(
                    worker_cmd, env=env, stdout=stdout, stderr=stderr,
                    preexec_fn=_worker_cap, timeout=WORKER_SECONDS,
                )
            except subprocess.TimeoutExpired:
                worker_code = 124
        status['worker_exit_code'] = worker_code
        need(worker_code == 0, 'QPT_REAL_CHERCHI_AND_SOURCE_WORKER_FAILED:' + str(worker_code))

        remaining = int(MAX_SECONDS - (time.monotonic() - start) - 10)
        need(remaining > 0, 'QPT_NO_TIME_LEFT_FOR_INDEPENDENT_AUDIT')
        audit_cmd = [sys.executable, str(Path(__file__).resolve()),
                     '--phase', 'audit', '--worker-dir', str(worker_dir),
                     '--audit-output', str(audit_path), *common]
        with (output / 'audit.stdout.txt').open('x') as stdout,              (output / 'audit.stderr.txt').open('x') as stderr:
            try:
                audit_code = run_process_group(
                    audit_cmd, env=env, stdout=stdout, stderr=stderr,
                    preexec_fn=_worker_cap, timeout=min(AUDIT_SECONDS, remaining),
                )
            except subprocess.TimeoutExpired:
                audit_code = 124
        status['audit_exit_code'] = audit_code
        need(audit_code == 0, 'QPT_INDEPENDENT_AUDIT_FAILED:' + str(audit_code))

        audit = strict_json(audit_path, file_hash(audit_path))
        need(audit.get('status') ==
             'ONE_QUARTERPOINT_INDEPENDENTLY_REVERIFIED_NOT_SMOOTH_OR_NEWTON_CERTIFIED'
             and audit.get('index') == args.index
             and audit.get('new_boolean_calls_this_run') == 1
             and audit.get('new_native_source_calls_this_run') == 1
             and audit.get('newton_admitted') is False,
             'QPT_INDEPENDENT_AUDIT_RESULT_INCOMPLETE')
        need(source_contract(repo) == contract, 'QPT_SOURCE_TREE_CHANGED_DURING_RUN')

        status.update(
            status='ONE_QUARTERPOINT_INDEPENDENTLY_VERIFIED_NO_NEWTON',
            new_qualified_quarterpoints=1,
            new_boolean_calls=1,
            new_native_source_calls=1,
            point_stem=capture_stem(point),
            plan_sha256=file_hash(args.plan),
            independent_audit_sha256=file_hash(audit_path),
            newton_admitted=False,
            continuous_neighborhood_certified=False,
        )
        print('M21_6D_QUARTERPOINT_STATUS', status['status'])
        print('M21_6D_QUARTERPOINT_INDEX', args.index)
        print('M21_6D_NEWTON', False)
        return 0
    except Exception as error:
        status.update(
            status='FAILED_CLOSED_NO_NEWTON',
            error=f'{type(error).__name__}: {error}',
            traceback=traceback.format_exc(),
            newton_admitted=False,
        )
        return 2 if 'HOST_PREFLIGHT' in str(error) else 1
    finally:
        status['elapsed_seconds'] = time.monotonic() - start
        (output / 'launch_result.json').write_text(
            json.dumps(status, sort_keys=True, indent=2, allow_nan=False) + '\n',
            encoding='utf8',
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('run', 'worker', 'audit'), required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[4])
    for name in (
        'precision-ledger', 'artifact', 'stage17-native-dir', 'm19-run',
        'source-run', 'boundary-report', 'moment-layers', 'certificate',
        'stage18-audit', 'plan',
    ):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--index', type=int, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--worker-dir', type=Path)
    parser.add_argument('--audit-output', type=Path)
    parser.add_argument('--build-evidence', type=Path)
    args = parser.parse_args(argv)

    if args.phase == 'run':
        if args.output is None or args.build_evidence is None:
            parser.error('run requires --output and --build-evidence')
        return parent_run(args)
    if args.phase == 'worker':
        if args.output is None:
            parser.error('worker requires --output')
        work_one(args)
        return 0
    if args.worker_dir is None or args.audit_output is None:
        parser.error('audit requires --worker-dir and --audit-output')
    result = audit_one(args)
    with Path(args.audit_output).open('x', encoding='utf8') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print('M21_6D_INDEPENDENT_AUDIT', result['status'], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
