"""M12: standalone actual W3 Stage10 evidence + *synthetic* collector attacks.

No fake fixture here is asserted to originate from production Cherchi.
"""
from __future__ import annotations

import copy
import gzip
from hashlib import sha256
import json
from pathlib import Path
import os
import pytest

from . import w3_custody_m12 as m12
from . import w3_four_side_replay_m11 as m11
from .test_w3_four_side_replay_m11 import (
    make_structurally_consistent_synthetic_w3_report, make_toy_side,
)
from .real_h8e_archive_m8 import ArchiveAuditError

HERE=Path(__file__).parent
HISTORICAL=Path('/mnt/data/h8f-81-real-cherchi-proof-or-failure.zip')


def raw_stage10():
    return ((HERE/'w3_stage10_execution_snapshot_m12.json').read_bytes(),
            (HERE/'w3_stage10_input_snapshot_m12.json').read_bytes())


def make_prerun(binary=None):
    return {
        'schema':m12.LOCK_SCHEMA,
        'frozen_w3_head_sha':m12.FROZEN_W3_HEAD,
        'source_verifier_git_blob':m11.W3_SOURCE_VERIFIER_BLOB,
        'source_workflow_git_blob':m11.W3_FROZEN_WORKFLOW_BLOB,
        'source_input_gate_git_blob':m12.W3_STAGE10_SOURCE_GATE_BLOB,
        'source_stage10_evidence_git_blob':m12.W3_STAGE10_EXECUTION_BLOB,
        'historical_artifact_sha256':m11.ARCHIVE_SHA256,
        'precommitted_native_binary_sha256':binary or {
            'core':'a'*64,'boolean':'b'*64,'arithmetic':'c'*64},
    }


def encode_prerun(prerun):
    return (json.dumps(prerun,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def lock_bytes(binary=None):
    b=encode_prerun(make_prerun(binary));return b,sha256(b).hexdigest()


def make_synthetic_output(tmp_path):
    """Metadata mock only, NEVER a W3 native proof or real material receipt."""
    folder, _ = make_structurally_consistent_synthetic_w3_report(tmp_path)
    independent=folder/'independent-audit.json'
    audit=json.loads(independent.read_text())
    for i,side in enumerate(m11.W3_SIDES):
        mat,meta,*_=make_toy_side(i)
        stem=f'side-{i:02d}-{side}'
        packed=gzip.compress(json.dumps(mat,sort_keys=True).encode())
        data=folder/'native'/(stem+'.json.gz');data.write_bytes(packed)
        digest=sha256(packed).hexdigest()
        meta['material_sha256']=digest
        (folder/'native'/(stem+'.json')).write_text(json.dumps(meta))
        audit['sample_diagnostics'][i]['new_same_call_material_sha256']=digest
    independent.write_text(json.dumps(audit))
    return folder


def test_actual_stage10_raw_git_blobs_really_match_observed_github():
    ex,inp=raw_stage10()
    assert len(ex)==1001 and len(inp)==1620
    assert m12.git_blob_sha1(ex)=='254e93076d6fbec0a60632cee4c4731945f579d4'
    assert m12.git_blob_sha1(inp)=='8a352efca5f7f88dda24c359b7d5225f10f9cf66'
    a=m12.inspect_frozen_stage10(execution_bytes=ex,input_bytes=inp)
    assert a['status']=='BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS'
    assert a['plan_validated'] and a['new_material_files']==a['new_cherchi_calls']==0
    assert a['training_admissible'] is a['newton_admitted'] is False


@pytest.mark.parametrize('mutation',[
    'execution_status', 'execution_count', 'execution_newton',
    'execution_ci', 'input_point', 'input_newton', 'input_claims_native',
    'input_historical', 'execution_duplicate', 'input_nonfinite',
])
def test_real_stage10_bytes_cannot_be_resealed_to_claim_success(mutation):
    ex,inp=raw_stage10()
    if mutation=='execution_duplicate': ex=ex[:-2]+b',"run_status":"PASS"\n}'
    elif mutation=='input_nonfinite': inp=inp.replace(b'2.1805862283444328e-06',b'NaN')
    else:
        e,i=json.loads(ex),json.loads(inp)
        if mutation=='execution_status':e['run_status']='FOUR_REAL_SAMPLES_FINISHED'
        elif mutation=='execution_count':e['new_native_material_files']=4
        elif mutation=='execution_newton':e['newton_admitted']=True
        elif mutation=='execution_ci':e['github_W3_native_CI_triggered']=True
        elif mutation=='input_point':i['four_new_native_probe_plan'][1]['c7']+=1e-7
        elif mutation=='input_newton':i['newton_admitted']=True
        elif mutation=='input_claims_native':i['actual_native_boolean_result_available']=True
        elif mutation=='input_historical':i['historical_run_conclusion']='success'
        ex=json.dumps(e).encode();inp=json.dumps(i).encode()
    with pytest.raises(ArchiveAuditError):
        m12.inspect_frozen_stage10(execution_bytes=ex,input_bytes=inp)


def test_strict_json_rejects_duplicate_keys_and_nonfinite_even_synthetic():
    with pytest.raises(ArchiveAuditError,match='DUPLICATE'):
        m12.strict_json(b'{"a":1,"a":1}')
    with pytest.raises(ArchiveAuditError,match='NONFINITE'):
        m12.strict_json(b'{"x":Infinity}')


def test_real_stage10_cli_is_necessarily_blocked(tmp_path):
    dest=tmp_path/'readiness.json'
    assert m12.main(['--mode','stage10','--output',str(dest)])==3
    result=json.loads(dest.read_text())
    assert not result['four_native_samples_ready']
    with pytest.raises(FileExistsError):
        m12.main(['--mode','stage10','--output',str(dest)])


def test_pre_run_external_sha_and_frozen_git_sha_can_be_checked():
    b,d=lock_bytes()
    result=m12.check_pre_run_lock(b,expected_sha256=d)
    assert result['frozen_w3_head_sha']==m12.FROZEN_W3_HEAD
    assert result['source_verifier_git_blob']==m11.W3_SOURCE_VERIFIER_BLOB


@pytest.mark.parametrize('tamper',[
    'wrong_external_sha','absent_external_sha','wrong_w3_head','wrong_source_gate',
    'wrong_workflow','wrong_verifier','wrong_stage10_report','wrong_original',
    'binary_missing','binary_invalid','missing_key','extra_key','duplicate_json_key'
])
def test_precommitted_source_lock_rejects_reseal_and_scope_drift(tamper):
    item=make_prerun()
    if tamper=='wrong_external_sha':
        b,d=lock_bytes();d='f'*64
    elif tamper=='absent_external_sha':
        b,d=lock_bytes();d=None
    elif tamper=='duplicate_json_key':
        b,d=lock_bytes();b=b[:-2]+b',"schema":"fake"\n}'
        d=sha256(b).hexdigest()
    else:
        if tamper=='wrong_w3_head':item['frozen_w3_head_sha']='f'*40
        elif tamper=='wrong_source_gate':item['source_input_gate_git_blob']='f'*40
        elif tamper=='wrong_workflow':item['source_workflow_git_blob']='f'*40
        elif tamper=='wrong_verifier':item['source_verifier_git_blob']='f'*40
        elif tamper=='wrong_stage10_report':item['source_stage10_evidence_git_blob']='f'*40
        elif tamper=='wrong_original':item['historical_artifact_sha256']='f'*64
        elif tamper=='binary_missing':del item['precommitted_native_binary_sha256']['arithmetic']
        elif tamper=='binary_invalid':item['precommitted_native_binary_sha256']['boolean']='wrong'
        elif tamper=='missing_key':del item['frozen_w3_head_sha']
        elif tamper=='extra_key':item['self_attested_native_ok']=True
        b=encode_prerun(item);d=sha256(b).hexdigest()
    with pytest.raises(ArchiveAuditError):
        m12.check_pre_run_lock(b,expected_sha256=d)


def test_no_native_material_is_real_block_even_with_precommitted_manifest(tmp_path):
    lock,d=lock_bytes()
    with pytest.raises(ArchiveAuditError,match='NOT_A_REAL_FOUR_SIDE_DIRECTORY'):
        m12.capture_after_native(tmp_path/'W3_not_run',pre_run_lock=lock,
            external_pre_run_sha256=d,original_archive=HISTORICAL)


def test_missing_real_historical_zip_is_independent_block(tmp_path):
    b,d=lock_bytes()
    folder=make_synthetic_output(tmp_path)
    with pytest.raises(ArchiveAuditError,match='ORIGINAL_H8F_ARCHIVE_MISSING'):
        m12.capture_after_native(folder,pre_run_lock=b,
            external_pre_run_sha256=d,original_archive=tmp_path/'fake.zip')


def test_synthetic_positive_receipt_collection_is_only_file_integrity(tmp_path):
    if not HISTORICAL.exists(): pytest.skip('authentic original 81-point ZIP unavailable')
    folder=make_synthetic_output(tmp_path)
    b,d=lock_bytes()
    receipt=m12.capture_after_native(folder,pre_run_lock=b,
        external_pre_run_sha256=d,original_archive=HISTORICAL)
    assert receipt['schema']==m11.RECEIPT_SCHEMA
    assert len(receipt['files'])==13
    assert receipt['frozen_w3_head_sha']==m12.FROZEN_W3_HEAD
    # Crosslinked fixtures are internally consistent, but the full M11 replay
    # MUST reject them as actual Cherchi because their tensors are synthetic.
    frozen=tmp_path/'captured.json';m12.write_exclusive(frozen,receipt)
    assert m11.check_external_receipt(folder,frozen)['files']==receipt['files']
    with pytest.raises((ArchiveAuditError, ValueError, KeyError)):
        m12.verify_collected_receipt(folder,receipt_path=frozen,
            pre_run_lock=b,external_pre_run_sha256=d,original_archive=HISTORICAL)


@pytest.mark.parametrize('attack',['corrupt_gzip','missing_side','symlink','add_unreviewed_side',
                                   'wrong_meta_sha','wrong_jacobian','wrong_binary','wrong_plan'])
def test_collector_rejects_fake_materials_even_with_matching_file_hashes(tmp_path,attack):
    if not HISTORICAL.exists():pytest.skip('authentic original ZIP unavailable')
    folder=make_synthetic_output(tmp_path)
    b,d=lock_bytes()
    target=folder/'native'/'side-00-left-coarse.json.gz'
    if attack=='corrupt_gzip':target.write_bytes(b'garbage-not-gzip')
    elif attack=='missing_side':target.unlink()
    elif attack=='symlink':target.unlink();target.symlink_to(folder/'run_status.json')
    elif attack=='add_unreviewed_side':(folder/'native'/'side-04-fake.json.gz').write_bytes(b'garbage')
    elif attack=='wrong_meta_sha':
        p=folder/'native'/'side-00-left-coarse.json';x=json.loads(p.read_text());x['material_sha256']='f'*64;p.write_text(json.dumps(x))
    elif attack=='wrong_jacobian':
        p=folder/'native'/'side-01-left-near.json.gz';x=json.loads(gzip.decompress(p.read_bytes()))
        x['derivative_defined']=False;p.write_bytes(gzip.compress(json.dumps(x).encode()))
    elif attack=='wrong_binary':
        p=folder/'native'/'report.json';x=json.loads(p.read_text());x['binary_hashes']['boolean']='f'*64;p.write_text(json.dumps(x))
        audit=folder/'independent-audit.json';y=json.loads(audit.read_text())
        y['new_native_run_report_sha256']=sha256(p.read_bytes()).hexdigest();audit.write_text(json.dumps(y))
    elif attack=='wrong_plan':
        p=folder/'native'/'report.json';x=json.loads(p.read_text());x['plan'][2]['c7']+=1e-6;p.write_text(json.dumps(x))
        audit=folder/'independent-audit.json';y=json.loads(audit.read_text());y['new_native_run_report_sha256']=sha256(p.read_bytes()).hexdigest();audit.write_text(json.dumps(y))
    with pytest.raises((ArchiveAuditError,ValueError,KeyError)):
        m12.capture_after_native(folder,pre_run_lock=b,
            external_pre_run_sha256=d,original_archive=HISTORICAL)


def test_postrun_early_failure_never_creates_success_receipt(tmp_path):
    lock,d=lock_bytes()
    dest=tmp_path/'failed.json'
    rc=m12.main(['--mode','capture','--w3-folder',str(tmp_path/'missing'),
        '--pre-run-lock',str(tmp_path/'frozen.json'),
        '--external-pre-run-sha256',d,
        '--historical-archive',str(HISTORICAL),
        '--output',str(dest)])
    assert rc in (2,3)
    x=json.loads(dest.read_text())
    assert x['status']=='BLOCKED_OR_REJECTED_FOUR_SIDE_EVIDENCE'
    assert x['training_admissible'] is False


def test_written_output_can_never_overwrite_previous_failed_report(tmp_path):
    target=tmp_path/'prior-failure.json'
    target.write_text('{"status":"historical_failure"}')
    with pytest.raises(FileExistsError):
        m12.write_exclusive(target,{'status':'made-up-success'})
    assert json.loads(target.read_text())['status']=='historical_failure'


def test_output_symlinks_rejected_even_if_target_absent(tmp_path):
    real=tmp_path/'original.txt';real.write_text('DO NOT ALTER')
    link=tmp_path/'link.json';link.symlink_to(real)
    with pytest.raises(FileExistsError):m12.write_exclusive(link,{'anything':True})
    assert real.read_text()=='DO NOT ALTER'
