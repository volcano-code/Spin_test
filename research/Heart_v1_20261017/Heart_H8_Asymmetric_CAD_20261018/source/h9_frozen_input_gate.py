"""W3 H9: offline, fail-closed input admission before expensive native execution.

Verifies the immutable failed H8f Actions ZIP, independently recomputes the
conditional interior-edge certificate, and emits the exact four planned q[7]
values. Does NOT perform any Cherchi Boolean call, prove a production smooth
neighborhood, or authorize Newton. Works without compiled native extensions.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path

from certify_h9_interior_edge_crossing import ZIP_SHA, REQUEST_SHA, solve
from probe_h9_crossing_sides_live import native_plan

SCHEMA = 'heart-h9-frozen-input-gate-v1'


class FrozenInputRejected(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise FrozenInputRejected(code)


def file_sha256(path):
    digest = sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_CERTIFICATE_JSON_KEY:' + key)
        result[key] = value
    return result


def finite_json_constant(value):
    raise FrozenInputRejected('NON_FINITE_CERTIFICATE_JSON_CONSTANT:' + value)


def validate_pair(artifact, certificate):
    """Replay historical source and compare certificate before allowing a native attempt."""
    artifact, certificate = Path(artifact), Path(certificate)
    require(artifact.is_file() and 50*1024**2 < artifact.stat().st_size < 90*1024**2,
            'ABSENT_OR_UNEXPECTED_SIZE_H8F_SOURCE_ARCHIVE')
    require(file_sha256(artifact) == ZIP_SHA, 'FROZEN_H8F_ARCHIVE_SHA256_CHANGED')
    require(certificate.is_file() and 200 < certificate.stat().st_size < 1024*1024,
            'ABSENT_OR_UNEXPECTED_SIZE_H9_CERTIFICATE')
    raw = certificate.read_bytes()
    try:
        supplied = json.loads(raw, object_pairs_hook=unique_keys,
                              parse_constant=finite_json_constant)
    except (ValueError, UnicodeDecodeError) as exc:
        raise FrozenInputRejected('MALFORMED_OR_AMBIGUOUS_H9_CERTIFICATE:' + str(exc)) from exc
    require(type(supplied) is dict, 'H9_CERTIFICATE_MUST_BE_AN_OBJECT')
    # The actual H8f material/10-moment evidence must be read and re-derived;
    # comparing an untrusted certificate to a stored hash is insufficient.
    try:
        recalculated = solve(artifact)
    except (KeyError, ValueError, OSError, EOFError, OverflowError) as exc:
        raise FrozenInputRejected('HISTORICAL_CHERCHI_SOURCE_REPLAY_FAILED:' + str(exc)) from exc
    require(supplied == recalculated, 'CERTIFICATE_DOES_NOT_MATCH_REAL_H8F_REPLAY')
    require(recalculated.get('schema') ==
            'heart-h9-native-endpoints-and-conditional-interior-event-v1'
            and recalculated.get('artifact_sha256') == ZIP_SHA
            and recalculated.get('request_sha256') == REQUEST_SHA
            and recalculated.get('historical_run_id') == 39123384402
            and recalculated.get('historical_run_conclusion') == 'failure'
            and recalculated.get('actual_in_between_native_boolean_samples_evaluated') == 0
            and recalculated.get('newton_admitted') is False
            and recalculated.get('native_production_continuity_or_topology_certified') is False,
            'HISTORICAL_FAILURE_OR_RESEARCH_SCOPE_MISREPRESENTED')
    try:
        plan = native_plan(recalculated)
    except (KeyError, ValueError, TypeError) as exc:
        raise FrozenInputRejected('FOUR_NATIVE_SIDE_POINTS_NOT_VALID:' + str(exc)) from exc
    require(len(plan) == 4 and [p.get('side') for p in plan] ==
            ['left-coarse', 'left-near', 'right-near', 'right-coarse']
            and [p.get('expected_proxy_event_sign') for p in plan] == [1,1,-1,-1]
            and all(type(p.get('c7')) is float and math.isfinite(p['c7']) for p in plan)
            and all(plan[i]['c7'] < plan[i+1]['c7'] for i in range(3)),
            'FOUR_REAL_NATIVE_SIDE_PLAN_CHANGED')
    return {
        'schema': SCHEMA,
        'status': 'FROZEN_INPUT_READY_FOR_NATIVE_ATTEMPT_ONLY',
        'source_artifact_sha256': ZIP_SHA,
        'source_artifact_id': 12135528290,
        'historical_run_id': 39123384402,
        'historical_run_conclusion': 'failure',
        'frozen_request_sha256': REQUEST_SHA,
        'exact_certificate_bytes_sha256': sha256(raw).hexdigest(),
        'certificate_recomputed_from_frozen_actual_material': True,
        'all_four_coefficients_are_finite_and_ordered': True,
        'four_new_native_probe_plan': plan,
        'four_new_native_calls_completed_by_this_gate': 0,
        'production_continuous_branch_certified': False,
        'actual_native_boolean_result_available': False,
        'newton_admitted': False,
        'final_heart_obj_produced': False,
    }


def run_inputs(artifact, certificate, output):
    """Immutable output location: write either success or a truthful blocker."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        evidence = validate_pair(artifact, certificate)
    except (FrozenInputRejected, OSError, EOFError, ValueError, TypeError) as exc:
        failure = {
            'schema': 'heart-h9-frozen-input-gate-failure-v1',
            'status': 'BLOCKED_BEFORE_NATIVE_IMPORT_AND_BOOLEAN',
            'error': f'{type(exc).__name__}: {exc}',
            'new_real_native_calls': 0,
            'newton_admitted': False,
        }
        (output / 'failure.json').write_text(json.dumps(failure, indent=2,
                                                         sort_keys=True) + '\n')
        print('H9_FROZEN_INPUT_GATE_REJECTED_NO_NATIVE_CALLS', failure['error'])
        return 2
    (output / 'input_gate.json').write_text(json.dumps(evidence, indent=2,
                                                     sort_keys=True, allow_nan=False) + '\n')
    print('H9_FROZEN_H8F_ARCHIVE_AND_CONDITIONAL_CERTIFICATE_VERIFIED_NO_NEW_NATIVE_CALLS')
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact', required=True, type=Path)
    p.add_argument('--certificate', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a=p.parse_args()
    return run_inputs(a.artifact,a.certificate,a.output)


if __name__ == '__main__':
    raise SystemExit(main())
