"""Discrete feature-branch component fingerprints matching Cherchi's V2 policy."""
from __future__ import annotations
import hashlib
import itertools
import json

def _plain(value):
    return value.tolist() if hasattr(value,"tolist") else value

def _sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def _cyclic_min(face):
    tri=tuple(int(x) for x in face)
    if len(tri)!=3 or len(set(tri))!=3:
        raise ValueError("M29_3_2_2_INVALID_TRIANGLE")
    return min(tri,tri[1:]+tri[:1],tri[2:]+tri[:2])

def _feature_keys(records):
    keys=[]
    normalized=[]
    for record in records:
        operands=[]
        norm_operands=[]
        for operand in record["operands"]:
            candidates=operand["source_vertices"]
            if operand["status"]!="UNIQUE" or len(candidates)!=1:
                raise ValueError("M29_3_2_2_FEATURE_CORRESPONDENCE_UNAVAILABLE")
            candidate=candidates[0]
            pair=(int(candidate["input_object"]),int(candidate["input_vertex"]))
            operands.append(pair)
            norm_operands.append({"status":operand["status"],"refs":[list(pair)]})
        kind=record["point_type"]
        keys.append(json.dumps([kind,operands],separators=(",",":")))
        normalized.append({"point_type":kind,"operands":norm_operands})
    if len(set(keys))!=len(keys):
        raise ValueError("M29_3_2_2_DUPLICATE_FEATURE_KEYS")
    return keys,normalized

def fingerprint_components(operation,faces,source_faces,surface_type,cap_count,source_edges,records):
    faces=_plain(faces);source_faces=_plain(source_faces);source_edges=_plain(source_edges)
    keys,construction=_feature_keys(records)
    triangles=[]
    for face in faces:
        if len(face)!=3 or any(int(i)<0 or int(i)>=len(keys) for i in face):
            raise ValueError("M29_3_2_2_INVALID_FEATURE_FACE")
        # Validate non-degeneracy as well as index range. The production
        # branch identity rejects repeated vertex indices in every triangle.
        _cyclic_min(tuple(int(i) for i in face))
        tri=tuple(keys[int(i)] for i in face)
        triangles.append(min(tri,tri[1:]+tri[:1],tri[2:]+tri[:2]))
    oriented_source=[_cyclic_min(face) for face in source_faces]
    unoriented_source=[min(tuple(p) for p in itertools.permutations(face)) for face in source_faces]
    oriented_source=sorted(oriented_source)
    unoriented_source=sorted(unoriented_source)
    components={
      "operation":str(operation),
      "surface_type":str(surface_type),
      "cap_face_count":int(cap_count),
      "source_faces_ordered_sha256":_sha(source_faces),
      "source_faces_oriented_set_sha256":_sha(oriented_source),
      "source_faces_unoriented_set_sha256":_sha(unoriented_source),
      "source_normal_edges_sha256":_sha(source_edges),
      "construction_signature_sha256":_sha(construction),
      "output_feature_triangles_sha256":_sha(sorted(triangles)),
    }
    branch_payload=dict(policy="SOURCE_FEATURE_BRANCH_V2",operation=operation,
        oriented_material_triangles=sorted(triangles),source_faces=source_faces,
        surface_type=surface_type,cap_count=int(cap_count),source_edges=source_edges)
    components["recomputed_feature_branch_sha256"]=_sha(branch_payload)
    components["source_face_count"]=len(source_faces)
    components["output_feature_triangle_count"]=len(triangles)
    components["construction_record_count"]=len(records)
    components["point_type_counts"]={
      kind:sum(1 for r in records if r["point_type"]==kind)
      for kind in sorted({r["point_type"] for r in records})}
    return components
