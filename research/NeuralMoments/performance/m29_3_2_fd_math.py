"""Pure numerical helpers for W1 M29.3.2 tangent-space finite differences."""
from __future__ import annotations
import numpy as np

def tangent_basis(q):
    q=np.asarray(q,dtype=np.float64)
    if q.shape!=(10,) or not np.isfinite(q).all():
        raise ValueError("M29_3_2_INVALID_Q")
    n=float(np.linalg.norm(q))
    if not np.isfinite(n) or n<=0:
        raise ValueError("M29_3_2_ZERO_Q")
    q=q/n
    # Keep the same deterministic construction used in the M29.3.1 host check.
    a=np.column_stack((q,np.eye(10,dtype=np.float64)))
    orth,_=np.linalg.qr(a)
    b=orth[:,1:]
    if b.shape!=(10,9):
        raise ValueError("M29_3_2_BAD_TANGENT_BASIS_SHAPE")
    if np.linalg.norm(b.T@q)>1e-12 or np.linalg.norm(b.T@b-np.eye(9))>1e-12:
        raise ValueError("M29_3_2_TANGENT_BASIS_NOT_ORTHONORMAL")
    return q,b

def retract_unit(q,delta):
    q=np.asarray(q,dtype=np.float64)
    delta=np.asarray(delta,dtype=np.float64)
    if q.shape!=(10,) or delta.shape!=(10,) or not np.isfinite(q).all() or not np.isfinite(delta).all():
        raise ValueError("M29_3_2_INVALID_RETRACTION_INPUT")
    x=q+delta
    n=float(np.linalg.norm(x))
    if not np.isfinite(n) or n<=1e-15:
        raise ValueError("M29_3_2_INVALID_RETRACTION_NORM")
    return x/n

def central_difference(f_plus,f_minus,h):
    if not np.isfinite(h) or h<=0:
        raise ValueError("M29_3_2_INVALID_STEP")
    p=np.asarray(f_plus,dtype=np.float64)
    m=np.asarray(f_minus,dtype=np.float64)
    if p.shape!=(10,) or m.shape!=(10,) or not np.isfinite(p).all() or not np.isfinite(m).all():
        raise ValueError("M29_3_2_INVALID_FUNCTION_VALUE")
    return (p-m)/(2.0*h)

def compare_jacobians(j_tangent,j_fd):
    a=np.asarray(j_tangent,dtype=np.float64)
    b=np.asarray(j_fd,dtype=np.float64)
    if a.shape!=(10,9) or b.shape!=(10,9) or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("M29_3_2_INVALID_JACOBIAN_SHAPE_OR_VALUE")
    diff=b-a
    denom=max(float(np.linalg.norm(a)),1e-15)
    col_den=np.maximum(np.linalg.norm(a,axis=0),1e-12)
    return {
      "global_relative_frobenius_error":float(np.linalg.norm(diff)/denom),
      "max_absolute_error":float(np.max(np.abs(diff))),
      "per_column_relative_error":[float(x) for x in np.linalg.norm(diff,axis=0)/col_den],
      "max_column_relative_error":float(np.max(np.linalg.norm(diff,axis=0)/col_den)),
      "fd_frobenius_norm":float(np.linalg.norm(b)),
      "analytic_tangent_frobenius_norm":float(np.linalg.norm(a)),
    }
