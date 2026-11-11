#!/usr/bin/env python3
"""Read-only M9 recovery: breadth-first search with independent root budgets.

Uses the existing identity filter unchanged. Every supplied root gets its own
budget; reaching a limit in one root never prevents searching the next root.
Symlinks and relevant archive names are leads only, not opened or extracted.
"""
from __future__ import annotations
import argparse
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import stat
import time

from m29_locate_m9_baseline import MAX_REPORT_BYTES, SKIP_DIRS, validate_report

RUN_NAME = 'w1-m29-m9-fixed-20261108-181458'
REPORT_NAMES = {'baseline-performance.json', 'm9-baseline-performance.json'}
HINTS = ('m9', 'm29', 'w1', 'spin_test', 'experiment', 'runs', 'research',
         'backup', 'archive', 'evidence', 'recovery', 'trash', 'download',
         '\u5907\u4efd', '\u5f52\u6863', '\u4e0b\u8f7d', '\u56de\u6536')
ARCHIVE_SUFFIXES = ('.zip', '.tar', '.tar.gz', '.tgz', '.tar.xz', '.tar.zst', '.7z')
LIST_LIMIT = 200


def priority(name):
    low = name.lower()
    if RUN_NAME in low or '20261108-181458' in low:
        return 0
    if any(hint in low for hint in HINTS):
        return 1
    return 3 if name.startswith('.') else 2


def path_status(path):
    p = Path(path).expanduser()
    row = {'path': str(p)}
    try:
        facts = p.lstat()
        if stat.S_ISLNK(facts.st_mode):
            row.update(status='SYMLINK_NOT_FOLLOWED', target=os.readlink(p))
        else:
            row['status'] = 'DIRECTORY' if stat.S_ISDIR(facts.st_mode) else 'EXISTS_NOT_DIRECTORY'
    except OSError as exc:
        row.update(status='UNRESOLVED', error=str(exc))
    return row


def search_fair(roots, *, max_depth=8, directories_per_root=12000,
                seconds_per_root=20.0, entries_per_directory=20000, known_run=None):
    """Search finite scopes, return coverage and candidates, never mutate files.

    Time limits are cooperative, not hard filesystem syscall timeouts. All
    limitations are retained. Only directly encountered regular reports are
    parsed; no symlink directory or symlink report is automatically followed.
    """
    if (type(max_depth) is not int or max_depth < 0 or
            type(directories_per_root) is not int or directories_per_root < 1 or
            type(entries_per_directory) is not int or entries_per_directory < 1 or
            not math.isfinite(seconds_per_root) or seconds_per_root <= 0):
        raise ValueError('INVALID_SEARCH_LIMITS')
    result = {'schema': 'w1-m29-fair-baseline-recovery-v1', 'matches': [],
              'rejected_reports': [], 'io_errors': [], 'symlink_leads': [],
              'archive_candidates_not_opened': [], 'run_directory_leads': [],
              'roots': [], 'root_summaries': [], 'truncated_lists': {},
              'native_evaluations': 0, 'files_mutated': 0,
              'skipped_directory_names': sorted(SKIP_DIRS),
              'known_run_status': path_status(known_run) if known_run else None}
    seen_roots, seen_reports = set(), set()

    def record(key, value):
        if len(result[key]) < LIST_LIMIT:
            result[key].append(value)
        else:
            result['truncated_lists'][key] = result['truncated_lists'].get(key, 0) + 1

    for raw in roots:
        started = time.monotonic()
        info = {'requested_root': str(raw), 'status': 'SCANNING',
                'directories_scanned': 0, 'reports_checked': 0,
                'depth_cutoffs': 0, 'skipped_named_directories': 0,
                'symlinks_not_followed': 0, 'directory_entry_cutoffs': 0,
                'limit_reached': False, 'limit_reason': None, 'io_errors': 0,
                'max_depth_scanned': 0, 'remaining_queued_directories': 0}
        result['root_summaries'].append(info)
        try:
            root = Path(raw).expanduser().resolve(strict=True)
            if not root.is_dir():
                raise NotADirectoryError(str(root))
        except (OSError, RuntimeError) as exc:
            info.update(status='ROOT_UNAVAILABLE', error=str(exc), elapsed_seconds=time.monotonic()-started)
            continue
        info['resolved_root'] = str(root)
        if root in seen_roots:
            info.update(status='DUPLICATE_RESOLVED_ROOT', elapsed_seconds=time.monotonic()-started)
            continue
        seen_roots.add(root)
        result['roots'].append(str(root))
        queue = [(0, 0, str(root))]
        while queue:
            if time.monotonic()-started >= seconds_per_root:
                info.update(limit_reached=True, limit_reason='SECONDS_PER_ROOT')
                break
            if info['directories_scanned'] >= directories_per_root:
                info.update(limit_reached=True, limit_reason='DIRECTORIES_PER_ROOT')
                break
            depth, _, current = heapq.heappop(queue)
            parent = Path(current)
            info['directories_scanned'] += 1
            info['max_depth_scanned'] = max(info['max_depth_scanned'], depth)
            children = []
            try:
                with os.scandir(parent) as entries:
                    for index, entry in enumerate(entries):
                        if index >= entries_per_directory:
                            info['directory_entry_cutoffs'] += 1
                            break
                        if time.monotonic()-started >= seconds_per_root:
                            info.update(limit_reached=True, limit_reason='SECONDS_PER_ROOT_DURING_DIRECTORY')
                            break
                        path = Path(entry.path)
                        try:
                            if entry.is_symlink():
                                info['symlinks_not_followed'] += 1
                                if priority(entry.name) <= 1 or entry.name.lower() in REPORT_NAMES:
                                    record('symlink_leads', {'path': str(path), 'target': os.readlink(path),
                                                            'status': 'NOT_FOLLOWED'})
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                if priority(entry.name) == 0:
                                    record('run_directory_leads', str(path))
                                if entry.name in SKIP_DIRS:
                                    info['skipped_named_directories'] += 1
                                elif depth >= max_depth:
                                    info['depth_cutoffs'] += 1
                                else:
                                    children.append((depth+1, priority(entry.name), str(path)))
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            low = entry.name.lower()
                            if low.endswith(ARCHIVE_SUFFIXES) and priority(entry.name) <= 1:
                                record('archive_candidates_not_opened', str(path))
                            if low not in REPORT_NAMES or str(path) in seen_reports:
                                continue
                            seen_reports.add(str(path))
                            info['reports_checked'] += 1
                            # A FIFO or symlink must not block a read if a path
                            # changes between scandir and open on this Linux host.
                            flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
                            fd = os.open(path, flags)
                            with os.fdopen(fd, 'rb') as stream:
                                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                                    raise ValueError('REPORT_NOT_REGULAR')
                                data = stream.read(MAX_REPORT_BYTES+1)
                            if len(data) > MAX_REPORT_BYTES:
                                raise ValueError('REPORT_TOO_LARGE')
                            reasons = validate_report(json.loads(data))
                            if reasons:
                                record('rejected_reports', {'path': str(path), 'reasons': reasons})
                            else:
                                record('matches', {'report': str(path), 'm9_run': str(parent),
                                    'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                                    'runner_filename_compatible': entry.name == 'baseline-performance.json'})
                        except (OSError, ValueError, TypeError, OverflowError) as exc:
                            info['io_errors'] += 1
                            record('io_errors', {'path': str(path), 'error': str(exc)})
            except OSError as exc:
                info['io_errors'] += 1
                record('io_errors', {'path': str(parent), 'error': str(exc)})
            for child in children:
                heapq.heappush(queue, child)
            if info['limit_reached']:
                break
        info['remaining_queued_directories'] = len(queue)
        info['elapsed_seconds'] = time.monotonic()-started
        info['status'] = 'LIMIT_REACHED' if info['limit_reached'] else 'SCOPED_WALK_FINISHED'
    result['directories_scanned'] = sum(x['directories_scanned'] for x in result['root_summaries'])
    result['report_files_checked'] = sum(x['reports_checked'] for x in result['root_summaries'])
    result['limit_reached'] = any(x['limit_reached'] or x['directory_entry_cutoffs'] for x in result['root_summaries'])
    result['status'] = 'MATCHING_REPORT_CANDIDATES_FOUND' if result['matches'] else 'NO_MATCH_IN_SCOPED_SEARCH'
    result['interpretation'] = ('Every distinct available root received an independent bounded breadth-first search. '
        'All filename, depth, pruning, symlink and budget restrictions still apply. No match does not prove deletion. '
        'Candidates passed only the existing known-field filter, not full independent evidence authentication. '
        'Archives and symlinks are uninspected leads. No extraction, replacement report, or native run occurred.')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', action='append', required=True)
    p.add_argument('--known-run')
    p.add_argument('--max-depth', type=int, default=8)
    p.add_argument('--directories-per-root', type=int, default=12000)
    p.add_argument('--seconds-per-root', type=float, default=20.)
    p.add_argument('--entries-per-directory', type=int, default=20000)
    a = p.parse_args()
    result = search_fair(a.root, max_depth=a.max_depth, directories_per_root=a.directories_per_root,
                        seconds_per_root=a.seconds_per_root, entries_per_directory=a.entries_per_directory,
                        known_run=a.known_run)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result['matches'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
