"""Pure-Python guards: verify no silent fallback / no invalid OBJ approval."""
import importlib.util
from pathlib import Path
import sys
import numpy as np
import pytest
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'source'))
from cherchi_heart_guard import validate_packet_shape,verify_material,publish,evaluate_proxy,assert_native_boundary,CHERCHI_BACKEND,load_modules

class NativeStub:
    def audit_exact_rational_triangle_boundary(self,*a):
        return {'boundary_valid':True,'intersecting_pair_count':0,'backend':'independent-exact-geometry-audit'}
    def audit_exact_triangle_boundary(self,*a):
        return {'boundary_valid':False,'intersecting_pair_count':78,'backend':'independent-binary64-geometry-audit'}

class InvalidExactStub(NativeStub):
    def audit_exact_rational_triangle_boundary(self,*a):
        return {'boundary_valid':False,'intersecting_pair_count':3}


def packet():
    return {'backend':CHERCHI_BACKEND,'vertices':[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],
            'faces':[[0,1,2],[0,2,3],[0,3,1],[1,3,2]],
            'exact_vertices':[['0','0','0'],['1','0','0'],['0','1','0'],['0','0','1']],
            'construction_records':[{'vertex_index':i,'point_type':'EXPLICIT3D'} for i in range(4)]}

def test_pinned_backend_accepts():
    validate_packet_shape(packet(),'intersection')

def test_backend_impersonation_fails_no_cgal_fallback():
    p=packet();p['backend']='CGAL'
    with pytest.raises(RuntimeError,match='CHERCHI_BACKEND_IDENTITY_MISMATCH_NO_FALLBACK'):
        validate_packet_shape(p,'intersection')

def test_missing_provenance_fails():
    p=packet();del p['construction_records']
    with pytest.raises(ValueError,match='MISSING_CHERCHI_CONSTRUCTION_RECORDS'):
        validate_packet_shape(p,'intersection')

def test_bad_provenance_order_fails():
    p=packet();p['construction_records'][0]['vertex_index']=2
    with pytest.raises(ValueError,match='CHERCHI_PROVENANCE_INDEX_MISMATCH'):
        validate_packet_shape(p,'intersection')

def test_bad_face_index_fails():
    p=packet();p['faces'][0][1]=100
    with pytest.raises(ValueError,match='OUT_OF_RANGE_TRIANGLE_INDICES'):
        validate_packet_shape(p,'intersection')

def test_exact_pass_float_failure_must_reject_obj():
    r=verify_material(NativeStub(),packet(),'intersection')
    assert r['exact_boundary_passed'] and r['binary64_self_intersections']==78
    assert not r['qualified_binary64_obj_export']
    assert not r['full_newton_converged']

def test_invalid_exact_fails():
    with pytest.raises(ValueError,match='CHERCHI_EXACT_RATIONAL_BOUNDARY_REJECTED'):
        verify_material(InvalidExactStub(),packet(),'intersection')

def test_publish_keeps_rationals_but_not_bad_obj(tmp_path):
    result=verify_material(NativeStub(),packet(),'intersection')
    out=tmp_path/'new'
    row=publish(out,packet(),result)
    assert row['status']=='RATIONAL_MATERIAL_ACCEPTED_FLOAT_OBJ_REJECTED'
    assert (out/'cherchi-authoritative-exact.json').exists()
    assert not list(out.glob('*.obj'))

def test_duplicate_output_not_overwritten(tmp_path):
    out=tmp_path/'existing';out.mkdir()
    with pytest.raises(FileExistsError):publish(out,packet(),{})

def test_invalid_input_boundary_rejected():
    with pytest.raises(ValueError,match='DESIGN_SOURCE_INPUT_BOUNDARY_REJECTED'):
        assert_native_boundary(NativeStub(),packet()['vertices'],packet()['faces'],'DESIGN')

def test_only_known_boolean_ops():
    with pytest.raises(ValueError,match='INVALID_BOOLEAN_OPERATION'):
        validate_packet_shape(packet(),'union')
