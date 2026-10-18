"""Explicit physical frame/scale and native quadric pullback for MomentContractV1."""
import numpy as np
from .moment_coordinates import checked,normalize_new_c,pushforward_raw


def quadric_homogeneous(c):
    """beta=c0+b·x+x^T A x, native c stores symmetric matrix entries."""
    c = checked(c,(10,),"c")
    H = np.zeros((4,4))
    H[:3,:3] = ((c[4],c[9],c[8]),(c[9],c[5],c[7]),(c[8],c[7],c[6]))
    H[:3,3] = c[1:4]/2
    H[3,:3] = c[1:4]/2
    H[3,3] = c[0]
    return H


def pullback_native(c,linear,translation=(0.,0.,0.)):
    """C++ equivalent: normalized beta(A y+t) without flipping positive sign."""
    A,t=checked(linear,(3,3),"linear"),checked(translation,(3,),"translation")
    if abs(float(np.linalg.det(A)))<=1e-15:
        raise ValueError("singular pullback")
    T=np.eye(4)
    T[:3,:3],T[:3,3]=A,t
    H=T.T@quadric_homogeneous(c)@T
    coeff=np.array((H[3,3],2*H[0,3],2*H[1,3],2*H[2,3],
                    H[0,0],H[1,1],H[2,2],H[1,2],H[0,2],H[0,1]))
    return normalize_new_c(coeff)


def physical_from_normalized(raw,*,original_origin,length_units,density_units):
    """Model x_original=origin+L*x_normalized and rho_original=R*rho_normalized."""
    if length_units<=0 or density_units<=0:
        raise ValueError("positive scale and density required")
    return pushforward_raw(raw,np.eye(3)*length_units,original_origin,
                           density_ratio=density_units)
