"""M6 conservative all-empty/full-boundary shortcut and unsafe-prediction veto.

For a W0 native symmetric-entry quadric beta_c(x) inside an explicit D box,
a sound interval enclosure can prove beta<0 everywhere (EMPTY) or beta>0
(FULL). For those strict cases a known positive discrete quadrature density
has exactly r=0 or r=sum(w_k*m_k) and dr/dc=0, respectively. Otherwise do
not pretend a learned smooth convex potential is an exact material integral:
run necessary moment inequalities, report a possible physical violation and
optionally reject inference. Neither branch certifies true CAD/Boolean F/D
regions, source identities, derivative smoothness, Newton convergence, nor
absence of out-of-distribution failures.
"""
from __future__ import annotations

import math
from fractions import Fraction

import torch
from torch import Tensor

from .m6_moment_guard import physical_moment_diagnostic, PhysicalAdmissibilityFailure


def native_quadric_interval(c_native: Tensor, *, low=(-1.,-1.,-1.),
                            high=(1.,1.,1.)) -> tuple[Tensor,Tensor]:
    """Conservative min/max of beta_c over box, including 2*x*y cross terms.

    c=(constant,x,y,z,xx,yy,zz,yz,xz,xy) in W0 native coordinates.
    Bounds are per-term intervals, so never falsely classify a strict cut
    as empty or full for mathematically exact real values; correlations
    may make the test conservative. Double arithmetic is used internally.
    """
    if (not isinstance(c_native,Tensor) or c_native.ndim!=2 or c_native.shape[1]!=10
        or not c_native.is_floating_point() or not bool(torch.isfinite(c_native).all())):
        raise ValueError('finite floating c[B,10] required')
    if not bool((c_native.norm(dim=-1)>1e-12).all()):
        raise ValueError('nonzero native c required')
    c=c_native.double()
    lo=torch.as_tensor(low,device=c.device,dtype=c.dtype)
    hi=torch.as_tensor(high,device=c.device,dtype=c.dtype)
    if lo.shape!=(3,) or hi.shape!=(3,) or not bool(torch.isfinite(lo).all()) or not bool(torch.isfinite(hi).all()) or not bool((lo<hi).all()):
        raise ValueError('finite increasing three-dimensional bounds required')
    lower=c[:,0].clone()
    upper=c[:,0].clone()
    def add_term(coeff,minvalue,maxvalue):
        nonlocal lower,upper
        lower=lower+torch.where(coeff>=0,coeff*minvalue,coeff*maxvalue)
        upper=upper+torch.where(coeff>=0,coeff*maxvalue,coeff*minvalue)
    for i in range(3):
        add_term(c[:,i+1],lo[i],hi[i])
        squared_low=torch.where(lo[i]>=0,lo[i]**2,torch.where(hi[i]<=0,hi[i]**2,torch.zeros_like(lo[i])))
        squared_high=torch.maximum(lo[i]**2,hi[i]**2)
        add_term(c[:,i+4],squared_low,squared_high)
    for slot,(i,j) in ((7,(1,2)),(8,(0,2)),(9,(0,1))):
        products=torch.stack((lo[i]*lo[j],lo[i]*hi[j],hi[i]*lo[j],hi[i]*hi[j]))
        add_term(2*c[:,slot],products.min(),products.max())
    return lower,upper


def region_states(c_native: Tensor, *, low=(-1.,-1.,-1.),
                  high=(1.,1.,1.), relative_margin=1e-10) -> tuple[str,...]:
    """CERTIFIED_EMPTY/FULL sign is exact for the input binary floats.

    Values of c and the provided bounding box are interpreted as their
    *exact* binary rational values. Each monomial is interval-bounded via
    Fraction arithmetic, including the doubled native cross coefficients.
    Thus strict sign is not a guess based on rounded float64 interval values.
    This proves the quadric sign **inside the caller-provided box only**;
    it does not prove the material D actually lies within that box, nor the
    density or geometry identities. A positive rational relative margin
    is applied to the native coefficient L1 norm for conservative separation.
    """
    if (not isinstance(relative_margin,(float,int)) or
        not math.isfinite(relative_margin) or not 0<=relative_margin<1):
        raise ValueError('relative_margin must be finite in [0,1)')
    # Front-load shape, finiteness and nonzero validation. Tensor math is
    # intentionally NOT trusted as the final sign certification.
    native_quadric_interval(c_native,low=low,high=high)

    def rational(value):
        if isinstance(value,bool) or not isinstance(value,(int,float)):
            raise ValueError('rational classifier requires int/float binary inputs')
        if isinstance(value,float) and not math.isfinite(value):
            raise ValueError('nonfinite interval boundary')
        return Fraction(value)

    left=tuple(rational(x) for x in low)
    right=tuple(rational(x) for x in high)
    margin=Fraction(float(relative_margin))
    statuses=[]
    for sample in c_native.detach().cpu().tolist():
        coef=[rational(v) for v in sample]
        smallest=coef[0]
        largest=coef[0]
        def term(coefficient, minimum, maximum):
            nonlocal smallest,largest
            if coefficient>=0:
                smallest+=coefficient*minimum
                largest+=coefficient*maximum
            else:
                smallest+=coefficient*maximum
                largest+=coefficient*minimum
        for i in range(3):
            term(coef[i+1],left[i],right[i])
            diagonal_min=(min(left[i]*left[i],right[i]*right[i])
                          if left[i]*right[i]>0 else Fraction(0))
            diagonal_max=max(left[i]*left[i],right[i]*right[i])
            term(coef[4+i],diagonal_min,diagonal_max)
        for j,(k,l) in ((7,(1,2)),(8,(0,2)),(9,(0,1))):
            p=[left[k]*left[l],left[k]*right[l],right[k]*left[l],right[k]*right[l]]
            term(2*coef[j],min(p),max(p))
        budget=margin*sum(abs(v) for v in coef)
        statuses.append('CERTIFIED_EMPTY' if largest < -budget else
                        'CERTIFIED_FULL' if smallest > budget else 'UNDECIDED')
    return tuple(statuses)


def guarded_evaluate(model, z: Tensor, c_native: Tensor,
                     *, low=(-1.,-1.,-1.),high=(1.,1.,1.),
                     reject_invalid=True) -> dict:
    """Return revised r/J and explicit admission status for each query.

    z must be a cached nonnegative quadrature representation. This method
    does NOT authorize actual native training or solver decisions by itself.
    The geometry's physical bounds must be independently grounded by caller.
    """
    if not isinstance(reject_invalid,bool):
        raise ValueError('reject_invalid must be bool')
    model._validate(z,c_native)
    states=region_states(c_native,low=low,high=high)
    r_amb=model.moment(z,c_native)
    J_amb=model.jacobian(z,c_native)
    with torch.no_grad():
        # Even a FULL classification is an approximate discrete quadrature
        # of D, NOT an exact analytic/CAD full mass moment.
        m=model.monomials.to(dtype=z.dtype)
        r_full=z@m
        r_empty=torch.zeros_like(r_full)
        empty=torch.as_tensor([s=='CERTIFIED_EMPTY' for s in states],device=z.device)
        full=torch.as_tensor([s=='CERTIFIED_FULL' for s in states],device=z.device)
    r=torch.where(empty[:,None],r_empty,torch.where(full[:,None],r_full,r_amb))
    J=torch.where((empty|full)[:,None,None],torch.zeros_like(J_amb),J_amb)
    condition=physical_moment_diagnostic(r,low=low,high=high)
    accepted=condition['necessary_conditions_pass']
    if reject_invalid and not bool(accepted.all()):
        raise PhysicalAdmissibilityFailure('unsafe W6 surrogate moments: possible negative density or violated support inequalities')
    return {'r':r,'Jc':J,'region_state':states,
            'necessary_conditions_pass':accepted,
            'strict_empty_or_full':empty|full,
            'sign_proof_mode':'EXACT_BINARY_FLOAT_COEFFICIENTS_AS_FRACTIONS',
            'independent_CAD_material_certified':False,
            'true_native_derivative_certified':False,
            'training_admissible':False,
            'scope':'known W0 world-coordinate box; approximate positive node masses, not a real material seal'}
