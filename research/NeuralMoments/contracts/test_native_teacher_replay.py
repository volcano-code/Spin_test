"""M4 negative-case tests use synthetic tetrahedra; never native teacher truth."""
import copy
from fractions import Fraction
import math
from pathlib import Path
import pytest
import numpy as np

from .native_teacher_replay import (
    ReplayRejected, audit_same_call_material, audit_live_native_once,
    affine_target_from_physical, boundary_rows, canonical, digest,
    exact_raw_moments, frac)

P=(('0/1','0/1','0/1'),('1/1','0/1','0/1'),
   ('0/1','1/1','0/1'),('0/1','0/1','1/1'))
F=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
C=[-0.19611613513818404,0.,0.,0.9805806756909202,0.,0.,0.,0.,0.,0.]
BASE='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+'a'*64
FRAME=dict(original_origin=[.25,-.5,0.],normalization_length=2.,target_origin=[.5,-.25,.125],
           target_axes=[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])


def fmt(x):
    return f'{x.numerator}/{x.denominator}'


def fixture():
    points=tuple(tuple(frac(x) for x in row) for row in P)
    target=affine_target_from_physical(points,origin=FRAME['original_origin'],
        length=FRAME['normalization_length'],target_origin=FRAME['target_origin'],
        target_axes=FRAME['target_axes'])
    tokens=[[fmt(c) for c in row] for row in target]
    r=exact_raw_moments(target,tuple(map(tuple,F)),Fraction(2))
    fixed=[2.]+[0.]*9
    source_vertices=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
    source_faces=copy.deepcopy(F)
    saved={
        'quadric_coefficients':list(C), 'geometry_hash':digest(dict(vertices=P,faces=F)),
        'topology_hash':'topology-anchor',
        'evaluation_map_identity':'context-anchor',
        'boolean_backend_identity':BASE,
        'derivative_identity':'cherchi-constructed-vertex-motion-v1',
        'variable_rational_vertices':tokens,
        'variable_vertices':[[float(x) for x in row] for row in target],
        'variable_faces':copy.deepcopy(F),
        'variable_raw_moments':[float(x) for x in r],
        'moment_jacobian':[[0.]*10 for _ in range(10)],
        'derivative_defined':True,
        'quadric_source_vertices':source_vertices,
        'quadric_source_faces':source_faces,
        'quadric_source_identity':digest(dict(vertices=source_vertices,faces=source_faces,
                                             coefficients=C)),
        'material_proof':{'schema':'cherchi-same-call-material-v1',
                          'exact_vertices':[list(x) for x in P]},
    }
    # JSON canonical agrees for P tuple and list.
    mapped={k:copy.deepcopy(v) for k,v in saved.items()
            if k in ('geometry_hash','topology_hash','evaluation_map_identity',
                     'boolean_backend_identity','derivative_identity','moment_jacobian',
                     'variable_raw_moments','derivative_defined')}
    mapped['raw_moments']=[fixed[i]+float(r[i]) for i in range(10)]
    return saved,mapped,fixed,r


def evaluate(saved,mapped,fixed):
    return audit_same_call_material(saved,mapped,native_c=C,density=2.,
        original_origin=FRAME['original_origin'],
        normalization_length=FRAME['normalization_length'],
        target_origin=FRAME['target_origin'],target_axes=FRAME['target_axes'],
        expected_fixed_r=fixed)


def test_independent_rational_tetra_exact_and_cross_terms():
    points,triangles=boundary_rows(P,F)
    r=exact_raw_moments(points,triangles,Fraction(2))
    assert r[0]==Fraction(1,3)
    assert r[1:4]==(Fraction(1,12),)*3
    assert r[4:7]==(Fraction(1,30),)*3
    assert r[7:]==(Fraction(1,60),)*3


def test_same_call_replay_is_numeric_only():
    s,m,f,r=fixture()
    result=evaluate(s,m,f)
    assert result['mathematical_replay_passed']
    assert result['r_D_max_absolute_error']==0.
    assert result['total_max_absolute_error']==0.
    assert not result['native_region_proved']
    assert not result['smooth_derivative_proved']
    assert not result['training_admissible']
    assert result['source_geometry_sha256']==s['geometry_hash']
    assert result['vertex_count']==4 and result['face_count']==4


def test_numpy_native_output_is_accepted_without_claiming_truth():
    s,m,f,_=fixture()
    m['variable_raw_moments']=np.asarray(m['variable_raw_moments'])
    m['raw_moments']=np.asarray(m['raw_moments'])
    m['moment_jacobian']=np.asarray(m['moment_jacobian'])
    assert evaluate(s,m,f)['mathematical_replay_passed']


def test_binary_exact_coordinate_tokens():
    assert frac('0b101/0b10')==Fraction(5,2)
    assert frac('-0b11/0b100')==Fraction(-3,4)


@pytest.mark.parametrize('value',[True,0,3.2,None,'4.5','2/0','01/2','2/-3',
                                   'NaN','2/2/2','+1/2','0b2/2'])
def test_bad_exact_rational_tokens_rejected(value):
    with pytest.raises(ReplayRejected):frac(value)


@pytest.mark.parametrize('attack',[
    lambda s,m,f:s.__setitem__('geometry_hash','a'*64),
    lambda s,m,f:s['material_proof']['exact_vertices'][3].__setitem__(2,'2/1'),
    lambda s,m,f:s['variable_rational_vertices'][0].__setitem__(0,'6/1'),
    lambda s,m,f:s['variable_vertices'][1].__setitem__(0,99.),
    lambda s,m,f:s['variable_faces'].__setitem__(1,[0,3,1]),
    lambda s,m,f:s['variable_faces'].pop(),
    lambda s,m,f:s['variable_faces'].__setitem__(3,[0,1,3]),
    lambda s,m,f:s['variable_raw_moments'].__setitem__(0,500.),
    lambda s,m,f:m['raw_moments'].__setitem__(0,m['raw_moments'][0]+f[0]),
    lambda s,m,f:m['variable_raw_moments'].__setitem__(3,1.),
    lambda s,m,f:m['moment_jacobian'][3].__setitem__(5,7.),
    lambda s,m,f:s['moment_jacobian'][9].__setitem__(9,float('nan')),
    lambda s,m,f:s['quadric_coefficients'].__setitem__(3,-C[3]),
    lambda s,m,f:s.__setitem__('quadric_source_identity','a'*64),
    lambda s,m,f:s.__setitem__('boolean_backend_identity','fake-native'),
    lambda s,m,f:s.__setitem__('derivative_defined',False),
    lambda s,m,f:s['variable_faces'][2].__setitem__(2,True),
    lambda s,m,f:s.__setitem__('variable_rational_vertices',None),
    lambda s,m,f:s.__setitem__('material_proof',None),
])
def test_malicious_mutations_rejected(attack):
    s,m,f,_=fixture();attack(s,m,f)
    with pytest.raises((ReplayRejected,ValueError,OverflowError,TypeError)):
        evaluate(s,m,f)


def test_positive_no_fake_training_admission_even_resealed():
    s,m,f,_=fixture()
    s['material_proof']['certified']=True
    s['material_proof']['native_cherchi']=True
    # A field asserted by the producing code is not an external native proof.
    assert not evaluate(s,m,f)['training_admissible']


def test_exact_affine_nonidentity_cross_term_representation():
    s,m,f,r=fixture()
    # Exact transformed first moments have nonzero x/y/z; no XY double count.
    assert all(r[i] for i in (7,8,9))
    assert evaluate(s,m,f)['r_order'][-3:]==['QYZ','QXZ','QXY']


def test_live_native_execution_blocked_with_fake_evaluator():
    with pytest.raises(ReplayRejected,match='NATIVE_CHERCHI_RUNTIME_UNAVAILABLE'):
        audit_live_native_once(evaluator=object(),problem=None,c=C,pins={})
