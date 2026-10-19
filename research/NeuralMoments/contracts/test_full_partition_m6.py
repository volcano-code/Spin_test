"""W0 M6 pure rational / contract unit tests. NO native geometry is run."""
from __future__ import annotations

from fractions import Fraction as F
import copy
import math
import numpy as np
import pytest

from .full_partition_m6 import (
    inverse3_exact, parse_exact_points, partition_result,
    physical_from_target_points, to_rational_tokens)
from .native_teacher_replay import ReplayRejected, affine_target_from_physical


def v3():
    return ((F(-1,3), F(2,7), F(5,6)), (F(0), F(1,8), F(-3,5)),
            (F(12,17), F(-4,9), F(7,13)), (F(1,2), F(3,5), F(4,7)))


def affine():
    # In production Eigen axes may be only approximately orthogonal in
    # binary64. Exact rational inverse is required, NEVER simply transpose.
    return [[0.8,-0.6,0.0],[0.6,0.8,0.0],[0.0,0.0,1.0]]


def frame():
    return dict(original_origin=(0.7,-0.125,0.3),
                normalization_length=2.5,
                target_origin=(-0.2,0.125,0.7),target_axes=affine())


def test_exact_target_roundtrip_uses_rational_inverse_not_transpose():
    physical=v3();p=frame()
    target=affine_target_from_physical(physical,origin=p['original_origin'],
       length=p['normalization_length'],target_origin=p['target_origin'],
       target_axes=p['target_axes'])
    rebuilt=physical_from_target_points(to_rational_tokens(target),**p)
    assert tuple(rebuilt)==physical
    A=tuple(tuple(F.from_float(x) for x in row) for row in p['target_axes'])
    B=inverse3_exact(p['target_axes'])
    assert all(sum(A[i][k]*B[k][j] for k in range(3))==int(i==j)
               for i in range(3) for j in range(3))
    assert B != tuple(zip(*A)) # nonexact orthonormal columns are NOT exact inverse.


def test_exact_shear_scale_translation():
    p=dict(original_origin=(.7,0.,-1.),normalization_length=1.7,
           target_origin=(.1, -.4,0.),target_axes=[[1.,.25,0.],[0.,1.,.5],[0.,0.,1.]])
    target=affine_target_from_physical(v3(),origin=p['original_origin'],
          length=p['normalization_length'],target_origin=p['target_origin'],
          target_axes=p['target_axes'])
    assert physical_from_target_points(to_rational_tokens(target),**p)==v3()


def test_binary64_rotation_differs_from_exact_transpose():
    theta=.43
    A=[[math.cos(theta),-math.sin(theta),0.],
       [math.sin(theta),math.cos(theta),0.],[0.,0.,1.]]
    inv=inverse3_exact(A)
    assert inv[0][1]!=F.from_float(A[1][0]) or inv[1][0]!=F.from_float(A[0][1])


@pytest.mark.parametrize('bad',[
    [[1.,0.,0.],[1.,0.,0.],[0.,0.,1.]],
    [[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]],
])
def test_exact_singular_frame_rejected(bad):
    with pytest.raises(ReplayRejected,match='SINGULAR_EXACT_TARGET_FRAME'):
        inverse3_exact(bad)


@pytest.mark.parametrize('bad',[
    [[1,True,0],[0,1,0],[0,0,1]], [[1,0,0],[0,float('nan'),0],[0,0,1]],
    [[1,0,0],[0,1,0]],[1,2,3]
])
def test_invalid_axes_type_nonfinite_bool_rejected(bad):
    with pytest.raises(ReplayRejected): inverse3_exact(bad)


@pytest.mark.parametrize('bad',[
    [['0.0','0/1','0/1']], [['1/0','0/1','0/1']],
    [['1/1',1,'0/1']], [['0/1','0/1']], None,[],[True],
])
def test_non_exact_vertex_tokens_rejected(bad):
    with pytest.raises(ReplayRejected):parse_exact_points(bad)


def good_partition(part_count=3):
    return dict(completed=True,complete_partition=True,union_equals_whole=True,
        no_positive_volume_overlap=True,part_subset_whole=[True]*part_count,
        missing_whole_content=False,excess_union_content=False,
        positive_volume_overlap_pairs=[],partition_digest='a'*64)


def test_native_result_flags_require_all_predicates():
    outcome=partition_result(good_partition(),'outer',3)
    assert outcome['structural_flags_checked']
    assert not outcome['proves_actual_native_execution']
    assert outcome['part_count']==3


@pytest.mark.parametrize('field,replacement',[
    ('completed',False),('complete_partition',False),('union_equals_whole',False),
    ('no_positive_volume_overlap',False),('missing_whole_content',True),
    ('excess_union_content',True),('part_subset_whole',[True,False,True]),
    ('part_subset_whole',[True]),('part_subset_whole',[True,1,True]),
    ('positive_volume_overlap_pairs',[[0,1]]),('positive_volume_overlap_pairs',None),
    ('partition_digest',None),('partition_digest','f'*63),('partition_digest','z'*64),
])
def test_malformed_native_partition_result_always_denied(field,replacement):
    record=good_partition()
    record[field]=replacement
    with pytest.raises(ReplayRejected):partition_result(record,'outer',3)


def test_requires_exact_partition_part_count():
    with pytest.raises(ReplayRejected,match='SUBSET'):
        partition_result(good_partition(3),'design',2)


def test_missing_native_runtime_fails_before_promoting_geometry():
    from .full_partition_m6 import audit_native_full_partition_once
    with pytest.raises(ReplayRejected):
        audit_native_full_partition_once(evaluator=object(),problem=object(),c=[1.]*10,pins={})
