from __future__ import annotations
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import pytest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/'source'))
from cherchi_obj_export import (CHERCHI_BOOL,CHERCHI_ID_PREFIX,bound_packet,certified_export,
                                 load_accepted_formal_record,sha)
from cherchi_exact_flip import (fractional_vertices,oriented_edges,ten_moments,plane,
                                assert_local_flip,exact_plane_chain)

H1=HERE.parent/'Heart_Cherchi_H1' # fallback when this H5 is adjacent H1
if not H1.exists():H1=Path('/mnt/data/Heart_Cherchi_H1')
H4=HERE.parent/'Heart_Cherchi_H4'
if not H4.exists():H4=Path('/mnt/data/Heart_Cherchi_H4')

@pytest.fixture(scope='module')
def proxy():return json.loads((H1/'output_proxy_v1/cherchi-authoritative-exact.json').read_text())

def test_generic_packet_is_bound_to_canonical_cherc_backend(proxy):
    v,f,r,x=bound_packet(proxy,formal=False)
    assert len(v)==793 and len(f)==1570 and len(r)==len(x)==793
    assert proxy['backend']==CHERCHI_BOOL

def test_reject_different_boolean_backend(proxy):
    bad=dict(proxy,backend='cgal-candidate-fallback')
    with pytest.raises(ValueError,match='CHERCHI_BACKEND_REQUIRED_NO_FALLBACK'):
        bound_packet(bad,formal=False)

def test_reject_float_rational_mismatch(proxy):
    import copy
    bad=copy.deepcopy(proxy);bad['vertices'][0][0]+=.02
    with pytest.raises(ValueError,match='RATIONAL_FLOAT_VIEW_NOT_IDENTICAL'):
        bound_packet(bad,formal=False)

def test_reject_missing_provenance(proxy):
    bad=dict(proxy,construction_records=[])
    with pytest.raises(ValueError,match='CHERCHI_PROVENANCE_LENGTH_MISMATCH'):
        bound_packet(bad,formal=False)

def test_reject_fake_converged_status_on_proxy(proxy):
    with pytest.raises(ValueError,match='FORMAL_CHERCHI_BACKEND_REQUIRED'):
        bound_packet(proxy,formal=True)

def test_rational_face_flip_exactly_conserves_ten_moments():
    # Four exact coplanar points; outside diameter switches but not the region.
    rational=fractional_vertices([['0','0','0'],['1','0','0'],['1','1','0'],['0','1','0']])
    before=np.array([[0,1,2],[2,3,0]],dtype=np.int32)
    after=np.array([[1,2,3],[3,0,1]],dtype=np.int32)
    assert oriented_edges(before)==oriented_edges(after)
    assert exact_plane_chain(before,rational)==exact_plane_chain(after,rational)
    assert ten_moments(before,rational)==ten_moments(after,rational)

def test_bad_signature_rejected_without_model(tmp_path,proxy):
    class OnlyIdentity:
        __file__=__file__
    with pytest.raises(ValueError,match='NATIVE_BINARY_IDENTITY_MISMATCH'):
        certified_export(proxy,tmp_path/'denied',native=OnlyIdentity(),scope='PROXY',formal=False,expected_native_sha256='0'*64)
    assert not list((tmp_path/'denied').glob('*.obj*'))
    assert (tmp_path/'denied'/'rejected.json').exists()

def test_formal_run_requires_complete_sealed_evidence(tmp_path):
    p=tmp_path/'empty';p.mkdir()
    with pytest.raises(ValueError,match='MISSING_ACCEPTED_RUN_FILE'):
        load_accepted_formal_record(p)

def _formal_fake_run(root,packet):
    root.mkdir()
    c={'boolean_backend_identity':CHERCHI_ID_PREFIX+'abc'}
    (root/'configuration.json').write_text(json.dumps(c))
    q=[0.1]*10
    material={'boolean_backend_identity':c['boolean_backend_identity'], 'material_proof':{
        'schema':'cherchi-same-call-material-v1','construction_records':[{'point_type':'MOCK'}]*3},
        'geometry_hash':'GEOM','topology_hash':'TOP','evaluation_map_identity':'EVAL',
        'quadric_source_identity':'SOURCE','derivative_defined':True,
        'quadric_coefficients':q,'variable_raw_moments':[1]*10,
        'variable_rational_vertices':[['0','0','0'],['1','0','0'],['0','1','0']],
        'variable_vertices':[[0,0,0],[1,0,0],[0,1,0]],'variable_faces':[[0,1,2]]}
    (root/'evaluation-000001.json').write_text(json.dumps(material))
    for name,data in {
       'native-result.json':{'native_run':{'status':'CONVERGED','quadric_coefficients':q},
                             'configuration_sha256':sha(root/'configuration.json')},
       'result.json':{'status':'CONVERGED','identity':{'terminal_complement':{'status':'PASSED'},
                        'external_terminal_binding':{'retained_geometry':'GEOM'}}},
       'complete.json':{'status':'CONVERGED','complete':True},
       'record-verification.json':{'record_integrity_valid':True,'accepted_updates':1},
       'terminal-material-reference.json':{'evaluation_file':'evaluation-000001.json',
           'geometry_hash':'GEOM','sha256':sha(root/'evaluation-000001.json'),'coefficients':q}
    }.items(): (root/name).write_text(json.dumps(data))
    return material

def test_formal_record_is_guarded_but_not_autonomously_accepted(tmp_path):
    p=tmp_path/'run';m=_formal_fake_run(p,None)
    assert load_accepted_formal_record(p)==m
    # A real native audit must still be run: this just validates binding.
    r=json.loads((p/'result.json').read_text());r['identity'].pop('external_terminal_binding')
    (p/'result.json').write_text(json.dumps(r))
    with pytest.raises(ValueError,match='FORMAL_ACCEPTED_SEALED_EVIDENCE_REQUIRED'):
        load_accepted_formal_record(p)

def test_formal_record_rejects_stale_material_checksum(tmp_path):
    p=tmp_path/'run';_formal_fake_run(p,None)
    m=json.loads((p/'evaluation-000001.json').read_text());m['geometry_hash']='CHANGED'
    (p/'evaluation-000001.json').write_text(json.dumps(m))
    with pytest.raises(ValueError,match='TERMINAL_RECORD_MATERIAL_BINDING_MISMATCH'):
        load_accepted_formal_record(p)

def test_formal_record_rejects_wrong_solver_coefficients(tmp_path):
    p=tmp_path/'run';_formal_fake_run(p,None)
    r=json.loads((p/'native-result.json').read_text());r['native_run']['quadric_coefficients']=[1.]*10
    (p/'native-result.json').write_text(json.dumps(r))
    with pytest.raises(ValueError,match='TERMINAL_NEWTON_COEFFICIENTS_MISMATCH'):
        load_accepted_formal_record(p)

@pytest.mark.native
def test_proxy_native_reproduction_matches_h4_faces_and_is_not_a_formal_result(tmp_path,proxy):
    native=pytest.importorskip('_make_it_stand')
    out=tmp_path/'h5-certified'
    before=json.dumps(proxy,sort_keys=True)
    certificate=certified_export(proxy,out,native=native,
        expected_native_sha256='24386389631f9bbeaa3a331fe14dce43eda150f020c7d1d07e9784dc4e63208f',
        scope='ARCHIVED_HEART_V4_PROXY_NOT_AUTHORITATIVE_EVAL60')
    assert certificate['qualified'] is True
    assert certificate['initial_intersections']==78
    assert certificate['final_intersections']==0
    assert certificate['flip_count']==38
    assert certificate['changed_face_rows']==64
    assert certificate['formal_accepted'] is False
    assert certificate['heart_newton_run_performed_here'] is False
    assert certificate['complete_heart_assembly'] is False
    assert before==json.dumps(proxy,sort_keys=True)
    assert (out/'retained-target-normalized.obj').exists()
    assert (out/'certification.json').exists()
    assert not (out/'rejected.json').exists()
    assert (out/'retained-target-normalized.obj').read_text().splitlines()[1:] == \
      (H4/'final_certified/v4-proxy-cherchi-retained-material-retriangulated.obj').read_text().splitlines()[1:]

def test_formal_call_requires_verified_run_path_even_with_structured_packet(tmp_path):
    p=tmp_path/'formal'; m=_formal_fake_run(p,None)
    class Native:
        __file__=__file__
    with pytest.raises(ValueError,match='FORMAL_ACCEPTED_RUN_BINDING_REQUIRED'):
        certified_export(m,tmp_path/'denied',native=Native(),scope='FORMAL',formal=True,
                         expected_native_sha256='0'*64)
    assert not (tmp_path/'denied'/'retained-target-normalized.obj').exists()
    assert (tmp_path/'denied'/'rejected.json').exists()

def test_changed_only_global_moment_proof_is_exact():
    rational=fractional_vertices([['0','0','0'],['1','0','0'],['1','1','0'],['0','1','0'],['0','0','1']])
    before=np.array([[0,1,2],[2,3,0],[0,2,4]],dtype=np.int32)
    after=np.array([[1,2,3],[3,0,1],[0,2,4]],dtype=np.int32)
    changed=np.flatnonzero(np.any(before!=after,axis=1))
    assert changed.tolist()==[0,1]
    assert ten_moments(before[changed],rational)==ten_moments(after[changed],rational)
    assert ten_moments(before,rational)==ten_moments(after,rational)
