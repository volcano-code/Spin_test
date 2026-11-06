"""Compare the historical H8f point-000 boundary with the frozen M21 Heart evidence.

Run in the W2 teacher directory (or place it on PYTHONPATH):
    python m22_recover_h8f_point0.py --pilot-dir RUN_DIR --historical FILE
FILE is the pinned H8f ZIP or its original point-000-material.json.gz member.
Exit 0: full canonical material and exact boundary match. Exit 3: boundary only.
Exit 2: conflicting or invalid evidence. No native evaluation or training release.
"""
import argparse
from fractions import Fraction
import gzip
import json
from pathlib import Path
import sys
from zipfile import BadZipFile, is_zipfile, ZipFile

from independent_reference import integrate_exact_boundary
from m16_native_acceptance import file_hash, h256, HEART_ARTIFACT_SHA, strict_json
from m22_audit_heart_label import audit, RECEIPT, require
from native_cherchi_teacher import digest

TEACHER = RECEIPT.parent
MEMBER = 'artifacts/h8f-all81-points/point-000-material.json.gz'
LEDGER_SHA = 'fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a'


def read_material(path, gzip_sha, archive_sha):
    if is_zipfile(path):
        require(file_hash(path) == archive_sha, 'H8F_ARCHIVE_SHA_MISMATCH')
        with ZipFile(path) as archive:
            require(archive.namelist().count(MEMBER) == 1, 'POINT000_MEMBER_COUNT_MISMATCH')
            raw = archive.read(MEMBER)
    else:
        raw = path.read_bytes()
    require(h256(raw) == gzip_sha, 'POINT000_GZIP_SHA_MISMATCH')
    return strict_json(gzip.decompress(raw))


def compare_material(material, row, payload):
    proof = payload['exact_proof']
    require(row['index'] == 0 and row['split'] == 'excluded'
            and row['training_admitted'] is False and row['J_D'] is None, 'INVALID_M9_POINT000')
    for key in ('geometry_hash', 'topology_hash'):
        require(material[key] == row[key] == proof[key], 'IDENTITY_MISMATCH:' + key)
    for key, source in (('native_c', 'quadric_coefficients'), ('r_D', 'variable_raw_moments')):
        require(digest(material[source]) == digest(row[key]) == digest(payload[key]),
                'VALUE_MISMATCH:' + key)
    require(digest(row['r_F']) == digest(payload['r_F']), 'VALUE_MISMATCH:r_F')

    moments, boundary = integrate_exact_boundary(material['variable_rational_vertices'],
                                                  material['variable_faces'], payload['density'])
    ref = proof['independent_ten_moment_audit']
    expected_moments = [Fraction(x) for x in ref['reference_raw_moments_exact']]
    require(len(moments) == len(expected_moments) == 10, 'TEN_COMPONENTS_REQUIRED')
    errors = [abs(a-b) for a, b in zip(moments, expected_moments)]
    boundary_match = (not any(errors) and all(boundary[k] == ref[k]
                      for k in ('exact_boundary_sha256', 'vertex_count', 'face_count')))
    historical_digest = digest(material)
    expected_digest = proof['same_call_attachment']['serialized_material_sha256']
    full_match = historical_digest == expected_digest
    if not boundary_match:
        status = 'REJECTED_BOUNDARY_CONFLICT'
    elif full_match:
        status = 'FULL_CANONICAL_MATERIAL_MATCH'
    else:
        status = 'BOUNDARY_ONLY'
    return {
        'status': status, 'boundary_matched': boundary_match,
        'full_canonical_material_matched': full_match,
        'historical_material_sha256': historical_digest, 'm21_material_sha256': expected_digest,
        'historical_exact_boundary_sha256': boundary['exact_boundary_sha256'],
        'm21_exact_boundary_sha256': ref['exact_boundary_sha256'],
        'vertices': boundary['vertex_count'], 'faces': boundary['face_count'],
        'exact_moments_matched': sum(e == 0 for e in errors),
        'max_exact_absolute_difference': str(max(errors)),
        'historical_process_identity_certified': False, 'continuity_certified': False,
        'solid_validity_certified': False, 'new_native_calls': 0,
        'split': 'excluded', 'J_D': None, 'training_admitted': False,
    }


def recover(pilot_dir, historical):
    files = strict_json((TEACHER / 'M22_M21_HEART_ARCHIVE_AUDIT_20261106.json').read_bytes())['files']
    paths = {}
    for name in ('spec', 'label', 'result'):
        entry = files[name]
        paths[name] = pilot_dir / entry['path']
        require(file_hash(paths[name]) == entry['sha256'], 'M21_RAW_FILE_HASH_MISMATCH:' + name)
    replay = audit(paths['spec'], paths['label'], paths['result'], strict_json(RECEIPT.read_bytes()))
    label = strict_json(paths['label'].read_bytes())
    ledger_raw = (TEACHER / 'M9_H8F_81_EXCLUDED_CANDIDATES.json').read_bytes()
    require(h256(ledger_raw) == LEDGER_SHA, 'M9_LEDGER_SHA_MISMATCH')
    ledger = strict_json(ledger_raw)
    require(ledger['source']['archive_sha256'] == HEART_ARTIFACT_SHA, 'H8F_LEDGER_SOURCE_MISMATCH')
    row = ledger['samples'][0]
    material = read_material(historical, row['same_call_material_gzip_sha256'], HEART_ARTIFACT_SHA)
    result = compare_material(material, row, label['payload'])
    return dict(result, historical_point_gzip_sha256=row['same_call_material_gzip_sha256'],
                m9_ledger_sha256=LEDGER_SHA, m21_payload_sha256=label['payload_sha256'],
                m21_label_sha256=replay['label_sha256'], m21_result_sha256=replay['result_sha256'],
                m21_spec_sha256=replay['spec_sha256'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-dir', type=Path, required=True)
    parser.add_argument('--historical', type=Path, required=True)
    args = parser.parse_args()
    if hasattr(sys, 'set_int_max_str_digits'):
        sys.set_int_max_str_digits(100000)
    try:
        report = recover(args.pilot_dir, args.historical)
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, ZeroDivisionError, OverflowError) as e:
        parser.exit(2, 'Point-000 recovery rejected: ' + str(e) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return {'FULL_CANONICAL_MATERIAL_MATCH': 0, 'BOUNDARY_ONLY': 3,
            'REJECTED_BOUNDARY_CONFLICT': 2}[report['status']]


if __name__ == '__main__':
    sys.exit(main())
