"""Fail-closed snapshot identities and archive availability, no native admission."""
import gzip,hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from classify_h8_exact_branch_snapshots import read_one,sha

def test_missing_exact_snapshot_cannot_count_as_certified(tmp_path):
    (tmp_path/'point-000.json').write_text(json.dumps(dict(index=0,exact_same_call_material_archive_sha256='0'*64)))
    with pytest.raises(ValueError,match='MISSING_OR_SHA_MISMATCH'):
        read_one(tmp_path,0,dict(design_vertices=[],design_faces=[]))

def test_unpinned_boolean_rejected_even_if_snapshot_sha_matches(tmp_path):
    material=dict(topology_hash='t',geometry_hash='g',
        quadric_coefficients=[0.]*10,boolean_backend_identity='CGAL')
    archive=tmp_path/'point-000-material.json.gz'
    with gzip.open(archive,'wt') as f:json.dump(material,f)
    point=dict(index=0,coefficients=[0.]*10,
        feature_branch_hash='t',material_geometry_hash='g',
        native_boolean_backend='CGAL',exact_same_call_material_archive_sha256=sha(archive))
    (tmp_path/'point-000.json').write_text(json.dumps(point))
    with pytest.raises(ValueError,match='UNPINNED_DYNAMIC_BOOLEAN'):
        read_one(tmp_path,0,dict(design_vertices=[],design_faces=[]))

def test_wrong_quadrics_rejected_before_classification(tmp_path):
    material=dict(topology_hash='t',geometry_hash='g',
        quadric_coefficients=[1.]*10,boolean_backend_identity='CGAL')
    archive=tmp_path/'point-000-material.json.gz'
    with gzip.open(archive,'wt') as f:json.dump(material,f)
    point=dict(index=0,coefficients=[0.]*10,
        feature_branch_hash='t',material_geometry_hash='g',
        native_boolean_backend='CGAL',exact_same_call_material_archive_sha256=sha(archive))
    (tmp_path/'point-000.json').write_text(json.dumps(point))
    with pytest.raises(ValueError,match='IDENTITY_MISMATCH'):
        read_one(tmp_path,0,dict(design_vertices=[],design_faces=[]))
