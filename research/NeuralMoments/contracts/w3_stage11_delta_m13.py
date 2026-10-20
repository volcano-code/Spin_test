"""W0 M13: review W3 Stage11 source transition without promoting early packets.

This module is read-only. A W3 `unverified-*` same-call checkpoint is merely a
forensic artifact saved *before* exact Nef geometry and Fraction checks. It is
NOT a completed 4-point teacher audit and NEVER makes W0/M11 receipts valid.
W0 M12 Stage10 pre-run lock is NOT reusable after a W3 source revision.
"""
from __future__ import annotations
import gzip
from hashlib import sha1, sha256
import io
import json
from pathlib import Path

from .archived_raw_c_m13 import _binary64_vector, RawCRejected, require
from .w3_custody_m12 import read_regular, strict_json

BASE_W0_HEAD = 'deb8efb26da1401f0bbe462299119c52e5d142c7'
OLD_W3_STAGE10_HEAD = '324256786bc189abbbb93452ed2627cfe0b28a13'
NEW_W3_STAGE11_HEAD = '8322f381ee23f26ef6be0378bba7d4cececbb60e'
STAGE11_EVIDENCE_SHA1 = '342b5e6968ba029c2af389de8de4a394543f422e'
STAGE11_CAPTURE_SHA1 = '22a62f46a458452186126ae571b50a44212197aa'
STAGE11_PROBE_SHA1 = '083ea0075d9df7d71f97e77591a18f5453691665'
STAGE11_VERIFIER_SHA1 = '375fc1f3f04e110563ab53281200d99041cf12cd'
H8F_ARCHIVE_SHA256 = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
W3_SIDES=('left-coarse','left-near','right-near','right-coarse')
BACKEND_PREFIX='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'


def git_blob_sha1(raw:bytes) -> str:
    return sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()


def inspect_stage11(*, evidence_bytes, capture_source_bytes, probe_source_bytes):
    """Require ACTUAL Git-blob-equivalent raw bytes, not self-reported SHA."""
    require(type(evidence_bytes) is bytes and
            git_blob_sha1(evidence_bytes)==STAGE11_EVIDENCE_SHA1,
            'W3_STAGE11_EVIDENCE_GIT_BLOB_CHANGED')
    require(type(capture_source_bytes) is bytes and
            git_blob_sha1(capture_source_bytes)==STAGE11_CAPTURE_SHA1,
            'W3_STAGE11_CAPTURE_SOURCE_GIT_BLOB_CHANGED')
    require(type(probe_source_bytes) is bytes and
            git_blob_sha1(probe_source_bytes)==STAGE11_PROBE_SHA1,
            'W3_STAGE11_PROBE_SOURCE_GIT_BLOB_CHANGED')
    report=strict_json(evidence_bytes)
    require(type(report) is dict and
            report.get('schema')=='heart-h9-stage11-execution-evidence-v1' and
            report.get('branch')=='research/neuralmoments-w3-heart-h9-20261019' and
            report.get('frozen_ancestor_sha')=='0bcc187b3005478baa586a6d6f450e73811ca342' and
            report.get('baseline_head_sha')==OLD_W3_STAGE10_HEAD and
            report.get('historical_workflow_run_id')==39123384402 and
            report.get('historical_workflow_run_conclusion')=='failure' and
            report.get('historical_zip_sha256')==H8F_ARCHIVE_SHA256 and
            report.get('new_cherchi_native_calls')==0 and
            report.get('new_real_native_side_count')==0 and
            report.get('newton_admitted') is False and
            report.get('heart_final_obj_produced') is False and
            report.get('build_preflight_exit')==2 and
            report.get('run_preflight_exit')==2 and
            report.get('tests',{}).get('total_passed')==94,
            'W3_STAGE11_FAILED_NATIVE_STATUS_PROMOTED')
    # The capture checkpoint is written before numeric or geometry audit.
    require(b'unverified-' in capture_source_bytes and
            b'UNVERIFIED_PACKET_PRESERVED_BEFORE_EXACT_BOUNDARY_AUDIT' in capture_source_bytes and
            b'promote_after_full_audit' in probe_source_bytes and
            b'capture_same_call' in probe_source_bytes,
            'W3_STAGE11_UNVERIFIED_CAPTURE_SEMANTICS_MISSING')
    return {
        'schema':'W0_M13_W3_STAGE11_SOURCE_CHANGE_REVIEW_V1',
        'w3_stage10_previous_head':OLD_W3_STAGE10_HEAD,
        'w3_stage11_verified_head':NEW_W3_STAGE11_HEAD,
        'w3_stage11_evidence_git_blob':STAGE11_EVIDENCE_SHA1,
        'capture_source_git_blob':STAGE11_CAPTURE_SHA1,
        'probe_source_git_blob':STAGE11_PROBE_SHA1,
        'historical_h8f_ci':'failure',
        'new_native_cherchi_calls':0,
        'new_verified_four_side_packets':0,
        'w3_source_changed_since_m12':True,
        'stage10_pre_run_lock_reusable_for_stage11':False,
        'new_pre_run_source_and_binary_lock_required':True,
        'unverified_capture_is_a_qualified_native_sample':False,
        'M11_four_verified_sides_admitted':False,
        'newton_admitted':False,
        'training_admissible':False,
        'status':'W3_STAGE11_SOURCE_CHANGED_NO_NEW_NATIVE_SAMPLE'}


def _ungzip_bounded(packed,max_output=30_000_000):
    chunks=[];total=0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(packed),mode='rb') as z:
            while data:=z.read(1_048_576):
                total+=len(data)
                require(total<=max_output,'UNVERIFIED_GZIP_UNBOUNDED')
                chunks.append(data)
    except (OSError,EOFError) as exc:
        raise RawCRejected('UNVERIFIED_GZIP_CORRUPT') from exc
    require(total>0,'EMPTY_UNVERIFIED_MATERIAL')
    return b''.join(chunks)


def inspect_unverified_capture(native_dir,*,index,side,expected_raw_c=None):
    """Only diagnose an unverified W3 early packet, NEVER count it as native.

    Source/build attestation is external; these bytes can be fully simulated.
    The hash check establishes byte consistency of two files, NOT origin.
    """
    require(type(index) is int and 0<=index<4 and side==W3_SIDES[index],
            'WRONG_W3_SIDE_IDENTITY')
    root=Path(native_dir)
    stem=f'unverified-{index:02d}-{side}'
    manifest=strict_json(read_regular(root/(stem+'.json'),max_size=500_000))
    packed=read_regular(root/(stem+'.json.gz'),max_size=10_000_000)
    require(type(manifest) is dict and
            manifest.get('schema')=='heart-h9-unverified-same-call-checkpoint-v1' and
            manifest.get('index')==index and manifest.get('side')==side and
            manifest.get('status')=='UNVERIFIED_PACKET_PRESERVED_BEFORE_EXACT_BOUNDARY_AUDIT' and
            manifest.get('strict_native_boundary_certified') is False and
            manifest.get('independent_fraction_moments_certified') is False and
            manifest.get('newton_admitted') is False and
            manifest.get('final_heart_obj_produced') is False and
            manifest.get('archive_sha256')==sha256(packed).hexdigest(),
            'UNVERIFIED_CAPTURE_STATUS_OR_SHA_INVALID')
    decoded=_ungzip_bounded(packed)
    require(sha256(decoded).hexdigest()==manifest.get('material_json_sha256'),
            'UNVERIFIED_JSON_SHA_INVALID')
    material=strict_json(decoded)
    raw=manifest.get('coefficients')
    _binary64_vector(raw)
    require(material.get('quadric_coefficients')==raw and
            material.get('boolean_backend_identity')==manifest.get('backend_identity') and
            type(manifest.get('backend_identity')) is str and
            manifest['backend_identity'].startswith(BACKEND_PREFIX) and
            material.get('material_proof',{}).get('schema')=='cherchi-same-call-material-v1',
            'UNVERIFIED_MATERIAL_SOURCE_C_MISMATCH')
    if expected_raw_c is not None:
        _binary64_vector(expected_raw_c)
        require(raw==expected_raw_c,'UNVERIFIED_CAPTURE_EXPECTED_RAW_C_MISMATCH')
    return {'schema':'W0_M13_W3_UNVERIFIED_CAPTURE_DIAGNOSTIC_V1',
            'index':index,'side':side,
            'capture_gzip_sha256':sha256(packed).hexdigest(),
            'capture_json_sha256':sha256(decoded).hexdigest(),
            'numeric_native_c_sha256':sha256(__import__('struct').pack('!10d',*_binary64_vector(raw))).hexdigest(),
            'bytes_internally_consistent':True,
            'producer_runtime_cryptographically_authenticated':False,
            'unverified_checkpoint_counted_as_native_side':False,
            'full_native_geometry_certified':False,
            'four_verified_sides_completed':False,
            'newton_admitted':False,
            'training_admissible':False,
            'status':'UNVERIFIED_EARLY_CAPTURE_ONLY'}
