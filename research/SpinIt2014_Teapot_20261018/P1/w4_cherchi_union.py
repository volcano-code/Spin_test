#!/usr/bin/env python3
"""W4's Cherchi-only three-solid union contract, with no CGAL fallback.

Requires a pinned native _cherchi_core_boolean compiled with operation='union'.
The frozen common binding currently exposes only intersection/difference, so
W4 must NOT pass this gate or pretend a CGAL result came from Cherchi.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import numpy as np
import trimesh

from p2_self_intersection import check_nonincident_triangle_contacts

P0_SOURCE_SHA256='1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4'
P1_CANDIDATE_SHA256='3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47'
BACKEND='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1'


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_sources(p0,p1):
    if digest_file(p0)!=P0_SOURCE_SHA256: raise ValueError('ORIGINAL_SOURCE_SHA_MISMATCH')
    if digest_file(p1)!=P1_CANDIDATE_SHA256: raise ValueError('P1_SHA_MISMATCH')


def import_native(path):
    path=Path(path)
    if not path.is_file(): raise RuntimeError('CHERCHI_NATIVE_MODULE_NOT_INSTALLED')
    if '_cherchi_core_boolean' not in path.name: raise ValueError('WRONG_NATIVE_MODULE_FILENAME')
    spec=importlib.util.spec_from_file_location('_cherchi_core_boolean',path)
    if spec is None or spec.loader is None:raise RuntimeError('CHERCHI_NATIVE_MODULE_UNLOADABLE')
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    if not callable(getattr(module,'boolean',None)):raise RuntimeError('CHERCHI_BOOLEAN_NOT_EXPORTED')
    return module


def check_result(packet, native_sha):
    if packet.get('backend')!=BACKEND:raise ValueError('NON_CHERCHI_BACKEND_REJECTED')
    if not isinstance(packet.get('construction_records'),list) or not isinstance(packet.get('exact_vertices'),list):
        raise ValueError('CHERCHI_EXACT_PROVENANCE_MISSING')
    v=np.asarray(packet.get('vertices',[]),dtype=np.float64)
    f=np.asarray(packet.get('faces',[]),dtype=np.int64)
    if v.ndim!=2 or v.shape[1:]!=(3,) or f.ndim!=2 or f.shape[1:]!=(3,) or len(f)<4:
        raise ValueError('CHERCHI_MALFORMED_MESH')
    if len(packet['exact_vertices'])!=len(v) or len(packet['construction_records'])!=len(v):
        raise ValueError('CHERCHI_EXACT_LENGTH_MISMATCH')
    if not np.isfinite(v).all() or f.min()<0 or f.max()>=len(v):raise ValueError('CHERCHI_MESH_NONFINITE_OR_INDEX')
    # The exact-to-float conversion and topology need separate precise audits.
    mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
    if not mesh.is_volume:raise ValueError('CHERCHI_OUTPUT_NOT_CLOSED_OR_INVERTED')
    if len(mesh.split(only_watertight=False))!=1:raise ValueError('CHERCHI_OUTPUT_NOT_SINGLE_COMPONENT')
    contacts=check_nonincident_triangle_contacts(v,f,max_witnesses=8)
    if contacts['witnesses'] or not contacts['exhaustive']:
        raise ValueError('CHERCHI_OUTPUT_FLOAT_SELF_CONTACT')
    return mesh, dict(native_sha256=native_sha,backend=packet['backend'],
                      vertices=len(v),triangles=len(f),volume=float(mesh.volume),
                      float_sat_nonincident_pairs=contacts['evaluated_nonincident_aabb_pairs'],
                      exact_vertices_provided=True,exact_retriangulation_certified=False)


def union_three(p0,p1,native_module,output,expected_native_sha256):
    """Two actual Cherchi union calls; fail closed on current unsupported op."""
    p0,p1,output=map(Path,(p0,p1,output))
    require_sources(p0,p1)
    module=import_native(native_module)
    module_sha=digest_file(native_module)
    if expected_native_sha256!=module_sha:
        raise ValueError('CHERCHI_NATIVE_BINARY_SHA_MISMATCH')
    source=trimesh.load_mesh(p1,process=False)
    parts=sorted(source.split(only_watertight=False),key=lambda m:len(m.faces),reverse=True)
    if len(parts)!=3 or [len(m.faces) for m in parts]!=[4800,840,840] or not all(m.is_volume for m in parts):
        raise ValueError('UNEXPECTED_P1_COMPONENTS')
    records=[]
    solid=parts[0]
    for stage, operand in enumerate(parts[1:],start=1):
        t=time.perf_counter()
        try:
            packet=module.boolean(np.asarray(solid.vertices).tolist(),
                                  np.asarray(solid.faces,dtype=np.int64).tolist(),
                                  np.asarray(operand.vertices).tolist(),
                                  np.asarray(operand.faces,dtype=np.int64).tolist(),'union')
        except Exception as exc:
            raise RuntimeError(f'CHERCHI_UNION_NATIVE_FAILED_STAGE_{stage}: {type(exc).__name__}: {exc}') from exc
        solid,proof=check_result(packet,module_sha)
        proof.update(stage=stage,seconds=time.perf_counter()-t)
        records.append(proof)
    # Output only after BOTH genuine native calls and independent floating gates.
    output.mkdir(parents=True,exist_ok=True)
    obj=output/'teapot-cherchi-only-union-pending-exact-review.obj'
    solid.export(obj)
    if not trimesh.load_mesh(obj,process=False).is_volume:
        obj.unlink(missing_ok=True)
        raise ValueError('CHERCHI_OBJ_ROUNDTRIP_INVALID')
    manifest=dict(schema='w4-teapot-cherchi-two-unions-v1',
                  status='CHERCHI_FLOAT_GEOMETRY_PASS_EXACT_CERTIFICATION_PENDING',
                  source_sha256=digest_file(p0),p1_sha256=digest_file(p1),
                  native_module_sha256=module_sha,obj_sha256=digest_file(obj),
                  stages=records,physical_frame_authorized=False,
                  teacher_labels_generated=0,mujoco_truth_authorized=False,
                  boolean_backend='CHERCHI_ONLY_NO_CGAL_FALLBACK')
    (output/'cherchi-result.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--p1',required=True,type=Path)
    p.add_argument('--native-module',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--expected-native-sha256',required=True)
    a=p.parse_args()
    print(json.dumps(union_three(a.source,a.p1,a.native_module,a.out,a.expected_native_sha256),indent=2))
