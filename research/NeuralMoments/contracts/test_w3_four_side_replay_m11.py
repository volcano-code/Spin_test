"""W0 M11: pure/replayed rejection tests; synthetic fixtures are NOT native provenance."""
from __future__ import annotations

import copy
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import os

import numpy as np
import pytest

from .real_h8e_archive_m8 import ArchiveAuditError, canonical_digest, exact_rational_ten_moments
from . import w3_four_side_replay_m11 as m11


def stage9_observed():
    return dict(schema='heart-h9-stage9-real-execution-and-source-integrity-v1',
                historical_run_id=39123384402,historical_actions_conclusion='failure',
                historical_artifact_sha256=m11.ARCHIVE_SHA256,
                new_native_cherchi_calls=0,new_native_four_point_material_archives=0,
                newton_admitted=False)


def test_w3_stage9_real_observation_stays_blocked():
    r=m11.stage9_readiness(stage9_observed())
    assert r['status']=='BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS'
    assert r['w3_new_native_calls']==0
    assert r['w3_new_materials']==0
    assert not r['newton_admitted'] and not r['training_admissible']


@pytest.mark.parametrize('key, value',[
 ('newton_admitted',True),('historical_actions_conclusion','success'),
 ('historical_artifact_sha256','0'*64),('historical_run_id',0),
 ('schema','unknown')
])
def test_w3_stage9_rejects_promoted_or_changed_claims(key,value):
    record=stage9_observed();record[key]=value
    with pytest.raises(ArchiveAuditError,match='M11_STAGE9_EVIDENCE'):
        m11.stage9_readiness(record)


@pytest.mark.parametrize('count,materials,expected',[
 (4,0,'BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS'),
 (3,4,'BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS'),
 (4,4,'W3_REPORTS_FOUR_NATIVE_CALLS_UNVERIFIED_FILES_REQUIRED')
])
def test_even_four_self_declared_calls_without_real_files_not_admitted(count,materials,expected):
    row=stage9_observed();row.update(new_native_cherchi_calls=count,new_native_four_point_material_archives=materials)
    outcome=m11.stage9_readiness(row)
    assert outcome['status']==expected and outcome['training_admissible'] is False


def test_sampling_plan_matches_w3_conditional_proxy_and_not_a_root_certificate():
    plan=m11.expected_plan()
    assert [x['side'] for x in plan]==list(m11.W3_SIDES)
    assert [x['expected_proxy_event_sign'] for x in plan]==[1,1,-1,-1]
    assert all(1.5e-6<x['c7']<3e-6 for x in plan)
    assert all(plan[i]['c7']<plan[i+1]['c7'] for i in range(3))
    assert plan[0]['distance_from_proxy_root']=='-1/10000000'
    assert plan[3]['distance_from_proxy_root']=='1/10000000'


def write_receipt(folder):
    hashes={}
    for name in sorted(m11.FILES_REQUIRED):
        path=folder/name
        path.parent.mkdir(parents=True,exist_ok=True)
        data=(name+' TEST_FIXTURE_NOT_NATIVE').encode()
        path.write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
    receipt={'schema':m11.RECEIPT_SCHEMA,'historical_artifact_sha256':m11.ARCHIVE_SHA256,
             'frozen_w3_head_sha':m11.W3_OBSERVED_STAGE9_HEAD,
             'source_verifier_git_blob':m11.W3_SOURCE_VERIFIER_BLOB,
             'source_workflow_git_blob':m11.W3_FROZEN_WORKFLOW_BLOB,
             'precommitted_native_binary_sha256':{'core':'a'*64,'boolean':'b'*64,'arithmetic':'c'*64},
             'files':hashes}
    p=folder.parent/'externally-collected-test-only.json'
    p.write_text(json.dumps(receipt))
    return p,receipt


def test_external_digest_receipt_positive_synthetic_bytes(tmp_path):
    folder=tmp_path/'w3';p,rec=write_receipt(folder)
    assert m11.check_external_receipt(folder,p)==rec


@pytest.mark.parametrize('mutation',[
 'missing_file','changed_bytes','extra_name','missing_digest',
 'bad_digest','untrusted_head','modified_verifier','wrong_historical_sha','symlink','unfrozen_binary'
])
def test_receipt_fails_closed_on_attack(tmp_path,mutation):
    folder=tmp_path/'w3';p,rec=write_receipt(folder)
    target=folder/'native'/'side-01-left-near.json.gz'
    if mutation=='missing_file':target.unlink()
    elif mutation=='changed_bytes':target.write_bytes(b'NEW_CONTENT')
    elif mutation=='extra_name':rec['files']['native/forged-side.json']='0'*64
    elif mutation=='missing_digest':del rec['files']['native/side-01-left-near.json.gz']
    elif mutation=='bad_digest':rec['files']['native/side-01-left-near.json.gz']='not-a-hash'
    elif mutation=='untrusted_head':rec['frozen_w3_head_sha']='invalid'
    elif mutation=='modified_verifier':rec['source_verifier_git_blob']='f'*40
    elif mutation=='wrong_historical_sha':rec['historical_artifact_sha256']='f'*64
    elif mutation=='unfrozen_binary':rec['precommitted_native_binary_sha256']['core']='bad'
    elif mutation=='symlink':
        target.unlink();target.symlink_to(folder/'run_status.json')
    p.write_text(json.dumps(rec))
    with pytest.raises(ArchiveAuditError):m11.check_external_receipt(folder,p)


def make_toy_side(i=0):
    """Small geometric polynomial toy only; no claim about real native W3 provenance."""
    V=[[0,0,0],[2,0,0],[2,3,0],[0,3,0],[0,0,4],[2,0,4],[2,3,4],[0,3,4]]
    F=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
       [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]]
    vertices=[[f'{p}/1' for p in point] for point in V]
    moments=[float(v) for v in exact_rational_ten_moments(vertices,F,1.)]
    plan=m11.expected_plan()[i]
    q=[0.]*10;q[0]=1.;q[7]=plan['c7']
    sources=[[0.,0.,0.] for _ in range(100)]
    sources[24]=[0.,0.,1. if i<2 else -1.]
    sources[90]=[1.,0.,1. if i<2 else -1.]
    source_faces=[[24,25,90],[24,90,30]]
    J=np.zeros((10,10))
    mat={
      'material_proof':{'schema':'cherchi-same-call-material-v1','exact_vertices':vertices},
      'derivative_defined':True,'boolean_backend_identity':m11.SOURCE_PREFIX+'a'*64,
      'boolean_operation':'intersection','quadric_coefficients':q,
      'variable_rational_vertices':vertices,'variable_faces':F,
      'quadric_source_vertices':sources,'quadric_source_faces':source_faces,
      'topology_hash':'toy-only','variable_raw_moments':moments,
      'moment_jacobian':J.tolist(),
    }
    mat['geometry_hash']=canonical_digest(dict(vertices=vertices,faces=F))
    mat['quadric_source_identity']=canonical_digest(dict(vertices=sources,faces=source_faces,coefficients=q))
    meta={'index':i,'side':plan['side'],'c7':plan['c7'],
          'native_event_sign':plan['expected_proxy_event_sign'],
          'native_geometry_valid':True,'newton_admitted':False,
          'agrees_with_analytic_proxy_sign':True,
          'vertex_count':len(vertices),'face_count':len(F),
          'native_feature_branch_hash':'toy-only',
          'native_material_geometry_hash':mat['geometry_hash'],
          'independent_scaled_moment_error':0.0,
          'independent_ten_mass_moments':moments,
          'native_moment_jacobian_column7':[0.]*10}
    audit_row={'index':i,'side':plan['side'],'c7':plan['c7'],
               'crossing_sign':plan['expected_proxy_event_sign'],
               'vertex_count':len(vertices),'face_count':len(F)}
    return mat,meta,plan,audit_row,q


@pytest.mark.parametrize('i',[0,1,2,3])
def test_crosscheck_actual_fraction_tetra_integral_logic_on_toy(i):
    mat,meta,plan,row,q=make_toy_side(i)
    result=m11.compare_one_side(mat,meta,plan,row,frozen_q=q,
        design_edge=[[.5,-1.,0.],[.5,1.,0.]],density=1.,original_boolean_sha='a'*64)
    assert result['side']==plan['side']
    assert result['exact_moment_max_relative_scaled_error']==0
    assert (Fraction(result['signed_edge_determinant_exact'])>0)==(i<2)
    assert result['native_and_original_boolean_binary_sha_equal']


@pytest.mark.parametrize('attack',[
 'wrong_q','wrong_j','wrong_density','wrong_backend','wrong_reported_moments',
 'wrong_hash','wrong_source_sha','wrong_sign','wrong_side','missing_density',
 'wrong_face','invalid_recorded_moment','wrong_audit_index','forged_numeric_error'
])
def test_one_side_rejects_fake_native_claims(attack):
    m,meta,plan,row,q=make_toy_side()
    density=1.
    if attack=='wrong_q':m['quadric_coefficients'][8]=0.1
    elif attack=='wrong_j':meta['native_moment_jacobian_column7'][0]=1.
    elif attack=='wrong_density':density=2.
    elif attack=='wrong_backend':m['boolean_backend_identity']='not-Cherchi'
    elif attack=='wrong_reported_moments':m['variable_raw_moments'][7]+=1.
    elif attack=='wrong_hash':m['geometry_hash']='bad'
    elif attack=='wrong_source_sha':m['quadric_source_identity']='0'*64
    elif attack=='wrong_sign':meta['native_event_sign']=-1
    elif attack=='wrong_side':meta['side']='right-coarse'
    elif attack=='missing_density':density=0.
    elif attack=='wrong_face':m['variable_faces'][0][0]=3
    elif attack=='invalid_recorded_moment':meta['independent_ten_mass_moments'][0]=float('nan')
    elif attack=='wrong_audit_index':row['index']=3
    elif attack=='forged_numeric_error':meta['independent_scaled_moment_error']=0.01
    with pytest.raises((ArchiveAuditError,ValueError)):
        m11.compare_one_side(m,meta,plan,row,frozen_q=q,
            design_edge=[[.5,-1.,0.],[.5,1.,0.]],density=density,
            original_boolean_sha='a'*64)


def test_pointwise_sha_self_consistency_does_not_imply_same_native_build():
    m,meta,plan,row,q=make_toy_side()
    out=m11.compare_one_side(m,meta,plan,row,frozen_q=q,
         design_edge=[[.5,-1.,0.],[.5,1.,0.]],density=1.,original_boolean_sha='b'*64)
    assert out['native_and_original_boolean_binary_sha_equal'] is False


def test_synthetic_four_side_consistent_secants_do_not_admit_newton():
    records=[]
    for i in range(4):
        r=m11.expected_plan()[i]
        values=[24.]+[0.]*9;values[0]+=2.*r['c7']
        J=[0.]*10;J[0]=2.
        records.append(dict(side=r['side'],c7=r['c7'],r10=values,Jc_column7=J))
    rows=m11.two_sided_derivative_diagnostics(records)
    assert len(rows)==2
    assert max(a['secant_vs_endpoint_average_scaled_error'] for a in rows)<1e-6
    assert all(a['sampling_only_not_continuity_certification'] for a in rows)


@pytest.mark.parametrize('attack',['wrong_order','NaN_J','duplicate_c7','wrong_vector_length'])
def test_one_side_secants_require_finite_ordered_records(attack):
    records=[]
    for i in range(4):
        p=m11.expected_plan()[i]
        records.append(dict(side=p['side'],c7=p['c7'],r10=[1.]*10,Jc_column7=[0.]*10))
    if attack=='wrong_order':records.reverse()
    elif attack=='NaN_J':records[0]['Jc_column7'][0]=float('nan')
    elif attack=='duplicate_c7':records[1]['c7']=records[0]['c7']
    elif attack=='wrong_vector_length':records[2]['r10']=[1.]*9
    with pytest.raises(ArchiveAuditError):m11.two_sided_derivative_diagnostics(records)


def test_cli_emits_resource_evidence_without_w3_materials(tmp_path):
    outfile=tmp_path/'w0-m11-blocker.json'
    assert m11.main(['--output',str(outfile)])==3
    result=json.loads(outfile.read_text())
    assert result['status']=='BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS'
    assert result['training_admissible'] is False
    with pytest.raises(FileExistsError,match='DO_NOT_OVERWRITE'):
        m11.main(['--output',str(outfile)])


def test_cli_with_stale_stage9_observation_is_explicit_block(tmp_path):
    evidence=tmp_path/'w3-stage9.json';evidence.write_text(json.dumps(stage9_observed()))
    out=tmp_path/'block.json'
    assert m11.main(['--w3-stage9-evidence',str(evidence),'--output',str(out)])==3
    assert json.loads(out.read_text())['w3_new_materials']==0


def test_cli_refuses_missing_receipt_and_absent_w3_folder(tmp_path):
    out=tmp_path/'bad.json'
    assert m11.main(['--w3-folder',str(tmp_path/'unknown'),
                     '--external-receipt',str(tmp_path/'missing.json'),
                     '--original-81-archive',str(tmp_path/'missing.zip'),
                     '--output',str(out)])==2
    assert json.loads(out.read_text())['status']=='REJECTED_W3_FOUR_SIDE_REPLAY'


def test_real_historical_81_point_anchor_is_not_new_in_between_sample():
    path=os.environ.get('W0_M11_ORIGINAL_81_ZIP')
    if not path:pytest.skip('real H8f GitHub original ZIP not provided')
    from .h9_event_admission_m10 import audit
    evidence=audit(path)
    assert evidence['actual_new_in_between_native_samples']==0
    assert evidence['original_h8f_job']['conclusion']=='failure'
    assert not evidence['newton_admitted']


def make_structurally_consistent_synthetic_w3_report(tmp_path):
    """A MOCK metadata-only W3 handoff. It has no actual material and no scientific authority."""
    folder=tmp_path/'w3'
    receipt_path,receipt=write_receipt(folder)
    plan=m11.expected_plan()
    binaries=receipt['precommitted_native_binary_sha256']
    run={'schema':'heart-h9-crossing-sides-live-v1',
         'status':'FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED',
         'new_real_native_calls':4,'finished_indices':[0,1,2,3],
         'historical_run_id':m11.HISTORICAL_RUN,
         'historical_run_conclusion':'failure','source_archive_sha256':m11.ARCHIVE_SHA256,
         'binary_hashes':binaries,'plan':plan,
         'native_binary_identical_to_h8f':{'core':False,'boolean':False,'arithmetic':False},
         'newton_admitted':False,'actual_accepted_step':False,
         'actual_smooth_neighborhood_certified':False,'final_heart_obj_produced':False}
    status={'status':'FOUR_NEW_REAL_NATIVE_POINTS_AND_INDEPENDENT_AUDIT_FINISHED_NO_NEWTON',
            'audit_exit_code':0,'newton_admitted':False}
    finite={'schema':'heart-h9-two-sided-finite-jacobian-diagnostics-v1',
            'finite_same_side_pairs':[{'side':'left','indices':[0,1]},
                                      {'side':'right','indices':[2,3]}],
            'newton_admitted':False,'continuous_neighborhood_certified':False}
    rows=[{'index':p['index'],'side':p['side']} for p in plan]
    audit={'schema':'heart-h9-independent-new-side-material-audit-v1',
           'historical_ci_conclusion':'failure','historical_run_id':m11.HISTORICAL_RUN,
           'frozen_artifact_sha256':m11.ARCHIVE_SHA256,
           'new_native_samples_reintegrated':4,
           'every_new_side_reproduces_expected_oriented_edge_sign':True,
           'original_H8f_binaries_identical_to_new_native':run['native_binary_identical_to_h8f'],
           'same_binary_across_runs':False,'sample_diagnostics':rows,
           'one_sided_independent_moment_jacobian_diagnostics':finite,
           'newton_admitted':False,'actual_newton_step_accepted':False,
           'continuous_native_boolean_smooth_stratum_proven':False,'final_heart_obj_produced':False}
    logs=''.join(f'H9_REAL_NATIVE_SIDE_PROBE {i} {p["side"]} {p["expected_proxy_event_sign"]}\n'
                 for i,p in enumerate(plan))
    (folder/'run_status.json').write_text(json.dumps(status))
    (folder/'native/report.json').write_text(json.dumps(run))
    audit['new_native_run_report_sha256']=hashlib.sha256((folder/'native/report.json').read_bytes()).hexdigest()
    (folder/'independent-audit.json').write_text(json.dumps(audit))
    (folder/'probe.stdout.txt').write_text(logs)
    (folder/'audit.stdout.txt').write_text('H9_NEW_NATIVE_SIDES_REINTEGRATED_BUT_NEWTON_STILL_DENIED 4\n')
    reseal_fixture(folder,receipt_path)
    return folder,receipt_path


def reseal_fixture(folder,receipt_path):
    receipt=json.loads(receipt_path.read_text())
    receipt['files']={name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
                      for name in m11.FILES_REQUIRED}
    receipt_path.write_text(json.dumps(receipt))


def test_structural_w3_report_consistency_is_only_a_mock(tmp_path):
    folder,receipt_path=make_structurally_consistent_synthetic_w3_report(tmp_path)
    receipt=m11.check_external_receipt(folder,receipt_path)
    run,audit=m11.check_report_and_logs(folder,receipt)
    assert run['new_real_native_calls']==4
    assert audit['new_native_samples_reintegrated']==4
    # There are no actual real side materials: these tests validate ONLY metadata.
    for name in m11.SIDE_REQUIRED:
        assert b'TEST_FIXTURE_NOT_NATIVE' in (folder/name).read_bytes()


@pytest.mark.parametrize('path,field,new',[
 ('run_status.json','newton_admitted',True),
 ('run_status.json','audit_exit_code',3),
 ('native/report.json','new_real_native_calls',5),
 ('native/report.json','historical_run_conclusion','success'),
 ('native/report.json','actual_smooth_neighborhood_certified',True),
 ('native/report.json','newton_admitted',True),
 ('native/report.json','finished_indices',[0,1,2]),
 ('independent-audit.json','historical_ci_conclusion','success'),
 ('independent-audit.json','new_native_samples_reintegrated',3),
 ('independent-audit.json','continuous_native_boolean_smooth_stratum_proven',True),
 ('independent-audit.json','newton_admitted',True),
 ('independent-audit.json','same_binary_across_runs',True),
])
def test_resealed_mutated_w3_report_is_still_rejected(tmp_path,path,field,new):
    folder,receipt_path=make_structurally_consistent_synthetic_w3_report(tmp_path)
    p=folder/path
    data=json.loads(p.read_text());data[field]=new;p.write_text(json.dumps(data))
    if path=='native/report.json':
        independent=folder/'independent-audit.json';record=json.loads(independent.read_text())
        record['new_native_run_report_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        independent.write_text(json.dumps(record))
    reseal_fixture(folder,receipt_path)
    receipt=m11.check_external_receipt(folder,receipt_path)
    with pytest.raises(ArchiveAuditError):m11.check_report_and_logs(folder,receipt)


def test_pinned_pre_execution_build_hash_must_match_actual_report_even_after_reseal(tmp_path):
    folder,receipt_path=make_structurally_consistent_synthetic_w3_report(tmp_path)
    receipt=json.loads(receipt_path.read_text())
    receipt['precommitted_native_binary_sha256']['boolean']='d'*64
    receipt_path.write_text(json.dumps(receipt))
    check=m11.check_external_receipt(folder,receipt_path)
    with pytest.raises(ArchiveAuditError,match='PRE_EXECUTION_IDENTITY'):
        m11.check_report_and_logs(folder,check)


@pytest.mark.parametrize('attack',['alter_plan','alter_left_right_pairs','change_binary_attestation'])
def test_frozen_receipt_still_rejects_bad_plan_derivative_or_crossbuild_claim(tmp_path,attack):
    folder,receipt_path=make_structurally_consistent_synthetic_w3_report(tmp_path)
    path=folder/'native/report.json' if attack!='alter_left_right_pairs' else folder/'independent-audit.json'
    content=json.loads(path.read_text())
    if attack=='alter_plan':content['plan'][1]['c7']+=1e-8
    elif attack=='alter_left_right_pairs':
        content['one_sided_independent_moment_jacobian_diagnostics']['finite_same_side_pairs'][0]['indices']=[0,2]
    elif attack=='change_binary_attestation':
        content['native_binary_identical_to_h8f']['boolean']=True
    path.write_text(json.dumps(content))
    if path.name=='report.json':
        other=folder/'independent-audit.json';a=json.loads(other.read_text());a['new_native_run_report_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();other.write_text(json.dumps(a))
    reseal_fixture(folder,receipt_path)
    with pytest.raises(ArchiveAuditError):m11.check_report_and_logs(folder,m11.check_external_receipt(folder,receipt_path))
