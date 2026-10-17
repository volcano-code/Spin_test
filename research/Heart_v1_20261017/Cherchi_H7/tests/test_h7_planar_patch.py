"""Pure Python H7 diagnostics; no native Cherchi or formal solve."""
import sys
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'source'))
from h7_planar_patch import (
    exact_surface_boundary_chain,observe_packet,compare_observations,
    canonical_plane,exact_point,construction_features)

def fake_packet(flipped=False):
    vertices=[[0,0,0],[2,0,0],[2,2,0],[0,2,0]]
    faces=[[0,1,3],[1,2,3]] if flipped else [[0,1,2],[0,2,3]]
    records=[dict(vertex_index=i,point_type='EXPLICIT3D',
        operand_coordinates_exact=[list(map(str,v))]) for i,v in enumerate(vertices)]
    return dict(backend='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
        exact_vertices=[list(map(str,v)) for v in vertices],faces=faces,
        construction_records=records),vertices

def fixture_observation(flipped=False):
    packet,design=fake_packet(flipped)
    source=[[x,y,z+1] for x,y,z in design]
    faces=[[0,1,2],[0,2,3]]
    return observe_packet(packet,design,faces,source,faces)

def test_exact_coplanar_diagonal_swap_preserves_oriented_surface():
    v=[[0,0,0],[2,0,0],[2,2,0],[0,2,0]]
    a=[[0,1,2],[0,2,3]];b=[[0,1,3],[1,2,3]]
    assert exact_surface_boundary_chain(v,a)==exact_surface_boundary_chain(v,b)

def test_reverse_winding_and_nonplanar_face_change_boundary():
    v=[[0,0,0],[2,0,0],[2,2,0],[0,2,0]]
    a=[[0,1,2],[0,2,3]]
    assert exact_surface_boundary_chain(v,a)!=exact_surface_boundary_chain(v,[[0,2,1],[0,3,2]])
    warped=[[0,0,0],[2,0,0],[2,2,1],[0,2,0]]
    assert exact_surface_boundary_chain(v,a)!=exact_surface_boundary_chain(warped,a)

def test_reject_exact_zero_area():
    with pytest.raises(ValueError,match='ZERO_AREA'):
        canonical_plane(exact_point([0,0,0]),exact_point([1,0,0]),exact_point([2,0,0]))

def test_coplanar_swap_is_candidate_not_jacobian_certification():
    base=fixture_observation()
    changed=fixture_observation(True)
    report=compare_observations(base,changed)
    assert report['status']=='COPLANAR_RETESS_CANDIDATE_NOT_CERTIFIED'
    assert report['symbolic_patch_boundaries_match']
    assert not report['qualified_smooth_derivative']

def test_identical_symbolic_triangles_also_not_admitted():
    item=fixture_observation()
    assert compare_observations(item,item)['status']=='SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
    assert not compare_observations(item,item)['qualified_boolean_set_continuity']

def test_reject_noncherchi_and_ambiguous_correspondence():
    packet,design=fake_packet()
    source=[[x,y,z+1] for x,y,z in design]
    faces=[[0,1,2],[0,2,3]]
    packet['backend']='CGAL'
    with pytest.raises(ValueError,match='NON_CHERCHI_BACKEND'):
        observe_packet(packet,design,faces,source,faces)
    packet['backend']='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1'
    with pytest.raises(ValueError,match='NON_UNIQUE_OR_MISSING'):
        observe_packet(packet,design,faces,design,faces)

def test_reject_unmatched_exact_constructed_operands():
    packet,design=fake_packet()
    packet['construction_records'][0]['operand_coordinates_exact']=[['1/3','0','0']]
    with pytest.raises(ValueError,match='NON_UNIQUE_OR_MISSING'):
        construction_features(packet,design,[[0,0,2]])

def test_reject_ambiguous_support_planes():
    packet,design=fake_packet()
    source=[[x+4,y,z] for x,y,z in design]
    faces=[[0,1,2],[0,2,3]]
    with pytest.raises(ValueError,match='AMBIGUOUS'):
        observe_packet(packet,design,faces,source,faces)
