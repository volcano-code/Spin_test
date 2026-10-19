"""M5 W0/W2 exact-source parity, never evidence of a real Cherchi computation."""
from __future__ import annotations

from fractions import Fraction as F
import hashlib
from pathlib import Path

import pytest

from .cross_oracle_gate import (cross_check_exact_boundary, compare_frozen_fd,
                                git_blob_sha1, load_pinned_w2_oracle,
                                W2_ORACLE_SOURCE_SHA)
from .native_teacher_replay import ReplayRejected


FACES=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
       [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]]


def label(x):return f"{x.numerator}/{x.denominator}"


def box(x0,x1,y0,y1,z0,z1):
    return [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
            (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]


def rational_rows(vertices):return [[label(F(x)) for x in row] for row in vertices]


def oracle_case():
    vertices=box(F(-3,2),F(7,3),F(1,2),F(9,4),F(-2,3),F(11,5))
    # Invertible rational affine transformation, with off-diagonal moments.
    A=((F(2),F(1,3),F(1,4)),(F(0),F(3,2),F(2,3)),(F(0),F(0),F(3,4)))
    t=(F(1,7),F(-2,5),F(3,8))
    return rational_rows([tuple(sum((A[i][j]*v[j] for j in range(3)),t[i])
                                for i in range(3)) for v in vertices]),FACES


def test_pinned_source_is_true_w2_git_blob():
    path=Path(__file__).with_name('w2_reference_snapshot.py')
    assert git_blob_sha1(path.read_bytes())==W2_ORACLE_SOURCE_SHA
    assert hashlib.sha256(path.read_bytes()).hexdigest()=="3238fb14d4cbf85d7754551689fa40cbb08653bf3a9bf631faf16138f9c6bea9"
    assert load_pinned_w2_oracle().POWER_ORDER[7:]==((0,1,1),(1,0,1),(1,1,0))


def test_w0_w2_oblique_closed_box_all_ten_exact():
    v,f=oracle_case()
    report=cross_check_exact_boundary(v,f,'7/4')
    assert report['identical_all_ten'] is True
    assert len(report['exact_r10'])==10
    assert all(F(report['exact_r10'][i])!=0 for i in (7,8,9))
    assert report['independent_w2_source_blob_sha1']==W2_ORACLE_SOURCE_SHA
    assert not report['training_admissible']


def test_w0_w2_shell_and_design_total_exact():
    outer=box(F(-2),F(3),F(-3),F(5),F(-1),F(4))
    inner=box(F(-1,4),F(1,2),F(-1,3),F(2,3),F(1,5),F(3,4))
    shell_vertices=rational_rows(outer+inner)
    shell_faces=FACES+[[i+8 for i in reversed(face)] for face in FACES]
    design_vertices=rational_rows(inner)
    expected_f=cross_check_exact_boundary(shell_vertices,shell_faces,'6/5')['exact_r10']
    expected_d=cross_check_exact_boundary(design_vertices,FACES,'7/4')['exact_r10']
    expected_total=[F(x)+F(y) for x,y in zip(expected_f,expected_d)]
    total=compare_frozen_fd(fixed_boundary=(shell_vertices,shell_faces),
                            design_boundary=(design_vertices,FACES),
                            fixed_density='6/5',design_density='7/4',
                            total_raw_exact=[label(x) for x in expected_total])
    assert total['fixed_added_once'] and not total['geometric_disjointness_proved']
    tampered=[label(x) for x in expected_total]
    tampered[0]=label(expected_total[0]+F(expected_f[0]))
    with pytest.raises(ReplayRejected,match='FIXED_DESIGN_TOTAL'):
        compare_frozen_fd(fixed_boundary=(shell_vertices,shell_faces),
                          design_boundary=(design_vertices,FACES),
                          fixed_density='6/5',design_density='7/4',total_raw_exact=tampered)


def test_w2_pin_tamper_fails_before_import(tmp_path):
    original=Path(__file__).with_name('w2_reference_snapshot.py')
    changed=tmp_path/'oracle.py'
    changed.write_bytes(original.read_bytes()+b'\nraise RuntimeError("SHOULD_NEVER_EXECUTE")\n')
    with pytest.raises(ReplayRejected,match='W2_ORACLE_SOURCE_SHA'):
        load_pinned_w2_oracle(changed)


def test_bad_w2_pin_path_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError):load_pinned_w2_oracle(tmp_path/'notthere.py')


@pytest.mark.parametrize('bad',[
    [0,1,2],None,[],1.75,[0,True,2],
])
def test_invalid_density_token_rejected(bad):
    v,f=oracle_case()
    with pytest.raises(ReplayRejected):cross_check_exact_boundary(v,f,bad)


@pytest.mark.parametrize('bad',['-1/4','0/1','1.0','NaN','1/0','2/01'])
def test_negative_zero_or_nonstrict_density_rejected(bad):
    v,f=oracle_case()
    with pytest.raises((ReplayRejected,ZeroDivisionError)):
        cross_check_exact_boundary(v,f,bad)


def test_wrong_face_orientation_rejected():
    v,faces=oracle_case()
    f=[r.copy() for r in faces];f[0]=f[0][::-1]
    with pytest.raises(ReplayRejected):cross_check_exact_boundary(v,f,'1/1')


def test_nonmanifold_shared_vertex_rejected_even_if_w2_oracle_accepts():
    # Two otherwise-disconnected tetrahedra share just one vertex index 0.
    vs=[['0/1','0/1','0/1'],['1/1','0/1','0/1'],['0/1','1/1','0/1'],['0/1','0/1','1/1'],
        ['2/1','1/1','1/1'],['1/1','2/1','1/1'],['1/1','1/1','2/1']]
    tet=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
    f=tet+[[{0:0,1:4,2:5,3:6}[i] for i in face] for face in tet]
    w2=load_pinned_w2_oracle()
    # W2 checks edges; W0 additionally checks connected fans at shared vertex.
    ref,_=w2.integrate_exact_boundary(vs,f,F(1))
    assert ref[0]>0
    with pytest.raises(ReplayRejected,match='PINCHED_NONMANIFOLD_VERTEX'):
        cross_check_exact_boundary(vs,f,'1/1')


def test_reject_boolean_as_geometry_coordinate():
    v,f=oracle_case();v[0][0]=True
    with pytest.raises(ReplayRejected):cross_check_exact_boundary(v,f,'1/1')


def test_overlapping_individually_closed_solids_are_not_native_geometry_proof():
    # Two overlapping but separately indexed closed tetrahedra are NOT a
    # Boolean union: both signed integrators quite properly add their moments.
    tet=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
    a=[(F(0),F(0),F(0)),(F(1),F(0),F(0)),(F(0),F(1),F(0)),(F(0),F(0),F(1))]
    b=[tuple(v+F(1,4) for v in point) for point in a]
    v=rational_rows(a+b)
    faces=tet+[[i+4 for i in face] for face in tet]
    report=cross_check_exact_boundary(v,faces,'1/1')
    assert report['identical_all_ten']
    assert not report['independent_cherchi_boolean_proof']
    assert not report['complete_material_partition_proof']
    assert not report['training_admissible']


def test_total_r_must_use_exact_rational_strings():
    v,f=oracle_case()
    with pytest.raises(ReplayRejected,match='TEN_CANONICAL_EXACT_TOTAL'):
        compare_frozen_fd(fixed_boundary=(v,f),design_boundary=(v,f),
            fixed_density='1/1',design_density='2/1',
            total_raw_exact=[float(3)]*10)


def test_w2_new_binary64_density_is_exact_as_fraction():
    v,f=oracle_case()
    module=load_pinned_w2_oracle()
    a,_=module.integrate_exact_boundary(v,f,1.25)
    b,_=module.integrate_exact_boundary(v,f,F(5,4))
    assert a==b
    with pytest.raises(ValueError,match='INVALID_BINARY64_DENSITY'):
        module.integrate_exact_boundary(v,f,float('nan'))
