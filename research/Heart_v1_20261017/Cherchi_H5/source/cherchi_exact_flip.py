"""Exact, mesh-generic *geometry-only* operations used after Cherchi Boolean.

No Boolean call, no Newton, no floating vertex movements, no cache mutation.
Every move replaces the diagonal of a strictly convex rational coplanar quad.
"""
from collections import Counter, defaultdict
from fractions import Fraction
import numpy as np


def minus(a, b):
    return tuple(x-y for x, y in zip(a,b))

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def dot(a,b):
    return sum(x*y for x,y in zip(a,b))

def det(a,b,c):
    return dot(a,cross(b,c))

def fractional_vertices(exact):
    if not isinstance(exact,(list,tuple)) or not exact:
        raise ValueError('MISSING_EXACT_RATIONAL_VERTICES')
    result=[]
    for p in exact:
        if not isinstance(p,(list,tuple)) or len(p)!=3 or not all(isinstance(t,str) for t in p):
            raise ValueError('INVALID_EXACT_VERTEX_RECORD')
        try:
            coords=tuple(Fraction(t) for t in p)
        except (ValueError,ZeroDivisionError) as ex:
            raise ValueError('INVALID_EXACT_RATIONAL') from ex
        result.append(coords)
    return result

def plane(tri, r):
    a,b,c=(r[int(i)] for i in tri)
    normal=cross(minus(b,a),minus(c,a))
    if not any(normal):
        raise ValueError('EXACT_ZERO_AREA_TRIANGLE')
    values=(*normal,-dot(normal,a))
    scale=next(x for x in values if x)
    return tuple(x/scale for x in values)

def oriented_edges(faces):
    edges=Counter()
    for tri in faces:
        a,b,c=(int(i) for i in tri)
        for u,v in ((a,b),(b,c),(c,a)):
            if edges[(v,u)]:
                edges[(v,u)]-=1
            else:
                edges[(u,v)]+=1
    return +edges

def is_strictly_convex(u,v,w,x,r):
    n=cross(minus(r[v],r[u]),minus(r[w],r[u]))
    boundary=(w,u,x,v)
    return all(dot(n,cross(minus(r[boundary[(i+1)%4]],r[boundary[i]]),
                           minus(r[boundary[(i+2)%4]],r[boundary[(i+1)%4]])))>0
               for i in range(4))

def ten_moments(faces,r):
    result=[Fraction(0) for _ in range(10)]
    for tri in faces:
        a,b,c=[r[int(i)] for i in tri]
        vol=det(a,b,c)/6
        sums=[a[i]+b[i]+c[i] for i in range(3)]
        result[0]+=vol
        for k in range(3):
            result[k+1]+=vol*sums[k]/4
            result[k+4]+=vol*(sums[k]**2+a[k]**2+b[k]**2+c[k]**2)/20
        for idx,(k,j) in enumerate(((1,2),(0,2),(0,1))):
            result[idx+7]+=vol*(sums[k]*sums[j]+a[k]*a[j]+b[k]*b[j]+c[k]*c[j])/20
    return result

def exact_plane_chain(faces,r):
    edges=Counter()
    coords=[tuple(map(str,x)) for x in r]
    for tri in faces:
        support=tuple(map(str,plane(tri,r)))
        vertices=[coords[int(i)] for i in tri]
        for a,b in zip(vertices,vertices[1:]+vertices[:1]):
            if a==b:raise ValueError('EXACT_COLLAPSED_EDGE')
            lo,hi=(a,b) if a<b else (b,a)
            edges[(support,lo,hi)]+=1 if a<b else -1
    return {key:val for key,val in edges.items() if val}

def safe_flips(faces,vertices,r,intersections):
    hit=Counter(int(i) for pair in intersections for i in pair)
    planes=[plane(face,r) for face in faces]
    inc=defaultdict(list)
    for index,(a,b,c) in enumerate(faces):
        for u,v,w in ((a,b,c),(b,c,a),(c,a,b)):
            inc[tuple(sorted((int(u),int(v))))].append((index,(int(u),int(v),int(w))))
    def float_area(t):
        a,b,c=vertices[np.asarray(t,dtype=np.intp)]
        return float(np.linalg.norm(np.cross(b-a,c-a))/2)
    choices=[]
    for uses in inc.values():
        if len(uses)!=2:continue
        (i,(u,v,w)),(j,(ru,rv,x))=uses
        if (u,v)!=(rv,ru) or planes[i]!=planes[j] or len({u,v,w,x})!=4:continue
        if not is_strictly_convex(u,v,w,x,r):continue
        old=[tuple(map(int,faces[k])) for k in (i,j)]
        new=[(w,x,v),(x,w,u)]
        if oriented_edges(old)!=oriented_edges(new):continue
        old_min=min(map(float_area,old));new_min=min(map(float_area,new))
        if old_min<=0 or new_min<=0:continue
        choices.append({'faces':(i,j),'before':old,'after':new,
                        'gain':new_min/old_min,'contacts':hit[i]+hit[j],
                        'affected':bool(hit[i] or hit[j])})
    return choices

def assert_local_flip(old_faces,new_faces,ij,r):
    i,j=ij
    old=[tuple(map(int,old_faces[k])) for k in (i,j)]
    new=[tuple(map(int,new_faces[k])) for k in (i,j)]
    if len({v for t in old for v in t})!=4:
        raise ValueError('NOT_FOUR_DISTINCT_VERTICES')
    lookup={(a,b):c for a,b,c in ((t[k],t[(k+1)%3],t[(k+2)%3]) for t in old[:1] for k in range(3))}
    edges=[(u,v,w,t[(k+2)%3]) for (u,v),w in lookup.items() for t in old[1:]
           for k in range(3) if (t[k],t[(k+1)%3])==(v,u)]
    if len(edges)!=1:raise ValueError('NO_MATCHING_DIAGONAL')
    if not is_strictly_convex(*edges[0],r):raise ValueError('NONCONVEX_EXACT_QUAD')
    if not all(plane(t,r)==plane(old[0],r) for t in (*old,*new)):
        raise ValueError('SUPPORT_PLANE_CHANGED')
    if oriented_edges(old)!=oriented_edges(new):raise ValueError('LOCAL_EDGE_CHAIN_CHANGED')
    if ten_moments(old,r)!=ten_moments(new,r):raise ValueError('LOCAL_TEN_MOMENTS_CHANGED')
    return True

def pick_choices(choices,initial=False):
    eligible=sorted((x for x in choices if x['affected'] and x['gain']>1),
                    key=lambda x:(x['contacts'],x['gain']),reverse=True)
    accepted=[];taken=set()
    for x in eligible:
        if any(i in taken for i in x['faces']):continue
        accepted.append(x);taken.update(x['faces'])
        if not initial and len(accepted)>=2:break
    return accepted
