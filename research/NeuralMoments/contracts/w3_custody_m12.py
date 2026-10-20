"""W0 M12: independent handoff custody for *future* W3 Cherchi four-side packets.

Phase A: verify the exact committed W3 Stage10 input gate / negative execution.
Phase B: a separate reviewer (not the W3 producer) freezes all 13 postrun
         files against a PRE-RUN source/native identity lock that was already
         externally SHA256 pinned before native execution.
Phase C: read the frozen receipt and invoke the existing M11 exact-geometry
         auditor over the real historical H8f archive.

This code never performs Cherchi, cannot infer real execution from self-reported
SHA hashes, and NEVER approves Newton, training or smooth topology.
"""
from __future__ import annotations

import argparse
from hashlib import sha1, sha256
import json
import os
import stat
from pathlib import Path
import re
import sys

from . import w3_four_side_replay_m11 as m11
from .real_h8e_archive_m8 import ArchiveAuditError, require

FROZEN_W3_HEAD = '324256786bc189abbbb93452ed2627cfe0b28a13'
W3_STAGE10_EXECUTION_BLOB = '254e93076d6fbec0a60632cee4c4731945f579d4'
W3_STAGE10_INPUT_BLOB = '8a352efca5f7f88dda24c359b7d5225f10f9cf66'
W3_STAGE10_SOURCE_GATE_BLOB = '5c7d71bb83cd195dea47d1c01400bc312fbbff65'
EXECUTION_SHA256 = '7f80525c2d87ab38f03bd679e57febd78d318b198fa172a087e27f5e161d2484'
INPUT_SHA256 = 'ef2e4dc902423b217bf319a949a848eaaceb8a37fee435a35130e63f18014784'
LOCK_SCHEMA = 'W0_M12_EXTERNALLY_PINNED_PRE_NATIVE_SOURCE_LOCK_V1'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')


def git_blob_sha1(content: bytes) -> str:
    return sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()


def strict_json(raw: bytes):
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ArchiveAuditError('M12_DUPLICATE_JSON_KEY:' + key)
            obj[key] = value
        return obj
    def reject_constant(value):
        raise ArchiveAuditError('M12_NONFINITE_JSON:' + value)
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as e:
        raise ArchiveAuditError('M12_INVALID_JSON') from e


def read_regular(path, max_size=1_000_000):
    """FD-bound bytes: never follow a symlink, never accept an in-read rewrite."""
    path=Path(path)
    flags=os.O_RDONLY | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    try:
        descriptor=os.open(path,flags)
    except (OSError, ValueError) as exc:
        raise ArchiveAuditError('M12_MISSING_OR_LINKED_EVIDENCE:'+path.name) from exc
    with os.fdopen(descriptor,'rb') as stream:
        start=os.fstat(stream.fileno())
        require(stat.S_ISREG(start.st_mode) and 0 < start.st_size <= max_size,
                'M12_EMPTY_OVERSIZED_OR_NONREGULAR_EVIDENCE:'+path.name)
        data=stream.read(max_size+1)
        end=os.fstat(stream.fileno())
    require(len(data)==start.st_size and
            (start.st_dev,start.st_ino,start.st_size,start.st_mtime_ns)==
            (end.st_dev,end.st_ino,end.st_size,end.st_mtime_ns),
            'M12_EVIDENCE_CHANGED_DURING_READ:'+path.name)
    return data


def stream_sha256_regular(path):
    """Stream historical H8f ZIP without following a symlink or mutable FD."""
    path=Path(path)
    flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_CLOEXEC',0)
    try:descriptor=os.open(path,flags)
    except OSError as exc:
        raise ArchiveAuditError('M12_ORIGINAL_H8F_ARCHIVE_MISSING') from exc
    with os.fdopen(descriptor,'rb') as source:
        before=os.fstat(source.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size>0,
                'M12_ORIGINAL_H8F_ARCHIVE_MISSING')
        result=sha256()
        for chunk in iter(lambda: source.read(1024*1024),b''):
            result.update(chunk)
        after=os.fstat(source.fileno())
    require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),
            'M12_HISTORICAL_ARCHIVE_CHANGED_DURING_READ')
    return result.hexdigest()


def inspect_frozen_stage10(*, execution_bytes: bytes, input_bytes: bytes):
    """Check genuine W3 Git blob bytes; no untrusted field can upgrade native work."""
    require(git_blob_sha1(execution_bytes) == W3_STAGE10_EXECUTION_BLOB and
            sha256(execution_bytes).hexdigest() == EXECUTION_SHA256,
            'M12_W3_STAGE10_EXECUTION_BLOB_CHANGED')
    require(git_blob_sha1(input_bytes) == W3_STAGE10_INPUT_BLOB and
            sha256(input_bytes).hexdigest() == INPUT_SHA256,
            'M12_W3_STAGE10_INPUT_BLOB_CHANGED')
    evidence, inp = strict_json(execution_bytes), strict_json(input_bytes)
    require(type(evidence) is dict and type(inp) is dict,
            'M12_W3_STAGE10_INVALID_OBJECTS')
    require(evidence.get('schema') == 'heart-h9-stage10-actual-execution-v1' and
            evidence.get('historical_H8f_run_id') == m11.HISTORICAL_RUN and
            evidence.get('historical_H8f_run_conclusion') == 'failure' and
            evidence.get('frozen_artifact_sha256') == m11.ARCHIVE_SHA256 and
            evidence.get('run_status') == 'BLOCKED_NO_NATIVE_EVALUATION' and
            evidence.get('new_real_cherchi_boolean_calls_completed') == 0 and
            evidence.get('new_native_material_files') == 0 and
            evidence.get('command_exit_codes') == {'plan': 0, 'inputs': 0,
                                                   'build': 2, 'run': 2} and
            evidence.get('container_cgroup_effective_memory_limit_bytes') == 4*1024**3 and
            all(evidence.get(k) is False for k in (
                'continuous_cherchi_boolean_stratum_proven',
                'newton_admitted', 'final_heart_obj_produced',
                'github_W3_native_CI_triggered')),
            'M12_STAGE10_NATIVE_BLOCKER_SUPPRESSED')
    require(inp.get('schema') == 'heart-h9-frozen-input-gate-v1' and
            inp.get('status') == 'FROZEN_INPUT_READY_FOR_NATIVE_ATTEMPT_ONLY' and
            inp.get('source_artifact_id') == m11.HISTORICAL_ARTIFACT and
            inp.get('source_artifact_sha256') == m11.ARCHIVE_SHA256 and
            inp.get('frozen_request_sha256') == m11.REQUEST_SHA256 and
            inp.get('historical_run_id') == m11.HISTORICAL_RUN and
            inp.get('historical_run_conclusion') == 'failure' and
            inp.get('certificate_recomputed_from_frozen_actual_material') is True and
            inp.get('all_four_coefficients_are_finite_and_ordered') is True and
            inp.get('four_new_native_probe_plan') == m11.expected_plan() and
            inp.get('four_new_native_calls_completed_by_this_gate') == 0 and
            all(inp.get(k) is False for k in (
                'actual_native_boolean_result_available',
                'production_continuous_branch_certified', 'newton_admitted',
                'final_heart_obj_produced')),
            'M12_STAGE10_PLAN_OR_SCIENTIFIC_STATUS_MISMATCH')
    return {'schema': 'W0_M12_STAGE10_READ_ONLY_W3_OBSERVATION_V1',
            'observed_w3_head': FROZEN_W3_HEAD,
            'stage10_input_git_blob': W3_STAGE10_INPUT_BLOB,
            'stage10_execution_git_blob': W3_STAGE10_EXECUTION_BLOB,
            'original_h8f_run_conclusion': 'failure',
            'plan_validated': True,
            'four_native_samples_ready': False,
            'new_cherchi_calls': 0,
            'new_material_files': 0,
            'status': 'BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS',
            'training_admissible': False, 'newton_admitted': False,
            'smooth_neighborhood_proven': False}


def check_pre_run_lock(raw: bytes, *, expected_sha256: str):
    """Expected SHA must arrive via independent PRE-run channel, never output."""
    require(type(expected_sha256) is str and HEX64.fullmatch(expected_sha256),
            'M12_EXTERNAL_PRERUN_SHA_REQUIRED')
    require(sha256(raw).hexdigest() == expected_sha256,
            'M12_PRE_EXECUTION_SOURCE_LOCK_DIGEST_MISMATCH')
    manifest = strict_json(raw)
    require(type(manifest) is dict and set(manifest) == {
        'schema', 'frozen_w3_head_sha', 'source_verifier_git_blob',
        'source_workflow_git_blob', 'source_input_gate_git_blob',
        'source_stage10_evidence_git_blob', 'historical_artifact_sha256',
        'precommitted_native_binary_sha256'},
        'M12_INCOMPLETE_PRE_RUN_LOCK')
    require(manifest['schema'] == LOCK_SCHEMA and
            manifest['frozen_w3_head_sha'] == FROZEN_W3_HEAD and
            manifest['source_verifier_git_blob'] == m11.W3_SOURCE_VERIFIER_BLOB and
            manifest['source_workflow_git_blob'] == m11.W3_FROZEN_WORKFLOW_BLOB and
            manifest['source_input_gate_git_blob'] == W3_STAGE10_SOURCE_GATE_BLOB and
            manifest['source_stage10_evidence_git_blob'] == W3_STAGE10_EXECUTION_BLOB and
            manifest['historical_artifact_sha256'] == m11.ARCHIVE_SHA256,
            'M12_W3_FROZEN_GIT_SOURCE_NOT_APPROVED')
    binary = manifest['precommitted_native_binary_sha256']
    require(type(binary) is dict and set(binary) == {'core', 'boolean', 'arithmetic'} and
            all(type(s) is str and HEX64.fullmatch(s) for s in binary.values()),
            'M12_UNPINNED_NATIVE_BINARIES')
    return manifest


def bound_file_digests(folder):
    """Return exactly M11's thirteen files, each bounded and no symlinks."""
    folder = Path(folder)
    require(folder.is_dir() and not folder.is_symlink() and
            (folder/'native').is_dir() and not (folder/'native').is_symlink(),
            'M12_NOT_A_REAL_FOUR_SIDE_DIRECTORY')
    receipts = {}
    for name in sorted(m11.FILES_REQUIRED):
        limit = 32_000_000 if name.endswith('.json.gz') else 20_000_000
        receipts[name] = sha256(read_regular(folder/name, max_size=limit)).hexdigest()
    expected_stems = {f'side-{i:02d}-{side}' for i,side in enumerate(m11.W3_SIDES)}
    for file in (folder/'native').glob('side-*'):
        require(file.is_file() and not file.is_symlink() and
                (file.name.removesuffix('.json.gz').removesuffix('.json') in expected_stems) and
                file.name.endswith(('.json', '.json.gz')),
                'M12_EXTRA_OR_LINKED_UNREVIEWED_SIDE_PACKET')
    return receipts


def capture_after_native(folder, *, pre_run_lock: bytes, external_pre_run_sha256: str,
                         original_archive):
    """Collector executed separately AFTER W3 exits. NOT an attestation.

    The producer cannot be its own independent collector. The expected prerun
    SHA256 MUST have been registered outside mutable native outputs beforehand.
    """
    pre = check_pre_run_lock(pre_run_lock, expected_sha256=external_pre_run_sha256)
    require(stream_sha256_regular(original_archive) == m11.ARCHIVE_SHA256,
            'M12_HISTORICAL_ARCHIVE_SHA256_DRIFT')
    digests = bound_file_digests(folder)
    receipt = {
        'schema': m11.RECEIPT_SCHEMA,
        'historical_artifact_sha256': m11.ARCHIVE_SHA256,
        'frozen_w3_head_sha': pre['frozen_w3_head_sha'],
        'source_verifier_git_blob': pre['source_verifier_git_blob'],
        'source_workflow_git_blob': pre['source_workflow_git_blob'],
        'precommitted_native_binary_sha256': dict(pre['precommitted_native_binary_sha256']),
        'files': digests,
    }
    # The cheap M11 report verifier inspects all source/result/counter/status
    # semantics BEFORE any receipt is saved. It does not authenticate the runtime.
    run, independent = m11.check_report_and_logs(folder, receipt)
    for i, side in enumerate(m11.W3_SIDES):
        stem = f'side-{i:02d}-{side}'
        row = m11._read_json_file(Path(folder)/'native'/(stem+'.json'))
        obj = m11.read_bounded_gzip(Path(folder)/'native'/(stem+'.json.gz'))
        frozen_digest = digests['native/'+stem+'.json.gz']
        require(row.get('index') == i and row.get('side') == side and
                row.get('material_sha256') == frozen_digest and
                independent['sample_diagnostics'][i].get('new_same_call_material_sha256') == frozen_digest and
                obj.get('material_proof',{}).get('schema') == 'cherchi-same-call-material-v1' and
                type(obj.get('variable_faces')) is list and len(obj['variable_faces'])>0 and
                obj.get('derivative_defined') is True and
                type(obj.get('quadric_coefficients')) is list and
                len(obj['quadric_coefficients']) == 10 and
                type(obj['quadric_coefficients'][7]) in (int,float) and
                obj['quadric_coefficients'][7] == run['plan'][i]['c7'] and
                type(obj.get('variable_raw_moments')) is list and
                len(obj['variable_raw_moments']) == 10,
                'M12_NEW_SIDE_GZIP_OR_AUDIT_IDENTITY_NOT_INTACT:'+stem)
    return receipt


def verify_collected_receipt(folder, *, receipt_path, pre_run_lock: bytes,
                             external_pre_run_sha256: str, original_archive):
    """Read-only independent M11 replay, distinct from the collector process."""
    pre = check_pre_run_lock(pre_run_lock, expected_sha256=external_pre_run_sha256)
    pinned = m11.check_external_receipt(folder, receipt_path)
    require(pinned['frozen_w3_head_sha'] == pre['frozen_w3_head_sha'] and
            pinned['source_verifier_git_blob'] == pre['source_verifier_git_blob'] and
            pinned['source_workflow_git_blob'] == pre['source_workflow_git_blob'] and
            pinned['precommitted_native_binary_sha256'] == pre['precommitted_native_binary_sha256'],
            'M12_W3_RECEIPT_DID_NOT_MATCH_PRE_RUN_LOCK')
    review = m11.audit_w3_handoff(folder, original_archive, receipt_path)
    require(review.get('newton_admitted') is False and
            review.get('training_admissible') is False,
            'M12_FORBIDDEN_EVIDENCE_PROMOTION')
    return {'schema': 'W0_M12_FOUR_SIDE_REVIEW_V1',
            'postrun_sha_verified': True,
            'pre_run_lock_sha_verified': True,
            'w0_m11_review': review,
            'scientific_scope': 'FINITE_FOUR_POINT_EVIDENCE_NOT_SMOOTH_CERTIFICATION',
            'newton_admitted': False, 'training_admissible': False}


def write_exclusive(path, obj):
    """Never clobber native output, earlier failures, or existing receipts."""
    path=Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError('M12_NEVER_OVERWRITE_EXISTING_EVIDENCE')
    serialized=json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n'
    path.parent.mkdir(parents=True,exist_ok=True)
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os, 'O_NOFOLLOW'):flags|=os.O_NOFOLLOW
    descriptor=os.open(path,flags,0o444)
    with os.fdopen(descriptor,'w',encoding='utf-8') as out:
        out.write(serialized);out.flush();os.fsync(out.fileno())


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('stage10','capture','review'),default='stage10')
    parser.add_argument('--stage10-input',type=Path)
    parser.add_argument('--stage10-execution',type=Path)
    parser.add_argument('--pre-run-lock',type=Path)
    parser.add_argument('--external-pre-run-sha256')
    parser.add_argument('--w3-folder',type=Path)
    parser.add_argument('--historical-archive',type=Path)
    parser.add_argument('--postrun-receipt',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError('M12_NEVER_OVERWRITE_EXISTING_EVIDENCE')
    try:
        if args.mode=='stage10':
            here=Path(__file__).resolve().parent
            inp=read_regular(args.stage10_input or here/'w3_stage10_input_snapshot_m12.json')
            ex=read_regular(args.stage10_execution or here/'w3_stage10_execution_snapshot_m12.json')
            report=inspect_frozen_stage10(execution_bytes=ex,input_bytes=inp)
            exit_code=3
        else:
            require(args.pre_run_lock is not None and
                    args.external_pre_run_sha256 is not None and
                    args.w3_folder is not None and args.historical_archive is not None,
                    'M12_MISSING_POSTRUN_REVIEW_ARGUMENT')
            pre=read_regular(args.pre_run_lock,max_size=100_000)
            if args.mode=='capture':
                report=capture_after_native(args.w3_folder,pre_run_lock=pre,
                    external_pre_run_sha256=args.external_pre_run_sha256,
                    original_archive=args.historical_archive)
            else:
                require(args.postrun_receipt is not None,
                        'M12_POSTRUN_RECEIPT_REQUIRED_FOR_REVIEW')
                report=verify_collected_receipt(args.w3_folder,
                    receipt_path=args.postrun_receipt,
                    pre_run_lock=pre,
                    external_pre_run_sha256=args.external_pre_run_sha256,
                    original_archive=args.historical_archive)
            exit_code=0
    except (ArchiveAuditError, OSError, KeyError, ValueError) as exc:
        report={'schema':'W0_M12_FAIL_CLOSED_REPORT_V1',
                'status':'BLOCKED_OR_REJECTED_FOUR_SIDE_EVIDENCE',
                'reason':f'{type(exc).__name__}: {exc}',
                'newton_admitted':False,'training_admissible':False}
        exit_code=3 if 'MISSING' in str(exc) or 'NOT_A_REAL_FOUR_SIDE_DIRECTORY' in str(exc) else 2
    write_exclusive(args.output,report)
    print(report.get('status', report.get('schema')), file=sys.stderr)
    return exit_code


if __name__=='__main__':
    raise SystemExit(main())
