"""W0-aligned analytic P0 ball-cap oracle and 1D optimization-decision audit.

Only signed beta(x)=a+b_z*z, b_z>0 and |h|<R are supported.
The full Jc is a continuum analytic *local* derivative at this vertical plane;
no real Cherchi, CAD Boolean, 10D global optimization or native proof is implied.
"""
from __future__ import annotations

import math
import numpy as np

B = np.array([1.]*7 + [2.]*3)
POWERS = ((0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),
          (0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))


def native_vertical_c(h: float) -> np.ndarray:
    if not math.isfinite(float(h)):
        raise ValueError('nonfinite cut height')
    c = np.zeros(10)
    norm = math.hypot(1., float(h))
    c[0], c[3] = -float(h)/norm, 1./norm
    return c


def _validate(radius: float, cut_h: float, density: float):
    if not all(math.isfinite(float(x)) for x in (radius,cut_h,density)) or radius <= 0 or density <= 0 or abs(cut_h) >= radius:
        raise ValueError('only strict interior positive-density ball caps admitted')


def cap_moments(radius: float, cut_h: float, *, density: float = 1.) -> np.ndarray:
    _validate(radius,cut_h,density)
    R,h,rho = float(radius),float(cut_h),float(density)
    M = rho*math.pi*(2*R**3/3-R**2*h+h**3/3)
    Lz = rho*math.pi*(R*R-h*h)**2/4
    Qz = rho*math.pi*(R*R*(R**3-h**3)/3-(R**5-h**5)/5)
    Qxy = rho*math.pi/4*(R**4*(R-h)-2*R*R*(R**3-h**3)/3+(R**5-h**5)/5)
    return np.array([M,0.,0.,Lz,Qxy,Qxy,Qz,0.,0.,0.])


def cap_jacobian_native(radius: float, cut_h: float, *, density: float = 1.) -> np.ndarray:
    """Jc=(rho/bz)*disk-monomial-Gram*B, only on normalized vertical c."""
    _validate(radius,cut_h,density)
    b_z = native_vertical_c(cut_h)[3]
    disk = math.sqrt(radius*radius - cut_h*cut_h)
    gram = np.empty((10,10),dtype=np.float64)
    for i,p in enumerate(POWERS):
        for j,q in enumerate(POWERS):
            nx,ny,nz = [p[k]+q[k] for k in range(3)]
            integral = (0. if nx%2 or ny%2 else
                math.gamma((nx+1)/2)*math.gamma((ny+1)/2)/math.gamma((nx+ny)/2+2)*disk**(nx+ny+2))
            gram[i,j] = density / b_z * cut_h**nz * integral
    return gram * B[None,:]


def dh_native_c(h: float) -> np.ndarray:
    """Derivative of c(h)=(-h,0,0,1,...)/sqrt(1+h^2)."""
    norm3 = (1+h*h)**1.5
    dc = np.zeros(10)
    dc[0], dc[3] = -1/norm3, -h/norm3
    return dc


def gauss_newton_decision(radius: float, h: float, target_h: float, *, density: float = 1.,
                          predicted_r=None, predicted_jc=None,
                          damping: float = 1e-2, max_step: float = .18) -> dict[str,float]:
    """True post-step residual energy, comparing candidate to analytic oracle.

    This is a *one-dimensional* height direction, not full native 10D Newton.
    Any candidate predictor is diagnostic only; material safety is not implied.
    """
    for v in (h,target_h):
        _validate(radius,v,density)
    if damping <= 0 or max_step <= 0:
        raise ValueError('positive damping/trust region required')
    target = cap_moments(radius,target_h,density=density)
    truth = cap_moments(radius,h,density=density)
    J = cap_jacobian_native(radius,h,density=density)
    r_hat = truth if predicted_r is None else np.asarray(predicted_r,dtype=np.float64)
    j_hat = J if predicted_jc is None else np.asarray(predicted_jc,dtype=np.float64)
    if r_hat.shape != (10,) or j_hat.shape != (10,10) or not np.isfinite(r_hat).all() or not np.isfinite(j_hat).all():
        raise ValueError('finite r[10] and Jc[10,10] required')
    def step(r,j):
        directional = j @ dh_native_c(h)
        slope = float(directional @ (r-target))
        curvature = float(directional @ directional) + damping
        return float(np.clip(-slope/curvature, -max_step, max_step))
    ideal = step(truth,J)
    predicted = step(r_hat,j_hat)
    if abs(h+ideal) >= radius or abs(h+predicted) >= radius:
        raise ValueError('trust region would leave smooth interior')
    def loss(x):
        residual = cap_moments(radius,x,density=density)-target
        return float(.5*(residual@residual))
    return {'oracle_step_h':ideal,'candidate_step_h':predicted,
            'step_absolute_error':abs(predicted-ideal),
            'loss_before':loss(h),'loss_oracle_after':loss(h+ideal),
            'loss_candidate_after':loss(h+predicted),
            'signed_oracle_loss_gap':loss(h+predicted)-loss(h+ideal),
            'truth_kind':'ANALYTIC_P0_ONLY'}
