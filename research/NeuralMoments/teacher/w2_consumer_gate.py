"""W2 M10: fail-closed, read-only consumer of archived H8f physical-moment evidence.

This module NEVER publishes a smooth Jacobian or training-ready teacher label.
A matching SHA authenticates this exact frozen snapshot against hardcoded W2/W0
handoff commitments, not against a cryptographic signature or original CAD.
The historical CI conclusion was FAILURE and is intentionally immutable here.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from zipfile import ZipFile

CANDIDATE_SHA256 = 'fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a'
CANDIDATE_BLOB_SHA1 = '213ed8db8e411aaa5c25a6fdd2afb1860c094b39'
ARCHIVE_SHA256 = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REPORT_SHA256 = '28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5'
CLASS_SHA256 = 'f82801aa26d3f4228b8cb68f08abab5ef45458cc2368703e9187e0745662d6c5'
REQUEST_SHA256 = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
SOURCE_SHA = '0bcc187b3005478baa586a6d6f450e73811ca342'
W0_HANDOFF_BLOB_SHA1 = '5f95bdeeb9f6b5bd9156aa796d3b72f9f1649de7'
W0_M9_REPORT_BLOB_SHA1 = '177fe9126d76d94236ecdca2d4750232f78f627a'
RUN_ID = 39123384402
ARTIFACT_ID = 12135528290
CANDIDATE_SCHEMA = 'w2-h8f-81-physical-moment-candidates-v1'
BASELINE = 'BASELINE_ONLY'
STABLE = 'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
CHANGED = 'CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE'
PREFIX = 'artifacts/h8f-all81-points/'
_HEX_SHA = re.compile(r'^[0-9a-f]{64}$')


class GateRejected(ValueError):
    """Fail-closed denial, not a prediction of underlying material invalidity."""


def require(condition, code):
    if not condition:
        raise GateRejected(code)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      allow_nan=False, ensure_ascii=True)


def _check_duplicate_keys(pairs):
    data = {}
    for key, value in pairs:
        require(key not in data, 'DUPLICATE_JSON_KEY:' + key)
        data[key] = value
    return data


def _reject_nonfinite_constant(value):
    raise GateRejected('NONFINITE_JSON_CONSTANT:' + value)


def decode_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_check_duplicate_keys,
                          parse_constant=_reject_nonfinite_constant)
    except (UnicodeDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, GateRejected):
            raise
        raise GateRejected('INVALID_JSON') from exc


def _read(path, *, max_bytes, pinned_sha256=None):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'MISSING_OR_LINKED_EVIDENCE')
    require(path.stat().st_size <= max_bytes, 'OVERSIZED_EVIDENCE')
    raw = path.read_bytes()
    if pinned_sha256 is not None:
        require(sha256(raw) == pinned_sha256, 'UNTRUSTED_CANDIDATE_BYTES_SHA256')
    return raw


def _hash_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _sha(value, name):
    require(type(value) is str and _HEX_SHA.fullmatch(value) is not None,
            'INVALID_SHA256_' + name)
    return value


def _real10(values, name):
    require(type(values) is list and len(values) == 10, 'INVALID_VECTOR10_' + name)
    require(all(type(x) in (int, float) and math.isfinite(x) for x in values),
            'NONFINITE_VECTOR10_' + name)
    return values


def _equal10(actual, expected, name):
    # Strictly compare JSON binary64 values. Never ignore swapped cross terms.
    require(_real10(actual, name) == _real10(expected, name + '_EXPECTED'),
            'MISMATCH_VECTOR10_' + name)


def validate_candidate_structure(record):
    """Scientific structural audit; call review() for pinned-byte provenance."""
    require(type(record) is dict and record.get('schema') == CANDIDATE_SCHEMA,
            'CANDIDATE_SCHEMA_MISMATCH')
    required = ('W0_MomentContractV1_derivative_admission', 'candidate_count',
                'derivative_training_samples', 'evaluated_historical_points',
                'exact_mode', 'exact_reintegrated_count', 'feature_counts',
                'finite_difference', 'formal_smooth_neighborhood_certified',
                'formal_training_samples', 'interpretation',
                'max_exact_r_D_abs_error', 'max_fixed_partition_abs_error',
                'new_native_evaluations', 'newton_converged', 'point60_witness',
                'samples', 'source')
    require(all(key in record for key in required), 'INCOMPLETE_CANDIDATE_ENVELOPE')
    source = record['source']
    require(type(source) is dict and source == {
        'run_id': RUN_ID, 'artifact_id': ARTIFACT_ID,
        'upstream_workflow_conclusion': 'failure',
        'github_head_sha': SOURCE_SHA,
        'archive_sha256': ARCHIVE_SHA256,
        'report_sha256': REPORT_SHA256,
        'classification_sha256': CLASS_SHA256,
        'request_sha256': REQUEST_SHA256,
        'cad_scope': 'H8_RECONSTRUCTED_NOT_AUTHOR_ORIGINAL'},
        'HISTORICAL_SOURCE_IDENTITY_CHANGED')
    require(all(type(record[field]) is int and record[field] == 81 for field in
                ('candidate_count', 'evaluated_historical_points', 'exact_reintegrated_count')),
            'NOT_ALL_81_EXACT_CANDIDATES')
    require(record['exact_mode'] == 'all', 'FOCUS_ONLY_NOT_FULL_EXACT_REFERENCE')
    for field in ('W0_MomentContractV1_derivative_admission',
                  'formal_smooth_neighborhood_certified', 'newton_converged'):
        require(record[field] is False, 'UNSUPPORTED_SCIENTIFIC_PROMOTION:' + field)
    for field in ('derivative_training_samples', 'formal_training_samples',
                  'new_native_evaluations'):
        require(type(record[field]) is int and record[field] == 0,
                'FORGED_TRAINING_OR_NEW_NATIVE_COUNT:' + field)
    require(record['interpretation'] ==
            'HISTORICAL_PHYSICAL_MOMENT_EVIDENCE_ONLY_NO_JACOBIAN_LABEL',
            'UNAUTHORIZED_DATA_SCOPE')
    counts = record['feature_counts']
    require(type(counts) is dict and counts == {STABLE: 79, CHANGED: 1},
            'FEATURE_CLASSIFICATION_COUNTS_DRIFT')
    fd = record['finite_difference']
    require(type(fd) is dict and type(fd.get('checked_stencils')) is int and
            fd['checked_stencils'] == 30 and
            type(fd.get('raw_hash_unstable_stencils')) is int and
            fd['raw_hash_unstable_stencils'] == 9 and
            fd.get('numerical_only_not_smooth_certificate') is True and
            type(fd.get('max_scaled_error')) in (int, float) and
            math.isfinite(fd['max_scaled_error']) and 0 <= fd['max_scaled_error'] < 1e-6,
            'FD_DIAGNOSTIC_MISMATCH')
    require(type(record['max_exact_r_D_abs_error']) in (int,float) and
            record['max_exact_r_D_abs_error'] == 0,
            'INDEPENDENT_EXACT_TEN_MOMENTS_NOT_REPRODUCED')
    fixed_error = record['max_fixed_partition_abs_error']
    require(type(fixed_error) in (int,float) and math.isfinite(fixed_error) and
            0 <= fixed_error < 1e-10, 'FIXED_VARIABLE_SEPARATION_FAILED')
    witness = record['point60_witness']
    require(type(witness) is dict and
            witness.get('sample_indices') == [59,60] and
            witness.get('native_c7') == [1.5e-6,3e-6] and
            witness.get('changed_vertex_indices') == [8043,8044,8045,8046,8047] and
            witness.get('removed_feature_count') ==
            witness.get('added_feature_count') == 2 and
            witness.get('removed_oriented_triangle_count') ==
            witness.get('added_oriented_triangle_count') == 17 and
            witness.get('same_source_faces') is True and
            witness.get('continuous_branch_certified') is False,
            'POINT60_TRUE_FEATURE_CHANGE_WITNESS_LOST')
    rows = record['samples']
    require(type(rows) is list and len(rows) == 81, 'CANDIDATE_SAMPLE_COUNT_MISMATCH')
    all_coefficients = set()
    fixed_baseline = None
    physical_records = []
    for i, row in enumerate(rows):
        require(type(row) is dict and type(row.get('index')) is int and
                row['index'] == i, 'CANDIDATE_SAMPLE_IDENTITY_OR_ORDER_MISMATCH')
        c = _real10(row.get('native_c'), 'NATIVE_C')
        q = _real10(row.get('polynomial_q'), 'POLYNOMIAL_Q')
        require(q == [x*(2 if j>=7 else 1) for j,x in enumerate(c)],
                'C_TO_POLYNOMIAL_Q_CROSS_TERM_MAPPING_CHANGED')
        require(any(x != 0 for x in c), 'ZERO_NATIVE_C')
        coeff_key = tuple(c)
        require(coeff_key not in all_coefficients, 'DUPLICATE_NATIVE_C_SAMPLE')
        all_coefficients.add(coeff_key)
        _real10(row.get('r_D'), 'VARIABLE_R')
        fixed = _real10(row.get('r_F'), 'FIXED_R')
        require(row['r_D'][0] > 0 and fixed[0] >= 0, 'INVALID_POSITIVE_MASS')
        if fixed_baseline is None:
            fixed_baseline = fixed
        else:
            _equal10(fixed, fixed_baseline, 'FROZEN_FIXED_MOMENTS')
        for field in ('same_call_material_gzip_sha256','geometry_hash',
                      'topology_hash','jacobian_attachment_sha256'):
            _sha(row.get(field), field.upper())
        require(row.get('topology_observation') ==
                'VALID_ARCHIVED_FINITE_POINT_NOT_CONTINUUM',
                'INVALID_FINITE_TOPOLOGY_STATUS')
        status = BASELINE if i == 0 else CHANGED if i == 60 else STABLE
        require(row.get('finite_feature_status') == status,
                'POINT60_OR_FINITE_SYMBOLIC_STATUS_FALSIFIED')
        require(row.get('independent_moment_rechecked') is True and
                type(row.get('exact_vs_archived_max_abs_error')) in (int,float) and
                row['exact_vs_archived_max_abs_error'] == 0,
                'SAMPLE_EXACT_TEN_MOMENT_NOT_VERIFIED')
        require(row.get('J_D') is None and
                row.get('derivative_status') == 'UNKNOWN_NOT_CERTIFIED',
                'UNAUTHENTICATED_JACOBIAN_RELEASE_ATTEMPT')
        require(row.get('split') == 'excluded' and
                row.get('training_admitted') is False,
                'TRAINING_SPLIT_PROMOTION_FORBIDDEN')
        physical_records.append((i, row['same_call_material_gzip_sha256']))
    require(rows[59]['native_c'][7] == witness['native_c7'][0] and
            rows[60]['native_c'][7] == witness['native_c7'][1],
            'POINT60_C7_WITNESS_NOT_ATTACHED_TO_SAMPLES')
    ledger = sha256(canonical(physical_records).encode('utf-8'))
    return {'rows': len(rows), 'native_coefficients_unique': len(all_coefficients),
            'exact_physical_ten_moment_components': 810,
            'fixed_moments_frozen': True, 'point60_feature_change': True,
            'material_archive_sha_ledger_sha256': ledger,
            'w0_continuous_derivative_neighborhood_certified': False,
            'newton_terminal_certified': False}


def validate_manifest(manifest, candidate):
    require(type(manifest) is dict and type(manifest.get('m9_real_h8f_81_evidence')) is dict,
            'MISSING_W2_M9_MANIFEST_HANDOFF')
    m = manifest['m9_real_h8f_81_evidence']
    fields = {'schema':'w2-h8f-81-physical-moment-candidates-v1',
              'workflow_run_id':RUN_ID, 'original_workflow_conclusion':'failure',
              'original_head_sha':SOURCE_SHA, 'archive_artifact_id':ARTIFACT_ID,
              'archive_sha256':ARCHIVE_SHA256, 'archive_report_sha256':REPORT_SHA256,
              'archive_classification_sha256':CLASS_SHA256,
              'frozen_request_sha256':REQUEST_SHA256,
              'candidate_index_sha256':CANDIDATE_SHA256,
              'candidate_index_git_blob_sha1':CANDIDATE_BLOB_SHA1,
              'W0_M9_report_blob_sha1':W0_M9_REPORT_BLOB_SHA1,
              'w0_handoff_document_blob_sha1':W0_HANDOFF_BLOB_SHA1,
              'original_native_evaluations':81,
              'new_native_evaluations':0,
              'independently_reintegrated_materials':81,
              'independently_reintegrated_ten_moment_components':810,
              'training_admitted':0,
              'newton_solved':False,
              'certified_continuous_neighborhood':False,
              'derivative_J_D_published':False}
    for key, value in fields.items():
        require(m.get(key) == value and type(m.get(key)) is type(value),
                'MANIFEST_UNTRUSTED_M9_' + key.upper())
    require(manifest.get('schema') == 'w2-cherchi-teacher-v2-pre-w0',
            'MANIFEST_SCHEMA_CHANGED')
    require(manifest.get('label_convention',{}).get('w0_verifier_integrated') is False,
            'MANIFEST_FALSE_W0_VERIFIER_INTEGRATION')
    require(m.get('finite_symbolic_classifications') ==
            {'STABLE_NOT_CERTIFIED':79,'FEATURE_CHANGE':1},
            'MANIFEST_FINITE_FEATURE_CLASSIFICATION_CHANGED')
    w = m.get('point60')
    require(type(w) is dict and
            w.get('changed_vertex_positions') == [8043,8044,8045,8046,8047] and
            w.get('removed_LPI_features') == w.get('added_LPI_features') == 2 and
            w.get('removed_oriented_triangles') == w.get('added_oriented_triangles') == 17 and
            w.get('c7_from') == 1.5e-6 and w.get('c7_to') == 3e-6,
            'MANIFEST_POINT60_CONSTRUCTION_CHANGE_LOST')
    require(m.get('candidate_index_path') ==
            'research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json',
            'MANIFEST_CANDIDATE_PATH_CHANGED')
    require(manifest.get('training_samples') == 0 and
            manifest.get('local_native_calls') == 0 and
            manifest.get('native_teacher_runs') == 0,
            'MANIFEST_FORGED_NATIVE_OR_TRAINING_PROGRESS')
    splits = manifest.get('data_splits')
    require(type(splits) is dict and all(not splits.get(s) for s in ('train','val','test')),
            'MANIFEST_TRAINING_SPLIT_FORBIDDEN')
    excluded = splits.get('excluded')
    require(type(excluded) is list and any(
        type(entry) is dict and entry.get('count') == 81 and
        entry.get('path') ==
        'research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json'
        for entry in excluded), 'MANIFEST_MISSING_81_EXCLUSION')
    require(candidate['source']['archive_sha256'] == m['archive_sha256'],
            'MANIFEST_ARCHIVE_SOURCE_DISAGREEMENT')
    return {'m9_source_manifest_consistent': True,
            'w0_m9_observed_handoff_git_blob_sha1':W0_HANDOFF_BLOB_SHA1,
            'w0_formal_verifier_integrated_into_w2':False}


def _read_zip_member(z, name, max_bytes):
    try:
        entry = z.getinfo(name)
    except KeyError as exc:
        raise GateRejected('MISSING_HISTORICAL_ARCHIVE_MEMBER:' + name) from exc
    require(entry.file_size <= max_bytes and entry.compress_size <= max_bytes,
            'HISTORICAL_ARCHIVE_MEMBER_TOO_LARGE:' + name)
    return z.read(entry)


def verify_original_archive(archive_path, rows):
    """Rebind all 81 compressed real materials; no native calls or new exact sums."""
    path = Path(archive_path)
    require(path.is_file() and not path.is_symlink(), 'MISSING_OR_LINKED_ORIGINAL_ARCHIVE')
    require(_hash_file(path) == ARCHIVE_SHA256, 'HISTORICAL_NATIVE_ARCHIVE_SHA256_MISMATCH')
    max_add = 0.0
    with ZipFile(path) as z:
        require(len(z.namelist()) == 183 and len(set(z.namelist())) == 183,
                'HISTORICAL_ARCHIVE_FILE_SET_UNEXPECTED')
        report_raw = _read_zip_member(z, PREFIX+'report.json', 500000)
        class_raw = _read_zip_member(z, 'artifacts/h8f-81-exact-construction-classification.json', 2000000)
        request_raw = _read_zip_member(z, 'artifacts/h8-request/prepared-request.json', 10000000)
        require(sha256(report_raw) == REPORT_SHA256 and sha256(class_raw) == CLASS_SHA256 and
                sha256(request_raw) == REQUEST_SHA256,'HISTORICAL_EMBEDDED_PROVENANCE_SHA256_MISMATCH')
        report = decode_json(report_raw)
        cls = decode_json(class_raw)
        require(report.get('completed_samples') == 81 and
                report.get('complete_eighty_one_samples') is False and
                report.get('qualified_branch_neighborhood') is False and
                report.get('formal_newton_converged') is False and
                report.get('all_tested_stencils_same_feature_hash') is False,
                'HISTORICAL_FAILURE_FLAGS_CHANGED')
        require(cls.get('classifications') == {STABLE:79, CHANGED:1} and
                cls.get('certified_smooth_neighborhood') is False,
                'HISTORICAL_CONSTRUCTION_CLASSIFICATION_CHANGED')
        for i, row in enumerate(rows):
            prefix = PREFIX + f'point-{i:03d}'
            point_raw = _read_zip_member(z, prefix + '.json', 200000)
            gzip_bytes = _read_zip_member(z, prefix + '-material.json.gz', 5000000)
            point = decode_json(point_raw)
            require(sha256(gzip_bytes) == row['same_call_material_gzip_sha256'] ==
                    point.get('exact_same_call_material_archive_sha256'),
                    'PER_SAMPLE_REAL_MATERIAL_SHA256_MISMATCH')
            try:
                raw = gzip.decompress(gzip_bytes)
            except (EOFError, OSError) as exc:
                raise GateRejected('ARCHIVED_MATERIAL_DECOMPRESSION_FAILED') from exc
            require(len(raw) <= 20_000_000, 'OVERSIZED_DECOMPRESSED_MATERIAL')
            material = decode_json(raw)
            require(type(point.get('index')) is int and point['index'] == i,
                    'ARCHIVED_POINT_INDEX_INCONSISTENT')
            _equal10(point.get('coefficients'), row['native_c'], 'ARCHIVED_NATIVE_C')
            _equal10(material.get('quadric_coefficients'), row['native_c'], 'ATTACHED_NATIVE_C')
            _equal10(material.get('variable_raw_moments'), row['r_D'], 'ATTACHED_VARIABLE_R')
            require(material.get('geometry_hash') == row['geometry_hash'] and
                    material.get('topology_hash') == row['topology_hash'],
                    'ATTACHED_GEOMETRY_TOPOLOGY_IDENTITY_DRIFT')
            J = material.get('moment_jacobian')
            require(type(J) is list and len(J) == 10 and
                    all(type(q) is list and len(q) == 10 and
                        all(type(x) in (float,int) and math.isfinite(x) for x in q)
                        for q in J), 'INVALID_ARCHIVED_10X10_JACOBIAN')
            require(sha256(canonical(J).encode('utf-8')) ==
                    row['jacobian_attachment_sha256'],
                    'ARCHIVED_JACOBIAN_DIGEST_MISMATCH')
            _equal10(material.get('raw_moments'), point.get('full_raw_moments'),
                     'ARCHIVED_TOTAL_R')
            total = material['raw_moments']
            difference = max(abs(total[k]-row['r_D'][k]-row['r_F'][k]) for k in range(10))
            max_add = max(max_add, difference)
            require(difference <= 1e-10,'ARCHIVED_FIXED_DOUBLE_COUNT_MISMATCH')
    return {'archive_gzip_sha_verified':True,'archived_materials_rebound':81,
            'jacobian_digests_rebound_without_releasing_values':81,
            'maximum_fixed_plus_variable_disagreement':max_add,
            'original_workflow_conclusion':'failure'}


def review(candidate_path, manifest_path, *, archive_path=None):
    candidate_raw = _read(candidate_path, max_bytes=500_000,
                          pinned_sha256=CANDIDATE_SHA256)
    candidate = decode_json(candidate_raw)
    summary = validate_candidate_structure(candidate)
    manifest = decode_json(_read(manifest_path, max_bytes=100_000))
    manifest_summary = validate_manifest(manifest, candidate)
    archive_status = ({'archive_gzip_sha_verified':False,'archived_materials_rebound':0,
                       'jacobian_digests_rebound_without_releasing_values':0}
                      if archive_path is None else
                      verify_original_archive(archive_path,candidate['samples']))
    return {'schema':'w2-m10-consumer-readonly-gate-v1',
            'status':('ARCHIVED_81_MATERIALS_REBOUND_DERIVATIVES_BLOCKED'
                      if archive_path is not None else
                      'PINNED_M9_INDEX_ONLY_DERIVATIVES_BLOCKED'),
            'source':{'github_run_id':RUN_ID,'artifact_id':ARTIFACT_ID,
                      'original_workflow_conclusion':'failure',
                      'frozen_source_commit_sha':SOURCE_SHA,
                      'candidate_file_sha256':CANDIDATE_SHA256,
                      'candidate_git_blob_sha1':CANDIDATE_BLOB_SHA1,
                      'original_artifact_zip_sha256':ARCHIVE_SHA256},
            'coverage':summary, 'manifest':manifest_summary,
            'archive_binding':archive_status,
            'certifications':{'physical_moments_numerically_reproduced':True,
                             'full_continuous_neighborhood':False,
                             'native_newton_terminal':False,
                             'independent_CAD_origin':False,
                             'w0_verified_derivative_J_D':False,
                             'w3_point60_event_resolved':False},
            'allowed_use':'READ_ONLY_FINITE_POINT_PHYSICAL_MOMENT_AUDIT',
            'training_admitted':False,'training_samples':0,
            'derivative_J_D':None,'training_export':None,
            'no_implicit_w0_or_w3_promotion':True}


def export_training(*args, **kwargs):
    """Explicitly unavailable until separately verified W0/W3 native proof."""
    raise GateRejected('DERIVATIVE_TRAINING_RELEASE_DENIED_W0_W3_PROOF_NOT_INTEGRATED')


def _write_exclusive(path, data):
    path = Path(path)
    require(path.parent.is_dir(), 'MISSING_OUTPUT_DIRECTORY')
    require(not os.path.lexists(path), 'REFUSE_OVERWRITE_SCIENTIFIC_EVIDENCE')
    payload = (json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf8')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', prefix='.'+path.name+'.',
                                         suffix='.partial',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
        fd=os.open(path.parent,os.O_RDONLY | getattr(os,'O_DIRECTORY',0))
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--manifest',required=True)
    parser.add_argument('--archive')
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        result=review(args.candidate,args.manifest,archive_path=args.archive)
        exit_code=0
    except (GateRejected, FileNotFoundError) as exc:
        result={'schema':'w2-m10-consumer-readonly-gate-v1',
                'status':'REJECTED','error':type(exc).__name__+': '+str(exc),
                'training_admitted':False,'training_samples':0,
                'derivative_J_D':None,'training_export':None}
        exit_code=2
    _write_exclusive(args.output,result)
    print(json.dumps({'status':result['status'], 'training_admitted':False,
                      'archive_rebound':result.get('archive_binding',{}).get('archived_materials_rebound',0)},
                     sort_keys=True))
    return exit_code


if __name__=='__main__':
    raise SystemExit(main())
