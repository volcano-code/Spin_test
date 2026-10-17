"""Conservative exact planar-patch diagnostics for Cherchi material snapshots.

Read-only: no Boolean fallback, material edits, or smooth-branch certification.
Across changing q compare symbolic input-face supports and construction identities,
not raw geometric planes, which naturally move.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from fractions import Fraction as Q
from hashlib import sha256
from math import gcd, lcm
import json

CHERCHI_PREFIX = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-'

def digest(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(',', ':'),default=str).encode()).hexdigest()

def exact_point(row):
    if len(row)!=3:raise ValueError('POINT_MUST_HAVE_THREE_COORDINATES')
    return tuple(Q(x) if isinstance(x,(str,int,Q)) else Q(float(x)) for x in row)

def canonical_plane(a,b,c):
    u=tuple(b[i]-a[i] for i in range(3));v=tuple(c[i]-a[i] for i in range(3))
    normal=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
    if normal==(0,0,0):raise ValueError('ZERO_AREA_EXACT_TRIANGLE')
    vals=(*normal,-sum(normal[i]*a[i] for i in range(3)))
    denom=lcm(*(x.denominator for x in vals))
    ints=tuple(x.numerator*(denom//x.denominator) for x in vals)
    factor=gcd(*ints);ints=tuple(n//factor for n in ints)
    if next(n for n in ints if n)<0:ints=tuple(-n for n in ints)
    return ints

def _face_indices(face,vertex_count):
    if len(face)!=3 or any(isinstance(v,bool) or not isinstance(v,int) or v<0 or v>=vertex_count for v in face):
        raise ValueError('INVALID_TRIANGLE_INDEX')
    a,b,c=face
    if len({a,b,c})!=3:raise ValueError('REPEATED_TRIANGLE_VERTEX')
    return a,b,c

def exact_surface_boundary_chain(exact_vertices,faces):
    """Exact oriented plane/edge boundary chains, ONLY for same q/coordinates.

    Cancels opposing coplanar interior edges. Nonconforming T-junctions remain
    observable rather than silently certified as identical boundaries.
    """
    points=tuple(exact_point(p) for p in exact_vertices)
    chains=defaultdict(Counter)
    for face in faces:
        a,b,c=_face_indices(face,len(points))
        plane=canonical_plane(points[a],points[b],points[c])
        for i,j in ((a,b),(b,c),(c,a)):
            if points[i]==points[j]:raise ValueError('ZERO_LENGTH_EDGE')
            chains[plane][(points[i],points[j])]+=1
            chains[plane][(points[j],points[i])]-=1
    return tuple(sorted((plane,tuple(sorted((edge,count) for edge,count in edges.items() if count)))
             for plane,edges in chains.items() if any(edges.values())))

def support_groups(design_vertices,design_faces,source_vertices,source_faces):
    """Exact plane -> all input face indices, grouped by operand identity."""
    planes=defaultdict(lambda:defaultdict(list))
    for obj,(vertices,faces) in enumerate(((design_vertices,design_faces),(source_vertices,source_faces))):
        points=tuple(exact_point(v) for v in vertices)
        for idx,face in enumerate(faces):
            a,b,c=_face_indices(face,len(points))
            planes[canonical_plane(points[a],points[b],points[c])][obj].append(idx)
    return {plane:tuple((obj,tuple(ids)) for obj,ids in sorted(items.items()))
            for plane,items in planes.items()}

def construction_features(packet,design_vertices,source_vertices):
    """Exact typed operand provenance; reject ambiguous or missing matches."""
    lookup=defaultdict(list)
    for obj,vertices in enumerate((design_vertices,source_vertices)):
        for i,point in enumerate(vertices):lookup[exact_point(point)].append((obj,i))
    records=packet['construction_records']
    if len(records)!=len(packet['exact_vertices']):
        raise ValueError('CONSTRUCTION_RECORD_COUNT_MISMATCH')
    out=[]
    for idx,rec in enumerate(records):
        if rec.get('vertex_index')!=idx:raise ValueError('CONSTRUCTION_RECORD_INDEX_MISMATCH')
        kind=rec['point_type'];operands=rec['operand_coordinates_exact']
        expected={'EXPLICIT3D':1,'LPI':5,'TPI':9,'LNC':2}.get(kind)
        if expected is None or len(operands)!=expected:raise ValueError('UNSUPPORTED_CONSTRUCTION_ARITY')
        refs=[]
        for tokens in operands:
            candidates=lookup[exact_point(tokens)]
            if len(candidates)!=1:raise ValueError('NON_UNIQUE_OR_MISSING_EXACT_OPERAND_CORRESPONDENCE')
            refs.append(candidates[0])
        if kind=='LPI':
            ref=(kind,tuple(sorted(refs[:2])),tuple(sorted(refs[2:])))
        elif kind=='TPI':
            ref=(kind,tuple(sorted(tuple(sorted(refs[j:j+3])) for j in (0,3,6))))
        else:
            ref=(kind,tuple(refs))
        out.append(ref)
    if len(set(out))!=len(out):raise ValueError('DUPLICATED_CONSTRUCTION_FEATURE')
    return tuple(out)

def observe_packet(packet,design_vertices,design_faces,source_vertices,source_faces):
    """Conservative symbolic patch witness for ONE real Cherchi Boolean result.

    Patch correspondence alone is not a smoothness or Boolean-set certificate.
    """
    if not str(packet.get('backend','')).startswith(CHERCHI_PREFIX):
        raise ValueError('NON_CHERCHI_BACKEND')
    points=tuple(exact_point(p) for p in packet['exact_vertices'])
    features=construction_features(packet,design_vertices,source_vertices)
    if not packet['faces']:raise ValueError('EMPTY_MATERIAL')
    groups=support_groups(design_vertices,design_faces,source_vertices,source_faces)
    patch_edges=defaultdict(Counter);triangles=[]
    for face in packet['faces']:
        a,b,c=_face_indices(face,len(points))
        candidates=groups.get(canonical_plane(points[a],points[b],points[c]),())
        if len(candidates)!=1:raise ValueError('AMBIGUOUS_OR_UNSUPPORTED_OPERAND_FACE_PLANE')
        support=candidates[0]
        feat=(features[a],features[b],features[c])
        triangles.append((support,min(feat,feat[1:]+feat[:1],feat[2:]+feat[:2])))
        for i,j in ((a,b),(b,c),(c,a)):
            if points[i]==points[j]:raise ValueError('ZERO_LENGTH_EDGE')
            edge=(features[i],features[j])
            patch_edges[support][edge]+=1
            patch_edges[support][(edge[1],edge[0])]-=1
    boundaries=tuple(sorted((patch,tuple(sorted((edge,n) for edge,n in es.items() if n)))
                            for patch,es in patch_edges.items()))
    return dict(schema='heart-h7-surface-combinatorics-v1',
        vertex_count=len(points),face_count=len(packet['faces']),
        constructed_features_digest=digest(sorted(features)),
        plane_supports_digest=digest(sorted(patch_edges)),
        boundary_digest=digest(boundaries),triangle_digest=digest(sorted(triangles)),
        _features=tuple(sorted(features)),_supports=tuple(sorted(patch_edges)),
        _boundaries=boundaries,_triangles=tuple(sorted(triangles)))

def compare_observations(base,trial):
    """Fail-closed hierarchy: NONE of these classes grants Jacobian admission."""
    if base['_features']!=trial['_features'] or base['vertex_count']!=trial['vertex_count']:
        status='CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE'
    elif base['_supports']!=trial['_supports'] or base['_boundaries']!=trial['_boundaries']:
        status='INPUT_PATCH_BOUNDARY_OR_SUPPORT_CHANGE'
    elif base['_triangles']!=trial['_triangles']:
        status='COPLANAR_RETESS_CANDIDATE_NOT_CERTIFIED'
    else:
        status='SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
    return dict(status=status,
        construction_features_match=base['_features']==trial['_features'],
        input_patch_supports_match=base['_supports']==trial['_supports'],
        symbolic_patch_boundaries_match=base['_boundaries']==trial['_boundaries'],
        triangle_identity_match=base['_triangles']==trial['_triangles'],
        qualified_smooth_derivative=False,
        qualified_boolean_set_continuity=False,
        exact_material_audit_performed=False)

def public_observation(item):
    return {key:value for key,value in item.items() if not key.startswith('_')}
