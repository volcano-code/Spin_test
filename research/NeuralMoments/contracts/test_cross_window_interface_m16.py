"""M16: source-linked offline contract review, not native certification."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from .cross_window_interface_m16 import (
    audit_pinned, semantic_review, strict_json, source_assignments,
    blob_sha1, InterfaceRejected, RELATIVE, PINS,
)

ROOT=Path(__file__).parent

def documents():
    return {name:(ROOT / relative).read_bytes() for name,relative in RELATIVE.items()}


def test_original_git_blobs_byte_locked():
    docs=documents()
    assert {name:blob_sha1(raw) for name,raw in docs.items()}==PINS


def test_real_four_branch_interface_compatibility_and_denial():
    r=audit_pinned()
    assert r['w2_archived_excluded']==81
    assert r['w5_legacy_expected_schema']=='w2-cherchi-teacher-v1-pre-w0'
    assert r['w5_native_unit_tolerance']==1e-9
    assert r['w0_native_unit_tolerance']==1e-12
    assert not r['w5_current_v2_schema_compatible']
    assert not r['W5_native_training_admitted'] and not r['W6_native_training_admitted']
    assert not r['training_admissible']


def test_v2_without_new_native_release_is_explicitly_excluded():
    r=audit_pinned()
    assert r['w2_formal_teacher_samples']==0
    assert 'W2_FORMAL_NATIVE_JACOBIAN_NOT_RELEASED' in r['blockers']


def test_snapshot_tamper_blocked_before_code_interpretation(tmp_path):
    # Alter only the W5 snapshot while retaining its otherwise valid source.
    docs=documents()
    for name,relative in RELATIVE.items():
        target=tmp_path/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(docs[name])
    with (tmp_path/RELATIVE['w5_contract_gate']).open('ab') as fp:
        fp.write(b'\n# drift\n')
    with pytest.raises(InterfaceRejected,match='SOURCE_GIT_BLOB_DRIFT'):
        audit_pinned(tmp_path)


def test_missing_frozen_source_denied(tmp_path):
    with pytest.raises(InterfaceRejected,match='MISSING_FROZEN_SOURCE'):
        audit_pinned(tmp_path)

@pytest.mark.parametrize('field,value',[
    ('training_samples',1),('native_teacher_runs',1),
    ('schema','w2-cherchi-teacher-v1-pre-w0'),
])
def test_mock_manifest_promotion_fails_semantics(field,value):
    d=documents();manifest=strict_json(d['w2_manifest']);manifest[field]=value
    d['w2_manifest']=json.dumps(manifest).encode()
    with pytest.raises(InterfaceRejected):semantic_review(d)


def test_v2_label_fake_training_split_rejected():
    d=documents();manifest=strict_json(d['w2_manifest'])
    manifest['data_splits']['train'].append({'fake':'released'})
    d['w2_manifest']=json.dumps(manifest).encode()
    with pytest.raises(InterfaceRejected):semantic_review(d)


def test_w5_v2_string_edit_does_not_grant_auto_admission():
    d=documents()
    d['w5_contract_gate']=d['w5_contract_gate'].replace(
        b'w2-cherchi-teacher-v1-pre-w0',b'w2-cherchi-teacher-v2-pre-w0')
    with pytest.raises(InterfaceRejected,match='W5_CONSUMER_VERSION'):
        semantic_review(d)


def test_w6_raise_removed_is_not_accepted():
    d=documents()
    d['w6_teacher_gate']=d['w6_teacher_gate'].replace(
        b'raise TeacherUnavailable(',b'print(')
    with pytest.raises(InterfaceRejected,match='W6_FAIL_CLOSED'):
        semantic_review(d)


def test_duplicate_json_refused():
    with pytest.raises(InterfaceRejected,match='DUPLICATE_JSON_KEY'):
        strict_json(b'{"train":[],"train":[]}')


def test_invalid_nonfinite_json_refused():
    with pytest.raises(InterfaceRejected,match='NONFINITE_JSON'):
        strict_json(b'{"sample":NaN}')


def test_pins_match_git_blob_without_running_foreign_code():
    d=documents()
    root,constants=source_assignments(d['w5_contract_gate'])
    assert root.body and constants['W2_SCHEMA']=='w2-cherchi-teacher-v1-pre-w0'
    assert isinstance(PINS['w6_teacher_gate'],str)
