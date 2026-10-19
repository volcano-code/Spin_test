"""Independent W0-native analytic cut oracle for M8 *synthetic* four-channel tests.

True moment labels are continuum box/ball/ellipsoid integrals. The 8^3 voxel
input is a sampled *approximation* to the uncut body, not exact native material.
This module contains NO W2 data and does not certify real CAD or manufacturing.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
import numpy as np
import torch

POWERS = ((0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),(0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))
B = np.diag([1.]*7 + [2.]*3)
TEACHER = 'W0_ANALYTIC_CONTINUUM_P0_NOT_NATIVE_W2'

@dataclass(frozen=True)
class Shape:
    family: str
    center: tuple[float, float, float]
    axes: tuple[float, float, float]
    density: float = 1.0

    def __post_init__(self):
        if self.family not in ('box','sphere','ellipsoid') or len(self.axes)!=3 or len(self.center)!=3:
            raise ValueError('unknown analytic geometry')
        if not all(math.isfinite(float(x)) for x in (*self.axes,*self.center,self.density)) or min(self.axes)<=0 or self.density<=0:
            raise ValueError('invalid axes/center/density')
        if self.family == 'sphere' and max(self.axes)-min(self.axes)>1e-12:
            raise ValueError('sphere axes must match')

    @property
    def identity(self):
        body={'family':self.family,'axes':self.axes,'center':self.center,'density':self.density}
        return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def _integral(power: int, lo: float, hi: float) -> float:
    return (hi**(power+1)-lo**(power+1))/(power+1)


def _unit_box(h: float):
    r=np.array([_integral(p[0],-1,1)*_integral(p[1],-1,1)*_integral(p[2],h,1)
                for p in POWERS],dtype=np.float64)
    G=np.array([[_integral(p[0]+q[0],-1,1)*_integral(p[1]+q[1],-1,1)*h**(p[2]+q[2])
                for q in POWERS] for p in POWERS])
    return r,G


def _unit_ball(h: float):
    pi=math.pi
    m=pi*(2./3.-h+h**3/3.)
    lz=pi*(1-h*h)**2/4.
    qxy=pi/4.*((1-h)-2*(1-h**3)/3.+(1-h**5)/5.)
    qzz=pi*((1-h**3)/3.-(1-h**5)/5.)
    r=np.array([m,0.,0.,lz,qxy,qxy,qzz,0.,0.,0.])
    disk=math.sqrt(1-h*h)
    G=np.empty((10,10),dtype=np.float64)
    for i,p in enumerate(POWERS):
        for j,q in enumerate(POWERS):
            nx,ny,nz=(p[k]+q[k] for k in range(3))
            G[i,j]=(0. if nx%2 or ny%2 else
                    math.gamma((nx+1)/2)*math.gamma((ny+1)/2)/math.gamma((nx+ny)/2+2)
                    *disk**(nx+ny+2)*h**nz)
    return r,G


def _affine_monomials(shape: Shape):
    """Exact polynomial binomial expansion phi(Au+t)=T phi(u), diagonal A."""
    idx={p:i for i,p in enumerate(POWERS)}
    T=np.zeros((10,10),dtype=np.float64)
    for i,p in enumerate(POWERS):
        terms={(0,0,0):1.}
        for axis,n in enumerate(p):
            updated={}
            for prior,weight in terms.items():
                for k in range(n+1):
                    power=list(prior);power[axis]+=k;power=tuple(power)
                    add=weight*math.comb(n,k)*shape.center[axis]**(n-k)*shape.axes[axis]**k
                    updated[power]=updated.get(power,0.)+add
            terms=updated
        for powers,weight in terms.items():
            T[i,idx[powers]]=weight
    return T


def analytic_truth(shape: Shape, h_local: float):
    """W0 native c and full *smooth continuous* ambient dr/dc at an interior plane."""
    h=float(h_local)
    if not math.isfinite(h) or not -1<h<1:
        raise ValueError('cut outside strict smooth P0 interior')
    r0,G0=_unit_box(h) if shape.family=='box' else _unit_ball(h)
    T=_affine_monomials(shape)
    world_h=shape.center[2]+shape.axes[2]*h
    c=np.zeros(10);c[0],c[3]=-world_h,1.
    native_norm=float(np.linalg.norm(c));c/=native_norm
    weight=shape.density*math.prod(shape.axes)
    r=weight*(T@r0)
    J=(weight*native_norm/shape.axes[2])*(T@G0@T.T)@B
    return c,r,J


def make_voxel(shape: Shape, grid_size: int = 8):
    """All four channels are label-independent density/occupancy/level/proximity.

    Channel 2 is a signed *implicit-level proxy*, not an exact Euclidean SDF
    for ellipsoids or boxes. Channel 3 is a derived boundary proximity.
    """
    if grid_size<8: raise ValueError('grid too small')
    xyz=np.linspace(-1.,1.,grid_size,dtype=np.float64)
    pts=np.stack(np.meshgrid(xyz,xyz,xyz,indexing='ij'),axis=-1)
    unit=(pts-np.asarray(shape.center))/np.asarray(shape.axes)
    level=(np.max(np.abs(unit),axis=-1)-1. if shape.family=='box'
           else np.sqrt(np.sum(unit*unit,axis=-1))-1.)
    occ=(level<=0).astype(np.float32)
    prox=np.exp(-8.*np.abs(level)).astype(np.float32)
    return torch.from_numpy(np.stack((occ*shape.density,occ,level.astype(np.float32),prox),axis=0))


def dataset(families, *, per_family: int, seed: int, grid_size: int=8, queries: int=2):
    """Samples whole geometry IDs; fixed seed, no reuse of test-family labels."""
    if per_family<1 or queries<1:raise ValueError('nonempty data required')
    rng=np.random.default_rng(int(seed))
    Ds=[];Cs=[];Rs=[];Js=[];meta=[]
    for family in families:
        for index in range(per_family):
            center=tuple(float(x) for x in rng.uniform(-.1,.1,3))
            if family=='sphere':
                a=float(rng.uniform(.46,.73));axes=(a,a,a)
            elif family in ('box','ellipsoid'):
                vals=tuple(float(x) for x in rng.uniform(.46,.73,3))
                axes=(vals[0],vals[1]*.8,vals[2]*1.1) if family=='ellipsoid' else vals
            else:raise ValueError('unknown family')
            shape=Shape(family,center,axes)
            voxel=make_voxel(shape,grid_size)
            for _ in range(queries):
                h=float(rng.uniform(-.65,.65))
                c,r,J=analytic_truth(shape,h)
                Ds.append(voxel);Cs.append(torch.from_numpy(c).float())
                Rs.append(torch.from_numpy(r).float());Js.append(torch.from_numpy(J).float())
                meta.append({'family':family,'geometry_id':shape.identity,'shape':{'center':center,'axes':axes,'density':shape.density},'h_local':h,'source':TEACHER})
    return (torch.stack(Ds),torch.stack(Cs),torch.stack(Rs),torch.stack(Js),meta)


def sha_dataset(data):
    sha=hashlib.sha256()
    for part in data[:4]:
        a=part.contiguous().cpu().numpy()
        sha.update(str((a.shape,str(a.dtype))).encode('ascii'));sha.update(a.tobytes())
    sha.update(json.dumps(data[4],sort_keys=True,separators=(',',':'),allow_nan=False).encode())
    return sha.hexdigest()


def independent_family_check(train, valid, heldout):
    sets=[{m['geometry_id'] for m in x[4]} for x in (train,valid,heldout)]
    fam=[{m['family'] for m in x[4]} for x in (train,valid,heldout)]
    if any(sets[i]&sets[j] for i,j in ((0,1),(0,2),(1,2))):
        raise ValueError('geometry-ID split leakage')
    if (fam[0]|fam[1]) & fam[2]:raise ValueError('held-out family leakage')
    return {'fit_ids':len(sets[0]),'validation_ids':len(sets[1]),'heldout_ids':len(sets[2]),'heldout_families':sorted(fam[2])}
