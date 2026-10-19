"""M7 synthetic production-shaped journal — tests DO NOT run or certify Cherchi."""
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from .native_teacher_replay import ReplayRejected, digest, exact_raw_moments
from .terminal_archive_m7 import (SCHEMA, _j_transform, review_pinned_terminal_archive)

C = [0., 0., 0., 1., 0., 0., 0., 0., 0., 0.]
POINTS = [["0/1","0/1","0/1"],["1/1","0/1","0/1"],
          ["0/1","1/1","0/1"],["0/1","0/1","1/1"]]
FACES = [[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
BACKEND = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:" + "a"*64
MAP = "b"*64
PROBLEM = "c"*64


def _save(root, name, content):
    if name == 'events.jsonl':
        source=''.join(json.dumps(x,sort_keys=True,allow_nan=False)+'\n' for x in content)
    else:
        source=json.dumps(content,sort_keys=True,allow_nan=False)+'\n'
    (root/name).write_text(source,encoding='utf-8')
    return hashlib.sha256(source.encode()).hexdigest()


def make_pinned_archive(tmp_path):
    """Return explicitly marked fake, physically consistent journal fixture."""
    root=tmp_path/'synthetic_not_a_native_run'
    root.mkdir()
    exact=exact_raw_moments(tuple(tuple(Fraction(x) for x in p) for p in POINTS),FACES,Fraction(2))
    r=[float(x) for x in exact]
    j=np.eye(10)
    p=np.asarray(C)
    b=np.array([1.]*7+[.5]*3)
    solver_j=(j@((np.eye(10)-np.outer(p,p))*b[None,:])).tolist()
    source_v=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
    source_sha=digest(dict(vertices=source_v,faces=FACES,coefficients=C))
    material=dict(quadric_coefficients=C,variable_rational_vertices=POINTS,
        variable_faces=FACES,variable_raw_moments=r,raw_moments=r,moment_jacobian=j.tolist(),
        material_proof={'schema':'cherchi-same-call-material-v1','exact_vertices':POINTS},
        quadric_source_identity=source_sha,quadric_source_vertices=source_v,
        quadric_source_faces=FACES,geometry_hash=digest(dict(vertices=POINTS,faces=FACES)),
        topology_hash='d'*64,boolean_operation='intersection',
        boolean_backend_identity=BACKEND,evaluation_map_identity=MAP)
    comp=dict(quadric_coefficients=C,quadric_source_identity=source_sha,
              boolean_operation='subtraction',geometry_hash='e'*64,topology_hash='f'*64)
    configuration=dict(schema='cherchi-inprocess-formal-run-v1',initialization='REQUEST_SEED_ONLY',
        boolean_backend_identity=BACKEND,evaluation_map_identity=MAP,
        request={'material_density':2.0,'settings':{'equation_profile':'DUAL_MONOMIAL_RAW_V1',
                                                'equation_tolerance':1e-12}})
    payload=dict(geometry_hash=material['geometry_hash'],boolean_backend_identity=BACKEND,
        evaluation_map_identity=MAP,solver_raw_moments=r,
        variable_raw_moments=r,solver_coordinates=C,
        solver_moment_jacobian=solver_j)
    accepted=dict(type='evaluation',restart=0,evaluation_index=1,outcome='accepted',
                  step=0.15,quadric_coefficients=C,
                  material_geometry_hash=material['geometry_hash'],
                  solver_coordinate_identity='literal_monomial_unit_sphere_v1',
                  evaluation_payload=payload)
    newton=[dict(type='attempt_start',restart=0,evaluation_index=0),accepted,
            dict(type='attempt_terminal',reason='converged',restart=0,evaluation_index=1)]
    run=dict(status='CONVERGED',equation_profile='DUAL_MONOMIAL_RAW_V1',
             raw_equation_residual=3e-14,quadric_coefficients=C,
             function_evaluations=1,events=newton)
    identity=dict(problem_digest=PROBLEM,native_run=run,
                  terminal_complement={'status':'PASSED','geometry_hash':comp['geometry_hash'],
                                       'topology_hash':comp['topology_hash'],
                                       'quadric_source_identity':source_sha},
                  external_terminal_binding={'retained_geometry':material['geometry_hash'],
                      'retained_topology':material['topology_hash'],
                      'complement_geometry':comp['geometry_hash'],
                      'complement_topology':comp['topology_hash'],
                      'fixed_moments_target':[0.]*10,
                      'variable_moments_target':r,'total_moments_target':r})
    events=[{'kind':'NEWTON_EVENT','event':event} for event in newton]
    events.extend([{'kind':'MAP_SAVED','evaluation':1,'evaluation_file':'evaluation-000001.json',
                    'sha256':None,'geometry_hash':material['geometry_hash'],
                    'coefficients':C},
                   {'kind':'RUN_TERMINATED','status':'CONVERGED','evaluation_count':1}])
    pins={}
    for name,obj in [('configuration.json',configuration),('events.jsonl',events),
                     ('evaluation-000001.json',material),('result.json',dict(status='CONVERGED',identity=identity)),
                     ('complete.json',dict(status='CONVERGED',complete=True,evaluation_count=1)),
                     ('terminal-material-reference.json',{}),('terminal-complement.json',comp),
                     ('terminal-complement-reference.json',{}),('native-result.json',{}),
                     ('record-verification.json',{'record_integrity_valid':True,'core_admission':False})]:
        if name in ('terminal-material-reference.json','terminal-complement-reference.json','native-result.json'):
            continue
        pins[name]=_save(root,name,obj)
    # Production MAP_SAVED events bind the material bytes *before* the log is sealed.
    events[-2]['sha256']=pins['evaluation-000001.json']
    pins['events.jsonl']=_save(root,'events.jsonl',events)
    native=dict(schema='cherchi-numerical-terminal-v1',native_run=run,
                configuration_sha256=pins['configuration.json'],material_audit_complete=False)
    pins['native-result.json']=_save(root,'native-result.json',native)
    tr=dict(coefficients=C,evaluation_file='evaluation-000001.json',
            sha256=pins['evaluation-000001.json'],geometry_hash=material['geometry_hash'])
    pins['terminal-material-reference.json']=_save(root,'terminal-material-reference.json',tr)
    cref=dict(schema='cherchi-terminal-complement-reference-v1',
              evaluation_file='terminal-complement.json',
              sha256=pins['terminal-complement.json'],
              retained_reference_sha256=pins['terminal-material-reference.json'],
              configuration_sha256=pins['configuration.json'],material_audit_complete=False)
    pins['terminal-complement-reference.json']=_save(root,'terminal-complement-reference.json',cref)
    contract={'schema':SCHEMA,'files':pins,'expected_c_sha256':digest(C),
              'expected_problem_digest':PROBLEM}
    return root,contract


def test_correctly_pinned_archive_is_numeric_only(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    report=review_pinned_terminal_archive(root,pins)
    assert report['numerical_terminal_record_consistent'] is True
    assert report['exact_rD_reintegrated'] is True
    assert report['raw_equation_residual_recorded']==pytest.approx(3e-14)
    assert report['jacobian_solver_chain_rule_max_error']==0
    assert report['native_full_partition_certified'] is False
    assert report['newton_terminal_independently_certified'] is False
    assert report['training_admissible'] is False


@pytest.mark.parametrize('field,mutate',[
    ('complete.json',lambda x:x.update(status='MAX_EVALUATIONS')),
    ('complete.json',lambda x:x.update(evaluation_count=2)),
    ('result.json',lambda x:x['identity'].update(problem_digest='f'*64)),
    ('result.json',lambda x:x['identity']['native_run'].update(raw_equation_residual=1e-3)),
    ('native-result.json',lambda x:x['native_run'].update(status='FAILED')),
    ('terminal-material-reference.json',lambda x:x.update(sha256='0'*64)),
    ('evaluation-000001.json',lambda x:x['variable_raw_moments'].__setitem__(9,9.0)),
    ('evaluation-000001.json',lambda x:x['moment_jacobian'][7].__setitem__(8,30.)),
    ('evaluation-000001.json',lambda x:x['quadric_source_faces'].append([0,1,2])),
    ('terminal-complement.json',lambda x:x.update(boolean_operation='intersection')),
    ('terminal-complement.json',lambda x:x.update(quadric_source_identity='0'*64)),
    ('terminal-complement-reference.json',lambda x:x.update(sha256='0'*64)),
    ('configuration.json',lambda x:x['request']['settings'].update(equation_tolerance=0.1)),
    ('record-verification.json',lambda x:x.update(core_admission=True)),
])
def test_pins_detect_any_mutated_file(tmp_path,field,mutate):
    root,pins=make_pinned_archive(tmp_path)
    p=root/field
    original=json.loads(p.read_text())
    mutate(original)
    p.write_text(json.dumps(original,allow_nan=False))
    with pytest.raises(ReplayRejected,match='EXTERNALLY_PINNED_SHA_MISMATCH'):
        review_pinned_terminal_archive(root,pins)


@pytest.mark.parametrize('path', ['record-verification.json','terminal-complement.json','evaluation-000001.json'])
def test_missing_file_fails(tmp_path,path):
    root,pins=make_pinned_archive(tmp_path)
    (root/path).unlink()
    with pytest.raises(ReplayRejected,match='ARCHIVE_FILE_MISSING'):
        review_pinned_terminal_archive(root,pins)


def test_symlink_rejected(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    original=root/'result.json'
    saved=root/'some-other-name'
    original.rename(saved)
    original.symlink_to(saved)
    with pytest.raises(ReplayRejected,match='SYMLINK'):
        review_pinned_terminal_archive(root,pins)


def test_changed_external_c_pin_rejected(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    pins['expected_c_sha256']='0'*64
    with pytest.raises(ReplayRejected,match='COEFFICIENT_PIN'):
        review_pinned_terminal_archive(root,pins)


def test_changed_external_problem_pin_rejected(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    pins['expected_problem_digest']='0'*64
    with pytest.raises(ReplayRejected,match='PROBLEM_PIN'):
        review_pinned_terminal_archive(root,pins)


def test_duplicate_json_denied_even_if_pin_recomputed(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    path=root/'complete.json'
    data='{"complete":true,"status":"CONVERGED","status":"CONVERGED","evaluation_count":1}'
    path.write_text(data)
    pins['files']['complete.json']=hashlib.sha256(data.encode()).hexdigest()
    with pytest.raises(ReplayRejected,match='DUPLICATE_JSON_KEY'):
        review_pinned_terminal_archive(root,pins)


def test_mutated_terminal_geometry_denied_even_with_rebased_local_pin(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    name='evaluation-000001.json'
    data=json.loads((root/name).read_text())
    data['variable_rational_vertices'][1][0]='2/1'
    pins['files'][name]=_save(root,name,data)
    # Rebased local hash cannot repair separate scientific geometry identity.
    with pytest.raises(ReplayRejected,match='TERMINAL_MATERIAL_REFERENCE_MISMATCH'):
        review_pinned_terminal_archive(root,pins)


def test_wrong_native_jacobian_projection_is_denied():
    payload={'evaluation_payload':{'solver_moment_jacobian':(np.ones((10,10))*200).tolist(),
                                   'solver_coordinates':C},
             'solver_coordinate_identity':'literal_monomial_unit_sphere_v1'}
    with pytest.raises(ReplayRejected,match='SOLVER_JACOBIAN_CHAIN_RULE_MISMATCH'):
        _j_transform(C,np.eye(10).tolist(),payload)


def test_direct_jc_symmetry_must_not_be_required():
    J=np.eye(10)
    J[0,9]=2.
    c=np.asarray(C)
    inv=np.array([1.]*7+[.5]*3)
    P=np.eye(10)-np.outer(c,c)
    expected=(J@P@np.diag(inv)).tolist()
    packet={'solver_coordinate_identity':'literal_monomial_unit_sphere_v1',
            'evaluation_payload':{'solver_coordinates':C,'solver_moment_jacobian':expected}}
    assert _j_transform(C,J.tolist(),packet)==pytest.approx(0.)


def test_external_pin_set_does_not_allow_missing_material(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    pins['files'].pop('evaluation-000001.json')
    with pytest.raises(ReplayRejected,match='FULL_ARCHIVE_FILE_PINS'):
        review_pinned_terminal_archive(root,pins)


def test_pinned_archive_never_declares_newton_independently_certified(tmp_path):
    root,pins=make_pinned_archive(tmp_path)
    result=review_pinned_terminal_archive(root,pins)
    assert not any(result[field] for field in (
       'production_evidence_verifier_executed','independent_physical_objective_residual_verified',
       'native_full_partition_certified','smooth_derivative_neighborhood_certified',
       'newton_terminal_independently_certified','training_admissible'))
