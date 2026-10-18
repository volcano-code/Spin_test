"""Independent analytic P0 references; NEVER a native Cherchi material certificate."""
import math
import numpy as np
from .moment_coordinates import checked,tensors_to_raw,jacobian_monomial_to_native


def box(center,half_extents,density=1.):
    c,h=checked(center,(3,),"center"),checked(half_extents,(3,),"half")
    if np.any(h<=0) or density<=0:
        raise ValueError("positive box extents and density required")
    m=8*float(np.prod(h))*density
    return tensors_to_raw(m,m*c,m*(np.outer(c,c)+np.diag(h*h/3)))


def ellipsoid(center,axes,rotation=None,density=1.):
    c,a=checked(center,(3,),"center"),checked(axes,(3,),"axes")
    R=np.eye(3) if rotation is None else checked(rotation,(3,3),"R")
    if np.any(a<=0) or density<=0 or not np.allclose(R.T@R,np.eye(3),rtol=1e-12,atol=1e-12) or not np.isclose(np.linalg.det(R),1.,atol=1e-12):
        raise ValueError("invalid ellipsoid geometry")
    m=4*math.pi/3*float(np.prod(a))*density
    return tensors_to_raw(m,m*c,m*(np.outer(c,c)+R@np.diag(a*a/5)@R.T))


def sphere_cap(radius,cut_z,density=1.):
    """Ball of radius R intersected with z>=h, with -R<h<R."""
    R,h,rho=float(radius),float(cut_z),float(density)
    if not (math.isfinite(R) and R>0 and math.isfinite(h) and -R<h<R and math.isfinite(rho) and rho>0):
        raise ValueError("invalid cap")
    mass=rho*math.pi*(2*R**3/3-R*R*h+h**3/3)
    Lz=rho*math.pi*(R*R-h*h)**2/4
    Qz=rho*math.pi*(R*R*(R**3-h**3)/3-(R**5-h**5)/5)
    Qx=rho*math.pi/4*(R**4*(R-h)-2*R*R*(R**3-h**3)/3+(R**5-h**5)/5)
    return np.array((mass,0.,0.,Lz,Qx,Qx,Qz,0.,0.,0.))


def sphere_cap_ambient_jacobian(radius,cut_z,*,vertical_coefficient=1.,density=1.):
    """Jc = Jq B for smooth beta=cz*(z-h)>=0 (cz>0), full ambient c.

    Jq = (rho/cz) integral_over_disk m(x,y,h)m(x,y,h)^T dA.
    Valid for continuum interior cut only; discrete contact J may be undefined.
    """
    R,h,cz,rho=map(float,(radius,cut_z,vertical_coefficient,density))
    if not (R>0 and -R<h<R and cz>0 and rho>0 and all(map(math.isfinite,(R,h,cz,rho)))):
        raise ValueError("smooth cap Hessian not applicable")
    powers=((0,0,0),(1,0,0),(0,1,0),(0,0,1),(2,0,0),(0,2,0),
            (0,0,2),(0,1,1),(1,0,1),(1,1,0))
    disk=math.sqrt(R*R-h*h)
    Jq=np.empty((10,10))
    for i,p in enumerate(powers):
        for j,q in enumerate(powers):
            nx,ny,nz=(p[k]+q[k] for k in range(3))
            moment=0. if nx%2 or ny%2 else (math.gamma((nx+1)/2)*math.gamma((ny+1)/2)/math.gamma((nx+ny)/2+2))*disk**(nx+ny+2)
            Jq[i,j]=rho/cz*h**nz*moment
    return jacobian_monomial_to_native(Jq)
