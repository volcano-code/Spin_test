"""W6 M13: source-bound exact cellwise vertical-plane ten-moment integral.

The sole integration input is frozen 4-channel CELL-CENTERED voxel D. Channel
0 means intrinsic nonnegative density; channel 1 means volume fraction in
[0,1]. The resulting *uniform piecewise-constant proxy* density equals D0*D1.
The other two channels are metadata, not pre-cut oracle data. Exactness and
local ambient Jacobian concern THIS VOLUME PROXY, NOT the source CAD mesh.

The mesh-input pipeline may supply lower/upper per-cell fill bounds. For each
plane cell fraction g and unknown material occupancy f in [lo,hi], the overlap
fraction obeys max(0,lo+g-1) <= overlap <= min(hi,g). These Frechet bounds
are conditional on the mesh being a valid embedded closed surface; oriented
edge closure alone does not certify CAD embedding or legal Boolean regions.
No quadratic/oblique cut is silently approximated as a vertical plane.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import numpy as np

from .m13_mesh_source import MeshCellSample, _sha

RAW_POWERS=((0,0,0),(1,0,0),(0,1,0),(0,0,1),
            (2,0,0),(0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))
B_NATIVE=np.asarray([1.]*7+[2.]*3,dtype=np.float64)


def _axis_integrals(lo,hi,max_power=4):
    return np.stack([(hi**(p+1)-lo**(p+1))/(p+1) for p in range(max_power+1)],axis=1)


def unit_vertical_native_c(h:float)->np.ndarray:
    if isinstance(h,bool) or not isinstance(h,(float,int)) or not math.isfinite(float(h)):
        raise ValueError('FINITE_HEIGHT_REQUIRED')
    c=np.zeros(10,dtype=np.float64)
    c[0],c[3]=-float(h),1.
    return c/math.hypot(1.,float(h))


@dataclass(frozen=True)
class ProxyCut:
    r:np.ndarray
    Jc:np.ndarray|None
    derivative_status:str
    native_c:np.ndarray
    source_voxel_sha256:str
    evidence_type:str='EXACT_CELLWISE_PIECEWISE_CONSTANT_NOT_CAD_OR_W2'


class FrozenCellVolume:
    """Validate and cache source; fixed F is NEVER added in this class."""
    def __init__(self,D):
        x=np.asarray(D)
        if (x.ndim!=4 or x.shape[0]!=4 or len(set(x.shape[1:]))!=1
                or x.shape[1]<4 or x.shape[1]>64 or x.dtype!=np.float32):
            raise ValueError('FROZEN_4CHANNEL_CENTERED_FLOAT32_CUBE_REQUIRED')
        if not np.isfinite(x).all() or np.any(x[0]<0) or np.any((x[1]<0)|(x[1]>1)):
            raise ValueError('INVALID_DENSITY_OR_FRACTION')
        self.D=np.ascontiguousarray(x).copy()
        self.source_voxel_sha256=_sha(self.D.tobytes())
        self.resolution=int(x.shape[1]);n=self.resolution
        self.weights=self.D[0].astype(np.float64)*self.D[1].astype(np.float64)
        self.edges=np.linspace(-1.,1.,n+1,dtype=np.float64)
        lo,hi=self.edges[:-1],self.edges[1:]
        self.ax=_axis_integrals(lo,hi)
        self.ay=self.ax.copy()
        self.az=self.ax.copy()
        self.D.setflags(write=False);self.weights.setflags(write=False)
        self.edges.setflags(write=False);self.ax.setflags(write=False)
        self.ay.setflags(write=False);self.az.setflags(write=False)

    def assert_source(self,D)->None:
        x=np.asarray(D)
        if x.shape!=self.D.shape or x.dtype!=self.D.dtype or _sha(np.ascontiguousarray(x).tobytes())!=self.source_voxel_sha256:
            raise ValueError('FROZEN_VOXEL_SOURCE_MISMATCH')

    def _height(self,c):
        cc=np.asarray(c)
        if cc.shape!=(10,) or cc.dtype!=np.float64 or not np.isfinite(cc).all():
            raise ValueError('SAVED_NATIVE_10_FLOAT64_COEFFICIENT_REQUIRED')
        if np.any(cc[[1,2,4,5,6,7,8,9]]!=0) or cc[3]<=0 or abs(np.linalg.norm(cc)-1)>1e-12:
            raise ValueError('ONLY_UNIT_POSITIVE_VERTICAL_PLANAR_NATIVE_C')
        return float(-cc[0]/cc[3]),cc

    def evaluate(self,c)->ProxyCut:
        """Exact r, local Jc for smooth slices *of cellwise proxy*.

        With beta=c0+c3*z, Jc_ij=(1/c3) int_(z=h) rho_cell
        m_i (B*m)_j dA. Jc B^-1 is PSD symmetric whenever defined. A plane
        coinciding with any voxel layer interface is conservatively rejected
        for Jacobian because rho_eff can jump there.
        """
        h,cc=self._height(c)
        zlo=np.maximum(self.edges[:-1],h)
        zhi=self.edges[1:]
        zclip=np.maximum(0.,zhi-zlo)
        zint=np.stack([np.where(zclip>0,(zhi**(p+1)-zlo**(p+1))/(p+1),0.)
                       for p in range(5)],axis=1)
        r=np.empty(10,dtype=np.float64)
        for i,(px,py,pz) in enumerate(RAW_POWERS):
            r[i]=np.einsum('ijk,i,j,k->',self.weights,self.ax[:,px],self.ay[:,py],zint[:,pz],optimize=True)
        J=None
        if h<self.edges[0] or h>self.edges[-1] or np.count_nonzero(self.weights)==0:
            J=np.zeros((10,10),dtype=np.float64)
            status='SMOOTH_EMPTY_OR_FULL'
        elif np.min(np.abs(self.edges-h)) < 5e-13:
            status='UNAVAILABLE_AT_CELL_LAYER_CONTACT'
        else:
            k=int(np.searchsorted(self.edges,h,side='right')-1)
            if not 0<=k<self.resolution:raise RuntimeError('height index invariant')
            layer=self.weights[:,:,k]
            J=np.empty((10,10),dtype=np.float64)
            for i,(px,py,pz) in enumerate(RAW_POWERS):
                for j,(qx,qy,qz) in enumerate(RAW_POWERS):
                    J[i,j]=(B_NATIVE[j]/cc[3])*h**(pz+qz)*np.einsum(
                        'ij,i,j->',layer,self.ax[:,px+qx],self.ay[:,py+qy],optimize=True)
            status='SMOOTH_INSIDE_SINGLE_CELL_LAYER'
        for arr in (r,cc):arr.setflags(write=False)
        if J is not None:J.setflags(write=False)
        return ProxyCut(r,J,status,cc.copy(),self.source_voxel_sha256)

    def mass_overlap_bracket(self,c,sample:MeshCellSample)->tuple[float,float]:
        """Conditional conservative mass bracket from the exact SAME D.

        Does not use true mesh moments or shape axes. ``sample`` lower/upper
        counts come only from its original indexed mesh and broad-phase AABB.
        """
        h,_=self._height(c)
        if not isinstance(sample,MeshCellSample) or sample.resolution!=self.resolution:
            raise ValueError('MESH_CELL_CERTIFICATE_REQUIRED')
        sample.verify_D(self.D)
        g=np.clip((self.edges[1:]-np.maximum(self.edges[:-1],h))/(2/self.resolution),0.,1.)
        g3=g[None,None,:]
        lower_overlap=np.maximum(0.,sample.lower_occupancy+g3-1.)
        upper_overlap=np.minimum(sample.upper_occupancy,g3)
        rho=self.D[0].astype(np.float64)
        unit=(2./self.resolution)**3
        low=float(np.einsum('ijk,ijk->',rho,lower_overlap)*unit)
        high=float(np.einsum('ijk,ijk->',rho,upper_overlap)*unit)
        if not (0<=low<=high+1e-11):raise RuntimeError('mass bracket invariant')
        return low,high
