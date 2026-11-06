"""Exact rational intersection-segment extraction for one parent triangle.

Returns all non-coplanar cut segments induced by an opposite closed triangle mesh.
Coplanar overlap is rejected explicitly; it must be resolved by a separate
coplanar arrangement policy, never silently ignored.
"""
from fractions import Fraction as Q

def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def qpoint(p):
    if len(p)!=3 or any(type(x) not in (int,Q) for x in p): raise ValueError("NONEXACT_POINT")
    return tuple(map(Q,p))
def inside(p,t,n):
    return all(dot(cross(sub(t[(i+1)%3],t[i]),sub(p,t[i])),n)>=0 for i in range(3))
def plane_segment(parent, other):
    a,b,c=parent; u,v,w=other
    np=cross(sub(b,a),sub(c,a)); no=cross(sub(v,u),sub(w,u))
    if np==(0,0,0) or no==(0,0,0): raise ValueError("DEGENERATE_TRIANGLE")
    sp=[dot(np,sub(x,a)) for x in (u,v,w)]
    so=[dot(no,sub(x,u)) for x in (a,b,c)]
    if all(x==0 for x in sp) and all(x==0 for x in so):
        raise ValueError("COPLANAR_PAIR_REQUIRES_SEPARATE_POLICY")
    if (all(x>0 for x in sp) or all(x<0 for x in sp) or
        all(x>0 for x in so) or all(x<0 for x in so)): return ()
    hits=[]
    for tri, vals, test_tri, test_n in ((other,sp,parent,np),(parent,so,other,no)):
        for i in range(3):
            j=(i+1)%3
            if vals[i]==0 and inside(tri[i],test_tri,test_n): hits.append(tri[i])
            if vals[i]*vals[j]<0:
                den=vals[i]-vals[j]
                p=tuple((vals[i]*tri[j][k]-vals[j]*tri[i][k])/den for k in range(3))
                if inside(p,test_tri,test_n): hits.append(p)
    unique=sorted(set(hits))
    if len(unique)<=1: return ()
    pair=max(((dot(sub(x,y),sub(x,y)),x,y) for i,x in enumerate(unique) for y in unique[i+1:]),key=lambda z:z[0])
    if pair[0]==0:return ()
    return (pair[1],pair[2])
def extract(parent, opposite_vertices, opposite_faces):
    parent=tuple(qpoint(p) for p in parent)
    segments=set()
    for face in opposite_faces:
        other=tuple(qpoint(opposite_vertices[i]) for i in face)
        seg=plane_segment(parent,other)
        if seg:
            a,b=sorted(seg)
            if a!=b: segments.add((a,b))
    return sorted(segments)
