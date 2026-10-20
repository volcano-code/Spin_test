"""W5 M12: certified *analytic-primitive* saturation, not native CAD material.

Strict exact-binary-rational interval signs prove whether W0's native beta_c
is positive or negative on a known box containing an independently specified
analytic Shape. If strictly full/empty, return its independent CONTINUUM
closed-form r_D (or zero) and derivative zero. Reuse the cached M11 cone-valued
surrogate only for undecided interior controls. Withhold ambient J at nodal
activation boundaries; local surrogate smoothness is NEVER native-W2 proof.

The full moment is not learned: one independently computed analytic reference
per geometry. This is intentionally unavailable for arbitrary CAD meshes.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math

import numpy as np
import torch
from torch import Tensor

from .m8_analytic_data import Shape, make_voxel
from .m11_cone_integrable import ConeIntegrableMoment

FROZEN_SOURCE = "0bcc187b3005478baa586a6d6f450e73811ca342"
NATIVE_B = (1.0,)*7 + (2.0,)*3


def analytic_full_moments(shape: Shape) -> np.ndarray:
    """Independent raw box/axis-aligned ellipsoid/ball full integrals.

    A=diag(axes), x=A u+center. Uniform unit-box E[u_i²]=1/3,
    uniform unit-ball E[u_i²]=1/5, with ordinary (undoubled) Q cross terms.
    This routine is NOT a volume integrator for a CAD mesh/Boolean solid.
    """
    if not isinstance(shape, Shape):
        raise ValueError("ANALYTIC_SHAPE_REQUIRED")
    ax = np.asarray(shape.axes, dtype=np.float64)
    ctr = np.asarray(shape.center, dtype=np.float64)
    mass = shape.density * float(np.prod(ax)) * (8.0 if shape.family == 'box' else (4*math.pi/3))
    second = mass * (np.outer(ctr,ctr) + np.diag(ax*ax/(3.0 if shape.family=='box' else 5.0)))
    return np.array([mass, *(mass*ctr), second[0,0], second[1,1], second[2,2],
                     second[1,2], second[0,2], second[0,1]], dtype=np.float64)


def _fraction(value) -> Fraction:
    if isinstance(value, bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('INVALID_FINITE_BINARY_COORDINATE')
    return Fraction(value)


def analytic_aabb(shape: Shape) -> tuple[tuple[Fraction,...],tuple[Fraction,...]]:
    """Exact bounds of the *serialized binary64* shape spec, not rounded endpoints."""
    if not isinstance(shape,Shape):
        raise ValueError('ANALYTIC_SHAPE_REQUIRED')
    center = tuple(_fraction(float(x)) for x in shape.center)
    axes = tuple(_fraction(float(x)) for x in shape.axes)
    lo = tuple(x-a for x,a in zip(center, axes))
    hi = tuple(x+a for x,a in zip(center, axes))
    if any(x>=y for x,y in zip(lo,hi)):
        raise ValueError('INVALID_SHAPE_BOUNDS')
    if any(x< -1 or y>1 for x,y in zip(lo,hi)):
        raise ValueError('GEOMETRY_OUTSIDE_FROZEN_WORLD_CUBE')
    return lo,hi


def strict_native_sign(c_native: Tensor, shape: Shape) -> str:
    """Sound interval sufficient sign test, native cross entries doubled.

    The bound may return UNDECIDED despite strict sign on the actual solid.
    No arbitrary bounding-volume statement for an unknown CAD is accepted.
    """
    if (not isinstance(c_native,Tensor) or c_native.shape!=(10,) or
        not c_native.is_floating_point() or not bool(torch.isfinite(c_native).all())):
        raise ValueError('FINITE_NATIVE_C10_REQUIRED')
    if abs(float(torch.linalg.vector_norm(c_native))-1.0)>2e-6:
        raise ValueError('SAVED_NATIVE_C_MUST_BE_UNIT_LENGTH')
    lo,hi = analytic_aabb(shape)
    coeff = tuple(_fraction(float(v)) for v in c_native.detach().cpu().tolist())
    lower=upper=coeff[0]
    def add(coefficient, mini, maxi):
        nonlocal lower,upper
        lower+= min(coefficient*mini,coefficient*maxi)
        upper+= max(coefficient*mini,coefficient*maxi)
    for i in range(3):
        add(coeff[i+1],lo[i],hi[i])
        sqlo=Fraction(0) if lo[i]<=0<=hi[i] else min(lo[i]**2,hi[i]**2)
        sqhi=max(lo[i]**2,hi[i]**2)
        add(coeff[4+i],sqlo,sqhi)
    for j,(i,k) in ((7,(1,2)),(8,(0,2)),(9,(0,1))):
        corners=[lo[i]*lo[k],lo[i]*hi[k],hi[i]*lo[k],hi[i]*hi[k]]
        add(2*coeff[j],min(corners),max(corners))
    return ('ANALYTIC_CERTIFIED_EMPTY' if upper<0 else
            'ANALYTIC_CERTIFIED_FULL' if lower>0 else 'UNDECIDED')


def tensor_sha256(t: Tensor) -> str:
    if not isinstance(t,Tensor) or t.ndim!=5 or t.shape[1]!=4:
        raise ValueError('FOUR_CHANNEL_VOXEL_REQUIRED')
    if not bool(torch.isfinite(t).all()):
        raise ValueError('NONFINITE_VOXEL')
    a=t.detach().cpu().contiguous().numpy()
    return hashlib.sha256(str((a.shape,str(a.dtype))).encode()+a.tobytes()).hexdigest()


def _tensor_digest(t: Tensor) -> str:
    a=t.detach().cpu().contiguous().numpy()
    return hashlib.sha256(str((a.shape,str(a.dtype))).encode()+a.tobytes()).hexdigest()


@dataclass(frozen=True)
class AnalyticGeometryCache:
    """Internal analytic-P0-only cache; fields do NOT authorize real CAD truth."""
    shape: Shape
    shape_identity: str
    tensor_sha256: str
    z: Tensor
    full_moments: Tensor
    full_moments_digest: str
    cached_embedding_digest: str
    source: str = 'ANALYTIC_P0_ONLY_NOT_NATIVE_MATERIAL'


class SaturationGuard:
    def __init__(self, model: ConeIntegrableMoment):
        if not isinstance(model,ConeIntegrableMoment):
            raise ValueError('SHA_PINNED_W5_M11_CONE_MODEL_REQUIRED')
        self.model=model
        self.encoding_calls=0
        self.analytic_full_reference_calls=0
        self.native_teacher_calls=0

    def bind_analytic_geometry(self, D: Tensor, shape: Shape) -> AnalyticGeometryCache:
        """Match exact analytic Shape -> voxel serialization; compute full truth once.

        An independent analytic formula is accessible for Shape; no public
        API here accepts self-asserted true CAD r_F/r_D as a full reference.
        """
        if not isinstance(shape,Shape) or D.ndim!=5 or D.shape[0]!=1 or D.shape[-3:]!=(8,8,8):
            raise ValueError('ONLY_SINGLE_8CUBED_ANALYTIC_P0_GEOMETRY')
        analytic_aabb(shape)
        expected=make_voxel(shape,grid_size=8)[None]
        if (D.device.type!='cpu' or D.dtype!=torch.float32 or not torch.equal(D.detach(),expected)):
            raise ValueError('ANALYTIC_SHAPE_VOXEL_BYTES_DO_NOT_MATCH')
        with torch.no_grad():
            z=self.model.encode_geometry(D).detach()
        self.encoding_calls+=1
        full=analytic_full_moments(shape)
        self.analytic_full_reference_calls+=1
        full_tensor=torch.as_tensor(full,dtype=D.dtype,device=D.device)
        return AnalyticGeometryCache(shape,shape.identity,tensor_sha256(D),z,full_tensor,
                                     _tensor_digest(full_tensor),_tensor_digest(z))

    def predict(self, cache: AnalyticGeometryCache, c: Tensor) -> dict:
        """No geometry recoding for repeat c. Returns Jc=None when not admissible.

        Every Jc is only an analytic/surrogate derivative, NEVER a certified
        W0/W2 production native Cherchi derivative or optimizer approval.
        """
        if (not isinstance(cache, AnalyticGeometryCache) or
            cache.source!='ANALYTIC_P0_ONLY_NOT_NATIVE_MATERIAL' or
            cache.shape_identity!=cache.shape.identity or
            cache.full_moments.shape!=(10,) or
            not bool(torch.isfinite(cache.full_moments).all()) or
            _tensor_digest(cache.full_moments)!=cache.full_moments_digest or
            _tensor_digest(cache.z)!=cache.cached_embedding_digest):
            raise ValueError('UNTRUSTED_OR_INVALID_ANALYTIC_CACHE')
        if not isinstance(c,Tensor) or c.shape!=(1,10) or c.dtype!=cache.z.dtype or c.device!=cache.z.device:
            raise ValueError('SAVED_NATIVE_C_SHAPE_DEVICE_OR_DTYPE_MISMATCH')
        state=strict_native_sign(c[0],cache.shape)
        if state=='ANALYTIC_CERTIFIED_EMPTY':
            r=torch.zeros((1,10),dtype=c.dtype,device=c.device)
            J=torch.zeros((1,10,10),dtype=c.dtype,device=c.device)
            interpretation='EXACT_ANALYTIC_ZERO_ONLY'
        elif state=='ANALYTIC_CERTIFIED_FULL':
            r=cache.full_moments.unsqueeze(0).clone()
            J=torch.zeros((1,10,10),dtype=c.dtype,device=c.device)
            interpretation='INDEPENDENT_CONTINUUM_ANALYTIC_FULL_R_ONLY'
        else:
            with torch.no_grad():
                r=self.model.moment(cache.z,c)
                regime=self.model.derivative_regime(cache.z,c)[0]
                J=(None if regime=='NODE_SIGN_BOUNDARY_UNDEFINED'
                   else self.model.jacobian(cache.z,c))
            interpretation=('SURROGATE_NODE_BOUNDARY_J_WITHHELD' if J is None else
                            'M11_LOCAL_SURROGATE_DERIVATIVE_ONLY')
        return {'r':r,'Jc':J,'region':state,'interpretation':interpretation,
                'native_training_admissible':False,'native_cherchi_proof':False,
                'source':'ANALYTIC_P0_ONLY_NOT_NATIVE_CAD',
                'source_geometry_id':cache.shape_identity,
                'full_reference_queries_for_geometry':1}
