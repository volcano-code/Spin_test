"""CI reads persisted native results. These tests do NOT rerun native Cherchi."""
import json
from pathlib import Path
import numpy as np

H6=Path(__file__).resolve().parents[1]
NUM=H6/'evidence/three-column-numerical-report.json'
FEAT=H6/'evidence/three-column-feature-classification.json'


def test_native_numerical_pilot_record_not_relabelled_as_formal():
    d=json.loads(NUM.read_text())
    assert d['scope']=='ARCHIVED_V4_PROXY_NOT_AUTHORITATIVE_EVAL60_NOT_FORMAL_HEART'
    assert d['ten_by_ten_jacobian_computed'] is True
    assert d['sample_count']==25
    assert d['columns_evaluated']==[0,4,8]
    assert len(d['checks'])==9
    assert d['all_numerical_checks_passed'] is True
    assert d['all_feature_branches_stable'] is False
    assert d['original_evaluation_60_reproduced'] is False
    assert d['formal_heart_jacobian_qualified'] is False
    assert d['original_newton_converged'] is False
    assert len(d['evaluated_points'])==25
    assert all(z['backend'].startswith('cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:') for z in d['evaluated_points'])
    for k in ('source','boolean','derivative','integration','intersection_motion'):
        assert d['call_counts'][k]==25


def test_real_jacobian_and_numerical_error():
    d=json.loads(NUM.read_text());J=np.asarray(d['jacobian'])
    assert J.shape==(10,10) and np.isfinite(J).all()
    assert len(d['raw_moments'])==10
    assert d['coefficient_scale_null_norm']<1e-8
    assert max(k['maximum_relative_error'] for k in d['checks'])<1e-6
    assert all(k['numeric_passed'] for k in d['checks'])
    assert not all(k['same_feature_branch'] for k in d['checks'])


def test_actual_cherchi_source_stable_but_material_facets_change():
    d=json.loads(FEAT.read_text())
    assert d['scope']=='HISTORICAL_V4_PROXY_ONLY_NOT_AUTHENTIC_EVAL60'
    assert d['evaluated_points']==25 and d['any_change_count']==22
    assert d['feature_changes_by_type']['canonical_triangles']==22
    assert d['feature_changes_by_type']['constructed_vertex_features']==4
    assert d['topology_neighborhood_certified'] is False
    rows=d['rows']
    for label in ('source_faces','source_normal_edges','source_normal_vertices',
        'source_projective_rays','source_face_caps','source_surface_type','source_radius'):
        assert len(set(json.dumps(r[label],sort_keys=True) for r in rows))==1
    assert set(r['source_vertices'] for r in rows)=={168}
    assert set(r['source_faces_count'] for r in rows)=={328}
    assert set(r['geometric_vertices'] for r in rows)=={793}
    assert set(r['geometric_faces'] for r in rows)=={1570}
    assert set(json.dumps(r['type_counts'],sort_keys=True) for r in rows)=={'{"EXPLICIT3D": 269, "LPI": 524}'}


def test_real_native_run_payload_keeps_25_points_and_branch_verdict_distinct():
    n=json.loads(NUM.read_text());f=json.loads(FEAT.read_text())
    assert n['sample_count']==f['evaluated_points']==25
    assert n['columns_evaluated']==f['directions']==[0,4,8]
    assert n['all_numerical_checks_passed'] and not n['all_feature_branches_stable']
    assert not f['topology_neighborhood_certified']
