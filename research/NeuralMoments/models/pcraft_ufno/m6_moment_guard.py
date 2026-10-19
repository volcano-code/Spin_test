"""M6 necessary physical-moment inequalities, not a material certificate.

For a positive measure supported in a known axis-aligned bounding box,
raw mass M>=0, low*M<=L<=high*M, (M Q - L L^T)>=0, and the scalar
bound on each diagonal Qii <= (low+high)*Li - low*high*M all follow from
nonnegative density. Failure *proves an invalid moment tuple* for this
support assumption; passing DOES NOT certify existence, topology, CAD,
printability, correct solver derivative, or native material partition.

Important M5/M6 observation: convexity and PSD of Jq alone do not imply
moment-cone admissibility. The smoothed projective norm can produce negative
mass for native c=(-1,0,...,0), even with nonnegative quadrature weights.
"""
from __future__ import annotations

import torch
from torch import Tensor


class PhysicalAdmissibilityFailure(ValueError):
    pass


def physical_moment_diagnostic(r: Tensor, *, low=(-1.,-1.,-1.),
                                high=(1.,1.,1.), tol: float = 1e-8) -> dict:
    """One diagnostic per row of r[B,10], assuming known x,y,z bounds.

    tol is a *numerical feasibility check* in moment units relative to batch
    scale, not a learned prediction-error threshold and not a proof tolerance.
    """
    if not isinstance(r, Tensor) or r.ndim!=2 or r.shape[1]!=10 or not r.is_floating_point():
        raise ValueError('raw r must be floating [B,10]')
    if not bool(torch.isfinite(r).all()):
        raise ValueError('raw moments must be finite')
    lows=torch.as_tensor(low,dtype=r.dtype,device=r.device)
    highs=torch.as_tensor(high,dtype=r.dtype,device=r.device)
    if (lows.shape!=(3,) or highs.shape!=(3,) or not bool(torch.isfinite(lows).all())
        or not bool(torch.isfinite(highs).all()) or not bool((lows<highs).all())
        or not isinstance(tol,(int,float)) or not 0<=float(tol)<1):
        raise ValueError('finite increasing 3D box and tol in [0,1) required')
    M=r[:,0]
    L=r[:,1:4]
    Q=torch.empty((len(r),3,3),dtype=r.dtype,device=r.device)
    Q[:,0,0],Q[:,1,1],Q[:,2,2]=r[:,4],r[:,5],r[:,6]
    Q[:,1,2]=Q[:,2,1]=r[:,7]
    Q[:,0,2]=Q[:,2,0]=r[:,8]
    Q[:,0,1]=Q[:,1,0]=r[:,9]
    covariance=M[:,None,None]*Q-L[:,:,None]*L[:,None,:]
    min_cov_eig=torch.linalg.eigvalsh(covariance).amin(-1)
    upper_second=(lows+highs)[None,:]*L-(lows*highs)[None,:]*M[:,None]
    ub_slack=(upper_second-Q.diagonal(dim1=-2,dim2=-1)).amin(-1)
    bound_lo=(L-lows[None,:]*M[:,None]).amin(-1)
    bound_hi=(highs[None,:]*M[:,None]-L).amin(-1)
    scale=torch.maximum(r.abs().amax(-1),torch.ones_like(M))
    budget=tol*scale
    mask=(M>=-budget)&(min_cov_eig>=-budget)&(ub_slack>=-budget)&(
        bound_lo>=-budget)&(bound_hi>=-budget)
    return {'necessary_conditions_pass':mask,
            'mass':M,'smallest_covariance_eigenvalue':min_cov_eig,
            'smallest_diagonal_upper_slack':ub_slack,
            'smallest_lower_first_moment_slack':bound_lo,
            'smallest_upper_first_moment_slack':bound_hi,
            'reference_box_low':tuple(float(x) for x in lows),
            'reference_box_high':tuple(float(x) for x in highs),
            'not_a_material_proof':True}


def require_necessary_physical_moments(r: Tensor, **kwargs) -> None:
    diagnostic=physical_moment_diagnostic(r,**kwargs)
    if not bool(diagnostic['necessary_conditions_pass'].all()):
        raise PhysicalAdmissibilityFailure('predicted r violates necessary positive-material raw-moment inequalities')


def hard_quadrature_moments(weights: Tensor, c_native: Tensor, monomials: Tensor) -> Tensor:
    """Mathematical comparison only; hard Heaviside material is nonsmooth.

    With w>=0 and m[0]=1, this is an actual nonnegative discrete measure on
    the supplied quadrature points. Derivatives are withheld: the piecewise
    constant result must NOT be assigned a synthetic smooth native Jacobian.
    """
    if (not isinstance(weights,Tensor) or not isinstance(c_native,Tensor) or
        weights.ndim!=2 or c_native.shape!=(weights.shape[0],10) or
        monomials.shape!=(weights.shape[1],10)):
        raise ValueError('weights[B,N], native c[B,10], monomials[N,10] required')
    if (not weights.is_floating_point() or not bool(torch.isfinite(weights).all()) or
        not bool((weights>=0).all()) or not bool(torch.isfinite(c_native).all()) or
        not bool(torch.isfinite(monomials).all()) or
        not bool((c_native.norm(dim=-1)>1e-12).all())):
        raise ValueError('finite nonnegative weights and nonzero native c required')
    q=c_native*torch.as_tensor([1.]*7+[2.]*3,dtype=c_native.dtype,device=c_native.device)
    mask=(q@monomials.to(q.dtype).T>=0).to(weights.dtype)
    return torch.einsum('bk,ki->bi',weights*mask,monomials.to(weights.dtype))
