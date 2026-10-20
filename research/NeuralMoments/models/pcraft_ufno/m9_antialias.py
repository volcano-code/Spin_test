"""M9: conservative *interval-enclosed* occupancy on voxel CELLS (analytic P0).

This geometry-only reference receives a box/sphere/axis-aligned ellipsoid
primitive specification; NO cut controls, moments, or teacher labels. Such a
spec is *additional geometric information* unavailable in legacy M8 D8 binary
inputs. This is an upper-bound / geometry ablation, NOT a fair deployment
comparison against a model given only coarse voxels, nor a Cherchi/CAD proof.

For a box the cell intersection is integrated analytically. For ellipsoids,
interval classification bounds occupancy from inside/uncertain cells; adaptive
subdivision tightens a lower and an upper volume estimate. Finite-precision
floating arithmetic is not exact rational interval certification, so brackets
are numerical conservative *diagnostics* only. Unresolved subcells contribute
0 to the lower bound and their whole volume to the upper bound; their center
indicator supplies a deterministic estimate strictly between these bounds.

All capacities describe NONNEGATIVE ATOMIC measures at cell centers, not the
exact underlying continuous geometry. No geometry is inferred from truth r/J.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
import torch


@dataclass(frozen=True)
class PrimitiveP0:
    family: str
    center: tuple[float, float, float]
    axes: tuple[float, float, float]
    density: float = 1.

    def __post_init__(self):
        if self.family not in ("box", "sphere", "ellipsoid"):
            raise ValueError("only analytic P0 box/sphere/ellipsoid supported")
        if len(self.center)!=3 or len(self.axes)!=3 or not all(
            math.isfinite(float(v)) for v in (*self.center, *self.axes, self.density)):
            raise ValueError("invalid center/axes/density")
        if min(self.axes)<=0 or self.density<=0:
            raise ValueError("positive axes and density required")
        if self.family=='sphere' and max(self.axes)-min(self.axes)>1e-12:
            raise ValueError("sphere axes unequal")
        if any(abs(float(c))+float(a)>1+1e-12 for c,a in zip(self.center,self.axes)):
            raise ValueError("primitive must lie entirely within fixed [-1,1]^3")

    @property
    def true_full_mass(self)->float:
        volume = 8*math.prod(self.axes) if self.family=='box' else (4*math.pi/3)*math.prod(self.axes)
        return float(self.density*volume)


@dataclass(frozen=True)
class CapacityGrid:
    resolution: int
    refinement_depth: int
    xyz: torch.Tensor                  # [N,3] in world frame, dtype float64
    moment_basis: torch.Tensor         # [N,10], W0 raw monomials
    estimated_capacity: torch.Tensor   # [N] (positive estimated volume fractions)
    lower_capacity: torch.Tensor       # [N] interval-inside subvolume
    upper_capacity: torch.Tensor       # [N] interval-inside+unresolved subvolume
    uncertain_subcells: int
    shape_source: str

    @property
    def mass_bracket(self) -> tuple[float,float]:
        return float(self.lower_capacity.sum()),float(self.upper_capacity.sum())

    @property
    def estimated_mass(self) -> float:
        return float(self.estimated_capacity.sum())

    def raw_full_moments(self) -> torch.Tensor:
        return torch.einsum('n,ni->i',self.estimated_capacity,self.moment_basis)


def _xyz_and_bounds(n:int) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    edges=np.linspace(-1.,1.,n+1,dtype=np.float64)
    left=np.stack(np.meshgrid(edges[:-1],edges[:-1],edges[:-1],indexing='ij'),-1).reshape(-1,3)
    right=left+2/n
    return (left+right)*.5,left,right


def _classify_ellipsoid(lo, hi, shape:PrimitiveP0)->tuple[np.ndarray,np.ndarray]:
    center=np.asarray(shape.center,dtype=np.float64)
    axes=np.asarray(shape.axes,dtype=np.float64)
    # The minimum distance to [lo,hi] is zero if center lies within the slab.
    min_distance=np.maximum(np.maximum(lo-center,center-hi),0)
    max_distance=np.maximum(np.abs(lo-center),np.abs(hi-center))
    d_min=np.sum(np.square(min_distance/axes),axis=-1)
    d_max=np.sum(np.square(max_distance/axes),axis=-1)
    # Deliberately leave a generous ambiguity band around floating boundaries.
    inside=d_max <= 1.-1e-12
    outside=d_min >= 1.+1e-12
    return inside,outside


def _interval_volume_fractions(shape:PrimitiveP0,n:int,depth:int):
    xyz,lo0,hi0=_xyz_and_bounds(n)
    total=n**3
    step=2/n
    cell_v=step**3
    if shape.family=='box':
        a=np.asarray(shape.center)-np.asarray(shape.axes)
        b=np.asarray(shape.center)+np.asarray(shape.axes)
        intersection=np.maximum(0,np.minimum(hi0,b)-np.maximum(lo0,a))
        frac=np.prod(intersection,axis=-1)/cell_v
        return xyz,frac,frac.copy(),frac.copy(),0
    lower=np.zeros(total,np.float64)
    upper=np.zeros(total,np.float64)
    estimate=np.zeros(total,np.float64)
    lo=lo0;hi=hi0;origin=np.arange(total,dtype=np.int64)
    uncertain_leaf=0
    for level in range(depth+1):
        inside,outside=_classify_ellipsoid(lo,hi,shape)
        v=np.prod(hi-lo,axis=-1)/cell_v
        np.add.at(lower,origin[inside],v[inside])
        np.add.at(upper,origin[inside],v[inside])
        np.add.at(estimate,origin[inside],v[inside])
        undecided=~(inside|outside)
        if not undecided.any():break
        l=lo[undecided];h=hi[undecided];parents=origin[undecided]
        if level==depth:
            v_uncertain=np.prod(h-l,axis=-1)/cell_v
            midpoint=(l+h)*.5
            score=np.sum(((midpoint-np.asarray(shape.center))/np.asarray(shape.axes))**2,axis=-1)
            np.add.at(upper,parents,v_uncertain)
            np.add.at(estimate,parents,v_uncertain*(score<=1))
            uncertain_leaf=len(parents)
            break
        center=(l+h)*.5
        next_lo=[];next_hi=[];next_ids=[]
        for i in range(8):
            mask=np.array([bool(i&1),bool(i&2),bool(i&4)],dtype=bool)
            next_lo.append(np.where(mask,center,l))
            next_hi.append(np.where(mask,h,center))
            next_ids.append(parents)
        lo=np.concatenate(next_lo,axis=0)
        hi=np.concatenate(next_hi,axis=0)
        origin=np.concatenate(next_ids,axis=0)
    return xyz,np.clip(estimate,0,1),np.clip(lower,0,1),np.clip(upper,0,1),uncertain_leaf


def sample_capacity(shape:PrimitiveP0, *, resolution:int=8, refinement_depth:int=2)->CapacityGrid:
    if type(resolution) is not int or not 4<=resolution<=48:
        raise ValueError("resolution must be integer in [4,48]")
    if type(refinement_depth) is not int or not 0<=refinement_depth<=5:
        raise ValueError("refinement_depth must be integer in [0,5]")
    if resolution**3 * 8**refinement_depth > 50_000_000:
        raise ValueError("adaptive occupancy work exceeds M9 CPU limit")
    xyz,est,lo,hi,uncertain=_interval_volume_fractions(shape,resolution,refinement_depth)
    vol=float((2/resolution)**3*shape.density)
    p=torch.as_tensor(xyz.copy(),dtype=torch.float64)
    mono=torch.stack([torch.ones(len(p),dtype=p.dtype),p[:,0],p[:,1],p[:,2],
                      p[:,0]**2,p[:,1]**2,p[:,2]**2,p[:,1]*p[:,2],p[:,0]*p[:,2],p[:,0]*p[:,1]],dim=-1)
    return CapacityGrid(resolution,refinement_depth,p,mono,
          torch.as_tensor(est.copy(),dtype=p.dtype)*vol,
          torch.as_tensor(lo.copy(),dtype=p.dtype)*vol,
          torch.as_tensor(hi.copy(),dtype=p.dtype)*vol,
          uncertain,"ANALYTIC_PRIMITIVE_GEOMETRY_NOT_M8_D8_ONLY")


def baseline_point_sample_mass(shape:PrimitiveP0, *, resolution:int=8)->float:
    """M8-style BINARY point density+occupancy grid then Gauss-6 bilinear sample.

    Isolate the geometrical capacity loss: no neural gate is applied. The old
    M7 point input grid runs from -1 to 1 with grid_sample(align_corners=True).
    """
    import torch.nn.functional as F
    if resolution<4:raise ValueError('resolution>=4 required')
    coords=np.linspace(-1.,1.,resolution)
    p=np.stack(np.meshgrid(coords,coords,coords,indexing='ij'),-1)
    z=(p-np.asarray(shape.center))/np.asarray(shape.axes)
    binary=(np.max(np.abs(z),axis=-1)<=1. if shape.family=='box' else np.sum(z*z,axis=-1)<=1.)
    occ=torch.as_tensor(binary.astype(np.float64))[None,None]
    xs,weights=np.polynomial.legendre.leggauss(6)
    points=np.stack(np.meshgrid(xs,xs,xs,indexing='ij'),-1).reshape(-1,3)
    w=np.prod(np.stack(np.meshgrid(weights,weights,weights,indexing='ij'),-1),axis=-1).reshape(-1)
    sampling=torch.as_tensor(points[:,::-1].copy(),dtype=torch.float64).reshape(1,-1,1,1,3)
    occ_gauss=F.grid_sample(occ,sampling,mode='bilinear',padding_mode='zeros',align_corners=True).flatten().numpy()
    return float(shape.density*np.dot(np.asarray(w),occ_gauss*occ_gauss))
