#!/usr/bin/env python3
"""Read-only independent internal consistency audit of W3 H9 M21.3 LPI output.

Requires only the derived M21.3 JSON, not the original six native packets.
Exact rational identities are rechecked; this NEVER authenticates a native run,
proves continuous differentiability, or admits Newton.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
from hashlib import sha256
import json
import math
from pathlib import Path
import re

STEMS = ('side-00-left-coarse', 'side-01-left-near', 'side-02-right-near',
         'side-03-right-coarse', 'm19-mid-00-left-mid', 'm19-mid-01-right-mid')
LABELS = ('Repeated', 'Left-full', 'Right-first')
CASES = {
    'Repeated': ((3756, 3813), (24, 86, 87)),
    'Left-full': ((9992, 10119), (31, 105, 110)),
    'Right-first': ((3168, 3618), (24, 151, 152)),
}
INTERVALS = (('left', 'full', 0, 1), ('left', 'first-half', 0, 4),
             ('left', 'second-half', 4, 1), ('right', 'full', 2, 3),
             ('right', 'first-half', 2, 5), ('right', 'second-half', 5, 3))
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, 'DUPLICATE_JSON_KEY:' + k)
        result[k] = v
    return result


def deny_constant(s):
    raise ValueError('NONFINITE_JSON_CONSTANT:' + s)


def q(value):
    require(type(value) is str and len(value) < 10000,
            'EXPECTED_BOUNDED_RATIONAL_TOKEN')
    require(re.fullmatch(r'-?\d+(?:/\d+)?', value) is not None,
            'INVALID_RATIONAL_TOKEN')
    return F(value)


def v3(tokens):
    require(type(tokens) is list and len(tokens) == 3, 'EXPECTED_VECTOR3')
    return tuple(q(x) for x in tokens)


def near(a, b):
    return math.isfinite(a) and math.isfinite(b) and math.isclose(
        a, b, rel_tol=3e-13, abs_tol=1e-14)


def avg(a, b):
    return tuple((x + y)/2 for x, y in zip(a, b))


def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))


def weighted(a, b, h1, h2):
    return tuple((h1*x + h2*y)/(h1+h2) for x, y in zip(a, b))


def parse_input(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and
            0 < path.stat().st_size <= 3*1024*1024, 'MISSING_OR_OVERSIZED_REPORT')
    raw = path.read_bytes()
    data = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=deny_constant)
    require(type(data) is dict and
            data.get('schema') == 'heart-h9-m21-3-selected-lpi-motion-v1' and
            data.get('status') == 'SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY',
            'WRONG_M21_3_SCHEMA_OR_STATUS')
    require(data.get('new_boolean_calls_this_run') == 0 and
            data.get('new_native_source_calls_this_run') == 0 and
            data.get('newton_admitted') is False and
            data.get('root_cause_determined') is False and
            data.get('continuous_neighborhood_certified') is False and
            data.get('asymptotic_order_certified') is False and
            data.get('final_heart_obj_produced') is False and
            data.get('runtime_origin_cryptographically_attested') is False,
            'SCIENTIFIC_SCOPE_FLAGS_INCONSISTENT')
    for field in ('native_core_sha256', 'precision_ledger_sha256',
                  'worker_report_sha256', 'script_sha256'):
        require(type(data.get(field)) is str and HEX64.fullmatch(data[field]),
                'MISSING_SOURCE_HASH:' + field)
    return data, sha256(raw).hexdigest(), len(raw)


def audit(path, ledger_path=None):
    data, digest, byte_count = parse_input(path)
    ledger_binding = {'ledger_original_bytes_read': False, 'six_material_hashes_matched_to_ledger': None}
    if ledger_path is not None:
        ledger_path = Path(ledger_path)
        require(ledger_path.is_file() and not ledger_path.is_symlink() and
                0 < ledger_path.stat().st_size <= 5*1024*1024, 'LEDGER_MISSING_OR_OVERSIZED')
        ledger_raw = ledger_path.read_bytes()
        require(sha256(ledger_raw).hexdigest() == data['precision_ledger_sha256'],
                'M20_LEDGER_SHA_MISMATCH')
        ledger = json.loads(ledger_raw, object_pairs_hook=unique_pairs, parse_constant=deny_constant)
        require(ledger.get('schema') == 'heart-h9-m20-exact-difference-rounding-ledger-v1' and
                len(ledger.get('packets', [])) == 6, 'M20_LEDGER_SCHEMA_OR_PACKET_COUNT')
        ledger_binding = {'ledger_original_bytes_read': True,
                          'ledger_sha256': sha256(ledger_raw).hexdigest(),
                          'six_material_hashes_matched_to_ledger': False}
    samples = data.get('samples')
    if ledger_path is not None:
        require([(x['stem'], x['material_sha256']) for x in samples] ==
                [(x['stem'], x['material_sha256']) for x in ledger['packets']],
                'SIX_MATERIAL_DIGESTS_DIFFER_FROM_M20_LEDGER')
        ledger_binding['six_material_hashes_matched_to_ledger'] = True
    intervals = data.get('same_side_interval_lpi_secants')
    require(type(samples) is list and len(samples) == 6 and
            [s['stem'] for s in samples] == list(STEMS), 'SAMPLE_SET_OR_ORDER')
    require(type(intervals) is list and len(intervals) == 6, 'INTERVAL_SET_OR_COUNT')
    by_sample = []
    rows_checked = 0
    direction0 = 0
    measurements = {label: [] for label in LABELS}
    for sample in samples:
        require(HEX64.fullmatch(sample['material_sha256']) is not None and
                HEX64.fullmatch(sample['attachment_sha256']) is not None,
                'MISSING_PACKET_OR_ATTACHMENT_HASH')
        constructions = sample['constructions']
        require(type(constructions) is list and
                [r['label'] for r in constructions] == list(LABELS),
                'MISSING_OR_UNORDERED_LPI_CONSTRUCTION')
        indexed = {}
        for row in constructions:
            label = row['label']
            require(tuple(row['design_edge']) == CASES[label][0] and
                    tuple(row['source_plane']) == CASES[label][1],
                    'CANDIDATE_CONSTRUCTION_ID_MISMATCH')
            d, dp, numerator, np = (q(row[k]) for k in ('d', 'd_prime', 'numerator', 'numerator_prime'))
            t, tp = q(row['t']), q(row['t_prime'])
            require(d != 0 and t == numerator/d, 'LPI_INTERSECTION_IDENTITY')
            require(tp == q(row['t_prime_numerator']) + q(row['t_prime_denominator']) and
                    q(row['t_prime_numerator']) == np/d and
                    q(row['t_prime_denominator']) == -t*dp/d,
                    'LPI_QUOTIENT_RULE')
            require(tp == q(row['t_prime_normal_net']) + q(row['t_prime_plane_anchor']) +
                    q(row['t_prime_line_motion']), 'LPI_IMPLICIT_DERIVATIVE')
            require(dp == q(row['d_prime_normal']) + q(row['d_prime_line']) and
                    np == q(row['numerator_prime_normal']) + q(row['numerator_prime_anchor_minus_line']),
                    'LPI_DERIVATIVE_COMPONENTS')
            require(q(row['abs_d']) == abs(d) and
                    q(row['abs_d_prime_over_d']) == abs(dp/d) and
                    q(row['abs_t_prime']) == abs(tp), 'LPI_ABSOLUTE_VALUES')
            vel = v3(row['velocity'])
            require(q(row['speed_squared']) == sum((x*x for x in vel), F(0)) and
                    near(row['speed_approx'], math.sqrt(float(q(row['speed_squared'])))) and
                    near(row['incidence_approx'], math.sqrt(float(q(row['incidence_squared'])))),
                    'LPI_SPEED_OR_INCIDENCE_MISMATCH')
            require(0 < q(row['incidence_squared']) <= 1 and
                    row['reference_position_velocity_exact_match'] is True,
                    'INTERNAL_RECONSTRUCTION_NOT_REPORTED_AS_MATCH')
            _ = v3(row['position'])
            if q(row['t_prime_line_motion']) == 0 and q(row['d_prime_line']) == 0:
                direction0 += 1
            indexed[label] = row
            measurements[label].append({
                'c7': float(q(sample['c7'])),
                'incidence': row['incidence_approx'],
                'abs_d': float(abs(d)),
                'abs_d_prime_over_d': float(abs(dp/d)),
                't': float(t), 't_prime': float(tp),
                't_prime_plane_anchor': float(q(row['t_prime_plane_anchor'])),
                't_prime_normal_net': float(q(row['t_prime_normal_net'])),
                't_prime_line_motion': float(q(row['t_prime_line_motion'])),
                'speed': row['speed_approx']})
            rows_checked += 1
        by_sample.append(indexed)
    interval_summary = []
    identity_count = 0
    for row, (side, label, i, j) in zip(intervals, INTERVALS):
        require((row['side'], row['interval'], row['from_stem'], row['to_stem']) ==
                (side, label, STEMS[i], STEMS[j]), 'WRONG_INTERVAL_ORDER_OR_ENDPOINTS')
        require(set(row['features']) == set(LABELS), 'MISSING_INTERVAL_FEATURE')
        delta = q(samples[j]['c7']) - q(samples[i]['c7'])
        require(delta > 0, 'NONPOSITIVE_SIDE_INTERVAL')
        features = {}
        for name in LABELS:
            record = row['features'][name]
            require(q(record['delta_c7']) == delta, 'DELTA_C7_MISMATCH')
            start, end = by_sample[i][name], by_sample[j][name]
            p0,p1 = v3(start['position']),v3(end['position'])
            v0,v1 = v3(start['velocity']),v3(end['velocity'])
            secant = tuple((b-a)/delta for a,b in zip(p0,p1))
            mean = avg(v0,v1)
            residual = subtract(secant,mean)
            require(v3(record['position_secant']) == secant and
                    v3(record['endpoint_average_velocity']) == mean and
                    v3(record['signed_residual']) == residual,
                    'EXACT_INTERVAL_RESIDUAL_IDENTITY')
            require(q(record['max_abs_residual']) == max(map(abs,residual)),
                    'INTERVAL_MAX_RESIDUAL_MISMATCH')
            residual_norm = math.sqrt(float(sum((x*x for x in residual), F(0))))
            mean_norm = math.sqrt(float(sum((x*x for x in mean), F(0))))
            require(near(residual_norm, record['residual_norm_approx']) and
                    (near(residual_norm/mean_norm, record['relative_residual_approx'])
                     if mean_norm else record['relative_residual_approx'] is None),
                    'INTERVAL_RESIDUAL_NORM_MISMATCH')
            features[name] = {
                'residual_norm': residual_norm,
                'relative_residual': record['relative_residual_approx'],
                'max_abs_residual': float(max(map(abs,residual)))}
            identity_count += 1
        interval_summary.append({'side':side,'interval':label,'delta_c7':float(delta),
                                 'features':features})
    cancellation_checks = []
    for side, (a,m,b), idx in (('left',(0,4,1),0), ('right',(2,5,3),3)):
        full, left, right = intervals[idx:idx+3]
        h1=q(samples[m]['c7'])-q(samples[a]['c7'])
        h2=q(samples[b]['c7'])-q(samples[m]['c7'])
        require(h1>0 and h2>0 and h1+h2==q(full['features'][LABELS[0]]['delta_c7']),
                'PARTITION_C7_MISMATCH')
        for name in LABELS:
            rf, rl, rr = (v3(x['features'][name]['signed_residual'])
                          for x in (full,left,right))
            va,vm,vb = (v3(by_sample[k][name]['velocity']) for k in (a,m,b))
            curvature = subtract(weighted(avg(va,vm),avg(vm,vb),h1,h2),avg(va,vb))
            require(rf == tuple(x+y for x,y in zip(weighted(rl,rr,h1,h2),curvature)),
                    'PARTITION_VELOCITY_CURVATURE_IDENTITY')
            cancellation_checks.append({'side':side,'feature':name,
                                        'half_weighted_residual_norm':math.sqrt(float(sum((x*x for x in weighted(rl,rr,h1,h2)), F(0)))),
                                        'curvature_correction_norm':math.sqrt(float(sum((x*x for x in curvature), F(0)))),
                                        'full_residual_norm':math.sqrt(float(sum((x*x for x in rf),F(0))))})
    per_feature=[]
    for name, rows in measurements.items():
        per_feature.append({'feature':name,'samples':len(rows),
            'incidence_range':[min(x['incidence'] for x in rows),max(x['incidence'] for x in rows)],
            'abs_d_range':[min(x['abs_d'] for x in rows),max(x['abs_d'] for x in rows)],
            'abs_d_prime_over_d_range':[min(x['abs_d_prime_over_d'] for x in rows),max(x['abs_d_prime_over_d'] for x in rows)],
            't_range':[min(x['t'] for x in rows),max(x['t'] for x in rows)],
            't_prime_range':[min(x['t_prime'] for x in rows),max(x['t_prime'] for x in rows)],
            't_prime_line_motion_zero_count':sum(x['t_prime_line_motion']==0 for x in rows),
            'plane_anchor_tprime_fraction_range':[min(x['t_prime_plane_anchor']/x['t_prime'] for x in rows),
                                                  max(x['t_prime_plane_anchor']/x['t_prime'] for x in rows)],
            'speed_range':[min(x['speed'] for x in rows),max(x['speed'] for x in rows)]})
    return {'schema':'heart-h9-m21-5b-derived-lpi-independent-internal-audit-v1',
            'status':'DERIVED_LPI_EXACT_IDENTITIES_RECHECKED_NOT_NATIVE_ATTESTATION',
            'source_file_sha256':digest,'source_file_bytes':byte_count,
            'ledger_binding':ledger_binding,
            'source_script_sha256_claim':data['script_sha256'],
            'source_precision_ledger_sha256_claim':data['precision_ledger_sha256'],
            'source_worker_report_sha256_claim':data['worker_report_sha256'],
            'source_native_core_sha256_claim':data['native_core_sha256'],
            'counts':{'samples':len(samples),'LPI_rows_exactly_rechecked':rows_checked,
                      'same_side_intervals':len(intervals),'interval_feature_exactly_rechecked':identity_count,
                      'full_vs_two_halves_curvature_identities':len(cancellation_checks),
                      'both_line_motion_and_line_denominator_static_rows':direction0},
            'features':per_feature,'intervals':interval_summary,
            'full_half_cancellation_and_curvature':cancellation_checks,
            'limits':{'original_six_native_material_bytes_independently_reopened':False,
                      'source_motion_attachments_independently_reopened':False,
                      'derivative_source_authentication':False,
                      'new_native_source_calls':0,'new_boolean_calls':0,
                      'continuous_neighborhood_certified':False,
                      'root_cause_determined':False,'newton_admitted':False,
                      'final_heart_obj_produced':False}}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--ledger',type=Path,help='Optional original M20 ledger for SHA and material binding')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    require(not args.output.exists(), 'REFUSE_OVERWRITE')
    result=audit(args.input, args.ledger)
    with args.output.open('x',encoding='utf-8') as file:
        json.dump(result,file,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)
        file.write('\n')
    print(result['status'])
    print('source SHA256:',result['source_file_sha256'])
    print('counts:',result['counts'])
    print('Newton admitted:',result['limits']['newton_admitted'])


if __name__=='__main__':main()
