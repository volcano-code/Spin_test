"""W1 M11: fail-closed M10 -> independent receipt validation launcher.

No new production ABI, source edit, Cherchi shortcut, or full Newton claim.
M10's intermediate result stays quarantined until M11 independently binds
M5/M9 full saved material and per-call timing to real native module hashes.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import m10_native_host_runner as m10
from m11_native_evidence_gate import verify


def _write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def run(root, archive, output, *, module_dirs=(), max_seconds=m10.MAX_SECONDS):
    """Run with genuine native prerequisites, or record a meaningful blocker.

    M10 stages and lower-level summary are isolated under `work/` so a
    tampered or partial M5/M9 receipt can never become M11 success.
    """
    root, archive, output = Path(root).resolve(), Path(archive).resolve(), Path(output)
    if not type(max_seconds) is int or not 1 <= max_seconds <= m10.MAX_SECONDS:
        raise ValueError('M11_MAX_SECONDS_OUTSIDE_PER_JOB_CONTRACT')
    output.mkdir(parents=True, exist_ok=False)
    try:
        preflight = m10.preflight(root, archive, module_dirs)
        _write_new(output/'m11-preflight.json', preflight)
        if preflight['state'] != 'READY_FOR_REAL_NATIVE_ABBA':
            _write_new(output/'failure.json', dict(
                schema='w1-m11-native-blocked-v1', status='BLOCKED_BEFORE_BOOLEAN',
                blockers=preflight.get('blockers', []),
                native_calls=0, solver_speedup=None, paper_speed_qualified=False))
            return dict(state='BLOCKED', blockers=preflight.get('blockers', []))
        # M10 is the ONLY subprocess executor. It enforces the same pinned
        # worktree, module import ABI, independent geometry, swap and job lock.
        interim = m10.execute(root, archive, output/'work',
                             extra_modules=module_dirs, max_seconds=max_seconds)
        if (interim.get('schema') != 'w1-m10-fresh-native-evaluation-complete-v1' or
                interim.get('scope') != 'M5_SINGLE_Q_PLUS_M9_ABBA_NOT_FULL_NEWTON' or
                interim.get('fresh_boolean_calls') != 5 or
                interim.get('full_solver_speedup') is not None or
                interim.get('paper_speed_qualified') is not False or
                len(interim.get('jobs', [])) != 2 or
                [row.get('stage') for row in interim['jobs']] != ['m5','m9'] or
                any(row.get('returncode') != 0 for row in interim['jobs'])):
            raise ValueError('M11_INCOMPLETE_OR_MISLABELED_M10_EXECUTION')
        evidence = verify(output/'work/preflight.json',
                          output/'work/m5', output/'work/m9')
        _write_new(output/'m11-verified-native-receipts.json', evidence)
        # Do not promote source, material, or Jacobian parity to a complete
        # Newton terminal seal / physically admissible spinning top.
        return dict(schema='w1-m11-native-receipt-suite-v1',
                    state='FIVE_REAL_CHERCHI_EVALUATIONS_AND_SAVED_RECEIPTS_ADMITTED',
                    admission_document_sha256=sha256(
                        (output/'m11-verified-native-receipts.json').read_bytes()).hexdigest(),
                    native_samples=5,
                    historical_h8e_branch_hash_failure_preserved=True,
                    full_solver_speedup=None, newton_terminal_verified=False,
                    w0_w2_production_admitted=False,paper_speed_qualified=False)
    except BaseException as error:
        if not (output/'failure.json').exists():
            _write_new(output/'failure.json', dict(
                schema='w1-m11-native-failed-v1', status='FAILED_CLOSED',
                error=f'{type(error).__name__}: {error}',
                full_solver_speedup=None,paper_speed_qualified=False))
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--module-dir',type=Path,action='append',default=[])
    p.add_argument('--max-seconds',type=int,default=3600)
    a=p.parse_args()
    receipt=run(a.root,a.archive,a.output,module_dirs=a.module_dir,
                max_seconds=a.max_seconds)
    if receipt.get('state')=='BLOCKED':
        print(json.dumps(receipt,sort_keys=True))
        raise SystemExit(2)
    _write_new(a.output/'m11-native-validation-summary.json',receipt)
    print(json.dumps({'status':receipt['state'],'full_solver_speedup':None}))


if __name__ == '__main__': main()
