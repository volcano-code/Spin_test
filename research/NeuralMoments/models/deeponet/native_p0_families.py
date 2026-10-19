"""Independent *physical* W0-native P0 analytic labels on closed primitives.

For D a box/ball/axis-aligned ellipsoid, beta_c(x) = c0 + c3*z, c3>0,
D_cut = D intersect {beta >= 0}. r_D = integral_D_cut rho*m(x) dx,
Jc = (rho/c3) * (integral_{z=h} m(x)m(x)^T dA) * B,
where B=diag(1,...,1,2,2,2) and m=(1,x,y,z,xx,yy,zz,yz,xz,xy).

Only smooth strict-interior horizontal cuts are supported. The entire *ambient*
10x10 derivative is calculated at this cut, but is NOT a certificate for a
Cherchi discrete Boolean or a nonhorizontal nonlinear parameter excursion.
This module does not import any W2 code or train from a W2 record.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Sequence

import numpy as np

from .native_p0 import POWERS, B, dh_native_c, native_vertical_c

FAMILIES = ('box', 'sphere', 'ellipsoid')


def _finite_vec(value: Sequence[float], length: int, name: str) -> tuple[float, ...]:
    try:
        arr = np.asarray(value, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} must be a finite vector') from exc
    if arr.shape != (length,) or not np.isfinite(arr).all():
        raise ValueError(f'{name} must be a finite vector of length {length}')
    return tuple(float(v) for v in arr)


@dataclass(frozen=True)
class NativeP0Primitive:
    family: str
    center: tuple[float, float, float]
    axes: tuple[float, float, float]
    density: float = 1.0

    def __post_init__(self):
        if self.family not in FAMILIES:
            raise ValueError('unknown analytic primitive family')
        center = _finite_vec(self.center, 3, 'center')
        axes = _finite_vec(self.axes, 3, 'semiaxes')
        if any(x <= 0 for x in axes):
            raise ValueError('strictly positive semiaxes required')
        if type(self.density) not in (int, float) or not math.isfinite(self.density) or self.density <= 0:
            raise ValueError('positive finite density required')
        if self.family == 'sphere' and not np.allclose(axes, axes[0], rtol=1e-12, atol=1e-12):
            raise ValueError('sphere requires three equal semiaxes')
        if self.family == 'ellipsoid' and np.allclose(axes, axes[0], rtol=1e-12, atol=1e-12):
            raise ValueError('use sphere family for isotropic axes')
        object.__setattr__(self, 'center', center)
        object.__setattr__(self, 'axes', axes)
        object.__setattr__(self, 'density', float(self.density))

    @property
    def source_sha256(self) -> str:
        # This is an *analytic primitive specification identity*, not CAD-file identity.
        content = {'family': self.family, 'center': self.center,
                   'axes': self.axes, 'density': self.density}
        return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    @property
    def interval(self) -> tuple[float, float]:
        return self.center[2]-self.axes[2], self.center[2]+self.axes[2]

    def descriptor(self) -> np.ndarray:
        """Ten physical descriptors, no unseen-family categorical indicator.

        center(3), axes(3), density, mass, central Qtrace/M and central Qzz/M.
        The last three are uncut *original* analytic-solid features. They
        are NOT cut-specific r_D(h) labels, so there is no target leakage.
        This is NOT M3's 24D triangle-mesh input or actual CAD encoding.
        """
        cx,cy,cz=self.center
        ax,ay,az=self.axes
        factor = 8. if self.family=='box' else 4.*math.pi/3.
        k = 3. if self.family=='box' else 5.
        mass = factor*ax*ay*az*self.density
        return np.array([cx,cy,cz,ax,ay,az,self.density,mass,
                         (ax*ax+ay*ay+az*az)/k,az*az/k], dtype=np.float64)

    def _interior(self, h: float) -> float:
        h = float(h)
        lower, upper = self.interval
        if not math.isfinite(h) or not (lower < h < upper):
            raise ValueError('only strict-interior horizontal cuts have P0 labels')
        return h


def _unit_disk_moment(i: int, j: int) -> float:
    if i & 1 or j & 1:
        return 0.0
    return (math.gamma((i+1)/2)*math.gamma((j+1)/2)
            / math.gamma((i+j)/2 + 2))


def _power_integral_from_u0(m: int, n: int, u0: float) -> float:
    """Exact polynomial antiderivative of integral u^m*(1-u^2)^n du."""
    return sum(((-1)**k)*math.comb(n, k) * (1.-u0**(m+2*k+1))/(m+2*k+1)
               for k in range(n+1))


def _ellipse_xy_terms(p: int, q: int, primitive: NativeP0Primitive):
    """A_x A_y times expanded centered-unit-disk moments, with (1-u^2)^n."""
    cx, cy = primitive.center[:2]
    ax, ay = primitive.axes[:2]
    for i in range(0, p+1, 2):
        for j in range(0, q+1, 2):
            coefficient = (math.comb(p, i)*math.comb(q, j)
                           * cx**(p-i)*cy**(q-j)*ax**(i+1)*ay**(j+1)
                           * _unit_disk_moment(i, j))
            yield coefficient, 1+(i+j)//2


def _rectangle_power(c: float, extent: float, power: int) -> float:
    a, b = c-extent, c+extent
    return (b**(power+1)-a**(power+1))/(power+1)


def _xy_surface_moment(primitive: NativeP0Primitive, h: float, p: int, q: int) -> float:
    if primitive.family == 'box':
        return (_rectangle_power(primitive.center[0], primitive.axes[0], p)
                * _rectangle_power(primitive.center[1], primitive.axes[1], q))
    u = (h-primitive.center[2])/primitive.axes[2]
    t = 1-u*u
    return math.fsum(weight*t**n for weight, n in _ellipse_xy_terms(p,q,primitive))


def _solid_monomial(primitive: NativeP0Primitive, h: float, p: int, q: int, r: int) -> float:
    if primitive.family == 'box':
        return (primitive.density
                * _rectangle_power(primitive.center[0], primitive.axes[0], p)
                * _rectangle_power(primitive.center[1], primitive.axes[1], q)
                * (primitive.interval[1]**(r+1)-h**(r+1))/(r+1))
    u0 = (h-primitive.center[2])/primitive.axes[2]
    cz, az = primitive.center[2], primitive.axes[2]
    series = []
    for weight, n in _ellipse_xy_terms(p, q, primitive):
        for m in range(r+1):
            series.append(weight*math.comb(r,m)*cz**(r-m)*az**m
                          * _power_integral_from_u0(m, n, u0))
    return primitive.density*az*math.fsum(series)


def oracle(primitive: NativeP0Primitive, h: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return r_D, full Jc_D, and *unit native* c(h), exact up to float roundoff.

    There is NO fixed material: r_F=0 and r_total=r_D, J_total=J_D.
    Validity of the derivative is restricted to the smooth continuum primitive.
    """
    h = primitive._interior(h)
    c = native_vertical_c(h)
    r = np.array([_solid_monomial(primitive, h, *power) for power in POWERS], dtype=np.float64)
    gram = np.empty((10,10), dtype=np.float64)
    for i,(px,py,pz) in enumerate(POWERS):
        for j,(qx,qy,qz) in enumerate(POWERS):
            gram[i,j] = (_xy_surface_moment(primitive, h, px+qx, py+qy)
                         * h**(pz+qz))
    j_native = (primitive.density/c[3]) * gram * B[None,:]
    if not np.isfinite(r).all() or not np.isfinite(j_native).all():
        raise ValueError('nonfinite P0 oracle')
    return r, j_native, c


def decision(primitive: NativeP0Primitive, h: float, target_h: float,
             *, predicted_r=None, predicted_jc=None, damping: float = .02,
             max_step: float = .15) -> dict[str, float | str]:
    """True retained-solid objective after a 1D trust-region height update.

    Compare both candidate and oracle steps using independent physical r(h).
    Not a general 10D native Spin optimizer. The target query is NOT used as
    a network feature. Strictly interior cuts are enforced for every step.
    """
    h, target_h = primitive._interior(h), primitive._interior(target_h)
    if not math.isfinite(damping) or damping <= 0 or not math.isfinite(max_step) or max_step <= 0:
        raise ValueError('positive finite damping and max_step required')
    r, j, _ = oracle(primitive,h)
    target = oracle(primitive,target_h)[0]
    pr = r if predicted_r is None else np.asarray(predicted_r,dtype=np.float64)
    pj = j if predicted_jc is None else np.asarray(predicted_jc,dtype=np.float64)
    if pr.shape != (10,) or pj.shape != (10,10) or not np.isfinite(pr).all() or not np.isfinite(pj).all():
        raise ValueError('finite predicted r[10] and Jc[10,10] required')
    lower,upper = primitive.interval
    radius = min(max_step,.49*(h-lower),.49*(upper-h))
    if radius <= 0:
        raise ValueError('trust region left strict interior')
    dh = dh_native_c(h)
    def make_step(rr, jj):
        d = jj @ dh
        return float(np.clip(-float(d @ (rr-target))/(float(d@d)+damping),-radius,radius))
    ideal = make_step(r,j)
    candidate = make_step(pr,pj)
    def true_loss(height):
        residual = oracle(primitive,height)[0]-target
        return float(.5*(residual@residual))
    return {'oracle_step_h':ideal,'candidate_step_h':candidate,
            'step_absolute_error':abs(candidate-ideal),
            'loss_before':true_loss(h), 'loss_oracle_after':true_loss(h+ideal),
            'loss_candidate_after':true_loss(h+candidate),
            'signed_oracle_loss_gap':true_loss(h+candidate)-true_loss(h+ideal),
            'truth_kind':'W0_NATIVE_ANALYTIC_P0_NOT_W2'}


def validate_exact_reference(primitive: NativeP0Primitive, h: float, *, eps: float = 1e-5) -> dict[str, float]:
    """Independently audit the directional derivative and conditional B rule."""
    h = primitive._interior(h)
    if eps <= 0 or not (primitive.interval[0] < h-eps < h+eps < primitive.interval[1]):
        raise ValueError('finite difference must remain strict interior')
    r,j,c = oracle(primitive,h)
    d = j@dh_native_c(h)
    fd = (oracle(primitive,h+eps)[0]-oracle(primitive,h-eps)[0])/(2*eps)
    H = j/B[None,:]
    return {'max_directional_fd_abs_error':float(np.max(np.abs(d-fd))),
            'max_B_corrected_asymmetry':float(np.max(np.abs(H-H.T))),
            'max_scale_null_error':float(np.max(np.abs(j@c))),
            'mass':float(r[0])}
