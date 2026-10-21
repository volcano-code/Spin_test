"""W6 M13: strict, source-hashed triangle-mesh -> *same-source* voxel input.

No analytic shape class/center/axes, cut control, teacher label, or P-CRAFT
network output is used to build D. The sole geometric input is the indexed
triangle surface supplied to FrozenTriMesh.

An oriented edge-closed positive-volume surface is NECESSARY, not proof of an
embedded, non-self-intersecting CAD solid. Conditional on a valid embedded
watertight surface, broad-phase triangle AABBs over-approximate all boundary
cells, so [lower, upper] occupancy bounds are conservative. A boundary cell's
stratified winding estimate is a numerical estimate, NOT a proved occupancy.
The volume moment of the explicitly triangulated source uses signed tetrahedra;
this is NOT W2 independently authenticated original material.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import numpy as np

# Undoubled monomial ten moments, W0 native order.
_COMPONENT_PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))


def _sha(*items: bytes) -> str:
    h=hashlib.sha256()
    for b in items:
        h.update(len(b).to_bytes(8,'big'));h.update(b)
    return h.hexdigest()


def _mesh_moments(v:np.ndarray,f:np.ndarray,density:float)->np.ndarray:
    triangles=v[f]
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    signed_volume=np.einsum('ni,ni->n',a,np.cross(b,c))/6.*density
    s=a+b+c
    out=[float(signed_volume.sum())]
    out.extend(float((signed_volume*s[:,k]/4).sum()) for k in range(3))
    out.extend(float((signed_volume*(s[:,i]*s[:,j] +
        a[:,i]*a[:,j]+b[:,i]*b[:,j]+c[:,i]*c[:,j])/20).sum())
        for i,j in _COMPONENT_PAIRS)
    return np.array(out,dtype=np.float64)


class FrozenTriMesh:
    """Frozen indexed closed oriented triangle soup with exact byte identity.

    The input need not be convex but no full self-intersection test is made.
    Signed-tetra moments are exact polynomial integrals of the triangle *proxy*
    to float64 precision. They are held out of model encoder inputs.
    """
    def __init__(self,vertices,faces,*,density:float=1.):
        v=np.array(vertices,dtype=np.float64,copy=True)
        raw=np.asarray(faces)
        if raw.dtype.kind not in 'iu' or raw.dtype.kind=='u' and raw.size and raw.max()>2**63-1:
            raise ValueError('MESH_FACE_INDICES_INTEGER_REQUIRED')
        f=np.array(raw,dtype=np.int64,copy=True)
        if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3 or len(v)<4 or len(f)<4:
            raise ValueError('MESH_INDEXED_TRIANGLES_REQUIRED')
        if not np.isfinite(v).all() or (np.abs(v)>1+1e-12).any():
            raise ValueError('MESH_OUTSIDE_FIXED_UNIT_WORLD_OR_NONFINITE')
        if not isinstance(density,(int,float)) or isinstance(density,bool) or not math.isfinite(density) or density<=0:
            raise ValueError('POSITIVE_FINITE_DENSITY_REQUIRED')
        if (f<0).any() or (f>=len(v)).any() or (f[:,0]==f[:,1]).any() or (f[:,1]==f[:,2]).any() or (f[:,2]==f[:,0]).any():
            raise ValueError('INVALID_FACE_INDEX')
        if len({tuple(sorted(t)) for t in f.tolist()})!=len(f):
            raise ValueError('DUPLICATE_FACE')
        t=v[f]
        area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)
        if (area<1e-13).any():
            raise ValueError('DEGENERATE_TRIANGLE')
        directed=Counter()
        undirected=Counter()
        for i,j,k in f:
            for a,b in ((i,j),(j,k),(k,i)):
                directed[int(a),int(b)]+=1
                undirected[tuple(sorted((int(a),int(b))))]+=1
        if not all(n==2 and directed[a,b]==1 and directed[b,a]==1 for (a,b),n in undirected.items()):
            raise ValueError('MESH_OPEN_OR_WRONG_WINDING')
        m=_mesh_moments(v,f,density)
        if not np.isfinite(m).all() or m[0]<=1e-12:
            raise ValueError('MESH_SIGNED_VOLUME_NONPOSITIVE')
        self.vertices=v
        self.faces=f
        self.density=float(density)
        self.mesh_moments=m
        self.identity=_sha(np.ascontiguousarray(v.astype('<f8')).tobytes(),
            np.ascontiguousarray(f.astype('<i8')).tobytes(),
            np.asarray([self.density],dtype='<f8').tobytes())
        for a in (self.vertices,self.faces,self.mesh_moments):a.setflags(write=False)

    def verify_frozen(self) -> None:
        candidate=_sha(np.ascontiguousarray(self.vertices.astype('<f8')).tobytes(),
            np.ascontiguousarray(self.faces.astype('<i8')).tobytes(),
            np.asarray([self.density],dtype='<f8').tobytes())
        if candidate!=self.identity:
            raise ValueError('MESH_SOURCE_SHA_CHANGED')

    def winding(self,points:np.ndarray)->np.ndarray:
        """Continuous signed solid-angle winding; deterministically chunked.

        A near-half-integer boundary point is rejected rather than labeled.
        This is not a CAD embedding/self-intersection proof.
        """
        p=np.asarray(points,dtype=np.float64)
        if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():
            raise ValueError('FINITE_QUERY_POINTS_REQUIRED')
        tri=self.vertices[self.faces]
        out=np.empty(len(p),dtype=np.float64)
        for start in range(0,len(p),128):
            query=p[start:start+128]
            r=tri[None,:,:,:]-query[:,None,None,:]
            a,b,c=r[:,:,0],r[:,:,1],r[:,:,2]
            aa=np.linalg.norm(a,axis=-1);bb=np.linalg.norm(b,axis=-1);cc=np.linalg.norm(c,axis=-1)
            numerator=np.einsum('...i,...i->...',a,np.cross(b,c))
            denominator=(aa*bb*cc + np.einsum('...i,...i->...',a,b)*cc +
                          np.einsum('...i,...i->...',a,c)*bb +
                          np.einsum('...i,...i->...',b,c)*aa)
            winding=np.sum(2*np.arctan2(numerator,denominator),axis=1)/(4*np.pi)
            if (np.abs(np.abs(winding)-.5)<.01).any() or not np.isfinite(winding).all():
                raise ValueError('MESH_POINT_ON_OR_NEAR_BOUNDARY_UNDECIDABLE')
            out[start:start+len(query)]=winding
        return out


@dataclass(frozen=True)
class MeshCellSample:
    resolution:int
    mesh_sha256:str
    voxel_sha256:str
    D:np.ndarray                 # 4,n,n,n, float32; frozen copied input
    lower_occupancy:np.ndarray   # conservative iff closed embedded material
    upper_occupancy:np.ndarray
    uncertain_cells:int
    center_sample_only:bool
    source_policy:str='INDEXED_MESH_WINDING_AND_AABB_BOUNDARY_V1_NOT_CAD_CERTIFICATE'

    def verify_D(self,D)->None:
        x=np.asarray(D)
        if x.shape!=self.D.shape or x.dtype!=np.float32 or _sha(np.ascontiguousarray(x).tobytes())!=self.voxel_sha256:
            raise ValueError('VOXEL_IDENTITY_MISMATCH')

    @property
    def conditional_mass_bracket(self):
        step=(2/self.resolution)**3
        rho=self.D[0].astype(np.float64)
        return (float(np.sum(rho*self.lower_occupancy)*step),
                float(np.sum(rho*self.upper_occupancy)*step))


def mesh_to_cells(mesh:FrozenTriMesh,*,resolution:int=8,samples_per_axis:int=3)->MeshCellSample:
    if not isinstance(mesh,FrozenTriMesh):raise TypeError('FrozenTriMesh required')
    mesh.verify_frozen()
    if type(resolution) is not int or not 4<=resolution<=32 or type(samples_per_axis) is not int or samples_per_axis not in (1,2,3,4):
        raise ValueError('INVALID_GRID_OR_SUBCELL_SAMPLE_BUDGET')
    n=resolution
    edges=np.linspace(-1,1,n+1)
    bounds_lo=np.stack(np.meshgrid(edges[:-1],edges[:-1],edges[:-1],indexing='ij'),axis=-1).reshape(-1,3)
    bounds_hi=bounds_lo+2/n
    centers=(bounds_hi+bounds_lo)/2
    faces=mesh.vertices[mesh.faces]
    tri_min=faces.min(axis=1);tri_max=faces.max(axis=1)
    potential_boundary=np.zeros(len(centers),dtype=bool)
    # Broad-phase AABB check is conservative (may over-report a boundary cell).
    for first in range(0,len(centers),192):
        l=bounds_lo[first:first+192,None,:]
        h=bounds_hi[first:first+192,None,:]
        intersects=np.all((tri_max[None]>=l-1e-14)&(tri_min[None]<=h+1e-14),axis=2)
        potential_boundary[first:first+len(l)]=np.any(intersects,axis=1)
    center_occupied=np.abs(mesh.winding(centers))>.5
    lower=np.where(potential_boundary,0.,center_occupied.astype(float))
    upper=np.where(potential_boundary,1.,center_occupied.astype(float))
    estimate=center_occupied.astype(np.float64)
    if samples_per_axis>1 and potential_boundary.any():
        idx=np.flatnonzero(potential_boundary)
        frac=np.zeros(len(idx),dtype=np.float64)
        for i in range(samples_per_axis):
            for j in range(samples_per_axis):
                for k in range(samples_per_axis):
                    pos=bounds_lo[idx]+(np.array([i,j,k])+.5)*(2/n/samples_per_axis)
                    frac+=(np.abs(mesh.winding(pos))>.5).astype(float)
        estimate[idx]=frac/samples_per_axis**3
    D=np.zeros((4,n,n,n),dtype=np.float32)
    D[0]=mesh.density   # intrinsic density, not density premultiplied by occupancy
    D[1]=estimate.reshape(n,n,n).astype(np.float32)
    D[3]=potential_boundary.reshape(n,n,n).astype(np.float32)
    lower=lower.reshape(n,n,n)
    upper=upper.reshape(n,n,n)
    digest=_sha(D.tobytes())
    for a in (D,lower,upper):a.setflags(write=False)
    return MeshCellSample(n,mesh.identity,digest,D,lower,upper,
          int(potential_boundary.sum()),samples_per_axis==1)
