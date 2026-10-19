"""W0 M7: inspect a pre-existing, externally pinned Newton archive, read-only.

This NEVER starts Cherchi or Newton. By default performs arithmetic/archive
consistency only. --require-production-record invokes the pinned production
`verify_cherchi_run_evidence`, whose own scope is record integrity *only*.
No input/failed evidence is overwritten; this command writes one new report.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys

from .native_teacher_replay import ReplayRejected, canonical, need, sha256_file, digest
from .terminal_archive_m7 import _json, review_pinned_terminal_archive
from .m7_evidence_chain import review_terminal_partition_chain


def _production_verifier(sha):
    need(type(sha) is str and len(sha)==64 and
         all(c in '0123456789abcdef' for c in sha),
         'EXTERNAL_PRODUCTION_VERIFIER_SHA_REQUIRED')
    try:
        module=importlib.import_module('make_it_stand.verification.cherchi_run_evidence')
    except (ImportError,RuntimeError,OSError) as e:
        raise ReplayRejected('PRODUCTION_TERMINAL_VERIFIER_NOT_INSTALLED') from e
    need(type(getattr(module,'verify_cherchi_run_evidence',None)) is type(lambda:None),
         'PRODUCTION_TERMINAL_VERIFIER_SYMBOL_MISSING')
    need(sha256_file(module.__file__)==sha,
         'PRODUCTION_VERIFIER_SOURCE_SHA_MISMATCH')
    return module.verify_cherchi_run_evidence


def _emit(path, report):
    if path is not None:
        dest=Path(path)
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            with dest.open('x',encoding='utf-8') as stream:
                stream.write(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
        except FileExistsError as e:
            raise ReplayRejected('EVIDENCE_FILE_EXISTS_NO_OVERWRITE') from e
    print(canonical(report))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--pins',required=True)
    parser.add_argument('--output')
    parser.add_argument('--partition',help='optional independent M6 report; no source execution')
    parser.add_argument('--partition-sha256',help='externally frozen M6 canonical SHA256')
    parser.add_argument('--require-production-record',action='store_true')
    parser.add_argument('--production-verifier-sha256',help='external pre-run SHA256 of real production Python verifier')
    parser.add_argument('--require-original-kkt',action='store_true',help='only original Spin2014 equations on installed, pinned Python sources')
    parser.add_argument('--original-physics-sha256',help='external pre-run SHA256 of faster_material.py')
    parser.add_argument('--objective-contract-sha256',help='external pre-run SHA256 of spin2014_objective_contract.py')
    args=parser.parse_args(argv)
    report={'schema':'W0_M7_TERMINAL_ARCHIVE_RUN_REPORT_V1',
            'status':'NOT_STARTED',
            'training_admissible':False,
            'newton_terminal_independently_certified':False,
            'smooth_derivative_neighborhood_certified':False,
            'full_native_geometry_certified':False}
    if args.output and Path(args.output).exists():
        print('EVIDENCE_FILE_EXISTS_NO_OVERWRITE',file=sys.stderr)
        return 4
    try:
        pins_path=Path(args.pins)
        need(pins_path.is_file() and not pins_path.is_symlink(),
             'EXTERNAL_PIN_MANIFEST_MISSING_OR_SYMLINK')
        pins_raw=pins_path.read_text(encoding='utf-8')
        pins=_json(pins_raw,'pins.json')
        report['pins_file_sha256']=sha256_file(pins_path)
        review=review_pinned_terminal_archive(args.archive,pins)
        report['terminal_archive_review']=review
        report['status']='NUMERICAL_ARCHIVE_CONSISTENT_NOT_NATIVE_CERTIFICATE'
        need((args.partition is None)==(args.partition_sha256 is None),
             'M6_PARTITION_AND_PIN_MUST_BE_TOGETHER')
        if args.partition is not None:
            path=Path(args.partition)
            need(path.is_file() and not path.is_symlink(),
                 'M6_PARTITION_EVIDENCE_FILE_MISSING_OR_SYMLINK')
            partition=_json(path.read_text(encoding='utf-8'),'M6 partition')
            report['M6_cross_commit_identity_check']=review_terminal_partition_chain(
                review,partition,expected_partition_sha256=args.partition_sha256)
            report['status']='M6_TERMINAL_IDENTITY_CONSISTENT_NO_NATIVE_CERTIFICATE'
        if args.require_original_kkt:
            from .live_original_objective_m7 import recheck_archived_original_objective
            report['original_objective_recheck']=recheck_archived_original_objective(
                args.archive,review,
                expected_faster_material_sha256=args.original_physics_sha256,
                expected_objective_contract_sha256=args.objective_contract_sha256)
            report['status']='INDEPENDENT_ORIGINAL_EQUATION_RECHECKED_FULL_SCIENCE_PENDING'
        if args.require_production_record:
            verify=_production_verifier(args.production_verifier_sha256)
            evidence=verify(args.archive)   # Original read-only scientific journal verifier.
            need(type(evidence) is dict and evidence.get('record_integrity_valid') is True
                 and evidence.get('core_admission') is False,
                 'PRODUCTION_LOG_VERIFIER_DID_NOT_VALIDATE')
            report['production_log_verifier_report']=evidence
            report['status']='PRODUCTION_RECORD_INTEGRITY_VERIFIED_FULL_SCIENCE_PENDING'
        _emit(args.output,report)
        return 0
    except (ReplayRejected,ValueError,TypeError,OverflowError,RuntimeError,
            FileNotFoundError,PermissionError,OSError) as e:
        report['status']=('BLOCKED_PRODUCTION_VERIFIER_UNAVAILABLE' if
            ('PRODUCTION_TERMINAL_VERIFIER_NOT_INSTALLED' in str(e) or
             'ORIGINAL_OBJECTIVE_PRODUCTION_SOURCE_UNAVAILABLE' in str(e)) else
            'FAILED_CLOSED_TERMINAL_REVIEW')
        report['reason']=f'{type(e).__name__}: {e}'
        try: _emit(args.output,report)
        except ReplayRejected: print('EVIDENCE_FILE_EXISTS_NO_OVERWRITE',file=sys.stderr)
        return 3 if report['status'].startswith('BLOCKED') else 4


if __name__=='__main__':
    raise SystemExit(main())
