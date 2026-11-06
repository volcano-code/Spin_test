#!/usr/bin/env python3
"""Read-only internal review of a W3 M20 precision ledger.

Recomputes secants from the six exact moment vectors stored in the ledger.
It does not re-integrate meshes, authenticate source packets, call Cherchi,
or certify derivatives/Newton. Output must be a new JSON file.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import sys

NAMES = ('mass', 'Mx', 'My', 'Mz', 'Mxx', 'Myy', 'Mzz', 'Myz', 'Mxz', 'Mxy')
STEMS = {
    'left': ('side-00-left-coarse', 'm19-mid-00-left-mid', 'side-01-left-near'),
    'right': ('side-02-right-near', 'm19-mid-01-right-mid', 'side-03-right-coarse'),
}

def reject_constant(value: str):
    raise ValueError('Non-finite JSON constant: ' + value)

def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('Duplicate JSON key: ' + key)
        out[key] = value
    return out

def same_float(a: float, b: float) -> bool:
    return math.isfinite(a) and math.isfinite(b) and struct.pack('!d', a) == struct.pack('!d', b)

def review(path: Path) -> dict:
    if not path.is_file() or not (0 < path.stat().st_size < 32 * 1024 ** 2):
        raise ValueError('Missing or oversized ledger')
    raw = path.read_bytes()
    data = json.loads(raw, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    if data.get('schema') != 'heart-h9-m20-exact-difference-rounding-ledger-v1':
        raise ValueError('Unexpected ledger schema')
    if data.get('saved_materials_reintegrated') != 6 or data.get('newton_admitted') is not False:
        raise ValueError('Unexpected input scope or admission flag')
    packets = data['packets']
    if len(packets) != 6 or len({p['stem'] for p in packets}) != 6:
        raise ValueError('Exactly six unique stored moment packets are required')
    exact = {}
    for packet in packets:
        tokens = packet['exact_ten_moments']
        if len(tokens) != 10 or not all(isinstance(x, str) and len(x) <= 64000 for x in tokens):
            raise ValueError('Invalid bounded exact-moment vector')
        exact[packet['stem']] = [Fraction(x) for x in tokens]
    rows = []
    checks = []
    for side in data['two_sides']:
        name = side['side']
        a, m, b = STEMS[name]
        intervals = [side['full_interval']] + side['two_half_intervals']
        local_rows = []
        for label, (s0, s1), interval in zip(('full', 'half_1', 'half_2'), ((a, b), (a, m), (m, b)), intervals):
            h = Fraction(interval['delta_c7_exact'])
            if h <= 0:
                raise ValueError('Non-positive interval')
            components = interval['components']
            for k, component in enumerate(NAMES):
                recomputed = float((exact[s1][k] - exact[s0][k]) / h)
                recorded = components[component]['exact_surface_secant']
                checks.append({'side': name, 'interval': label, 'component': component,
                               'bitwise_binary64_match': same_float(recomputed, recorded)})
            mz = components['Mzz']
            local_rows.append({
                'interval': label,
                'delta_c7': float(h),
                'max_binary64_scaled_error': interval['max_binary64_scaled_error'],
                'max_exact_surface_scaled_error': interval['max_exact_surface_scaled_error'],
                'worst_exact_surface_component': interval['worst_exact_surface_component'],
                'Mzz_exact_signed_residual': mz['exact_surface_signed_residual'],
                'Mzz_rounded_moment_input_contribution': mz['rounded_moment_input_contribution_signed'],
                'Mzz_arithmetic_contribution': mz['floating_arithmetic_contribution_signed'],
                'Mzz_endpoint_average_J7': mz['saved_jacobian_endpoint_average'],
                'Mzz_residual_relative_to_nonzero_average_J7': (
                    abs(mz['exact_surface_signed_residual']) / abs(mz['saved_jacobian_endpoint_average'])
                    if mz['saved_jacobian_endpoint_average'] != 0 else None),
                'Mzz_moment_space_residual': mz['moment_space_signed_residual'],
                'all_common_scales_one': all(c['common_scale'] == 1 for c in components.values()),
            })
        full = local_rows[0]['max_exact_surface_scaled_error']
        worst_half = max(x['max_exact_surface_scaled_error'] for x in local_rows[1:])
        cancel = side['signed_cancellation_ledger']['Mzz']
        rows.append({
            'side': name,
            'intervals': local_rows,
            'recomputed_worst_half_over_full_exact_error': worst_half / full if full else None,
            'Mzz_signed_cancellation': cancel,
            'Mzz_fraction_cancelled_from_unsigned_weighted_halves': 1 - cancel['weighted_cancellation_fraction'],
            'reported_opposite_residual_sign_components': [k for k, v in side['signed_cancellation_ledger'].items()
                                                           if v['opposite_half_residual_signs']],
        })
    matched = sum(c['bitwise_binary64_match'] for c in checks)
    if matched != 60 or len(checks) != 60:
        raise ValueError(f'Exact secant reproduction mismatch: {matched}/{len(checks)}')
    all_components = [v for s in data['two_sides'] for x in [s['full_interval']] + s['two_half_intervals']
                      for v in x['components'].values()]
    result = {
        'schema': 'w3-m20-uploaded-ledger-internal-review-v1',
        'status': 'SAVED_EXACT_INTEGRAL_SECANTS_REPRODUCED_60_OF_60_NO_NEWTON',
        'source_file_sha256': sha256(raw).hexdigest(),
        'source_script_sha256_as_recorded': data['diagnostic_script_sha256'],
        'recomputed_secant_binary64_matches': matched,
        'recomputed_secant_total': len(checks),
        'reported_rounded_exact_moment_matches': sum(sum(p['moment_binary64_equals_rounded_exact']) for p in packets),
        'reported_exact_residual_decompositions': sum(c['exact_residual_decomposition_verified'] for c in all_components),
        'reported_within_half_ulp_input_bounds': sum(c['observed_moment_rounding_within_half_ulp_bound'] for c in all_components),
        'reported_exact_partition_identities': sum(v['exact_partition_identity_verified'] for s in data['two_sides']
                                                  for v in s['signed_cancellation_ledger'].values()),
        'two_sides': rows,
        'checks': checks,
        'evidence_scope': {
            'exact_moments_from_uploaded_report_used': True,
            'six_original_geometry_packets_read': False,
            'surface_integrals_recomputed_from_vertices_in_this_review': False,
            'original_packet_hashes_independently_authenticated': False,
            'new_native_calls_this_review': 0,
            'continuous_neighborhood_certified': False,
            'asymptotic_order_certified': False,
            'newton_admitted': False,
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite existing output')
    # Limited to this review process, with separately bounded JSON/tokens.
    if hasattr(sys, 'set_int_max_str_digits'):
        sys.set_int_max_str_digits(64000)
    result = review(args.ledger)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(result['status'])
    print('INPUT_SHA256:', result['source_file_sha256'])
    for side in result['two_sides']:
        print(side['side'], 'exact worst_half/full:', side['recomputed_worst_half_over_full_exact_error'])
    print('No original-mesh re-integration, Cherchi call, or Newton approval was performed.')

if __name__ == '__main__':
    main()
