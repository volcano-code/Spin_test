"""Strict Cherchi-material authority gate for Heart experiments.

Production Boolean: ONLY the linked _cherchi_core_boolean native module. CGAL is
allowed only as an independent read-only exact geometry auditor. A rejected
binary64 output is NOT silently repaired/exported as a qualified OBJ.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np

CHERCHI_BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1'


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_modules(native=None, cherchi=None):
    if native is None:
        import _make_it_stand as native
    if cherchi is None:
        try:
            import _cherchi_core_boolean as cherchi
        except (ImportError, OSError) as exc:
            raise RuntimeError('CHERCHI_REQUIRED_NO_FALLBACK') from exc
    if not callable(getattr(cherchi, 'boolean', None)):
        raise RuntimeError('CHERCHI_BOOLEAN_REQUIRED_NO_FALLBACK')
    return native, cherchi


def assert_native_boundary(native, vertices, faces, label):
    facts=dict(native.audit_exact_triangle_boundary(
        np.asarray(vertices,dtype=np.float64),np.asarray(faces,dtype=np.int32),'AnyNonzero'))
    if not facts.get('boundary_valid',False):
        raise ValueError(f'{label}_SOURCE_INPUT_BOUNDARY_REJECTED')
    return facts


def _valid_faces(faces, num_vertices):
    f=np.asarray(faces)
    if f.ndim!=2 or f.shape[1]!=3 or not np.issubdtype(f.dtype,np.integer):
        raise ValueError('INVALID_TRIANGLE_INDICES')
    if f.size==0 or f.min()<0 or f.max()>=num_vertices:
        raise ValueError('OUT_OF_RANGE_TRIANGLE_INDICES')
    return np.asarray(f,dtype=np.int32)


def _as_vertices(rows):
    a=np.asarray(rows,dtype=np.float64)
    if a.ndim!=2 or a.shape[1]!=3 or not len(a) or not np.isfinite(a).all():
        raise ValueError('INVALID_VERTEX_COORDINATES')
    return a


def validate_packet_shape(packet, operation):
    if not isinstance(packet,dict):
        raise ValueError('INVALID_CHERCHI_PACKET')
    if packet.get('backend') != CHERCHI_BACKEND:
        raise RuntimeError('CHERCHI_BACKEND_IDENTITY_MISMATCH_NO_FALLBACK')
    if operation not in ('intersection','difference'):
        raise ValueError('INVALID_BOOLEAN_OPERATION')
    v=_as_vertices(packet.get('vertices'))
    f=_valid_faces(packet.get('faces'),len(v))
    exact=packet.get('exact_vertices')
    provenance=packet.get('construction_records')
    if not isinstance(exact,list) or len(exact)!=len(v):
        raise ValueError('MISSING_CHERCHI_EXACT_VERTICES')
    if not isinstance(provenance,list) or len(provenance)!=len(v):
        raise ValueError('MISSING_CHERCHI_CONSTRUCTION_RECORDS')
    for index,(triple,item) in enumerate(zip(exact,provenance)):
        if not isinstance(triple,list) or len(triple)!=3 or not all(isinstance(x,str) and x for x in triple):
            raise ValueError('MALFORMED_CHERCHI_EXACT_VERTEX')
        if not isinstance(item,dict) or item.get('vertex_index')!=index:
            raise ValueError('CHERCHI_PROVENANCE_INDEX_MISMATCH')
    return v,f


def verify_material(native, packet, operation):
    vertices,faces=validate_packet_shape(packet,operation)
    exact=dict(native.audit_exact_rational_triangle_boundary(
        packet['exact_vertices'],faces,'AnyNonzero'))
    floating=dict(native.audit_exact_triangle_boundary(vertices,faces,'AnyNonzero'))
    if not exact.get('boundary_valid',False):
        raise ValueError('CHERCHI_EXACT_RATIONAL_BOUNDARY_REJECTED')
    return {
        'cherchi_backend':packet['backend'],
        'independent_exact_auditor':exact.get('backend'),
        'independent_binary64_auditor':floating.get('backend'),
        'exact_boundary_passed':True,
        'exact_self_intersections':exact.get('intersecting_pair_count',len(exact.get('intersecting_pairs',[]))),
        'binary64_boundary_passed':bool(floating.get('boundary_valid',False)),
        'binary64_self_intersections':floating.get('intersecting_pair_count',len(floating.get('intersecting_pairs',[]))),
        'vertices':len(vertices),'faces':len(faces),
        'qualified_binary64_obj_export':bool(floating.get('boundary_valid',False)),
        'complete_formal_heart_evaluation':False,
        'full_newton_converged':False,
        'independent_exact_set_equality_verified':False,
    }


def evaluate_proxy(native, cherchi, fixture):
    if fixture.get('classification')!='ARCHIVED_HEART_V4_PROXY_NOT_AUTHORITATIVE_EVAL60':
        raise ValueError('UNAUTHORIZED_INPUT_CLASSIFICATION')
    req=fixture['request'];cfg=native.SpinTriangulationSettings()
    for key,value in fixture['source_settings'].items(): setattr(cfg,key,value)
    cfg.maximum_icosphere_subdivisions=cfg.icosphere_subdivisions
    cfg.paper_projective_hyperboloid=True
    cfg.retain_fixed_normal_provenance=True
    origin=np.asarray(req['target_origin']);axes=np.asarray(req['target_axes'])
    design=(_as_vertices(req['design_vertices'])-origin)@axes.T
    design_faces=_valid_faces(req['design_faces'],len(design))
    assert_native_boundary(native,design,design_faces,'DESIGN')
    src=native.evaluate_spin_it_faster_source_motion(np.asarray(fixture['q']),design,cfg)
    if not src.get('defined') or not src.get('side_selection_defined'):
        raise ValueError('ACTUAL_QUADRIC_SOURCE_UNDEFINED')
    source=_as_vertices(src['vertices']);source_faces=_valid_faces(src['faces'],len(source))
    assert_native_boundary(native,source,source_faces,'SOURCE')
    op='intersection' if src['interior_is_positive'] else 'difference'
    packet=cherchi.boolean(design.tolist(),design_faces.tolist(),source.tolist(),source_faces.tolist(),op)
    report=verify_material(native,packet,op)
    report.update({'input_classification':fixture['classification'],'source_faces':len(source_faces),
                   'design_faces':len(design_faces),'boolean_operation':op,
                   'source_defined':True,'algorithm_boolean_fallback_count':0})
    return packet,report


def publish(output:Path,packet,report):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    # Keep the actual Cherchi rational geometry and provenance; do NOT emit a
    # misleading float OBJ for an independently rejected binary64 boundary.
    (output/'cherchi-authoritative-exact.json').write_text(
        json.dumps({key:packet[key] for key in ('backend','vertices','faces','exact_vertices','construction_records')},
                   separators=(',',':'),allow_nan=False))
    report=dict(report,exact_material_json_sha256=digest(output/'cherchi-authoritative-exact.json'))
    report['status']='RATIONAL_MATERIAL_ACCEPTED_FLOAT_OBJ_REJECTED' if not report['binary64_boundary_passed'] else 'RATIONAL_AND_BINARY64_BOUNDARY_PASSED'
    (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    return report
