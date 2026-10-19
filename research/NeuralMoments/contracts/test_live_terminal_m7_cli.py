"""M7 CLI actually executes pinned archive review, never launches native."""
import json
from pathlib import Path
import pytest
from .native_teacher_replay import digest
from .live_terminal_m7_cli import main
from .test_terminal_archive_m7 import make_pinned_archive
from .test_m7_evidence_chain import make_parts
from .terminal_archive_m7 import review_pinned_terminal_archive


def inputs(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    p=tmp_path/'external-pins.json';p.write_text(json.dumps(pins))
    return root,p


def test_pinned_archive_review_cli_fails_closed_about_training(tmp_path,capsys):
    root,pins=inputs(tmp_path)
    out=tmp_path/'m7-review.json'
    result=main(['--archive',str(root),'--pins',str(pins),'--output',str(out)])
    assert result==0
    record=json.loads(out.read_text())
    assert record['status']=='NUMERICAL_ARCHIVE_CONSISTENT_NOT_NATIVE_CERTIFICATE'
    assert not record['training_admissible']
    assert not record['newton_terminal_independently_certified']


def test_cli_requires_pinned_production_module_for_next_trust_gate(tmp_path):
    root,pins=inputs(tmp_path);out=tmp_path/'blocked.json'
    code=main(['--archive',str(root),'--pins',str(pins),'--output',str(out),
               '--require-production-record','--production-verifier-sha256','f'*64])
    assert code in (3,4) # environment may contain production verifier but synthetic run must fail
    report=json.loads(out.read_text())
    assert report['status'] in ('BLOCKED_PRODUCTION_VERIFIER_UNAVAILABLE',
                                'FAILED_CLOSED_TERMINAL_REVIEW')
    assert not report['training_admissible']


def test_externally_pinned_M6_identity_chain_cli(tmp_path):
    root,pins=inputs(tmp_path)
    report=review_pinned_terminal_archive(root,json.loads(pins.read_text()))
    m6=make_parts(report)
    f=tmp_path/'m6-review.json';f.write_text(json.dumps(m6))
    out=tmp_path/'m7-with-m6.json'
    code=main(['--archive',str(root),'--pins',str(pins),'--partition',str(f),
               '--partition-sha256',digest(m6),'--output',str(out)])
    assert code==0
    saved=json.loads(out.read_text())
    assert saved['status']=='M6_TERMINAL_IDENTITY_CONSISTENT_NO_NATIVE_CERTIFICATE'
    assert saved['M6_cross_commit_identity_check']['exact_partition_predicate_count']==3
    assert not saved['M6_cross_commit_identity_check']['training_admissible']


def test_missing_sha_or_partition_does_not_pass(tmp_path):
    root,pins=inputs(tmp_path);out=tmp_path/'bad.json'
    assert main(['--archive',str(root),'--pins',str(pins),
                 '--partition',str(tmp_path/'no-m6.json'),'--output',str(out)])==4
    assert json.loads(out.read_text())['status']=='FAILED_CLOSED_TERMINAL_REVIEW'


def test_existing_failure_report_never_overwritten(tmp_path):
    root,pins=inputs(tmp_path)
    out=tmp_path/'prior-failure.json';out.write_text('unchanged-data')
    assert main(['--archive',str(root),'--pins',str(pins),'--output',str(out)])==4
    assert out.read_text()=='unchanged-data'


def test_corrupted_external_pins_are_rejected(tmp_path):
    root,pins=inputs(tmp_path);pins.write_text('{}')
    out=tmp_path/'invalid-pins.json'
    assert main(['--archive',str(root),'--pins',str(pins),'--output',str(out)])==4
    assert json.loads(out.read_text())['status']=='FAILED_CLOSED_TERMINAL_REVIEW'


def test_missing_archive_results_in_not_converged_evidence(tmp_path):
    root,pins=inputs(tmp_path);out=tmp_path/'no-archive.json'
    assert main(['--archive',str(tmp_path/'missing'),'--pins',str(pins),'--output',str(out)])==4
    assert json.loads(out.read_text())['status']=='FAILED_CLOSED_TERMINAL_REVIEW'
