"""W5 M13: continuous-volume (piecewise constant density) voxel-cell moments.

This is an *exact integral of the explicitly declared cellwise-density proxy*,
not an exact integral of the underlying CAD/analytic primitive. Each input
array element is interpreted as one whole cell in the fixed [-1,1]^3 cube.
The existing M8/M12 tensors instead sample shape levels at linspace nodes;
interpreting those as cells is a new model of D, not a lossless conversion.

For the W0-native positive vertical plane c=(-h,0,0,b,0,..), b>0,
  r_i = sum_cells (rho*occupancy) integral_{cell intersect z>=h} m_i dV
  Jc[:,j] = (1/b) integral_{D intersect z=h} rho*occ m_i (B*m)_j dA.
Thus Jc B^-1 is a symmetric PSD boundary Gram, Jc c=0. The derivative
is withheld at a voxel layer boundary because an unverified density jump
may make it non-differentiable. Nonvertical quadrics are deliberately NOT
implemented and must fail closed. No native Cherchi material/J is inferred.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Any

import numpy as np

POWERS = ((0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),
          (0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))
B = np.asarray([1.]*7+[2.]*3)


def vertical_native_c(h: float) -> np.ndarray:
    """Construct a unit W0 native coefficient; never renormalizes saved data."""
    if not math.isfinite(float(h)):
        raise ValueError('NONFINITE_HEIGHT')
    c=np.zeros(10, dtype=np.float64)
    n=math.hypot(float(h),1.)
    c[0],c[3]=-float(h)/n,1./n
    return c


def _powers(left: np.ndarray, right: np.ndarray, max_degree: int) -> np.ndarray:
    return np.stack([(right**(p+1)-left**(p+1))/(p+1)
                     for p in range(max_degree+1)],axis=-1)


def voxel_cell_identity(raw: np.ndarray) -> str:
    a=np.ascontiguousarray(raw)
    payload=(str(a.shape)+'|'+str(a.dtype)+'|CELL_CENTERED_FIXED_CUBE_V1').encode('ascii')
    return hashlib.sha256(payload+a.tobytes()).hexdigest()


@dataclass(frozen=True)
class CellwiseMomentReference:
    """Single geometry cache; CPU binary64; no native-CAD trust or training.

    `density` is a 4-channel `[rho,occupancy,SDF,other]` tensor with shape
    `[4,n,n,n]`. Only the first two channels define nonnegative *cellwise*
    effective density `rho*occupancy`, not point samples or a native Boolean.
    The third and fourth channels are not reconstructed/decoded.
    """
    weights: np.ndarray
    source_sha256: str
    edges: np.ndarray
    x_integrals: np.ndarray
    y_integrals: np.ndarray
    xy_power_sums: np.ndarray
    cached_numeric_sha256: str
    source: str = 'DECLARED_PIECEWISE_CONSTANT_VOXEL_VOLUME_NOT_CAD'

    @classmethod
    def bind(cls, D: Any) -> 'CellwiseMomentReference':
        import torch
        if isinstance(D,torch.Tensor):
            if D.device.type!='cpu' or D.requires_grad:
                raise ValueError('CELL_SOURCE_CPU_FROZEN_ONLY')
            raw=D.detach().numpy()
        else:
            raw=np.asarray(D)
        if raw.ndim!=4 or raw.shape[0]!=4 or len(set(raw.shape[1:]))!=1 or raw.shape[1]<4:
            raise ValueError('FOUR_CHANNEL_CUBIC_VOLUME_REQUIRED')
        if raw.dtype.kind!='f' or not np.isfinite(raw).all():
            raise ValueError('FINITE_FLOAT_VOXELS_REQUIRED')
        if np.any(raw[0]<0) or np.any(raw[1]<0) or np.any(raw[1]>1):
            raise ValueError('NEGATIVE_DENSITY_OR_OCCUPANCY_OUT_OF_RANGE')
        n=raw.shape[1]
        edges=np.linspace(-1.,1.,n+1,dtype=np.float64)
        x=_powers(edges[:-1],edges[1:],4)
        y=_powers(edges[:-1],edges[1:],4)
        w=(raw[0].astype(np.float64)*raw[1].astype(np.float64)).copy()
        # Amortize geometry across all later native c queries. For each z layer,
        # preserve all x^p y^q integrated density sums (p,q in 0..4).
        xy=np.einsum('ijk,ip,jq->pqk',w,x,y,optimize=True)
        cache_digest=hashlib.sha256(w.tobytes()+edges.tobytes()+x.tobytes()+y.tobytes()+xy.tobytes()).hexdigest()
        for a in (w,edges,x,y,xy): a.setflags(write=False)
        return cls(w,voxel_cell_identity(raw),edges,x,y,xy,cache_digest)

    def assert_same_voxel_source(self,D:Any)->None:
        import torch
        a=D.detach().cpu().numpy() if isinstance(D,torch.Tensor) else np.asarray(D)
        if a.ndim!=4 or voxel_cell_identity(a)!=self.source_sha256:
            raise ValueError('CELL_CACHE_SOURCE_IDENTITY_MISMATCH')

    @property
    def resolution(self) -> int:
        return self.weights.shape[0]

    def _verify_cache(self) -> None:
        if (self.source!='DECLARED_PIECEWISE_CONSTANT_VOXEL_VOLUME_NOT_CAD'
            or self.weights.shape!=(self.resolution,)*3
            or self.edges.shape!=(self.resolution+1,)
            or not np.isfinite(self.weights).all() or (self.weights<0).any()
            or self.xy_power_sums.shape!=(5,5,self.resolution)
            or not isinstance(self.source_sha256,str) or len(self.source_sha256)!=64):
            raise ValueError('INVALID_CELL_CACHE')
        digest=hashlib.sha256(self.weights.tobytes()+self.edges.tobytes()+
                              self.x_integrals.tobytes()+self.y_integrals.tobytes()+
                              self.xy_power_sums.tobytes()).hexdigest()
        if digest!=self.cached_numeric_sha256:
            raise ValueError('CELL_CACHE_NUMERIC_CONTENT_TAMPERED')

    def raw_moments(self, h: float) -> np.ndarray:
        """Exact polynomial integration over every partially retained cell."""
        if not math.isfinite(float(h)):
            raise ValueError('NONFINITE_PLANE')
        self._verify_cache()
        n=self.resolution
        zlow=np.maximum(self.edges[:-1],float(h))
        zhigh=self.edges[1:]
        z_int=np.stack([np.where(zlow<zhigh,(zhigh**(p+1)-zlow**(p+1))/(p+1),0.)
                        for p in range(3)],axis=-1)
        out=[]
        for px,py,pz in POWERS:
            out.append(float(np.dot(self.xy_power_sums[px,py,:],z_int[:,pz])))
        return np.asarray(out,dtype=np.float64)

    def evaluate(self,c_native: Any, *, reject_boundary: bool=True) -> dict:
        """Return raw cell integral and derivative ONLY for admissible cut.

        A native positive-vertical halfspace is recognized exactly in the 8
        unused coefficient slots; no false ambient J for nonvertical cuts.
        Unit-c uses a tolerance to accept float32 W0 normalization artifacts,
        but we NEVER rewrite/renormalize a saved native coefficient vector.
        """
        c=np.asarray(c_native,dtype=np.float64)
        if c.shape!=(10,) or not np.isfinite(c).all():
            raise ValueError('FINITE_NATIVE_C10_REQUIRED')
        if any(c[i]!=0. for i in (1,2,4,5,6,7,8,9)) or c[3]<=0:
            raise ValueError('ONLY_NATIVE_POSITIVE_VERTICAL_PLANE_SUPPORTED')
        if abs(float(np.linalg.norm(c))-1.)>2e-6:
            raise ValueError('NONUNIT_SAVED_NATIVE_C_REJECTED')
        h=-float(c[0]/c[3])
        r=self.raw_moments(h)
        # Outside the geometry cube, the branch is constant in a full
        # neighborhood. At +/-1 (contact) do not fabricate smooth derivatives.
        if h< -1. or h>1.:
            return {'r':r,'Jc':np.zeros((10,10)),
                    'derivative_status':'STRICT_SIGN_CONSTANT_P0',
                    'source':self.source,'geometry_sha256':self.source_sha256}
        if h== -1. or h==1.:
            return {'r':r,'Jc':None,'derivative_status':'CELL_CONTACT_UNAVAILABLE',
                    'source':self.source,'geometry_sha256':self.source_sha256}
        # Conservative local nonsmoothness: every internal layer plane can
        # coincide with a discontinuity. Do not claim a two-sided derivative.
        k=int(np.searchsorted(self.edges,h,side='right')-1)
        boundary=float(np.min(np.abs(self.edges-h)))
        if boundary<=1e-11:
            if reject_boundary:
                return {'r':r,'Jc':None,'derivative_status':'CELL_INTERFACE_UNAVAILABLE',
                        'source':self.source,'geometry_sha256':self.source_sha256}
            raise ValueError('CELL_INTERFACE_HAS_NO_CERTIFIED_AMBIENT_J')
        if not 0<=k<self.resolution:
            raise AssertionError('invalid cell plane index')
        gram=np.zeros((10,10),dtype=np.float64)
        for i,pi in enumerate(POWERS):
            for j,pj in enumerate(POWERS):
                sx,sy,sz=(pi[t]+pj[t] for t in range(3))
                gram[i,j]=self.xy_power_sums[sx,sy,k]*h**sz/c[3]
        Jc=gram*B[None,:]
        return {'r':r,'Jc':Jc,'derivative_status':'PIECEWISE_CONSTANT_SMOOTH_CELL_INTERIOR',
                'source':self.source,'geometry_sha256':self.source_sha256,
                'cell_layer_index':k,'native_c_passthrough':c.copy(),
                'native_teacher_training_admissible':False,
                'full_CAD_geometry_certified':False}
