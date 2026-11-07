"""W3 Heart H9 M21.6A: retained-boundary/source motion residuals, by identity.

Read only. No Boolean, source evaluator, native import, Newton, or topology
certification. The CLI loads the six *already saved* Cherchi material packets
and the six previously recorded source-motion attachments, authenticates their
M18/M19/M20/M21 provenance with existing W3 readers, and independently
reconstructs the boundary tangent using rational EXPLICIT3D/LPI/TPI rules.

All per-interval vertex identities and oriented semantic triangle multisets
must match. An observed mismatch is never repaired with slot indices.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
from hashlib import sha256
import json
import math
from pathlib import Path

STEMS = ('side-00-left-coarse', 'side-01-left-near',
         'side-02-right-near', 'side-03-right-coarse',
         'm19-mid-00-left-mid', 'm19-mid-01-right-mid')
SEQUENCES = {'left': (0, 4, 1), 'right': (2, 5, 3)}
INTERVALS = (('full', 0, 2), ('first-half', 0, 1), ('second-half', 1, 2))
KINDS = ('EXPLICIT3D', 'LPI', 'TPI')
LEDGER_SHA = '95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703'
LPI_SHA = 'd353486cafb3b81a97c302c51d8a034eedee327fabe92f2497df2c48b49c522e'
CORE_SHA = 'd66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd'


class Refused(ValueError):
    """Never convert a failed proof or a missing input into an accepted result."""


def require(ok, reason):
    if not ok:
        raise Refused(reason)


def token(value):
    q = F(value)
    return f'{q.numerator}/{q.denominator}'


def to_exact(value):
    if isinstance(value, F):
        return value
    if type(value) in (int, float):
        require(math.isfinite(value), 'NONFINITE_COORDINATE')
        return F(value)
    require(type(value) is str and 0 < len(value) < 100000,
            'INVALID_RATIONAL_INPUT')
    # Existing M21.3 signed residual outputs use str(Fraction): zero is '0'.
    # Accept only explicit decimal integers or exact n/d, never decimals.
    if '/' not in value:
        require(value.lstrip('-').isascii() and value.lstrip('-').isdigit(),
                'BAD_INTEGER_RATIONAL_TOKEN')
        return F(int(value), 1)
    require(value.count('/') == 1, 'BAD_RATIONAL_TOKEN')
    a, b = value.split('/', 1)
    require(a.lstrip('-').isascii() and a.lstrip('-').isdigit() and
            b.isascii() and b.isdigit() and int(b) > 0,
            'BAD_RATIONAL_TOKEN')
    return F(int(a), int(b))


def v3(v):
    require(isinstance(v, (tuple, list)) and len(v) == 3, 'BAD_VECTOR3')
    return tuple(to_exact(x) for x in v)


def vec_sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def vec_add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def vec_scale(q, v):
    return tuple(q*x for x in v)


def norm2(v):
    return sum((x*x for x in v), F(0))


def norm_approx(v):
    return math.sqrt(float(norm2(v)))


def require_unique_ordered(keys, label):
    keys = list(keys)
    require(len(keys) == len(set(keys)), 'DUPLICATE_IDENTITY:' + label)
    return keys


def file_sha256(path):
    h = sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_strict_json(path, expected_sha=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'MISSING_OR_SYMLINK:' + str(path))
    require(0 < path.stat().st_size < 32*1024**2, 'FILE_SIZE_OUT_OF_RANGE:' + str(path))
    if expected_sha is not None:
        require(file_sha256(path) == expected_sha, 'INPUT_SHA_MISMATCH:' + path.name)
    def unique_pairs(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out, 'DUPLICATE_JSON_KEY:' + k)
            out[k] = v
        return out
    def invalid_number(s):
        raise Refused('NONFINITE_JSON_NUMBER:' + s)
    return json.loads(path.read_text(encoding='utf8'),
                      object_pairs_hook=unique_pairs, parse_constant=invalid_number)


class Stats:
    """Bounded-memory summary; the top-k witnesses include exact residuals."""
    def __init__(self, top_k):
        self.count = 0
        self.top_k = top_k
        self.max_norm = 0.0
        self.max_axis = 0.0
        self.max_relative = 0.0
        self.sum_norm = 0.0
        self.sum_sq_norm = 0.0
        self.top = []

    def put(self, name, residual, average, *, identity=None):
        residual = v3(residual)
        average = v3(average)
        n = norm_approx(residual)
        a = norm_approx(average)
        relative = n/a if a else None
        self.count += 1
        self.sum_norm += n
        self.sum_sq_norm += n*n
        self.max_norm = max(self.max_norm, n)
        self.max_axis = max(self.max_axis, *(float(abs(x)) for x in residual))
        if relative is not None:
            self.max_relative = max(self.max_relative, relative)
        row = {'name': name, 'residual_norm': n,
               'signed_residual_exact': [token(x) for x in residual],
               'endpoint_average_velocity_exact': [token(x) for x in average],
               'relative_residual_if_velocity_nonzero': relative}
        if identity is not None:
            row['identity'] = repr(identity)
        self.top.append(row)
        self.top.sort(key=lambda x: (-x['residual_norm'], x['name']))
        del self.top[self.top_k:]

    def export(self):
        return {'count': self.count,
                'max_residual_norm': self.max_norm,
                'max_abs_coordinate': self.max_axis,
                'max_relative_residual_if_velocity_nonzero': self.max_relative,
                'mean_residual_norm': self.sum_norm/self.count if self.count else None,
                'rms_residual_norm': math.sqrt(self.sum_sq_norm/self.count) if self.count else None,
                'top': self.top}


def pair_interval(left, right, vel_left, vel_right, *, side, interval,
                  from_stem, to_stem, top_k=5):
    """Compare same-stratum exact rational boundary/source velocities.

    Existing material_state verifies all operand identities, exact positions,
    oriented face edges and the frozen physical->target frame. We still demand
    identical retained identities and oriented semantic triangle multisets on
    both sides before matching any vertex.
    """
    require(side in SEQUENCES and interval in {x[0] for x in INTERVALS},
            'BAD_INTERVAL_LABEL')
    require(1 <= top_k <= 20, 'BAD_TOP_K')
    p0, p1 = left['positions'], right['positions']
    m0, m1 = left.get('motion'), right.get('motion')
    require(isinstance(p0, dict) and isinstance(p1, dict) and
            isinstance(m0, dict) and isinstance(m1, dict), 'MISSING_BOUNDARY_MOTION')
    require(p0.keys() == p1.keys() and m0.keys() == p0.keys() and m1.keys() == p0.keys(),
            'CHANGED_RETAINED_CONSTRUCTION_IDENTITIES')
    require(left['semantic_triangles'] == right['semantic_triangles'],
            'CHANGED_ORIENTED_SEMANTIC_TRIANGLES')
    require(left['source_faces'] == right['source_faces'], 'CHANGED_SOURCE_FACE_SIGNATURE')
    h = to_exact(right['c7']) - to_exact(left['c7'])
    require(h > 0, 'NONPOSITIVE_PARAMETER_INTERVAL')
    require(len(left['source']) == len(right['source']) == len(vel_left) == len(vel_right),
            'SOURCE_MOTION_INDEXING_MISMATCH')
    groups = {k: Stats(top_k) for k in KINDS}
    for key in sorted(require_unique_ordered(p0, 'retained'), key=repr):
        kind = key[0]
        require(kind in groups, 'UNKNOWN_CONSTRUCTION_KIND')
        pa, pb, va, vb = v3(p0[key]), v3(p1[key]), v3(m0[key]), v3(m1[key])
        average = vec_scale(F(1, 2), vec_add(va, vb))
        secant = vec_scale(1/h, vec_sub(pb, pa))
        groups[kind].put(repr(key), vec_sub(secant, average), average, identity=key)
    source = Stats(top_k)
    for index, (pa, pb, va, vb) in enumerate(zip(left['source'], right['source'],
                                                vel_left, vel_right)):
        pa, pb, va, vb = v3(pa), v3(pb), v3(va), v3(vb)
        average = vec_scale(F(1, 2), vec_add(va, vb))
        secant = vec_scale(1/h, vec_sub(pb, pa))
        source.put('source:'+str(index), vec_sub(secant, average), average)
    require(sum(s.count for s in groups.values()) == len(p0),
            'INCOMPLETE_BOUNDARY_GROUP_COVERAGE')
    return {'side': side, 'interval': interval,
            'from_stem': from_stem, 'to_stem': to_stem,
            'delta_c7_exact': token(h),
            'retained_vertex_count': len(p0),
            'same_retained_constraints_and_oriented_triangles': True,
            'group_residuals': {k: v.export() for k, v in groups.items()},
            'source_residuals': source.export(),
            'continuously_smooth_stratum_certified': False,
            'newton_admitted': False}


def partition_identity(pa, pm, pb, va, vm, vb, h1, h2):
    """Verify finite-interval secant/trapezoid partition exactly (Fractions)."""
    pa, pm, pb = map(v3, (pa, pm, pb))
    va, vm, vb = map(v3, (va, vm, vb))
    h1, h2 = to_exact(h1), to_exact(h2)
    require(h1 > 0 and h2 > 0, 'BAD_PARTITION_INTERVAL')
    total = h1+h2
    w1, w2 = h1/total, h2/total
    avg1, avg2 = vec_scale(F(1, 2), vec_add(va, vm)), vec_scale(F(1, 2), vec_add(vm, vb))
    avg = vec_scale(F(1, 2), vec_add(va, vb))
    r1 = vec_sub(vec_scale(1/h1, vec_sub(pm, pa)), avg1)
    r2 = vec_sub(vec_scale(1/h2, vec_sub(pb, pm)), avg2)
    full = vec_sub(vec_scale(1/total, vec_sub(pb, pa)), avg)
    weighted = vec_add(vec_scale(w1, r1), vec_scale(w2, r2))
    correction = vec_sub(vec_add(vec_scale(w1, avg1), vec_scale(w2, avg2)), avg)
    require(full == vec_add(weighted, correction), 'FULL_HALF_RESIDUAL_IDENTITY_FAILED')
    return (r1, r2, full, correction)


def summarize_partition(states, velocities, side, sequence):
    """Quantify cancellation and midpoint correction on all retained keys."""
    a, m, b = (states[i] for i in sequence)
    v0, vm, v2 = (velocities[i] for i in sequence)
    h1 = to_exact(m['c7'])-to_exact(a['c7'])
    h2 = to_exact(b['c7'])-to_exact(m['c7'])
    require(h1 > 0 and h2 > 0, 'PARTITION_PARAMETER_ORDER')
    require(a['positions'].keys() == m['positions'].keys() == b['positions'].keys(),
            'PARTITION_CHANGED_CONSTRUCTION_IDENTITIES')
    require(a['semantic_triangles'] == m['semantic_triangles'] == b['semantic_triangles'],
            'PARTITION_CHANGED_ORIENTED_SEMANTIC_TRIANGLES')
    groups = {k: {'count': 0, 'opposing_half_residual_directions': 0,
                  'max_midpoint_velocity_correction': 0.0,
                  'max_full_residual_norm': 0.0} for k in KINDS}
    for key in a['positions']:
        r1, r2, full, correction = partition_identity(
            a['positions'][key], m['positions'][key], b['positions'][key],
            a['motion'][key], m['motion'][key], b['motion'][key], h1, h2)
        kind = key[0]
        require(kind in groups, 'PARTITION_UNKNOWN_CONSTRUCTION_KIND')
        group = groups[kind]
        group['count'] += 1
        group['opposing_half_residual_directions'] += (sum((x*y for x,y in zip(r1, r2)), F(0)) < 0)
        group['max_midpoint_velocity_correction'] = max(
            group['max_midpoint_velocity_correction'], norm_approx(correction))
        group['max_full_residual_norm'] = max(group['max_full_residual_norm'], norm_approx(full))
    require(len(a['source']) == len(m['source']) == len(b['source']) == len(v0) == len(vm) == len(v2),
            'PARTITION_SOURCE_VERTEX_COUNT_CHANGED')
    source = {'count': 0, 'opposing_half_residual_directions': 0,
              'max_midpoint_velocity_correction': 0.0, 'max_full_residual_norm': 0.0}
    for i in range(len(v0)):
        r1, r2, full, corr = partition_identity(
            a['source'][i], m['source'][i], b['source'][i],
            v0[i], vm[i], v2[i], h1, h2)
        source['count'] += 1
        source['opposing_half_residual_directions'] += (sum((x*y for x,y in zip(r1, r2)), F(0)) < 0)
        source['max_midpoint_velocity_correction'] = max(source['max_midpoint_velocity_correction'], norm_approx(corr))
        source['max_full_residual_norm'] = max(source['max_full_residual_norm'], norm_approx(full))
    require(sum(g['count'] for g in groups.values()) == len(a['positions']),
            'PARTITION_INCOMPLETE_BOUNDARY_COVERAGE')
    return {'side': side, 'delta_c7_first_half_exact': token(h1),
            'delta_c7_second_half_exact': token(h2),
            'exact_partition_identities_verified': len(a['positions'])+len(v0),
            'groups': groups, 'source': source,
            'continuous_neighborhood_certified': False}


def selected_lpi_crosscheck(states, lpi, request, packet_hashes=None, attachment_hashes=None):
    """Bind each of the 18 earlier LPI rows to the full-boundary key/velocity.

    Unlike slot-index alignment, this uses the source-operand identity key;
    physical->target conversion is the same frozen transform used by M21.
    """
    from h9_m21_3_lpi import CASES
    from h9_m21_motion_math import to_target
    rows = lpi.get('samples')
    require(lpi.get('schema') == 'heart-h9-m21-3-selected-lpi-motion-v1' and
            lpi.get('status') == 'SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY' and
            lpi.get('precision_ledger_sha256') == LEDGER_SHA and
            lpi.get('native_core_sha256') == CORE_SHA and
            lpi.get('new_boolean_calls_this_run') == 0 and
            lpi.get('new_native_source_calls_this_run') == 0 and
            lpi.get('newton_admitted') is False and
            isinstance(rows, list) and len(rows) == 6, 'UNBOUND_LPI_REFERENCE')
    checked = 0
    for s, state, stem in zip(rows, states, STEMS):
        require(s['stem'] == stem and s['c7'] == token(state['c7']),
                'LPI_SAMPLE_PARAMETER_OR_ORDER_CHANGED')
        i = checked // 3
        if packet_hashes is not None:
            require(s['material_sha256'] == packet_hashes[i],
                    'LPI_MATERIAL_SHA_DRIFT')
        if attachment_hashes is not None:
            require(s['attachment_sha256'] == attachment_hashes[i],
                    'LPI_ATTACHMENT_SHA_DRIFT')
        require(len(s['constructions']) == len(CASES) == 3,
                'LPI_SELECTED_ROWS_INCOMPLETE')
        names = set()
        for row in s['constructions']:
            label = row['label']
            require(label in CASES and label not in names and
                    row.get('reference_position_velocity_exact_match') is True,
                    'LPI_CONSTRUCTION_LABEL_OR_ATTESTATION_MISMATCH')
            names.add(label)
            edge, face = CASES[label]
            key = ('LPI', tuple((0, i) for i in edge), tuple((1, i) for i in face))
            require(key in state['positions'] and key in state['motion'],
                    'LPI_SELECTED_FEATURE_IDENTITY_MISSING')
            px = to_target(v3(row['position']), request)
            vx = to_target(v3(row['velocity']), request, True)
            require(px == state['positions'][key] and vx == state['motion'][key],
                    'LPI_SELECTED_POSITION_OR_VELOCITY_DRIFT')
            checked += 1
    require(checked == 18, 'LPI_REFERENCE_COVERAGE_INCOMPLETE')
    return checked


def selected_interval_crosscheck(intervals, lpi, request, states):
    """Exact comparison of 18 selected LPI residuals, not only their existence."""
    from h9_m21_3_lpi import CASES
    from h9_m21_motion_math import to_target
    saved = lpi.get('same_side_interval_lpi_secants')
    require(isinstance(saved, list) and len(saved) == 6 and len(intervals) == 6,
            'SELECTED_INTERVAL_COVERAGE')
    by_stem = dict(zip(STEMS, states))
    checked = 0
    for interval, ref in zip(intervals, saved):
        require(all(interval[k] == ref[k] for k in ('side', 'interval', 'from_stem', 'to_stem')) and
                to_exact(ref['features']['Repeated']['delta_c7']) ==
                to_exact(interval['delta_c7_exact']), 'LPI_INTERVAL_IDENTITY_DRIFT')
        require(set(ref['features']) == set(CASES), 'LPI_INTERVAL_FEATURE_SET_MISMATCH')
        a = by_stem[interval['from_stem']]
        b = by_stem[interval['to_stem']]
        h = to_exact(interval['delta_c7_exact'])
        for label, (edge, face) in CASES.items():
            key = ('LPI', tuple((0, i) for i in edge), tuple((1, i) for i in face))
            require(key in a['positions'] and key in b['positions'],
                    'LPI_INTERVAL_FEATURE_IDENTITY_MISSING')
            pa, pb = v3(a['positions'][key]), v3(b['positions'][key])
            va, vb = v3(a['motion'][key]), v3(b['motion'][key])
            average = vec_scale(F(1, 2), vec_add(va, vb))
            actual = vec_sub(vec_scale(1/h, vec_sub(pb, pa)), average)
            rec = ref['features'][label]
            require(to_exact(rec['delta_c7']) == h and
                    to_target(v3(rec['signed_residual']), request, True) == actual and
                    to_target(v3(rec['endpoint_average_velocity']), request, True) == average,
                    'LPI_SELECTED_INTERVAL_RESIDUAL_DRIFT')
            checked += 1
    require(checked == 18, 'LPI_SELECTED_INTERVAL_NOT_FULLY_CHECKED')
    return checked


def analyze(states, source_velocities, stems, lpi, request, top_k=5,
            packet_hashes=None, attachment_hashes=None, expected_boundary_count=None):
    require(tuple(stems) == STEMS and len(states) == len(source_velocities) == 6,
            'SIX_PACKET_ORDER_OR_COUNT_MISMATCH')
    if expected_boundary_count is not None:
        require(type(expected_boundary_count) is int and expected_boundary_count > 0 and
                all(len(state['positions']) == expected_boundary_count for state in states) and
                all(len(state['source']) > 0 for state in states),
                'EXPECTED_FULL_BOUNDARY_OR_SOURCE_MISSING')
    count = selected_lpi_crosscheck(states, lpi, request, packet_hashes, attachment_hashes)
    intervals = []
    for side, sequence in SEQUENCES.items():
        for label, a, b in INTERVALS:
            i, j = sequence[a], sequence[b]
            interval = pair_interval(states[i], states[j], source_velocities[i],
                                     source_velocities[j], side=side, interval=label,
                                     from_stem=stems[i], to_stem=stems[j], top_k=top_k)
            intervals.append(interval)
    partitions = [summarize_partition(states, source_velocities, side, sequence)
                  for side, sequence in SEQUENCES.items()]
    return {'schema': 'heart-h9-m21-6a-all-retained-boundary-motion-v1',
            'status': ('SIX_SAVED_PACKETS_FULL_BOUNDARY_DISCRETE_MOTION_DIAGNOSTIC_ONLY'
                       if expected_boundary_count is not None else
                       'SELECTED_OR_SYNTHETIC_SUBSET_DIAGNOSTIC_NOT_FULL_BOUNDARY'),
            'sample_count': 6, 'samples': [
                {'stem': stem, 'retained_vertex_count': len(state['positions']),
                 'source_vertex_count': len(state['source']),
                 'construction_counts': state['kinds']}
                for state, stem in zip(states, stems)],
            'intervals': intervals,
            'full_half_exact_partition_checks': partitions,
            'crosschecks': {
                'm21_5b_lpi_sample_positions_and_velocities': count,
                'm21_5b_lpi_interval_selected_features_present': selected_interval_crosscheck(intervals, lpi, request, states),
                'boundary_correspondence': 'STRICT_EXACT_CONSTRUCTION_IDENTITY_AND_ORIENTED_SEMANTIC_TRIANGLES',
                'finite_difference_scope': 'FINITE_SAVED_BINARY64_SOURCE_TANGENTS_NOT_CONTINUOUS_DERIVATIVE_PROOF'},
            'claims': {'new_boolean_calls': 0, 'new_native_source_calls_this_run': 0,
                       'root_cause_determined': False,
                       'continuous_neighborhood_certified': False,
                       'asymptotic_order_certified': False,
                       'newton_admitted': False, 'final_heart_obj_produced': False}}


def run(args):
    """CLI entry uses only existing W3 gates; imports do not load native modules."""
    from h9_m21_layered_replay import (LEDGER_SHA as GATE_LEDGER_SHA, STEMS as GATE_STEMS,
                                       load_ledger, load_six, frozen_request, bind_file, dump)
    from h9_m21_3_lpi import source_rows, read_motion
    from h9_m21_motion_math import material_state
    require(GATE_LEDGER_SHA == LEDGER_SHA and GATE_STEMS == STEMS,
            'UPSTREAM_M21_CONTRACT_CHANGED')
    require(args.output.parent.is_dir() and not args.output.exists(),
            'OUTPUT_PARENT_MISSING_OR_OUTPUT_EXISTS')
    ledger = load_ledger(args.precision_ledger)
    request = frozen_request(args.artifact)['request']
    materials, plan, _ = load_six(args, ledger)
    core = plan['stage17_current_binary_sha256']['core']
    require(core == CORE_SHA, 'SOURCE_CORE_BINARY_DRIFT')
    lpi = read_strict_json(args.lpi_report, LPI_SHA)
    master = read_strict_json(args.source_run / 'layered-report.json')
    report_path = bind_file(args.source_run / 'worker/layered-report.json',
                            master.get('worker_report_sha256'))
    report = read_strict_json(report_path)
    rows = source_rows(report, core)
    states, velocities = [], []
    for (material, _, evidence), row in zip(materials, rows):
        velocity = read_motion(args.source_run / 'worker', row, evidence, core)
        state = material_state(material, request, velocity)
        require(len(state['positions']) == 8455, 'UNEXPECTED_HEART_BOUNDARY_VERTEX_COUNT')
        states.append(state)
        velocities.append(velocity)
    out = analyze(states, velocities, STEMS, lpi, request, args.top_k,
                  [ev['material_sha256'] for _, _, ev in materials],
                  [r['source_motion_attachment_sha256'] for r in rows],
                  expected_boundary_count=8455)
    out['inputs'] = {
        'precision_ledger_sha256': LEDGER_SHA,
        'm21_5b_lpi_sha256': LPI_SHA,
        'source_worker_report_sha256': file_sha256(report_path),
        'native_source_core_sha256': core,
        'six_material_sha256': [evidence['material_sha256'] for _, _, evidence in materials],
        'six_motion_sha256': [r['source_motion_attachment_sha256'] for r in rows],
        'all_source_only_motion_attestations_replayed_and_hash_bound': True,
        'full_raw_six_packet_bytes_read': True,
        'runtime_origin_cryptographically_attested': False}
    require(out['crosschecks']['m21_5b_lpi_sample_positions_and_velocities'] == 18 and
            out['crosschecks']['m21_5b_lpi_interval_selected_features_present'] == 18,
            'MISSING_FROZEN_LPI_REFERENCE')
    dump(args.output, out)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for opt in ('precision-ledger', 'artifact', 'stage17-native-dir', 'm19-run',
                'source-run', 'lpi-report', 'output'):
        parser.add_argument('--'+opt, type=Path, required=True)
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args(argv)
    result = run(args)
    print('M21_6A_STATUS', result['status'])
    print('M21_6A_SAMPLE_COUNT', result['sample_count'])
    for x in result['intervals']:
        print('M21_6A_INTERVAL', x['side'], x['interval'],
              {k: round(v['max_residual_norm'], 12)
               for k,v in x['group_residuals'].items()},
              'SOURCE', round(x['source_residuals']['max_residual_norm'], 12))
    print('M21_6A_NEWTON_ADMITTED', False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
