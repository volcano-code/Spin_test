import sys, json, hashlib
from pathlib import Path
import numpy as np
import pytest
import trimesh

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from build_heart_h8 import Config, build, make_asymmetric_heart_polygon
from audit_h8 import audit, triangle_sphere_distance_bound, exact_oriented_partition

@pytest.fixture(scope='module')
def reference(tmp_path_factory):
    path=tmp_path_factory.mktemp('cad')/'output'
    result=build(path,Config(pitch=.033))
    return path,result

def test_asymmetric_heart_polygon_valid():
    p=make_asymmetric_heart_polygon(Config())
    assert p.is_valid and p.area>1 and not p.interiors

def test_exposed_initial_and_partition(reference):
    path,r=reference
    assert r['classification']=='PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED'
    assert r['initial_cad_constructed'] is True
    assert not r['faster_newton_converged']
    assert set(r['all_meshes'])=={'heart_input','shaft','initial_top','fixed_shell','design_domain'}
    assert r['initial_physical']['COM_axis_offset_mm']>1
    assert r['discrete_raw_ten_moment_max_scaled_partition_residual']<1e-10
    for name in ('heart_input','shaft','initial_top','fixed_shell','design_domain'):
        m=trimesh.load(path/(name+'.obj'),force='mesh',process=False)
        assert m.is_watertight and m.is_winding_consistent and m.volume>0

def test_independent_export_partition_check(reference):
    path,_=reference
    report=audit(path)
    assert report['success']
    assert report['exact_oriented_face_chain_cancelled']
    assert report['conservative_all_triangle_pair_distance_lower_bound_mm']>.375
    assert report['native_Cherchi_boolean_performed'] is False
    assert report['formal_newton_qualified'] is False

def test_reject_incorrect_surface_partition(reference):
    path,_=reference
    outer=trimesh.load(path/'initial_top.obj',process=False)
    design=trimesh.load(path/'design_domain.obj',process=False)
    fixed=trimesh.load(path/'fixed_shell.obj',process=False)
    assert exact_oriented_partition(outer,design,fixed)
    invalid=fixed.copy()
    invalid.faces[0]=invalid.faces[0][::-1]
    with pytest.raises(ValueError,match='ORIENTED_CHAIN'):
        exact_oriented_partition(outer,design,invalid)

def test_reject_tampered_sha256(reference):
    path,_=reference
    old=(path/'design_domain.obj').read_bytes()
    try:
        (path/'design_domain.obj').write_bytes(old+b'\n# corruption\n')
        with pytest.raises(ValueError,match='SHA256_DRIFT'):
            audit(path)
    finally:
        (path/'design_domain.obj').write_bytes(old)

def test_reject_wall_resolution_and_bad_geometry():
    with pytest.raises(ValueError,match='TWO_GRID_CELLS'):
        Config(pitch=.05,wall_mm=1.5).validate()
    with pytest.raises(ValueError,match='INVALID_H8_CAD_CONFIG'):
        Config(density_kg_m3=-1).validate()

def test_triangle_sphere_bound_conservative():
    outer=trimesh.creation.box(extents=[2,2,2]);d=outer.copy();d.apply_translation([10,0,0])
    lb=triangle_sphere_distance_bound(outer,d)
    assert 0<lb<=8