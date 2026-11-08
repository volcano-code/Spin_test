"""W3 M21.6D-P0: predeclare four real quarter-point probes; NO native calls.

The four q vectors are exact binary64 midpoints of already-qualified same-side
segments: left coarse->M19 midpoint, left midpoint->near, right near->midpoint,
and right midpoint->coarse. This file only validates existing inputs and writes
a create-only plan. It does not run Cherchi, source motion, or Newton.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

from h9_stage19_multiscale import (
    b64_same, digest as m19_digest, file_hash, generate_plan, midpoint, read_json,
)
from h9_m21_layered_replay import (
    LEDGER_SHA, STEMS, bind_file, frozen_request, load_ledger, load_six,
)
from h9_m21_3_lpi import read_motion, source_rows
from h9_m21_motion_math import material_state
from h9_m21_6b_moment_layers import (
    BINARY_SHA, BOUNDARY_SHA, LPI_SHA, digest, strict_json,
)

M21_6C_SHA = '62c69598747623121314cdf88055315dc7617726c3bfc0b8a9e7c3fd57ae3915'
M21_6C_SCHEMA = 'heart-h9-m21-6c-support-subgroup-audit-v1'
M21_6C_STATUS = 'SIX_SAVED_SURFACES_FACE_SUPPORT_SUBGROUP_TEN_MOMENT_J7_DIAGNOSTIC_ONLY'
SCHEMA = 'heart-h9-m21-6d-four-quarterpoint-plan-v1'
STATUS = 'FOUR_REAL_QUARTERPOINTS_PREDECLARED_NOT_EXECUTED'
EXPECTED_STEMS = (
    'side-00-left-coarse',
    'side-01-left-near',
    'side-02-right-near',
    'side-03-right-coarse',
    'm19-mid-00-left-mid',
    'm19-mid-01-right-mid',
)


class PlanRejected(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise PlanRejected(reason)


def _finite_q(row):
    q = row.get('q')
    need(type(q) is list and len(q) == 10, 'BAD_TEN_COEFFICIENT_VECTOR')
    need(all(type(x) in (int, float) and math.isfinite(float(x)) for x in q),
         'NONFINITE_COEFFICIENT_VECTOR')
    return [float(x) for x in q]


def make_quarterpoint_plan(samples):
    """Pure planner over six already-qualified binary64 coefficient vectors."""
    need(type(samples) is list and len(samples) == 6, 'SIX_QUALIFIED_ENDPOINTS_REQUIRED')
    need(tuple(row.get('stem') for row in samples) == EXPECTED_STEMS,
         'SIX_SAMPLE_STEM_ORDER_CHANGED')

    q_by_stem = {row['stem']: _finite_q(row) for row in samples}
    reference = q_by_stem[EXPECTED_STEMS[0]]
    for stem, q in q_by_stem.items():
        for k in range(10):
            if k != 7:
                need(b64_same(q[k], reference[k]),
                     'NON_C7_COEFFICIENT_CHANGED:' + stem + ':' + str(k))

    # Every row must be on its declared same-side branch and in strict c[7] order.
    ordered = (
        ('left', 'side-00-left-coarse', 'm19-mid-00-left-mid',
         'side-01-left-near', 1, 'H8F_SAMPLE_059'),
        ('right', 'side-02-right-near', 'm19-mid-01-right-mid',
         'side-03-right-coarse', -1, 'H8F_SAMPLE_060'),
    )
    for side, low, mid, high, sign, anchor in ordered:
        c0, cm, c1 = (q_by_stem[s][7] for s in (low, mid, high))
        need(c0 < cm < c1, 'SAME_SIDE_C7_ORDER_INVALID:' + side)

    specs = (
        (0, 'left', 'left-coarse-to-mid', 'side-00-left-coarse',
         'm19-mid-00-left-mid', 0, 4, 0.25, 1, 'H8F_SAMPLE_059'),
        (1, 'left', 'left-mid-to-near', 'm19-mid-00-left-mid',
         'side-01-left-near', 4, 1, 0.75, 1, 'H8F_SAMPLE_059'),
        (2, 'right', 'right-near-to-mid', 'side-02-right-near',
         'm19-mid-01-right-mid', 2, 5, 0.25, -1, 'H8F_SAMPLE_060'),
        (3, 'right', 'right-mid-to-coarse', 'm19-mid-01-right-mid',
         'side-03-right-coarse', 5, 3, 0.75, -1, 'H8F_SAMPLE_060'),
    )
    points = []
    for index, side, interval, from_stem, to_stem, i, j, fraction, sign, anchor in specs:
        a, b = q_by_stem[from_stem], q_by_stem[to_stem]
        c = midpoint(a[7], b[7])  # exact midpoint of binary64 endpoints, rounded once
        need(a[7] < c < b[7], 'QUARTERPOINT_NOT_STRICTLY_INTERIOR:' + interval)
        q = list(a)
        q[7] = c
        need(all(b64_same(q[k], a[k]) and b64_same(q[k], b[k])
                 for k in range(10) if k != 7),
             'QUARTERPOINT_CHANGED_NON_C7_COEFFICIENT:' + interval)
        points.append({
            'index': index,
            'side': side,
            'interval': interval,
            'from_stem': from_stem,
            'to_stem': to_stem,
            'fraction_of_original_full_interval': fraction,
            'c7': c,
            'c7_binary64_hex': struct.pack('!d', c).hex(),
            'q': q,
            'expected_proxy_event_sign': sign,
            'expected_same_side_anchor': anchor,
            'native_boolean_call_required': True,
            'same_side_finite_probe_only': True,
        })

    return {
        'schema': SCHEMA,
        'status': STATUS,
        'point_count': 4,
        'points': points,
        'new_boolean_calls_planned': 4,
        'new_boolean_calls_executed': 0,
        'new_native_source_calls_planned': 4,
        'new_native_source_calls_executed': 0,
        'continuous_neighborhood_certified': False,
        'asymptotic_order_certified': False,
        'root_cause_determined': False,
        'newton_admitted': False,
        'final_heart_obj_produced': False,
    }


def _validate_m21_6c(doc):
    need(doc.get('schema') == M21_6C_SCHEMA and doc.get('status') == M21_6C_STATUS,
         'M21_6C_RESULT_NOT_QUALIFIED')
    need(doc.get('sample_count') == 6 and len(doc.get('samples', [])) == 6
         and len(doc.get('intervals', [])) == 6,
         'M21_6C_SAMPLE_OR_INTERVAL_COUNT_CHANGED')
    need(doc.get('input_sha256') == {
        'm20_ledger': LEDGER_SHA,
        'm21_6a_full_boundary': BOUNDARY_SHA,
        'native_core': BINARY_SHA,
        'm21_5b_lpi': LPI_SHA,
    }, 'M21_6C_INPUT_IDENTITY_CHANGED')
    need(all(s.get('exact_moment_ledger_reintegration_match') is True
             and s.get('dual_vs_existing_retained_tangent_exact_match') is True
             for s in doc['samples']), 'M21_6C_SAMPLE_AUDIT_INCOMPLETE')
    need(doc.get('scientific_limits', {}).get('newton_admitted') is False,
         'M21_6C_NEWTON_FLAG_NOT_DENIED')
    need([s.get('stem') for s in doc['samples']] == list(STEMS),
         'M21_6C_SAMPLE_ORDER_CHANGED')
    return doc


def build_plan(args):
    output = Path(args.output)
    need(output.parent.is_dir() and not output.exists(),
         'OUTPUT_PARENT_MISSING_OR_OUTPUT_ALREADY_EXISTS')

    ledger = load_ledger(args.precision_ledger)
    boundary = strict_json(args.boundary_report, BOUNDARY_SHA)
    need(boundary.get('sample_count') == 6 and len(boundary.get('intervals', [])) == 6
         and boundary.get('claims', {}).get('newton_admitted') is False,
         'M21_6A_BOUNDARY_NOT_QUALIFIED')
    layer_doc = _validate_m21_6c(strict_json(args.moment_layers, M21_6C_SHA))

    request = frozen_request(args.artifact)['request']
    need(request.get('material_density') == 1.0, 'FROZEN_DENSITY_CHANGED')

    expected_m19_plan = generate_plan(
        args.artifact, args.certificate, args.stage18_audit, args.stage17_native_dir)
    supplied_m19_plan_path = Path(args.m19_run) / 'midpoint-plan.json'
    supplied_m19_plan = read_json(supplied_m19_plan_path)
    need(supplied_m19_plan == expected_m19_plan, 'M19_PLAN_OR_SOURCE_CHANGED')

    launch_path = Path(args.m19_run) / 'native-two-midpoints' / 'launch_result.json'
    refinement_path = Path(args.m19_run) / 'native-two-midpoints' / 'independent-refinement.json'
    launch = read_json(launch_path)
    refinement = read_json(refinement_path)
    need(launch.get('status') == 'TWO_NEW_NATIVE_MIDPOINTS_INDEPENDENTLY_VERIFIED_NO_NEWTON'
         and launch.get('worker_exit_code') == 0 and launch.get('audit_exit_code') == 0
         and launch.get('new_qualified_midpoints') == 2
         and launch.get('newton_admitted') is False,
         'M19_TWO_MIDPOINTS_NOT_INDEPENDENTLY_QUALIFIED')
    need(refinement.get('new_real_midpoint_materials_independently_verified') == 2
         and len(refinement.get('two_refined_sides', [])) == 2
         and refinement.get('newton_admitted') is False,
         'M19_REFINEMENT_AUDIT_INCOMPLETE')

    raw, m19_plan, _ = load_six(args, ledger)
    need(m19_plan == expected_m19_plan, 'M19_PLAN_DRIFT_AFTER_SIX_PACKET_LOAD')
    core = m19_plan['stage17_current_binary_sha256']['core']
    need(core == BINARY_SHA, 'NATIVE_CORE_IDENTITY_CHANGED')

    source_root = Path(args.source_run)
    summary_path = source_root / 'layered-report.json'
    summary = strict_json(summary_path, digest(summary_path))
    worker = source_root / 'worker'
    worker_report_path = worker / 'layered-report.json'
    worker_report = strict_json(worker_report_path, summary['worker_report_sha256'])
    rows = source_rows(worker_report, core)

    samples = []
    for i, ((material, meta, ev), row) in enumerate(zip(raw, rows)):
        need(ev.get('stem') == EXPECTED_STEMS[i] and row.get('stem') == EXPECTED_STEMS[i],
             'SOURCE_MOTION_SAMPLE_ORDER_CHANGED:' + str(i))
        speed = read_motion(worker, row, ev, core)
        state = material_state(material, request, speed)
        need(state.get('motion') is not None and len(state['positions']) == 8455
             and len(state['source']) == 162
             and state['kinds'] == {'EXPLICIT3D': 7671, 'LPI': 784},
             'SIX_SAVED_MATERIAL_STATE_NOT_RECONSTRUCTED:' + str(i))
        q = [float(x) for x in material['quadric_coefficients']]
        samples.append({'stem': ev['stem'], 'q': q,
                        'material_sha256': ev['material_sha256'],
                        'source_motion_attachment_sha256': row['source_motion_attachment_sha256'],
                        'source_motion_replayed': True,
                        'same_call_native_jacobian_present': True})

    quarter = make_quarterpoint_plan(samples)
    quarter.update({
        'date': '2026-11-08',
        'branch': 'research/neuralmoments-w3-heart-h9-20261019',
        'native_binary_sha256': m19_plan['stage17_current_binary_sha256'],
        'evaluation_map_identity': m19_plan['stage18_current_evaluation_map_identity'],
        'six_sample_manifest': samples,
        'input_sha256': {
            'm20_ledger': LEDGER_SHA,
            'h8f_artifact': file_hash(args.artifact),
            'stage18_audit': file_hash(args.stage18_audit),
            'stage17_report': file_hash(Path(args.stage17_native_dir) / 'report.json'),
            'm19_plan': file_hash(supplied_m19_plan_path),
            'm19_launch_result': file_hash(launch_path),
            'm19_independent_refinement': file_hash(refinement_path),
            'm21_6a_boundary': BOUNDARY_SHA,
            'm21_6c_result': M21_6C_SHA,
            'm21_source_summary': digest(summary_path),
            'm21_source_worker_report': summary['worker_report_sha256'],
        },
        'm21_6c_sample_count': len(layer_doc['samples']),
        'plan_interpretation': (
            'Four predeclared same-side binary64 midpoint probes. '
            'No Cherchi Boolean or native source call has been executed by this planner.'
        ),
    })
    with output.open('x', encoding='utf8') as stream:
        json.dump(quarter, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print('M21_6D_PLAN_STATUS', quarter['status'])
    print('M21_6D_PLAN_POINTS', quarter['point_count'])
    print('M21_6D_NEW_BOOLEAN_CALLS_EXECUTED', quarter['new_boolean_calls_executed'])
    print('M21_6D_NEW_SOURCE_CALLS_EXECUTED', quarter['new_native_source_calls_executed'])
    print('M21_6D_NEWTON', False)
    return quarter


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('precision-ledger', 'artifact', 'stage17-native-dir', 'm19-run',
                 'source-run', 'boundary-report', 'moment-layers', 'certificate',
                 'stage18-audit', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    build_plan(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
