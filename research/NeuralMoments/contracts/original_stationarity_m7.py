"""W0 M7: independently recompute the original Spin2014 terminal KKT residual.

Accepts frozen exact/material moments and a provided *independent* physics
implementation. This module alone cannot authenticate the implementation or
its source; the live production adapter must pin its module and settings.
Finite complex step matches the original objective audit's derivative convention.
"""
from __future__ import annotations

import math
from typing import Callable
import numpy as np

from .native_teacher_replay import need, ReplayRejected, vector10, finite_double


def _real_vector(value, label):
    arr=np.asarray(value)
    need(arr.ndim==1 and arr.dtype.kind in ('f','i','u') and
         arr.size>0, label+': FINITE_VECTOR_REQUIRED')
    try:
        arr=np.asarray(arr,dtype=np.float64)
    except (ValueError,TypeError,OverflowError) as e:
        raise ReplayRejected(label+': NOT_BINARY64_REPRESENTABLE') from e
    need(np.isfinite(arr).all(),label+': NONFINITE_VECTOR')
    return arr


def recompute_original_kkt(total_r, native_c, multipliers, mu, *, objective,
                           equation_tolerance, mode, original_objective_profile):
    """Independent equations at fixed actual raw moments, not neural predictions.

    objective must be independently source-audited by the caller and return
    (f(r), constraints(r)) with complex support. This arithmetic-only function
    never claims that requirement has been satisfied in a live native solve.
    """
    need(callable(objective),'INDEPENDENT_ORIGINAL_OBJECTIVE_REQUIRED')
    need(original_objective_profile=='SPIN2014_OBJECTIVES_QUADRIC_V1' and
         mode in ('SPINNING_TOP','YO_YO'), 'UNSUPPORTED_ORIGINAL_ROTATIONAL_OBJECTIVE')
    r=np.asarray(vector10(total_r,'r_total'),dtype=np.float64)
    c=np.asarray(vector10(native_c,'native_c'),dtype=np.float64)
    need(abs(float(np.linalg.norm(c))-1.)<=1e-12,'NONUNIT_NATIVE_COEFFICIENT')
    lam=_real_vector(multipliers,'lagrange_multipliers')
    mu=finite_double(mu,'mu')
    tol=finite_double(equation_tolerance,'equation_tolerance')
    need(mu>0 and 0<tol<=1e-12,'NONPOSITIVE_MU_OR_RELAXED_TOLERANCE')
    try:
        f,constraints=objective(r)
        f=float(f)
        constraints=_real_vector(constraints,'constraints')
    except (RuntimeError,ValueError,TypeError,OverflowError) as e:
        if isinstance(e,ReplayRejected):raise
        raise ReplayRejected('INDEPENDENT_ORIGINAL_OBJECTIVE_FAILED') from e
    need(math.isfinite(f) and len(constraints)==len(lam),
         'OBJECTIVE_OR_MULTIPLIER_DIMENSION_MISMATCH')
    grad=np.empty(10,dtype=np.float64)
    jac=np.empty((len(lam),10),dtype=np.float64)
    step=1e-24
    for i in range(10):
        perturbed=r.astype(np.complex128)
        perturbed[i]+=step*1j
        try:
            value,ct=objective(perturbed)
            ct=np.asarray(ct,dtype=np.complex128)
            require_dim=ct.shape==(len(lam),)
            if not require_dim:raise ValueError('constraint dimension drift')
            grad[i]=float(np.imag(value)/step)
            jac[:,i]=np.imag(ct)/step
        except (ValueError,TypeError,OverflowError,RuntimeError) as e:
            raise ReplayRejected('INDEPENDENT_COMPLEX_STEP_FAILED') from e
    need(np.isfinite(grad).all() and np.isfinite(jac).all(),
         'INDEPENDENT_COMPLEX_STEP_NONFINITE')
    dual=c.copy()
    dual[7:]*=2.0 # q=Bc, native matrix-entry c must not masquerade as monomial q
    norm=float(np.linalg.norm(dual))
    need(math.isfinite(norm) and norm>0,'ZERO_NATIVE_DUAL_COORDINATES')
    dual/=norm
    stationarity=grad-jac.T@lam+mu*dual
    raw=float(np.linalg.norm(np.r_[stationarity,constraints]))
    need(math.isfinite(raw) and raw<=tol,
         'INDEPENDENT_ORIGINAL_KKT_RESIDUAL_EXCEEDS_FROZEN_TOLERANCE')
    return {
        'schema':'W0_M7_INDEPENDENT_ORIGINAL_EQUATION_ARITHMETIC_V1',
        'objective':f,
        'constraint_residuals':constraints.tolist(),
        'objective_gradient':grad.tolist(),
        'constraint_jacobian':jac.tolist(),
        'stationarity_residual':stationarity.tolist(),
        'equation_norm':raw,
        'equation_tolerance':tol,
        'native_dual_coordinates_are_B_times_c':True,
        'mathematical_KKT_recomputation_passed':True,
        'authenticates_original_objective_implementation':False,
        'authenticates_native_or_cherchi_execution':False,
        'authenticates_full_geometry_or_smoothness':False,
        'training_admissible':False,
    }
