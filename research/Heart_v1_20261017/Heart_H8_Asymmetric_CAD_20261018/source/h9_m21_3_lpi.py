"""Offline W3 six-packet, three-construction LPI motion audit in the physical frame."""
import argparse
from math import sqrt
from pathlib import Path

from h9_m20_precision_replay import file_hash, read_json
from h9_m21_layered_replay import (
    FLAGS, LEDGER_SHA, STEMS, bind_file, dump, frozen_request, load_ledger, load_six,
)
from h9_m21_motion_math import (
    ZERO, add, construction, cross, dot, frac, key_for, mul, need, sub, to_target, vec,
)

CASES = {
    'Repeated': ((3756, 3813), (24, 86, 87)),
    'Left-full': ((9992, 10119), (31, 105, 110)),
    'Right-first': ((3168, 3618), (24, 151, 152)),
}


def decompose(positions, velocities):
    """Canonical line A,B and plane C,E,F. Use differentiated incidence at X."""
    a, b, c, e, f = map(vec, positions)
    va, vb, vc, ve, vf = map(vec, velocities)
    u, up = sub(b, a), sub(vb, va)
    w, wp = sub(c, a), sub(vc, va)
    ce, cf = sub(e, c), sub(f, c)
    n = cross(ce, cf)
    np = add(cross(sub(ve, vc), cf), cross(ce, sub(vf, vc)))
    d, num = dot(n, u), dot(n, w)
    need(d != 0, 'SINGULAR_LPI')
    t = num / d
    x = add(a, mul(t, u))
    # Derivative of n.(X-C) = 0; independent of construction's quotient rule.
    dt_normal = dot(np, sub(c, x)) / d
    dt_anchor = dot(n, vc) / d
    dt_line = -dot(n, add(va, mul(t, up))) / d
    tp = dt_normal + dt_anchor + dt_line
    xp = add(va, add(mul(t, up), mul(tp, u)))
    nd_normal, nd_anchor = dot(np, w), dot(n, wp)
    dp_normal, dp_line = dot(np, u), dot(n, up)
    dp = dp_normal + dp_line
    nd = nd_normal + nd_anchor
    need(tp == nd / d - t * dp / d, 'QUOTIENT_DECOMPOSITION_MISMATCH')
    incidence_squared = d*d / (dot(n, n) * dot(u, u))
    speed_squared = dot(xp, xp)
    values = dict(d=d, d_prime=dp, numerator=num, numerator_prime=nd,
                  abs_d=abs(d), abs_d_prime_over_d=abs(dp / d), t=t, t_prime=tp,
                  abs_t_prime=abs(tp), d_prime_normal=dp_normal, d_prime_line=dp_line,
                  numerator_prime_normal=nd_normal, numerator_prime_anchor_minus_line=nd_anchor,
                  t_prime_numerator=nd/d, t_prime_denominator=-t*dp/d,
                  t_prime_normal_net=dt_normal, t_prime_plane_anchor=dt_anchor,
                  t_prime_line_motion=dt_line, incidence_squared=incidence_squared,
                  speed_squared=speed_squared)
    row = {k: str(v) for k, v in values.items()}
    row.update(position=list(map(str, x)), velocity=list(map(str, xp)),
               incidence_approx=sqrt(float(incidence_squared)), speed_approx=sqrt(float(speed_squared)))
    return row, x, xp


def selected_rows(material, request, speeds, cases=CASES):
    proof = material['material_proof']
    need(proof.get('schema') == 'cherchi-same-call-material-v1', 'BAD_MATERIAL_PROOF')
    src, design = material['quadric_source_vertices'], request['design_vertices']
    need(len(speeds) == len(src), 'SOURCE_VELOCITY_LENGTH_MISMATCH')
    raw = {r['vertex_index']: r for r in proof['construction_records']}
    need(len(raw) == len(proof['construction_records']), 'DUPLICATE_RAW_SLOT')
    wanted = {('LPI', tuple((0, i) for i in edge), tuple((1, i) for i in face)): name
              for name, (edge, face) in cases.items()}
    rows = {}
    for record in proof['resolved_construction_records']:
        if record['point_type'] != 'LPI':
            continue
        key = key_for('LPI', record['operands'])
        if key not in wanted:
            continue
        name, i = wanted[key], record['vertex_index']
        need(name not in rows and type(i) is int and 0 <= i < len(proof['exact_vertices']),
             'DUPLICATE_CANDIDATE_OR_BAD_SLOT')
        r = raw[i]
        need(r['point_type'] == 'LPI' and len(r['operand_coordinates_exact']) == 5, 'RAW_LPI_MISMATCH')
        pts = list(map(vec, r['operand_coordinates_exact']))
        ids = [(o['source_vertices'][0]['input_object'], o['source_vertices'][0]['input_vertex'])
               for o in record['operands']]
        vel = []
        for (obj, index), p in zip(ids, pts):
            table = (design, src)[obj]
            need(index < len(table) and p == vec(table[index]), 'OPERAND_COORDINATE_MISMATCH')
            vel.append(vec(speeds[index]) if obj else ZERO)
        # Stable ordering gives comparable signed d, d-prime, t and t-prime across packets.
        order = [ids.index(j) for j in (*key[1], *key[2])]
        row, x, xp = decompose([pts[j] for j in order], [vel[j] for j in order])
        need((x, xp) == construction('LPI', pts, vel), 'INDEPENDENT_LPI_MISMATCH')
        need(x == vec(proof['exact_vertices'][i]) and
             to_target(x, request) == vec(material['variable_rational_vertices'][i]), 'SAVED_POSITION_MISMATCH')
        row.update(label=name, slot=i, design_edge=cases[name][0], source_plane=cases[name][1],
                   reference_position_velocity_exact_match=True)
        rows[name] = row
    need(rows.keys() == cases.keys(), 'MISSING_SELECTED_CONSTRUCTION')
    return [rows[name] for name in cases]


def source_rows(report, core_sha):
    rows = report['packet_results']
    need(report.get('schema') == 'heart-h9-m21-layered-motion-diagnostic-v1' and
         report.get('status') == 'SOURCE_MOTION_AND_EXACT_CHAIN_REPLAYED_DIAGNOSTIC_ONLY' and
         report.get('ledger_sha256') == LEDGER_SHA and report.get('native_core_sha256') == core_sha and
         report.get('new_native_source_calls_this_run') == 6 and report.get('new_boolean_calls_this_run') == 0 and
         report.get('newton_admitted') is False and [r['stem'] for r in rows] == list(STEMS),
         'INCOMPLETE_OR_MISBOUND_SOURCE_REPORT')
    return rows


def read_motion(worker, row, evidence, core_sha):
    need(row['material_sha256'] == evidence['material_sha256'] and row['stem'] == evidence['stem'] and
         row['source_motion_replayed'] is True and row['source_geometry_bitwise_matched'] is True,
         'SOURCE_PACKET_MISMATCH')
    att = read_json(bind_file(worker / (row['stem'] + '.source-motion.json'), row['source_motion_attachment_sha256']))
    need(att.get('schema') == 'heart-h9-m21-source-only-motion-v1' and
         att.get('material_sha256') == evidence['material_sha256'] and att.get('native_core_sha256') == core_sha and
         att.get('boolean_calls') == 0 and att.get('newton_admitted') is False, 'SOURCE_ATTACHMENT_MISMATCH')
    return att['physical_source_velocity_column7']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('precision-ledger', 'artifact', 'stage17-native-dir', 'm19-run', 'source-run', 'output'):
        ap.add_argument('--' + name, type=Path, required=True)
    args = ap.parse_args()
    ledger = load_ledger(args.precision_ledger)
    request = frozen_request(args.artifact)['request']
    packets, plan, _ = load_six(args, ledger)
    worker = args.source_run / 'worker'
    core_sha = plan['stage17_current_binary_sha256']['core']
    summary = read_json(args.source_run / 'layered-report.json')
    report_sha = summary['worker_report_sha256']
    report = read_json(bind_file(worker / 'layered-report.json', report_sha))
    rows = source_rows(report, core_sha)
    samples = []
    for (material, _, evidence), row in zip(packets, rows):
        speeds = read_motion(worker, row, evidence, core_sha)
        samples.append(dict(stem=row['stem'], material_sha256=evidence['material_sha256'],
                            attachment_sha256=row['source_motion_attachment_sha256'],
                            c7=str(frac(material['quadric_coefficients'][7])),
                            constructions=selected_rows(material, request, speeds)))
    dump(args.output, dict(schema='heart-h9-m21-3-selected-lpi-motion-v1', samples=samples,
                           status='SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY',
                           precision_ledger_sha256=LEDGER_SHA, worker_report_sha256=report_sha,
                           native_core_sha256=core_sha, script_sha256=file_hash(__file__),
                           new_native_source_calls_this_run=0, root_cause_determined=False, **FLAGS))


if __name__ == '__main__':
    main()
