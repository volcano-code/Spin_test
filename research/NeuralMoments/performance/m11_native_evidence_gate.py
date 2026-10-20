"""W1 M11: independent *receipt* and material-snapshot gate after M5/M9.

A valid receipt is NOT proof that a machine executed Cherchi by itself: it
requires M10's actual imported ELF/CPython-extension preflight and separate
real execution. No geometry check is removed, and no full Newton is claimed.
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import io
import json
import math
from pathlib import Path
from statistics import median

from m5_native_call_instrumentation import ARCHIVE_SHA, REQUEST_SHA, SOURCE_BLOB, AUDIT_TRUE
from m9_native_abba_gate import ORDER, CHERCHI_ID, certify_abba
from m10_native_host_runner import NATIVE

MAX_JSON_BYTES = 18_000_000
MAX_MATERIAL_BYTES = 32_000_000
MAX_SECONDS = 3600


def reject(reason):
    raise ValueError('M11_' + reason)


def _json_bytes(raw):
    # Duplicate keys or NaN/Infinity are not valid evidence.
    def unique_pairs(pairs):
        d = {}
        for k, v in pairs:
            if k in d: reject('DUPLICATE_JSON_KEY')
            d[k] = v
        return d
    def invalid_constant(s): reject('NONFINITE_JSON:' + s)
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=invalid_constant)


def _load(path, limit=MAX_JSON_BYTES):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= limit:
        reject('MISSING_OR_OVERSIZED_JSON:' + path.name)
    return _json_bytes(path.read_bytes())


def _decompress(path):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= MAX_MATERIAL_BYTES:
        reject('MISSING_OR_OVERSIZED_MATERIAL:' + path.name)
    with gzip.open(path, 'rb') as stream:
        data = stream.read(MAX_MATERIAL_BYTES + 1)
        if len(data) > MAX_MATERIAL_BYTES or stream.read(1):
            reject('MATERIAL_DECOMPRESS_LIMIT')
    return data


def _sha(data): return sha256(data).hexdigest()


def _ten(value):
    return type(value) is list and len(value) == 10 and all(
        type(x) in (int, float) and math.isfinite(x) for x in value)


def _jac(value): return type(value) is list and len(value) == 10 and all(_ten(row) for row in value)


def _positive_int(value): return type(value) is int and value > 0


def _flags(value):
    return type(value) is dict and set(value) == set(AUDIT_TRUE) and all(
        value[k] is True for k in AUDIT_TRUE)


def _ledger(record, *, require_boolean=True):
    if not isinstance(record, dict) or record.get('all_returned') is not True:
        reject('LEDGER_DID_NOT_RETURN')
    rows = record.get('exclusive_stages')
    if not type(rows) is list or not rows:
        reject('EMPTY_LEDGER')
    elapsed = record.get('wall_ns')
    exclusive = record.get('exclusive_ns')
    unattributed = record.get('unattributed_ns')
    if any(type(x) is not int or x < 0 for x in (elapsed, exclusive, unattributed)):
        reject('INVALID_LEDGER_CLOCK')
    if elapsed == 0 or exclusive + unattributed != elapsed:
        reject('LEDGER_DOES_NOT_CLOSE')
    names = []
    for row in rows:
        if row.get('status') != 'PASS' or type(row.get('exclusive_ns')) is not int or \
                type(row.get('inclusive_ns')) is not int or \
                not 0 <= row['exclusive_ns'] <= row['inclusive_ns']:
            reject('BAD_STAGE_RECORD')
        names.append(row.get('name'))
    if sum(row['exclusive_ns'] for row in rows) != exclusive:
        reject('STAGE_SUM_MISMATCH')
    if require_boolean and 'native:boolean' not in names:
        reject('NO_MEASURED_CHERCHI_BOOLEAN')
    if elapsed > MAX_SECONDS * 1_000_000_000:
        reject('JOB_WALL_LIMIT_EXCEEDED')
    if record.get('stage_exclusive_totals_ns') is not None:
        aggregates = {}
        for row in rows:
            aggregates[row['name']] = aggregates.get(row['name'], 0) + row['exclusive_ns']
        if record['stage_exclusive_totals_ns'] != aggregates:
            reject('STAGE_AGGREGATE_DRIFT')
    return len(rows)



# Tie reported performance windows to the actual mutually exclusive M5/M9
# timing spans.  A forged ratio can otherwise survive a self-consistent edit
# to M9's summary and point JSON while leaving the source time ledger intact.
# Every native audit is part of the recorded cost, not an optional fast path.
_M5_AUDITS = frozenset((
    'audit:same_call_material', 'audit:native_exact_rational_boundary',
    'audit:independent_fraction_ten', 'audit:complete_material_snapshot'))
_M9_AUDITS = frozenset((
    'audit:same_call_material', 'audit:native_exact_rational_boundary',
    'audit:independent_fraction_ten', 'audit:exact_material_serialization'))


def _required_spans(ledger, required, *, context):
    names = [row['name'] for row in ledger['exclusive_stages']]
    for name in required | {'native:boolean'}:
        if names.count(name) != 1:
            reject(context + '_REQUIRED_STAGE_MISSING_OR_REPEATED:' + name)
    for name in names:
        if (not isinstance(name, str) or not name.startswith(('python:', 'native:', 'audit:'))):
            reject(context + '_UNKNOWN_STAGE:' + str(name))
    eval_only = sum(row['exclusive_ns'] for row in ledger['exclusive_stages']
                    if row['name'].startswith(('native:', 'python:')))
    checks_only = sum(row['exclusive_ns'] for row in ledger['exclusive_stages']
                      if row['name'].startswith('audit:'))
    return eval_only, checks_only


def _bind_m5_timing(m5):
    """All measured stages fit in the single original evaluation+audit window."""
    profile = m5['profiler']
    sample = m5.get('sample_and_validation_wall_ns')
    if (type(sample) is not int or sample <= 0 or
            sample > profile['wall_ns']):
        reject('M5_SAMPLE_AND_VALIDATION_WALL_UNBOUND')
    evaluation, checks = _required_spans(profile, _M5_AUDITS, context='M5')
    if evaluation + checks > sample:
        reject('M5_STAGES_EXCEED_MEASURED_SAMPLE')
    return sample


def _bind_m9_timing(row):
    """The saved ABBA wall must literally equal that call's stage-ledger wall."""
    ledger = row['stage_ledger']
    wall = row.get('complete_validation_ns')
    evaluation_wall = row.get('eval_wall_ns')
    if (type(wall) is not int or type(evaluation_wall) is not int or
            wall != ledger.get('wall_ns') or
            evaluation_wall <= 0 or evaluation_wall > wall):
        reject('M9_COMPLETE_WALL_LEDGER_MISMATCH')
    evaluation, checks = _required_spans(ledger, _M9_AUDITS, context='M9')
    if evaluation > evaluation_wall:
        reject('M9_EVALUATION_SPANS_EXCEED_EVAL_WALL')
    if checks > wall - evaluation_wall:
        reject('M9_AUDITS_EXCEED_VALIDATION_WALL')
    return wall


def _module_receipt(preflight):
    if (preflight.get('schema') != 'w1-m10-native-host-preflight-v1' or
            preflight.get('state') != 'READY_FOR_REAL_NATIVE_ABBA' or
            preflight.get('blockers') or
            preflight.get('checks', {}).get('native_abi_import', {}).get('status') != 'PASS' or
            preflight.get('checks', {}).get('git', {}).get('status') != 'PASS' or
            preflight.get('checks', {}).get('source', {}).get('status') != 'PASS' or
            preflight.get('checks', {}).get('archive', {}).get('status') != 'PASS' or
            preflight.get('checks', {}).get('memory', {}).get('status') != 'PASS' or
            preflight.get('checks', {}).get('swap_disabled', {}).get('status') != 'PASS'):
        reject('REAL_M10_PREFLIGHT_REQUIRED')
    inventory = preflight['checks'].get('native_modules', {})
    if inventory.get('status') != 'PASS': reject('NATIVE_MODULES_NOT_ADMITTED')
    modules = inventory.get('modules')
    if type(modules) is not dict or set(modules) != set(NATIVE):
        reject('MISSING_MODULE_IDENTITY')
    sha = {}
    for name in NATIVE:
        item = modules[name]
        path = Path(item.get('path', '/nonexistent'))
        if (item.get('status') != 'FOUND' or not path.is_file() or
                item.get('bytes') != path.stat().st_size or
                item.get('sha256') != _sha(path.read_bytes())):
            reject('MODULE_BINARY_MISMATCH:' + name)
        sha[name] = item['sha256']
    if preflight.get('checks', {}).get('archive', {}).get('details', {}).get('zip_sha256') != ARCHIVE_SHA:
        reject('ARCHIVE_IDENTITY_DRIFT')
    return sha


def _material(raw, q, geometry_hash, topology_hash, source_id, ten, jac, backend):
    material = _json_bytes(raw)
    proof = material.get('material_proof')
    if (not isinstance(proof,dict) or
            any(not isinstance(proof.get(field),list) or len(proof[field]) != 8455
                for field in ('exact_vertices','construction_records','resolved_construction_records'))):
        reject('MATERIAL_EXACT_CONSTRUCTION_PROOF_INCOMPLETE')
    from hashlib import sha256
    def identity(obj):
        return sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),
                                 allow_nan=False).encode()).hexdigest()
    actual_geometry = identity(dict(vertices=proof['exact_vertices'],
                                    faces=material.get('variable_faces')))
    actual_source = identity(dict(vertices=material.get('quadric_source_vertices'),
                                  faces=material.get('quadric_source_faces'),
                                  coefficients=material.get('quadric_coefficients')))
    if actual_geometry != geometry_hash or actual_source != source_id:
        reject('MATERIAL_RECOMPUTED_SOURCE_OR_GEOMETRY_DIGEST_DRIFT')
    if (material.get('quadric_coefficients') != q or
            material.get('geometry_hash') != geometry_hash or
            material.get('topology_hash') != topology_hash or
            material.get('quadric_source_identity') != source_id or
            material.get('boolean_backend_identity') != backend or
            material.get('variable_raw_moments') != ten or
            material.get('moment_jacobian') != jac or
            not _ten(material.get('raw_moments')) or
            proof.get('schema') != 'cherchi-same-call-material-v1' or
            len(material.get('variable_rational_vertices', [])) != 8455 or
            len(material.get('variable_faces', [])) != 16910):
        reject('FULL_SNAPSHOT_SCIENTIFIC_DRIFT')
    if any(not isinstance(row, list) or len(row) != 3 for row in material['variable_rational_vertices']):
        reject('RATIONAL_VERTEX_SHAPE')
    # Not a new exact self-intersection proof; the native runner must have
    # independently executed the audit before recording the passed flags.
    return material


def verify(m10_preflight, m5_dir, m9_dir):
    """Validate all results and artifacts, or raise; never infer full solver speed."""
    pre = _load(m10_preflight)
    modules = _module_receipt(pre)
    m5_dir, m9_dir = Path(m5_dir), Path(m9_dir)
    m5 = _load(m5_dir/'baseline-performance.json')
    m9 = _load(m9_dir/'baseline-performance.json')
    if (m5.get('schema') != 'w1-m5-native-h8-instrumented-sample-v1' or
            m5.get('scope') != 'FRESH_H8_RECONSTRUCTED_SINGLE_Q_NOT_FULL_SOLVER' or
            m5.get('fresh_boolean_calls') != 1 or m5.get('full_solver_measured') is not False or
            m5.get('paper_speed_qualified') is not False or
            m5.get('input_request_sha256') != REQUEST_SHA or
            m5.get('archive_sha256') != ARCHIVE_SHA or
            m5.get('source_git_blob') != SOURCE_BLOB or
            m5.get('native_binary_sha256') != modules['_make_it_stand'] or
            m5.get('cherchi_binary_sha256') != modules['_cherchi_core_boolean'] or
            m5.get('gmp_binary_sha256') != modules['_cherchi_rational_moments'] or
            m5.get('material_vertices') != 8455 or m5.get('material_faces') != 16910 or
            m5.get('ten_moment_max_scaled_error', 1) > 1e-10 or
            not _flags(m5.get('all_boundary_proof_flags')) or
            m5.get('jacobian_shape') != [10, 10] or
            not _ten(m5.get('q'))):
        reject('M5_SCOPE_OR_PROOF_MISMATCH')
    _ledger(m5.get('profiler'))
    _bind_m5_timing(m5)
    m5_raw = _decompress(m5_dir/'same-call-material.json.gz')
    m5_material = _json_bytes(m5_raw)
    _material(m5_raw, m5['q'],m5['geometry_hash'],m5['topology_hash'],
              m5_material.get('quadric_source_identity'),
              m5_material.get('variable_raw_moments'),
              m5_material.get('moment_jacobian'),
              m5_material.get('boolean_backend_identity'))
    if (m5_material.get('geometry_hash') != m5['geometry_hash'] or
            m5_material.get('topology_hash') != m5['topology_hash'] or
            m5_material.get('quadric_coefficients') != m5['q'] or
            not _ten(m5_material.get('variable_raw_moments')) or
            not _jac(m5_material.get('moment_jacobian'))):
        reject('M5_SNAPSHOT_REPORT_DRIFT')

    if (m9.get('schema') != 'w1-m9-native-h8c-abba-v1' or
            m9.get('scope') != 'FOUR_REAL_H8C_SINGLE_Q_CHERCHI_MATERIALS_NOT_FULL_NEWTON' or
            m9.get('native_cherchi_calls') != 4 or
            m9.get('real_newton_solves') != 0 or
            m9.get('full_solver_speedup') is not None or
            m9.get('paper_speed_qualified') is not False or
            m9.get('archive_sha256') != ARCHIVE_SHA or
            m9.get('request_sha256') != REQUEST_SHA or
            m9.get('production_source_blob') != SOURCE_BLOB or
            m9.get('order') != list(ORDER) and m9.get('order') != ORDER or
            m9.get('module_binary_sha256') != {
                'native_sha256': modules['_make_it_stand'],
                'cherchi_sha256': modules['_cherchi_core_boolean'],
                'gmp_sha256': modules['_cherchi_rational_moments']}):
        reject('M9_SCOPE_OR_MODULE_MISMATCH')
    rows = m9.get('measurements')
    if not isinstance(rows, list) or len(rows) != 4:
        reject('M9_FOUR_ROWS_REQUIRED')
    independent = certify_abba(rows)
    if m9.get('parity_and_timing') != independent:
        reject('M9_REPORTED_ABBA_RATIO_DRIFT')
    if m9.get('candidate_parser_caches_by_call') is None or len(m9['candidate_parser_caches_by_call']) != 2:
        reject('M9_NO_PER_CALL_CACHE_RECEIPTS')
    for i, row in enumerate(rows):
        if row.get('iteration') != i:
            reject('M9_SAMPLE_INDEX_DRIFT')
        _ledger(row.get('stage_ledger'))
        _bind_m9_timing(row)
        if not _flags(row.get('boundary_flags')):
            reject('M9_MISSING_NATIVE_AUDIT_FLAGS')
        if type(row.get('eval_wall_ns')) is not int or not _positive_int(row['eval_wall_ns']):
            reject('M9_BAD_EVAL_WALL')
        if row['eval_wall_ns'] > row.get('complete_validation_ns', 0):
            reject('M9_EVAL_EXCEEDS_COMPLETE_WALL')
        expected = _load(m9_dir/f'point-{i:03d}-{row["mode"]}.json')
        if expected != row:
            reject('M9_POINT_REPORT_MUTATION')
        material_bytes = _decompress(m9_dir/f'point-{i:03d}-{row["mode"]}.json.gz')
        if _sha(material_bytes) != row.get('material_sha256'):
            reject('M9_SERIALIZED_PACKET_SHA_DRIFT')
        _material(material_bytes, row['q'],row['geometry_hash'],row['topology_hash'],
                  row['source_identity'],row['ten'],row['jacobian'],row['backend_identity'])
        if (row['native_sha256'] != modules['_make_it_stand'] or
                row['cherchi_sha256'] != modules['_cherchi_core_boolean'] or
                row['gmp_sha256'] != modules['_cherchi_rational_moments']):
            reject('M9_POINT_BINARY_DRIFT')
    if _sha(m5_raw) != rows[0]['material_sha256']:
        reject('M5_M9_COMPLETE_MATERIAL_BYTES_NOT_EQUAL')
    if (m5_material['quadric_coefficients'] != rows[0]['q'] or
            m5_material['variable_raw_moments'] != rows[0]['ten'] or
            m5_material['moment_jacobian'] != rows[0]['jacobian'] or
            m5_material['geometry_hash'] != rows[0]['geometry_hash'] or
            m5_material['topology_hash'] != rows[0]['topology_hash'] or
            m5_material['quadric_source_identity'] != rows[0]['source_identity'] or
            m5_material['boolean_backend_identity'] != rows[0]['backend_identity']):
        reject('M5_M9_CROSS_RUN_MOMENTS_JACOBIAN_OR_GEOMETRY_DRIFT')
    return dict(schema='w1-m11-independent-native-receipt-admission-v1',
                scope='FIVE_PINNED_SAME_Q_EVALUATION_RECEIPTS_ONLY_NOT_FULL_NEWTON',
                native_imports_attested_by_m10=True,
                complete_native_ledger_rows=5,
                m5_material_json_sha256=_sha(m5_raw),
                m9_all_material_sha256=[row['material_sha256'] for row in rows],
                independent_material_jacobian_and_ten_receipts_match=True,
                all_native_boundary_pass_flags_present=True,
                reproduced_abba_single_q_ratio=independent['single_q_evaluator_old_over_candidate'],
                fresh_native_execution_independently_proven_by_receipt_alone=False,
                full_solver_speedup=None, newton_terminal_verified=False,
                w0_w2_production_admitted=False,paper_speed_qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preflight',required=True,type=Path)
    p.add_argument('--m5-dir',required=True,type=Path)
    p.add_argument('--m9-dir',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if a.output.exists(): raise FileExistsError('M11_OUTPUT_EXISTS')
    try:
        result=verify(a.preflight,a.m5_dir,a.m9_dir)
    except Exception as error:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.with_suffix('.failure.json').write_text(json.dumps(
            dict(status='FAILED_CLOSED',error=f'{type(error).__name__}: {error}',
                 full_solver_speedup=None))+'\n')
        raise
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps(dict(status='CERTIFIED_RECEIPTS_ONLY_NOT_FULL_NEWTON')))


if __name__=='__main__': main()
