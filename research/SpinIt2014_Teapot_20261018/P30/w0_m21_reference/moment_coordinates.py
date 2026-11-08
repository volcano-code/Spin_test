"""MomentContractV1: native symmetric-entry coefficients and undoubled mass moments.

Read-only audit: src/spin/QuadricCoefficients.cpp at frozen
0bcc187b3005478baa586a6d6f450e73811ca342; native order:
[a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy].
Raw r order from spin_common.ORDER:
[M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY].
"""
from __future__ import annotations
import math
import numpy as np

SOURCE_SHA = "0bcc187b3005478baa586a6d6f450e73811ca342"
NATIVE_C_ORDER = ("CONST","X","Y","Z","XX","YY","ZZ","YZ","XZ","XY")
RAW_R_ORDER = ("M","LX","LY","LZ","QXX","QYY","QZZ","QYZ","QXZ","QXY")
B = np.diag([1.]*7 + [2.]*3)


def checked(data, shape, label):
    # np.asarray([True, 1., 2.]) silently promotes the boolean to a float.
    # A frozen scientific contract must reject such mixed-typed coordinates.
    def has_boolean(value):
        if isinstance(value, (bool, np.bool_)):
            return True
        if isinstance(value, (list, tuple)):
            return any(has_boolean(item) for item in value)
        return isinstance(value, np.ndarray) and (
            value.dtype.kind == "b" or
            (value.dtype.kind == "O" and any(has_boolean(v) for v in value.flat)))
    if has_boolean(data):
        raise ValueError(f"{label}: boolean cannot be a real coordinate")
    a = np.asarray(data)
    if a.shape != shape or a.dtype.kind not in "iuf":
        raise ValueError(f"{label}: expected finite real {shape}")
    a = np.asarray(a, dtype=np.float64)
    if not np.isfinite(a).all():
        raise ValueError(f"{label}: nonfinite")
    return a.copy()


def normalize_new_c(c):
    """Never use to rewrite a saved normalized/hash-bound native vector."""
    c = checked(c, (10,), "native c")
    norm = float(np.linalg.norm(c))
    if not math.isfinite(norm) or norm <= 1e-15:
        raise ValueError("zero/invalid native coefficients")
    return c/norm


def native_to_monomial_coefficients(c):
    """q=B@c; cross terms have coefficient 2 in the polynomial."""
    return B @ checked(c, (10,), "native c")


def monomial_to_native_coefficients(q):
    return checked(q, (10,), "monomial q") / np.diag(B)


def monomials(x):
    x,y,z = checked(x, (3,), "position")
    return np.array((1.,x,y,z,x*x,y*y,z*z,y*z,x*z,x*y))


def evaluate_native(c, x):
    return float(native_to_monomial_coefficients(c) @ monomials(x))


def raw_to_tensors(r):
    r = checked(r, (10,), "raw r")
    Q = np.array(((r[4],r[9],r[8]),(r[9],r[5],r[7]),(r[8],r[7],r[6])))
    return float(r[0]),r[1:4],Q


def tensors_to_raw(M,L,Q):
    L,Q = checked(L,(3,),"L"),checked(Q,(3,3),"Q")
    if not np.allclose(Q,Q.T,rtol=1e-12,atol=1e-12):
        raise ValueError("Q must be symmetric")
    return np.array((float(M),*L,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]))


def jacobian_native_to_monomial(Jc):
    """Jq=Jc@B^-1; never check the native Jc itself for symmetry."""
    return checked(Jc,(10,10),"ambient Jc") / np.diag(B)[None,:]


def jacobian_monomial_to_native(Jq):
    return checked(Jq,(10,10),"ambient Jq") * np.diag(B)[None,:]


def continuum_hessian_diagnostic(Jc, *, ambient, smooth_continuum):
    """Only applicable with fully ambient smooth fixed-domain boundary derivative.

    Tangent/discrete/undefined Jacobians lack the assumed ambient Hessian.
    A small antisymmetry norm proves neither geometry nor material validity.
    """
    if not ambient or not smooth_continuum:
        raise ValueError("ambient smooth-continuum Hessian unavailable")
    H = jacobian_native_to_monomial(Jc)
    return {"maximum_absolute_asymmetry":float(np.max(np.abs(H-H.T))),
            "certifies_material":False}


def pushforward_raw(r,A,t=(0.,0.,0.),*,density_ratio=1.):
    """x'=A x+t; weight=rho_ratio*abs(det A); includes scale and density."""
    M,L,Q = raw_to_tensors(r)
    A,t = checked(A,(3,3),"A"),checked(t,(3,),"t")
    determinant = float(np.linalg.det(A))
    density_ratio = float(density_ratio)
    if abs(determinant)<=1e-15 or not math.isfinite(determinant) or not math.isfinite(density_ratio) or density_ratio<=0:
        raise ValueError("invalid affine map or density")
    w = density_ratio*abs(determinant)
    AL = A @ L
    Qp = A@Q@A.T+np.outer(AL,t)+np.outer(t,AL)+M*np.outer(t,t)
    return tensors_to_raw(w*M,w*(AL+M*t),w*Qp)


def merge_cached_fixed(fixed_r, variable_r):
    """r_total=r_fixed+r_variable; native derivative of fixed F is zero."""
    return checked(fixed_r,(10,),"cached fixed r")+checked(variable_r,(10,),"variable r")


def normalized_component_error(predicted,truth,*,length_ref,density_ref):
    p,t = checked(predicted,(10,),"prediction"),checked(truth,(10,),"truth")
    if not math.isfinite(length_ref) or length_ref<=0 or not math.isfinite(density_ref) or density_ref<=0:
        raise ValueError("positive length/density references required")
    scales = density_ref*np.array([length_ref**3]+[length_ref**4]*3+[length_ref**5]*6)
    return np.abs(p-t)/scales
