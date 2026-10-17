"""Certify a Cherchi H1 rational-surface-preserving binary64 export.

Case study scope: the archived V4 proxy Heart geometry, NOT original eval60/CAD.
No vertices move, no material is removed, no production Boolean is executed.
All exact planar two-face flips are checked, followed by global rational
oriented-plane-chain equality and fresh native float and rational boundary audits.
An incomplete / invalid trial is NEVER marked a qualified output.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
import json
import math
import time
import numpy as np

MATERIAL_SHA = '0176c55d9a7858d5ed120d685ff386a123e1abb8db830b5eb1235bd44273a660'
BINARY_AUDIT_SHA = 'e0959c033682953adf9b85aa629675f3beb28e5ab1755233579bdbff717098d8'
EXACT_AUDIT_SHA = '933b0ee33ba74f9879a64eedf69b780a19a3331e39953724d9c61dc7442d286c'

def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def determinant(a,b,c):return dot(a,cross(b,c))

def face_plane(tri, rational):
    a,b,c=[rational[v] for v in tri]
    n=cross(sub(b,a),sub(c,a))
    if not any(n):raise ValueError('EXACT_ZERO_AREA')
    vals=(*n,-dot(n,a));pivot=next(v for v in vals if v)
    return tuple(v/pivot for v in vals)

def oriented_edges(triangles):
    tally=Counter()
    for t in triangles:
        a,b,c=(int(i) for i in t)
        for u,v in ((a,b),(b,c),(c,a)):
            if tally[(v,u)]:tally[(v,u)]-=1
            else:tally[(u,v)]+=1
    return +tally

def raw_ten_moments(triangles,r):
    output=[Fraction(0) for _ in range(10)]
    for tri in triangles:
        a,b,c=[r[int(i)] for i in tri]
        vol=determinant(a,b,c)/6
        output[0]+=vol
        s=[a[k]+b[k]+c[k] for k in range(3)]
        for k in range(3):
            output[1+k]+=vol*s[k]/4
            output[4+k]+=vol*(s[k]**2+a[k]**2+b[k]**2+c[k]**2)/20
        for idx,(j,k) in enumerate(((1,2),(0,2),(0,1))):
            output[7+idx]+=vol*(s[j]*s[k]+a[j]*a[k]+b[j]*b[k]+c[j]*c[k])/20
    return output

def strict_convex_quad_from_diagonal(u,v,w,x,r):
    # Old faces (u,v,w) and (v,u,x); boundary loop is (w,u,x,v).
    n=cross(sub(r[v],r[u]),sub(r[w],r[u]))
    loop=(w,u,x,v)
    return all(dot(n,cross(sub(r[loop[(i+1)%4]],r[loop[i]]),
                            sub(r[loop[(i+2)%4]],r[loop[(i+1)%4]])))>0 for i in range(4))

def find_safe_flips(faces,vertices,r,intersections):
    problem_faces=Counter(int(k) for pair in intersections for k in pair)
    planes=[face_plane(tri,r) for tri in faces]
    uses=defaultdict(list)
    for i,(a,b,c) in enumerate(faces):
        for u,v,w in ((a,b,c),(b,c,a),(c,a,b)):
            uses[tuple(sorted((int(u),int(v))))].append((i,(int(u),int(v),int(w))))
    def float_area(face):
        a,b,c=vertices[np.asarray(face,dtype=np.intp)]
        return float(np.linalg.norm(np.cross(b-a,c-a))/2)
    candidates=[]
    for pair,neighbors in uses.items():
        if len(neighbors)!=2:continue
        (i,(u,v,w)),(j,(r_v,r_u,x))=neighbors
        if (u,v)!=(r_u,r_v) or planes[i]!=planes[j] or len({u,v,w,x})!=4:continue
        if not strict_convex_quad_from_diagonal(u,v,w,x,r):continue
        before=[tuple(int(i) for i in faces[k]) for k in (i,j)]
        after=[(w,x,v),(x,w,u)]
        if oriented_edges(before)!=oriented_edges(after):continue
        before_min=min(float_area(t) for t in before);after_min=min(float_area(t) for t in after)
        if before_min<=0 or after_min<=0:continue
        improvement=after_min/before_min
        candidates.append(dict(indices=(i,j),before=before,after=after,gain=improvement,
                               collision_contacts=problem_faces[i]+problem_faces[j],
                               affected=bool(problem_faces[i] or problem_faces[j])))
    return candidates

def certify_single_flip(old_faces,new_faces,indices,r):
    i,j=indices
    old=[tuple(int(x) for x in old_faces[t]) for t in (i,j)]
    new=[tuple(int(x) for x in new_faces[t]) for t in (i,j)]
    if len({v for tri in old for v in tri})!=4:raise ValueError('FOUR_DISTINCT_VERTICES_REQUIRED')
    # Discover old diagonal from opposite directed shared edge without relying
    # on a producer-specific vertex order.
    oriented={(old[0][k],old[0][(k+1)%3]):old[0][(k+2)%3] for k in range(3)}
    common=[(u,v,w,old[1][(s+2)%3]) for (u,v),w in oriented.items()
            for s in range(3) if (old[1][s],old[1][(s+1)%3])==(v,u)]
    if len(common)!=1:raise ValueError('NO_UNIQUE_OPPOSITE_DIRECTED_EDGE')
    u,v,w,x=common[0]
    if not strict_convex_quad_from_diagonal(u,v,w,x,r):raise ValueError('NOT_STRICTLY_CONVEX_COPLANAR_QUAD')
    if not all(face_plane(t,r)==face_plane(old[0],r) for t in (*old,*new)):
        raise ValueError('SUPPORT_PLANE_CHANGED')
    if oriented_edges(old)!=oriented_edges(new):raise ValueError('LOCAL_ORIENTED_BOUNDARY_CHANGED')
    if raw_ten_moments(old,r)!=raw_ten_moments(new,r):raise ValueError('LOCAL_EXACT_MOMENTS_CHANGED')
    return True

def global_oriented_plane_chain(faces,r):
    tally=Counter()
    canonical_vertices=[tuple(map(str,vertex)) for vertex in r]
    for triangle in faces:
        plane=tuple(map(str,face_plane(triangle,r)))
        tri=[canonical_vertices[int(k)] for k in triangle]
        for a,b in zip(tri,tri[1:]+tri[:1]):
            if a==b:raise ValueError('ZERO_LENGTH_EXACT_EDGE')
            lo,hi=(a,b) if a<b else (b,a)
            tally[(plane,lo,hi)]+=1 if a<b else -1
    return {k:v for k,v in tally.items() if v}

def load_frozen(material_path,binary_path,exact_path):
    for p,expected in ((material_path,MATERIAL_SHA),(binary_path,BINARY_AUDIT_SHA),(exact_path,EXACT_AUDIT_SHA)):
        if sha256(Path(p).read_bytes()).hexdigest()!=expected:
            raise ValueError('FROZEN_INPUT_SHA256_CHANGED:'+Path(p).name)
    data=json.loads(Path(material_path).read_text());fa=json.loads(Path(binary_path).read_text());ex=json.loads(Path(exact_path).read_text())
    v=np.asarray(data['vertices'],dtype=np.float64);f=np.asarray(data['faces'],dtype=np.int32)
    rational=[tuple(Fraction(x) for x in row) for row in data['exact_vertices']]
    if v.shape!=(793,3) or f.shape!=(1570,3) or len(rational)!=len(v):raise ValueError('UNEXPECTED_FROZEN_H1_GEOMETRY')
    if not np.array_equal(v,np.asarray([[float(x) for x in row] for row in rational])):
        raise ValueError('BINARY64_DOES_NOT_MATCH_RATIONAL_DISPLAY')
    if not ex.get('boundary_valid') or not ex.get('self_intersection_free') or ex.get('intersecting_pair_count'):
        raise ValueError('ORIGINAL_EXACT_MATERIAL_UNVERIFIED')
    if fa.get('boundary_valid') or fa.get('intersecting_pair_count')!=78:
        raise ValueError('ORIGINAL_FLOAT_FAILURE_WITNESS_CHANGED')
    return data,v,f,rational,fa

def choose(candidates,initial=False):
    eligible=[c for c in candidates if c['affected'] and c['gain']>1]
    eligible.sort(key=lambda c:(c['collision_contacts'],c['gain']),reverse=True)
    consumed=set();selected=[]
    for c in eligible:
        if any(i in consumed for i in c['indices']):continue
        selected.append(c);consumed.update(c['indices'])
        if not initial and len(selected)>=2:break
    return selected

def audit_native(native, v, faces):
    a=dict(native.audit_exact_triangle_boundary(v,np.asarray(faces,dtype=np.int32),'AnyNonzero'))
    if not a.get('self_intersection_completed') or a.get('intersection_error'):
        raise ValueError('INCOMPLETE_NATIVE_FLOAT_AUDIT')
    return a

def write_obj(path,vertices,faces):
    with Path(path).open('x',encoding='ascii',newline='\n') as out:
        out.write('# H4 archived Heart V4 proxy Cherchi material, NOT final Heart assembly\n')
        for v in vertices:out.write('v '+' '.join(format(float(x),'.17g') for x in v)+'\n')
        for f in faces:out.write('f '+' '.join(str(int(k)+1) for k in f)+'\n')

def read_obj(path):
    vertices=[];faces=[]
    for line in Path(path).read_text().splitlines():
        if line.startswith('v '):vertices.append([float(x) for x in line.split()[1:]])
        elif line.startswith('f '):faces.append([int(x)-1 for x in line.split()[1:]])
    return np.asarray(vertices,dtype=np.float64),np.asarray(faces,dtype=np.int32)

def certify(args):
    import _make_it_stand as native
    started=time.monotonic()
    data,vertices,original,rational,baseline=load_frozen(args.material,args.binary_audit,args.rational_audit)
    faces=original.copy();pairs=baseline['intersecting_pairs'];steps=[]
    status={"final_qualified":False,"scope":"H1_V4_PROXY_ONLY_NOT_ORIGINAL_EVAL60_OR_HEART_OPTIMIZATION"}
    args.output.mkdir(parents=True,exist_ok=False)
    for index in range(18):
        if not pairs:break
        candidates=find_safe_flips(faces,vertices,rational,pairs)
        selected=choose(candidates,initial=(index==0))
        if not selected:raise ValueError('NO_MORE_EXACT_SAFE_IMPROVEMENT')
        trial=faces.copy()
        for choice in selected:
            i,j=choice['indices'];trial[i],trial[j]=choice['after']
            certify_single_flip(faces,trial,(i,j),rational)
        returned=audit_native(native,vertices,trial)
        new_pairs=returned['intersecting_pairs']
        if not (len(new_pairs)<len(pairs)):
            raise ValueError('NATIVE_FLOAT_COLLISION_COUNT_NOT_IMPROVED')
        steps.append({'round':index+1,'pairs_before':len(pairs),'pairs_after':len(new_pairs),
                      'flips':[{'face_indices':list(c['indices']),'old':c['before'],
                                'new':c['after'],'area_gain':c['gain']} for c in selected]})
        faces=trial;pairs=new_pairs
    if pairs:raise ValueError('FLOAT_INTERSECTION_REMAINING')
    # Independent global exact oriented plane-chain equality (using rational
    # world-space vertex coordinates rather than relying on vertex indices).
    before=global_oriented_plane_chain(original,rational)
    after=global_oriented_plane_chain(faces,rational)
    if before!=after:raise ValueError('GLOBAL_EXACT_ORIENTED_SUPPORT_CHAIN_DIFFERENCE')
    exact=dict(native.audit_exact_rational_triangle_boundary(data['exact_vertices'],faces,'AnyNonzero'))
    if not exact.get('boundary_valid') or not exact.get('self_intersection_free') or exact.get('intersecting_pair_count'):
        raise ValueError('FINAL_EXACT_RATIONAL_BOUNDARY_INVALID')
    candidate=args.output/'v4-proxy-cherchi-retained-material-retriangulated.obj'
    write_obj(candidate,vertices,faces)
    vv,ff=read_obj(candidate)
    if not np.array_equal(vv,vertices) or not np.array_equal(ff,faces):
        raise ValueError('OBJ_ROUNDTRIP_CHANGED_VERTEX_OR_FACE')
    exported=audit_native(native,vv,ff)
    if not exported.get('boundary_valid') or not exported.get('self_intersection_free') or exported.get('intersecting_pair_count'):
        raise ValueError('EXPORTED_OBJ_NATIVE_BINARY64_REJECTED')
    # Check 10 global moments by exact local 2-face swaps, not by float tets.
    status.update({'schema':'heart-h4-frozen-v4-proxy-qualified-obj-v1',
      'source_sha256':{name:sha256(Path(getattr(args,name)).read_bytes()).hexdigest() for name in ('material','binary_audit','rational_audit')},
      'native_binary_path':str(Path(native.__file__)),'native_module_sha256':sha256(Path(native.__file__).read_bytes()).hexdigest(),
      'initial_float_intersecting_pairs':78,'final_float_intersecting_pairs':0,
      'total_local_exact_flip_operations':sum(len(s['flips']) for s in steps),
      'rounds':len(steps),'changed_face_count':int(np.sum(np.any(original!=faces,axis=1))),
      'vertex_count':len(vertices),'face_count':len(faces),
      'all_flip_rational_moment_equalities':True,'all_flip_strict_convex_coplanar_proven':True,
      'global_exact_oriented_plane_boundary_chain_equal':True,
      'global_exact_support_planes':len({face_plane(t,rational) for t in faces}),
      'final_exact_rational_native_audit':{k:exact[k] for k in ('boundary_valid','closed','edge_manifold','vertex_manifold','self_intersection_free','intersecting_pair_count','component_orientations_valid')},
      'final_binary64_native_audit':{k:exported[k] for k in ('boundary_valid','closed','edge_manifold','vertex_manifold','self_intersection_free','intersecting_pair_count','component_orientations_valid')},
      'obj_sha256':sha256(candidate.read_bytes()).hexdigest(),
      'obj_size_bytes':candidate.stat().st_size,
      'qualified_precision':'EXACT_H1_MATERIAL_RATIONAL_SUPPORT_CHAIN_AND_RELOADED_BINARY64_BOUNDARY',
      'final_qualified':True,
      'complete_author_heart':False,'original_eval60_reproduced':False,
      'complete_faster_newton_converged':False,'physical_ground_contact_passed':False,
      'optimization_invocations':0,'source_backsum':'Cherchi H1 output, triangulation-only changes',
      'elapsed_seconds':time.monotonic()-started})
    (args.output/'certification.json').write_text(json.dumps(status,indent=2,allow_nan=False)+'\n')
    (args.output/'operations.json').write_text(json.dumps(steps,indent=2,allow_nan=False)+'\n')
    (args.output/'faces.json').write_text(json.dumps(faces.tolist(),separators=(',',':'))+'\n')
    print(json.dumps({k:status[k] for k in ['schema','final_qualified','total_local_exact_flip_operations','changed_face_count','rounds','vertex_count','face_count','final_exact_rational_native_audit','final_binary64_native_audit','obj_sha256','elapsed_seconds']},indent=2))
    return status

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('material','binary_audit','rational_audit'):
        parser.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    parser.add_argument('--output',required=True,type=Path)
    certify(parser.parse_args())
