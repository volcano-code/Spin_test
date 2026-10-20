"""Independent analytic P0 oracle for a unit ball/axis-aligned ellipsoid plane.

Used to evaluate the declared voxel-cell approximation, never for training
real Cherchi labels. This module is INDEPENDENT of M14 polyhedron clipping.
The surface Gram is integrated using polynomial-exact circle quadrature.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from .m13_cell_integrals import B


def ellipsoid_plane_oracle(center: Sequence[float], axes: Sequence[float],
                           density: float, c_native: Sequence[float]) -> dict:
    t=np.asarray(center,dtype=np.float64);A=np.asarray(axes,dtype=np.float64)
    c=np.asarray(c_native,dtype=np.float64)
    if t.shape!=(3,) or A.shape!=(3,) or c.shape!=(10,) or not np.isfinite(t).all() or not np.isfinite(A).all() or not np.isfinite(c).all() or not math.isfinite(float(density)) or density<=0 or (A<=0).any():
        raise ValueError('FINITE_POSITIVE_ELLIPSOID_REQUIRED')
    if np.any(c[4:]!=0) or abs(np.linalg.norm(c)-1.)>2e-6:
        raise ValueError('UNIT_NATIVE_PLANAR_C_REQUIRED')
    b=c[1:4]
    g=A*b
    norm=float(np.linalg.norm(g))
    if norm<=1e-12:
        raise ValueError('NONZERO_PLANE_NORMAL_REQUIRED')
    h=-float(c[0]+np.dot(b,t))/norm
    factor=float(density*np.prod(A))
    if abs(h)==1.:
        return {'r':None,'Jc':None,'status':'ANALYTIC_TANGENCY_UNAVAILABLE'}
    if h>=1.:
        return {'r':np.zeros(10),'Jc':np.zeros((10,10)),'status':'STRICTLY_EMPTY'}
    if h<=-1.:
        mass=4*math.pi/3
        l=np.zeros(3)
        q=np.eye(3)*(4*math.pi/15)
        gram=np.zeros((10,10))
    else:
        u=g/norm
        mass=math.pi*(2/3-h+h**3/3)
        l=(math.pi/4)*(1-h*h)**2 *u
        qparallel=math.pi*((1-h**3)/3 - (1-h**5)/5)
        qperp=math.pi/4*((1-h)-2*(1-h**3)/3+(1-h**5)/5)
        q=qperp*np.eye(3)+(qparallel-qperp)*np.outer(u,u)
        ref=np.array((1.,0.,0.)) if abs(u[0])<.85 else np.array((0.,1.,0.))
        e1=np.cross(u,ref);e1/=np.linalg.norm(e1)
        e2=np.cross(u,e1)
        radius=math.sqrt(1-h*h)
        xs,ws=np.polynomial.legendre.leggauss(5)
        rr=radius*(xs+1)*.5
        radial_w=ws*.5*radius*rr
        angles=2*math.pi*np.arange(24)/24
        gram=np.zeros((10,10))
        for rad,wr in zip(rr,radial_w):
            for ang in angles:
                up=h*u+rad*(e1*math.cos(ang)+e2*math.sin(ang))
                p=t+A*up
                x,y,z=p
                m=np.array((1.,x,y,z,x*x,y*y,z*z,y*z,x*z,x*y))
                gram+=wr*(2*math.pi/24)*np.outer(m,m)
        gram*=factor/norm
    mass_world=factor*mass
    first=factor*(A*l+mass*t)
    AL=A*l
    second=factor*(A[:,None]*q*A[None,:]+np.outer(AL,t)+np.outer(t,AL)+mass*np.outer(t,t))
    r=np.array((mass_world,*first,second[0,0],second[1,1],second[2,2],
                second[1,2],second[0,2],second[0,1]))
    return {'r':r,'Jc':gram*B[None,:], 'status':'SMOOTH_ELLIPSOID_PLANE' if abs(h)<1 else 'STRICTLY_FULL'}


def tilted_box_oracle_from_yz(b: Sequence[float], offset: float, *, density: float=1.) -> dict:
    """Independent tensor Gauss-Legendre integration for box x >= xcut(y,z).

    Requires plane x = (offset-b_y*y-b_z*z)/b_x contained strictly inside
    (-1,1) for every y,z in [-1,1], so a degree-six two-axis rule is exact.
    This does not use the M14 clipped-cell geometry routines.
    """
    v=np.asarray(b,dtype=np.float64)
    if v.shape!=(3,) or not np.isfinite(v).all() or v[0]<=abs(v[1])+abs(v[2])+abs(offset) or not math.isfinite(float(density)) or density<=0:
        raise ValueError('PLANE_MUST_CROSS_ONLY_BOX_X_FACES')
    xs,ws=np.polynomial.legendre.leggauss(6)
    r=np.zeros(10,dtype=np.float64)
    H=np.zeros((10,10),dtype=np.float64)
    powers=((0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),(0,2,0),
            (0,0,2),(0,1,1),(1,0,1),(1,1,0))
    for y,wy in zip(xs,ws):
        for z,wz in zip(xs,ws):
            low=(offset-v[1]*y-v[2]*z)/v[0]
            factors=[(1-low**(p+1))/(p+1) for p in range(3)]
            for k,(px,py,pz) in enumerate(powers):
                r[k]+=float(density*wy*wz*factors[px]*y**py*z**pz)
            m=np.array((1.,low,y,z,low**2,y**2,z**2,y*z,low*z,low*y))
            H+=density*wy*wz/v[0]*np.outer(m,m)
    # The tested native c is normalized from (-offset,b). The Gram below
    # used raw b; compensate by ||(-offset,b)|| for dr/dc_normalized.
    normalization=math.sqrt(float(offset)**2+float(v@v))
    return {'r':r,'Jc':normalization*H*B[None,:], 'status':'EXACT_BOX_YZ_QUADRATURE'}
