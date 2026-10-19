"""W0 M9 real evidence and adversarial tests; never promote finite samples."""
from __future__ import annotations

import copy
import gzip
import json
import os
from pathlib import Path
import zipfile

import numpy as np
import pytest

from .real_h8f_81_m9 import (
    ARCHIVE_SHA256, CHANGED, STABLE, RUN_ID, FOCUS_POINTS,
    normalized_constraint, normalized_features, oriented_face_key,
    oriented_triangle_multiset, construction_transition,
    five_point_verification, audit, main, require,
)
from .real_h8e_archive_m8 import ArchiveAuditError, open_pinned


def make_lpi(line=((0,2),(0,3)), plane=((1,5),(1,6),(1,7))):
    return dict(point_type='LPI',operands=[dict(status='UNIQUE',
                source_vertices=[dict(input_object=a,input_vertex=b)]) for a,b in (*line,*plane)])


def test_lpi_endpoint_and_plane_vertex_orders_are_mathematically_equivalent():
    base=make_lpi()
    reordered=copy.deepcopy(base)
    reordered['operands'][0],reordered['operands'][1]=reordered['operands'][1],reordered['operands'][0]
    reordered['operands'][2],reordered['operands'][4]=reordered['operands'][4],reordered['operands'][2]
    assert normalized_constraint(base)==normalized_constraint(reordered)


def test_lpi_changed_support_face_is_not_silently_canonicalized():
    a=make_lpi()
    b=make_lpi(plane=((1,5),(1,6),(1,8)))
    assert normalized_constraint(a)!=normalized_constraint(b)


def test_lpi_line_swapped_with_plane_constraints_is_not_equivalent():
    a=make_lpi()
    b=copy.deepcopy(a)
    b['operands'][1],b['operands'][2]=b['operands'][2],b['operands'][1]
    assert normalized_constraint(a)!=normalized_constraint(b)


@pytest.mark.parametrize('bad', [
    {},
    dict(point_type='LPI',operands=[]),
    dict(point_type='UNSUPPORTED',operands=[]),
])
def test_invalid_construction_schema_fails_closed(bad):
    with pytest.raises(ArchiveAuditError): normalized_constraint(bad)


@pytest.mark.parametrize('kind', ['MISSING','AMBIGUOUS'])
def test_ambiguous_lpi_operand_rejected(kind):
    item=make_lpi()
    item['operands'][0]['status']=kind
    with pytest.raises(ArchiveAuditError, match='UNRESOLVED_CONSTRUCTION_OPERAND'):
        normalized_constraint(item)


def test_duplicate_source_candidates_rejected():
    item=make_lpi()
    item['operands'][0]['source_vertices'].append(dict(input_object=0,input_vertex=4))
    with pytest.raises(ArchiveAuditError, match='NONUNIQUE_CONSTRUCTION_OPERAND'):
        normalized_constraint(item)


def test_boolean_source_index_rejected():
    item=make_lpi()
    item['operands'][0]['source_vertices'][0]['input_vertex']=True
    with pytest.raises(ArchiveAuditError): normalized_constraint(item)


def test_nonnegative_source_index_required():
    item=make_lpi()
    item['operands'][0]['source_vertices'][0]['input_vertex']=-1
    with pytest.raises(ArchiveAuditError): normalized_constraint(item)


def test_oriented_triangle_cycle_invariant_but_winding_matters():
    features=(('E',(0,)),('E',(1,)),('E',(2,)))
    assert oriented_face_key([0,1,2],features)==oriented_face_key([2,0,1],features)
    assert oriented_face_key([0,1,2],features)!=oriented_face_key([2,1,0],features)


def test_invalid_triangle_indices_rejected():
    features=(('E',(0,)),('E',(1,)),('E',(2,)))
    with pytest.raises(ArchiveAuditError):oriented_face_key([0,1,1],features)
    with pytest.raises(ArchiveAuditError):oriented_face_key([0,1,3],features)
    with pytest.raises(ArchiveAuditError):oriented_face_key([0,True,2],features)


def synthetic_points_and_report():
    base=[1.]+[0.]*9
    points=[dict(coefficients=base.copy(),
            independent_variable_raw_moments=[1.]+[0.]*9,
            feature_branch_hash='same') for _ in range(81)]
    checks=[]
    for col in range(10):
        ids0=1+8*col
        for h, positions in [
            (3e-6,[ids0,ids0+1,0,ids0+2,ids0+3]),
            (1.5e-6,[ids0+1,ids0+4,0,ids0+5,ids0+2]),
            (7.5e-7,[ids0+4,ids0+6,0,ids0+7,ids0+5]),
        ]:
            for i,shift in zip(positions,[-h,-h/2,0,h/2,h]):
                points[i]['coefficients'][col]=base[col]+shift
                points[i]['independent_variable_raw_moments'][0]=1.+shift*(col+1)
            checks.append(dict(column=col,step=h,sample_indices=positions,
                               max_scaled_derivative_error=0.,numerical_passed=True,
                               feature_hash_stable=True))
    J=np.zeros((10,10))
    for i in range(10):J[0,i]=i+1
    # Synthetic report need not be a projective invariant: null norm is computed from J@base.
    report=dict(analytic_10_by_10_jacobian=J.tolist(),numeric_checks=checks,
                scale_null_direction_norm=float(np.linalg.norm(J@np.asarray(base))))
    return points,report


def test_synthetic_30_five_point_checks_with_all_columns():
    points,report=synthetic_points_and_report()
    result=five_point_verification(points,report)
    assert result['checked_stencils']==30
    assert result['max_scaled_error']<1e-8
    assert result['original_feature_hash_unstable_stencils']==0


def test_finite_numeric_success_cannot_overrule_feature_hash_drift():
    points,report=synthetic_points_and_report()
    points[60]['feature_branch_hash']='branch_event'
    for row in report['numeric_checks']:
        row['feature_hash_stable']=all(points[i]['feature_branch_hash']=='same'
                                       for i in row['sample_indices'])
    result=five_point_verification(points,report)
    assert result['original_feature_hash_unstable_stencils']==1
    assert result['max_scaled_error']<1e-8


def test_misreported_feature_hash_stability_rejected():
    points,report=synthetic_points_and_report()
    points[60]['feature_branch_hash']='branch_event'
    with pytest.raises(ArchiveAuditError,match='HASH_STABILITY_STATUS_FORGED'):
        five_point_verification(points,report)


def test_misreported_jacobian_precision_rejected():
    points,report=synthetic_points_and_report()
    report['numeric_checks'][0]['max_scaled_derivative_error']=.01
    with pytest.raises(ArchiveAuditError,match='NUMERICAL_REPORT_NOT_REPRODUCED'):
        five_point_verification(points,report)


def test_promoting_original_invalid_states_to_success_is_disallowed():
    for datum in [False,True,None,'false']:
        if datum is not False:
            with pytest.raises(ArchiveAuditError):require(datum is False,'PROMOTION_NOT_ALLOWED')


def test_zip_missing_or_changed_digest_rejected(tmp_path):
    source=tmp_path/'other.zip';source.write_bytes(b'invalid archive bytes')
    with pytest.raises(ArchiveAuditError,match='GITHUB_ARTIFACT_DIGEST_MISMATCH'):
        open_pinned(source,ARCHIVE_SHA256)


def test_m9_refuses_existing_output_even_without_input_archive(tmp_path):
    destination=tmp_path/'immutable.json';destination.write_text('prior result')
    with pytest.raises(FileExistsError,match='DO_NOT_OVERWRITE'):
        main(['--archive',str(tmp_path/'absent.zip'),'--output',str(destination)])
    assert destination.read_text()=='prior result'


def test_m9_requires_pinned_archive(tmp_path):
    with pytest.raises(ArchiveAuditError,match='INVALID_REAL_ZIP_FILE'):
        audit(tmp_path/'no-archive.zip')


def test_real_point60_source_feature_change_from_genuine_archive():
    filename=os.environ.get('W0_M9_REAL_ZIP')
    if not filename:pytest.skip('real GitHub artifact ZIP not attached to this test runner')
    with zipfile.ZipFile(filename) as z:
        root='artifacts/h8f-all81-points/'
        def read(i):return json.loads(gzip.decompress(z.read(root+f'point-{i:03d}-material.json.gz')))
        baseline=read(0);stable=read(59);changed=read(60)
        x=construction_transition(baseline,stable)
        y=construction_transition(baseline,changed)
        assert not x['changed_vertex_indices']
        assert x['normalized_symbolic_triangle_identity']
        assert y['changed_vertex_indices']==[8043,8044,8045,8046,8047]
        assert len(y['added_features'])==len(y['removed_features'])==2
        assert y['removed_oriented_triangles']==y['added_oriented_triangles']==17
        assert y['same_source_faces'] is True
        assert not y['normalized_symbolic_triangle_identity']


def test_real_github_81_sample_end_to_end_readonly():
    filename=os.environ.get('W0_M9_REAL_ZIP')
    if not filename:pytest.skip('real GitHub artifact ZIP not attached to this test runner')
    result=audit(filename,exact_mode='none')
    assert result['original_point_count']==81
    assert result['independent_feature_classification']=={STABLE:79,CHANGED:1}
    assert result['point60_witness']['removed_oriented_triangles']==17
    assert result['numerical']['checked_stencils']==30
    assert result['numerical']['max_scaled_error']<1e-6
    assert result['github_original_workflow_conclusion']=='failure'
    assert result['training_admissible'] is False
    assert result['certified_smooth_neighborhood'] is False
    assert result['newton_converged'] is False
