#!/usr/bin/env python3
"""Read-only, bounded M9 report locator. No native imports or file mutations.

Matches the known fields of the user's successful H8c ABBA baseline; a match
is NOT independent authentication of all saved material or a numerical pass.
Archives are listed by filename only, never extracted or accepted as reports.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

ARCHIVE_SHA = '78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7'
MATERIAL_SHA = '57b4cf3edcf371c577c494a5a018fa78015e6bdf3e08b4cd1d7809770e0a53d3'
GEOMETRY_SHA = '8dc39e92b09f4c3f00f4415ed1a3f9e6673d4e04ae80723330e04b681b2b5ba0'
SOURCE_BLOB = 'f9fa539f699df8baf8b8d30729048269a26ecb3c'
MODULES = {
    'native_sha256': '579128457145c22f6192df8bf7b75603f5cfc5b3c719008d39ef9e3fb40ae0bf',
    'cherchi_sha256': 'd6c2da58e4396c7ad279fb10457dd365783ba6f056983acf1353a73ce63e3351',
    'gmp_sha256': 'ed05436e2796b190ddebb024f67318e2e88bdc46d96b01e9d7db71a6af080dca',
}
SKIP_DIRS = {'.git', '__pycache__', '.cache', 'anaconda3', 'miniconda3',
             'miniforge3', 'node_modules', 'build', 'external', '.venv', 'venv',
             '.rustup', '.cargo'}
MAX_REPORT_BYTES = 16 * 1024**2


def finite_vector(value, length):
    return (isinstance(value, list) and len(value) == length and
            all(type(x) in (int, float) and math.isfinite(x) for x in value))


def validate_report(doc):
    """Return reasons for rejection; never manufacture or repair a report."""
    if not isinstance(doc, dict) or doc.get('schema') != 'w1-m9-native-h8c-abba-v1':
        return ['WRONG_SCHEMA']
    errors = []
    for key, expected in (('archive_sha256', ARCHIVE_SHA),
                          ('production_source_blob', SOURCE_BLOB),
                          ('module_binary_sha256', MODULES)):
        if doc.get(key) != expected:
            errors.append('MISMATCH:' + key)
    parity = doc.get('parity_and_timing')
    if not isinstance(parity, dict) or parity.get('pass_all_four_material_and_jacobian_parity') is not True:
        errors.append('M9_PARITY_NOT_PASSED')
    rows = doc.get('measurements')
    if not isinstance(rows, list) or len(rows) != 4 or not all(isinstance(r, dict) for r in rows):
        return errors + ['INVALID_MEASUREMENT_COUNT']
    if [r.get('mode') for r in rows] != ['original', 'candidate', 'candidate', 'original']:
        errors.append('INVALID_ABBA_ORDER')
    for i, row in enumerate(rows):
        if row.get('material_sha256') != MATERIAL_SHA or row.get('geometry_hash') != GEOMETRY_SHA:
            errors.append('MATERIAL_OR_GEOMETRY_MISMATCH:' + str(i))
        matrix = row.get('jacobian')
        if not (finite_vector(row.get('q'), 10) and finite_vector(row.get('ten'), 10)
                and isinstance(matrix, list) and len(matrix) == 10
                and all(finite_vector(r, 10) for r in matrix)):
            errors.append('INVALID_NUMERICAL_FIELDS:' + str(i))
    for field in ('q', 'ten', 'jacobian'):
        if any(r.get(field) != rows[0].get(field) for r in rows[1:]):
            errors.append('ABBA_FIELD_DRIFT:' + field)
    return errors


def search(roots, max_depth=8, max_seconds=45.0, max_directories=20000):
    """Bounded filename scan. Scope/pruning/limits are always reported."""
    if max_depth < 0 or max_seconds <= 0 or max_directories < 1:
        raise ValueError('INVALID_SEARCH_LIMITS')
    result = dict(matches=[], archive_candidates_not_opened=[], rejected_reports=[],
                  io_errors=[], skipped_roots=[], roots=[], skipped_directory_names=sorted(SKIP_DIRS),
                  symlink_directories_not_followed=0, depth_cutoffs=0, directories_scanned=0,
                  report_files_checked=0, limit_reached=False, native_evaluations=0)
    seen_files, seen_roots = set(), set()
    started = time.monotonic()

    def onerror(error):
        result['io_errors'].append(str(error))

    for raw_root in roots:
        try:
            root = Path(raw_root).expanduser().resolve(strict=True)
            if not root.is_dir():
                raise NotADirectoryError(str(root))
        except OSError as exc:
            result['skipped_roots'].append({'path': str(raw_root), 'error': str(exc)})
            continue
        if root in seen_roots:
            continue
        seen_roots.add(root)
        result['roots'].append(str(root))
        for dirname, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
            if (time.monotonic() - started >= max_seconds or
                    result['directories_scanned'] >= max_directories):
                result['limit_reached'] = True
                break
            result['directories_scanned'] += 1
            parent = Path(dirname)
            depth = len(parent.relative_to(root).parts)
            result['symlink_directories_not_followed'] += sum((parent / d).is_symlink() for d in dirs)
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (parent / d).is_symlink())
            if depth >= max_depth:
                result['depth_cutoffs'] += len(dirs)
                dirs[:] = []
            for name in sorted(files):
                if time.monotonic() - started >= max_seconds:
                    result['limit_reached'] = True
                    break
                path = parent / name
                low = name.lower()
                if 'm9' in low and low.endswith(('.zip', '.tar', '.tar.gz', '.tgz', '.tar.xz')):
                    result['archive_candidates_not_opened'].append(str(path))
                if low not in ('baseline-performance.json', 'm9-baseline-performance.json'):
                    continue
                try:
                    resolved = path.resolve(strict=True)
                    if resolved in seen_files:
                        continue
                    seen_files.add(resolved)
                    result['report_files_checked'] += 1
                    with resolved.open('rb') as stream:
                        data = stream.read(MAX_REPORT_BYTES + 1)
                    if len(data) > MAX_REPORT_BYTES:
                        raise ValueError('REPORT_TOO_LARGE')
                    reasons = validate_report(json.loads(data))
                    if reasons:
                        result['rejected_reports'].append({'path': str(path), 'reasons': reasons})
                    else:
                        result['matches'].append({
                            'report': str(path), 'resolved_report': str(resolved),
                            'm9_run': str(path.parent), 'sha256': hashlib.sha256(data).hexdigest(),
                            'bytes': len(data),
                            'runner_filename_compatible': name == 'baseline-performance.json'})
                except (OSError, ValueError, TypeError, OverflowError) as exc:
                    result['io_errors'].append(str(path) + ': ' + str(exc))
            if result['limit_reached']:
                break
        if result['limit_reached']:
            break
    result['status'] = 'MATCHING_REPORT_CANDIDATES_FOUND' if result['matches'] else 'NO_MATCH_IN_SCOPED_SEARCH'
    result['elapsed_seconds'] = time.monotonic() - started
    result['interpretation'] = ('Read-only recovery aid. Not finding a report in this bounded, pruned search '
                                'does not prove deletion. Field matches are not a substitute for full evidence '
                                'authentication. No report was copied, created, or rewritten.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', required=True, help='Search root, repeatable')
    parser.add_argument('--max-depth', type=int, default=8)
    parser.add_argument('--max-seconds', type=float, default=45.0)
    parser.add_argument('--max-directories', type=int, default=20000)
    args = parser.parse_args()
    result = search(args.root, args.max_depth, args.max_seconds, args.max_directories)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result['matches'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
