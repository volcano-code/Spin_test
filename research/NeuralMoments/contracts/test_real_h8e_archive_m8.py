"""W0 M8 fast fail-closed regression. Full 25-point real audit is explicit opt-in.

No synthetic fixture is ever labelled a live Cherchi run.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import numpy as np
import pytest

from .real_h8e_archive_m8 import (
    ArchiveAuditError, NATIVE_ARCHIVE_SHA256, CLASSIFICATION_ARCHIVE_SHA256,
    check_closed_indexed_surface, exact_rational_ten_moments, target_fixed_moments,
    canonical_digest, open_pinned, read_json, read_member, verify_jacobian_stencils, main,
)


def cube(origin=(0, 0, 0), size=(1, 1, 1)):
    x, y, z = origin
    a, b, c = size
    v = [[x,y,z],[x+a,y,z],[x+a,y+b,z],[x,y+b,z],
         [x,y,z+c],[x+a,y,z+c],[x+a,y+b,z+c],[x,y+b,z+c]]
    f = [[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],
         [3,7,6],[3,6,2],[0,4,7],[0,7,3],[1,2,6],[1,6,5]]
    return [[f'{t}/1' for t in row] for row in v],f


def test_real_tetrahedral_box_all_ten_and_cross_terms():
    v,f=cube((1,2,3),(2,3,4))
    assert check_closed_indexed_surface(f,len(v))==18
    result=exact_rational_ten_moments(v,f,2.)
    # Volume 24, density 2, centroid (2,3.5,5)
    assert result[0]==48
    assert result[1]==96
    assert result[2]==168
    assert result[3]==240
    assert result[4]==48*(2**2+2**2/12)
    assert result[7]==48*3.5*5
    assert result[8]==48*2*5
    assert result[9]==48*2*3.5


def test_density_exact_binary64_not_decimal_guess():
    v,f=cube()
    out=exact_rational_ten_moments(v,f,0.1)
    assert out[0].numerator == (0.1).as_integer_ratio()[0]
    assert out[0].denominator == (0.1).as_integer_ratio()[1]


@pytest.mark.parametrize('mutator,reason',[
    (lambda f:f.pop(), 'EDGE_CLOSURE'),
    (lambda f:f.__setitem__(0,list(reversed(f[0]))),'EDGE_CLOSURE'),
    (lambda f:f.__setitem__(0,[0,0,1]),'DEGENERATE_FACE'),
    (lambda f:f.__setitem__(0,[0,1,99]),'DEGENERATE_FACE'),
])
def test_geometry_faults_rejected(mutator,reason):
    v,f=cube()
    mutator(f)
    with pytest.raises(ArchiveAuditError):check_closed_indexed_surface(f,len(v))


def test_non_rational_and_nonfinite_density_rejected():
    v,f=cube()
    v[0][0]='0.0'
    with pytest.raises(ArchiveAuditError,match='NON_RATIONAL_COORDINATE'):
        exact_rational_ten_moments(v,f,1.)
    v,f=cube()
    with pytest.raises(ArchiveAuditError,match='INVALID_MATERIAL_DENSITY'):
        exact_rational_ten_moments(v,f,float('nan'))


def test_fixed_frame_translation():
    # A point-mass at x=3: M=2,Lx=6,Qxx=18. Shift frame origin x=1.
    r=[2.,6.,0.,0.,18.,0.,0.,0.,0.,0.]
    mapped=target_fixed_moments(r,[1.,0.,0.],np.eye(3))
    np.testing.assert_allclose(mapped,[2.,4.,0.,0.,8.,0.,0.,0.,0.,0.],atol=0)
    with pytest.raises(ArchiveAuditError):target_fixed_moments(r,[0.,0.,0.],np.zeros((3,3)))


def test_artifact_bad_sha_is_rejected(tmp_path):
    p=tmp_path/'artifact.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('test.json','{}')
    with pytest.raises(ArchiveAuditError,match='GITHUB_ARTIFACT_DIGEST_MISMATCH'):
        open_pinned(p,NATIVE_ARCHIVE_SHA256)
    with open_pinned(p,hashlib.sha256(p.read_bytes()).hexdigest()) as z:
        assert read_json(read_member(z,'test.json'))=={}


def test_archive_duplicate_names_and_traversal_rejected(tmp_path):
    p=tmp_path/'unsafe.zip'
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('../oops','a')
    with pytest.raises(ArchiveAuditError,match='UNSAFE_ZIP_MEMBER_PATH'):
        open_pinned(p,hashlib.sha256(p.read_bytes()).hexdigest())


def test_nonfinite_json_rejected():
    with pytest.raises(ArchiveAuditError,match='NONFINITE_JSON_TOKEN'):
        read_json(b'{"a":NaN}')


def test_small_jacobian_stencil_and_false_flags_rejected():
    points=[dict(coefficients=[0.]*10,independent_variable_raw_moments=[0.]*10,
                 feature_branch_hash='same') for _ in range(25)]
    points[0]['coefficients'][0]=1.
    shifts=[-2e-6,-1e-6,0.,1e-6,2e-6]
    indices=[1,2,0,3,4]
    for i,s in zip(indices,shifts):
        points[i]['coefficients'][4]=s
        points[i]['independent_variable_raw_moments'][0]=2*s
    report=dict(analytic_10_by_10_jacobian=np.zeros((10,10)).tolist(),
                scale_null_direction_norm=0.,
                numeric_checks=[dict(column=4,sample_indices=indices,
                                     max_scaled_derivative_error=0.,numerical_passed=False,
                                     feature_hash_stable=True)])
    with pytest.raises(ArchiveAuditError,match='NUMERIC_FIVE_POINT_REPORT_MISMATCH'):
        verify_jacobian_stencils(points,report)
    report['analytic_10_by_10_jacobian'][0][4]=2.
    report['numeric_checks'][0]['max_scaled_derivative_error']=0.
    report['numeric_checks'][0]['numerical_passed']=True
    assert verify_jacobian_stencils(points,report)['check_reproduced_count']==1
    points[3]['feature_branch_hash']='changed'
    with pytest.raises(ArchiveAuditError,match='BRANCH_IDENTITY_FLAG_MISMATCH'):
        verify_jacobian_stencils(points,report)


def test_refuse_overwrite_without_touching_input(tmp_path):
    native=tmp_path/'native.zip';native.write_bytes(b'invalid')
    classify=tmp_path/'classify.zip';classify.write_bytes(b'invalid')
    dest=tmp_path/'output.json';dest.write_text('existing signed evidence')
    rc=main(['--native-archive',str(native),'--classification-archive',str(classify),
             '--output',str(dest)])
    assert rc==4 and dest.read_text()=='existing signed evidence'


def test_failed_archive_creates_explicit_rejected_record(tmp_path):
    native=tmp_path/'native.zip';native.write_bytes(b'invalid')
    classify=tmp_path/'classify.zip';classify.write_bytes(b'invalid')
    dest=tmp_path/'failure.json'
    rc=main(['--native-archive',str(native),'--classification-archive',str(classify),
             '--output',str(dest)])
    assert rc==2
    record=json.loads(dest.read_text())
    assert record['status']=='AUDIT_REJECTED' and record['training_admissible'] is False


def test_actual_archive_identity_only_if_locally_available():
    native=os.environ.get('W0_M8_NATIVE_ARCHIVE')
    classifier=os.environ.get('W0_M8_CLASSIFICATION_ARCHIVE')
    if not native or not classifier:
        pytest.skip('Real GitHub Actions ZIP not present; no synthetic PASS claimed')
    with open_pinned(native,NATIVE_ARCHIVE_SHA256) as zn, open_pinned(classifier,CLASSIFICATION_ARCHIVE_SHA256) as zc:
        report=json.loads(read_member(zn,'artifacts/h8e-jacobian-cols0-4-8/report.json'))
        classification=json.loads(read_member(zc,'twenty-five-exact-construction-classification.json'))
        assert report['completed_samples']==25
        assert report['formal_newton_converged'] is False
        assert report['all_tested_stencils_same_feature_hash'] is False
        assert classification['complete_material_snapshots_verified']==25
        assert classification['certified_smooth_neighborhood'] is False
