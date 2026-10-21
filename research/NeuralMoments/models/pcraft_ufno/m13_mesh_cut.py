"""W6 M13 independent convex triangulated source-mesh vertical P0 cut oracle.

For a strictly convex, positive-volume, coherently oriented closed triangle
mesh, clip each triangle by z>=h and cap with its convex intersection polygon.
Integrate degree<=2 monomials by signed tetrahedra; integrate the boundary
Gram (degree<=4) by the 7-point degree-5 exact triangle quadrature.

This is a NUMERIC geometric reference for the supplied indexed triangle mesh,
not an independently sealed Cherchi Boolean, not exact rational CAD input, not
arbitrary quadratic cut or an approved W2 training dataset. Reject nonconvex
mesh rather than giving a misleading single-polygon cap.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from .m13_mesh_source import FrozenTriMesh,_mesh_moments
from .m13_cell_integrals import unit_vertical_native_c, RAW_POWERS, B_NATIVE


def _convex_face_check(mesh:FrozenTriMesh)->None:
    v=mesh.vertices
    for t in mesh.vertices[mesh.faces]:
        normal=np.cross(t[1]-t[0],t[2]-t[0])
        d=(v-t[0])@normal
        if np.max(d)>2e-10*np.linalg.norm(normal):
            raise ValueError('NOT_CERTIFIED_CONVEX_BY_PLANE_HALFSPACE')


def _monomials(x:np.ndarray)->np.ndarray:
    x=np.asarray(x,dtype=np.float64)
    return np.stack([np.prod(x**np.asarray(power),axis=-1) for power in RAW_POWERS],axis=-1)


def _cap_gram(cap:np.ndarray)->np.ndarray:
    if len(cap)<3:return np.zeros((10,10),dtype=np.float64)
    bary=np.array([(1/3,1/3,1/3),
                   (.059715871789770,.470142064105115,.470142064105115),
                   (.470142064105115,.059715871789770,.470142064105115),
                   (.470142064105115,.470142064105115,.059715871789770),
                   (.797426985353087,.101286507323456,.101286507323456),
                   (.101286507323456,.797426985353087,.101286507323456),
                   (.101286507323456,.101286507323456,.797426985353087)],dtype=np.float64)
    qw=np.array([.225]+[.132394152788506]*3+[.125939180544827]*3)
    center=np.mean(cap,axis=0)
    gram=np.zeros((10,10),dtype=np.float64)
    for i in range(len(cap)):
        a=center;b=cap[i];c=cap[(i+1)%len(cap)]
        area=.5*np.linalg.norm(np.cross(b-a,c-a))
        if area<1e-15:continue
        xyz=bary@np.stack((a,b,c))
        m=_monomials(xyz)
        gram+=area*np.einsum('k,ki,kj->ij',qw,m,m,optimize=True)
    return gram


def _clip_triangle(t:np.ndarray,h:float):
    polygon=[];intersections=[]
    for i in range(3):
        a=t[i];b=t[(i+1)%3]
        fa=a[2]-h;fb=b[2]-h
        a_in=fa>=0;b_in=fb>=0
        if a_in:polygon.append(a)
        if a_in != b_in:
            p=a+(b-a)*(fa/(fa-fb))
            polygon.append(p)
            intersections.append(p)
    return polygon,intersections


def _cap_from_intersections(points:list[np.ndarray],h:float)->np.ndarray:
    if len(points)<3:return np.empty((0,3))
    xy=np.array(points)[:,:2]
    # Only a strictly interior plane without vertex hits should reach this.
    unique=np.unique(np.round(xy,12),axis=0)
    if len(unique)<3:return np.empty((0,3))
    midpoint=unique.mean(axis=0)
    angle=np.arctan2(unique[:,1]-midpoint[1],unique[:,0]-midpoint[0])
    ordered=unique[np.argsort(angle)]
    return np.column_stack((ordered,np.full(len(ordered),h)))


@dataclass(frozen=True)
class MeshCutTruth:
    r:np.ndarray
    Jc:np.ndarray|None
    derivative_status:str
    mesh_sha256:str
    source:str='INDEPENDENT_NUMERIC_CONVEX_TRIANGLE_CLIP_NOT_W2_CHERCHI'


def convex_mesh_vertical_cut(mesh:FrozenTriMesh,h:float)->MeshCutTruth:
    if not isinstance(mesh,FrozenTriMesh):raise TypeError('FrozenTriMesh required')
    mesh.verify_frozen()
    if isinstance(h,bool) or not isinstance(h,(int,float)) or not math.isfinite(float(h)):
        raise ValueError('FINITE_VERTICAL_HEIGHT_REQUIRED')
    h=float(h)
    _convex_face_check(mesh)
    heights=mesh.vertices[:,2]
    if h<np.min(heights)-1e-12:
        return MeshCutTruth(mesh.mesh_moments.copy(),np.zeros((10,10)),
                            'STRICT_FULL',mesh.identity)
    if h>np.max(heights)+1e-12:
        return MeshCutTruth(np.zeros(10),np.zeros((10,10)),
                            'STRICT_EMPTY',mesh.identity)
    contact=bool(np.min(np.abs(heights-h))<1e-10)
    triangles=[];intersections=[]
    for face in mesh.vertices[mesh.faces]:
        poly,cuts=_clip_triangle(face,h)
        intersections.extend(cuts)
        if len(poly)>=3:
            for k in range(1,len(poly)-1):
                triangles.append((poly[0],poly[k],poly[k+1]))
    cap=_cap_from_intersections(intersections,h)
    # cap sorted CCW in x/y so flip to outward -z for retained z>=h.
    if len(cap)>=3:
        for i in range(1,len(cap)-1):
            triangles.append((cap[0],cap[i+1],cap[i]))
    if not triangles:
        return MeshCutTruth(np.zeros(10),None,'UNAVAILABLE_DEGENERATE_PLANE',mesh.identity)
    flat=np.array(triangles,dtype=np.float64).reshape(-1,3)
    f=np.arange(len(flat),dtype=np.int64).reshape(-1,3)
    r=_mesh_moments(flat,f,mesh.density)
    if r[0]<-1e-8:raise RuntimeError('CUT_NEGATIVE_SIGNED_VOLUME')
    if contact:
        return MeshCutTruth(r,None,'UNAVAILABLE_MESH_VERTEX_EVENT',mesh.identity)
    if len(cap)<3:
        return MeshCutTruth(r,None,'UNAVAILABLE_NO_CAP_INSIDE_BBOX',mesh.identity)
    c=unit_vertical_native_c(h)
    Jq=mesh.density*_cap_gram(cap)/c[3]
    Jc=Jq*B_NATIVE[None]
    return MeshCutTruth(r,Jc,'SMOOTH_CONVEX_MESH_P0_LOCAL',mesh.identity)
