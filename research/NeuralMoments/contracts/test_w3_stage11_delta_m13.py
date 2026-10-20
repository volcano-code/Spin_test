from __future__ import annotations
import copy
import gzip
from hashlib import sha256
import json
from pathlib import Path
import os
import pytest

from .archived_raw_c_m13 import RawCRejected
from . import w3_stage11_delta_m13 as guard


def _stage11_evidence():
    return {'schema':'heart-h9-stage11-execution-evidence-v1',
            'branch':'research/neuralmoments-w3-heart-h9-20261019',
            'frozen_ancestor_sha':'0bcc187b3005478baa586a6d6f450e73811ca342',
            'baseline_head_sha':guard.OLD_W3_STAGE10_HEAD,
            'historical_workflow_run_id':39123384402,
            'historical_workflow_run_conclusion':'failure',
            'historical_zip_sha256':guard.H8F_ARCHIVE_SHA256,
            'new_cherchi_native_calls':0,'new_real_native_side_count':0,
            'newton_admitted':False,'heart_final_obj_produced':False,
            'build_preflight_exit':2,'run_preflight_exit':2,
            'tests':{'total_passed':94}}


def _raw(obj):return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()


def _fake_pinned(monkeypatch):
    record=_raw(_stage11_evidence())
    source=b'W3 unverified- source UNVERIFIED_PACKET_PRESERVED_BEFORE_EXACT_BOUNDARY_AUDIT'
    probe=b'W3 capture_same_call then promote_after_full_audit'
    monkeypatch.setattr(guard,'STAGE11_EVIDENCE_SHA1',guard.git_blob_sha1(record))
    monkeypatch.setattr(guard,'STAGE11_CAPTURE_SHA1',guard.git_blob_sha1(source))
    monkeypatch.setattr(guard,'STAGE11_PROBE_SHA1',guard.git_blob_sha1(probe))
    return record,source,probe


def test_conservative_stage11_transition_review(monkeypatch):
    evidence,source,probe=_fake_pinned(monkeypatch)
    result=guard.inspect_stage11(evidence_bytes=evidence,capture_source_bytes=source,probe_source_bytes=probe)
    assert result['new_native_cherchi_calls']==0
    assert result['w3_source_changed_since_m12'] is True
    assert result['stage10_pre_run_lock_reusable_for_stage11'] is False
    assert result['new_pre_run_source_and_binary_lock_required'] is True
    assert result['unverified_capture_is_a_qualified_native_sample'] is False
    assert result['newton_admitted'] is False


@pytest.mark.parametrize('mutation',[('new_cherchi_native_calls',4),('new_real_native_side_count',4),('newton_admitted',True),('historical_workflow_run_conclusion','success'),('heart_final_obj_produced',True),('run_preflight_exit',0)])
def test_stage11_misreported_native_success_rejected(monkeypatch,mutation):
    old,source,probe=_fake_pinned(monkeypatch)
    changed=_stage11_evidence();changed[mutation[0]]=mutation[1]
    monkeypatch.setattr(guard,'STAGE11_EVIDENCE_SHA1',guard.git_blob_sha1(_raw(changed)))
    with pytest.raises(RawCRejected,match='STAGE11_FAILED_NATIVE_STATUS_PROMOTED'):
        guard.inspect_stage11(evidence_bytes=_raw(changed),capture_source_bytes=source,probe_source_bytes=probe)


def test_raw_git_blob_tampering_denied_without_source_repin(monkeypatch):
    evidence,source,probe=_fake_pinned(monkeypatch)
    with pytest.raises(RawCRejected,match='EVIDENCE_GIT_BLOB_CHANGED'):
        guard.inspect_stage11(evidence_bytes=evidence+b' ',capture_source_bytes=source,probe_source_bytes=probe)
    with pytest.raises(RawCRejected,match='CAPTURE_SOURCE_GIT_BLOB_CHANGED'):
        guard.inspect_stage11(evidence_bytes=evidence,capture_source_bytes=source+b'!',probe_source_bytes=probe)


def _create_early_capture(tmp_path,*,idx=0,side='left-coarse',c=None):
    c=c if c is not None else [1.]+[0.]*9
    backend=guard.BACKEND_PREFIX+'some-raw-native-module'
    material={'quadric_coefficients':c,'boolean_backend_identity':backend,
              'material_proof':{'schema':'cherchi-same-call-material-v1'}}
    raw=_raw(material)
    packed=gzip.compress(raw,mtime=0)
    manifest={'schema':'heart-h9-unverified-same-call-checkpoint-v1',
              'index':idx,'side':side,'coefficients':c,'backend_identity':backend,
              'status':'UNVERIFIED_PACKET_PRESERVED_BEFORE_EXACT_BOUNDARY_AUDIT',
              'strict_native_boundary_certified':False,
              'independent_fraction_moments_certified':False,
              'newton_admitted':False,'final_heart_obj_produced':False,
              'archive_sha256':sha256(packed).hexdigest(),
              'material_json_sha256':sha256(raw).hexdigest()}
    stem=f'unverified-{idx:02d}-{side}'
    m=tmp_path/(stem+'.json');g=tmp_path/(stem+'.json.gz')
    m.write_bytes(_raw(manifest));g.write_bytes(packed)
    return manifest,material,m,g


def test_mock_unverified_capture_never_promotes(tmp_path):
    manifest,material,m,g=_create_early_capture(tmp_path)
    result=guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse',expected_raw_c=[1.]+[0.]*9)
    assert result['bytes_internally_consistent'] is True
    assert result['four_verified_sides_completed'] is False
    assert result['producer_runtime_cryptographically_authenticated'] is False
    assert result['training_admissible'] is False
    assert result['status']=='UNVERIFIED_EARLY_CAPTURE_ONLY'


def test_early_capture_sha_changed_rejected(tmp_path):
    manifest,material,m,g=_create_early_capture(tmp_path)
    g.write_bytes(g.read_bytes()+b'bad')
    with pytest.raises(RawCRejected,match='UNVERIFIED_CAPTURE_STATUS_OR_SHA_INVALID'):
        guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse')


def test_early_capture_wrong_expected_raw_c_rejected(tmp_path):
    _create_early_capture(tmp_path)
    with pytest.raises(RawCRejected,match='EXPECTED_RAW_C_MISMATCH'):
        guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse',expected_raw_c=[2.]+[0.]*9)


def test_early_capture_wrong_side_rejected(tmp_path):
    _create_early_capture(tmp_path)
    with pytest.raises(RawCRejected,match='WRONG_W3_SIDE_IDENTITY'):
        guard.inspect_unverified_capture(tmp_path,index=0,side='right-coarse')


def test_unverified_capture_false_green_rejected(tmp_path):
    _,_,m,g=_create_early_capture(tmp_path)
    data=json.loads(m.read_bytes());data['strict_native_boundary_certified']=True
    m.write_bytes(_raw(data))
    with pytest.raises(RawCRejected,match='UNVERIFIED_CAPTURE_STATUS_OR_SHA_INVALID'):
        guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse')


def test_unverified_capture_symlink_rejected(tmp_path):
    _,_,m,g=_create_early_capture(tmp_path)
    link=tmp_path/'linked.gz'
    g.rename(link)
    g.symlink_to(link)
    with pytest.raises(Exception):
        guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse')


def test_unverified_production_material_provenance_tampered_even_if_rehashed(tmp_path):
    man,mat,m,g=_create_early_capture(tmp_path)
    mat['boolean_backend_identity']='fake'
    payload=_raw(mat);p=gzip.compress(payload,mtime=0);g.write_bytes(p)
    man['archive_sha256']=sha256(p).hexdigest()
    man['material_json_sha256']=sha256(payload).hexdigest()
    m.write_bytes(_raw(man))
    with pytest.raises(RawCRejected,match='MATERIAL_SOURCE_C_MISMATCH'):
        guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse')


def test_duplicate_json_keys_rejected(tmp_path):
    _,_,m,_=_create_early_capture(tmp_path)
    m.write_bytes(b'{"schema":"x","schema":"y"}')
    with pytest.raises(Exception):
        guard.inspect_unverified_capture(tmp_path,index=0,side='left-coarse')
