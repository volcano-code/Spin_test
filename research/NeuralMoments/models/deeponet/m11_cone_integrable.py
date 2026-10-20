"""W5 M11: convex homogeneous scalar potential with nonnegative discrete raw moments.

For W0 native c, q=Bc and polynomial monomials m(x), w_k(D)>=0, let
    t_k = max(q.m_k, 0), S=sum w_k*t_k**2, W=sum w_k,
    Phi(q) = (1-lambda)*sum w_k*t_k + lambda*sqrt(W*S).

On OPEN fixed-node sign strata with S>0 and away from all a_k=0:
    r=dPhi/dq=sum alpha_k*m_k, alpha_k>=0,
    Jc=(d²Phi/dq²)*B, symmetric PSD Jq=Jc/B, and Jc*c=0.
For a strictly all-negative cut, (Phi,r,J)=(0,0,0).

This is NOT a C2 global potential: ReLU node activation changes and the S=0
boundary can be nondifferentiable. It does not approximate exact continuum
Cherchi material or Hessian by itself. In particular a strictly all-positive
cut need not have exact FULL moments or zero J except constant q. Never
substitute these surrogate derivatives for uncertified W2 native labels.
"""
from __future__ import annotations

import math
import torch
from torch import nn, Tensor

B_NATIVE = (1.0,)*7 + (2.0,)*3


class ConeIntegrableMoment(nn.Module):
    """Cache nonnegative W6 Gauss weights and use a W5-owned scalar potential.

    mix=1: positive-part weighted Euclidean norm; 0<mix<1: convex combination
    with a hard hinge integral. Models have identical Gauss encoder parameters.
    """

    def __init__(self, weight_model: nn.Module, *, mix: float = 0.75,
                 boundary_rtol: float = 1e-8):
        super().__init__()
        if (not isinstance(weight_model,nn.Module) or
            getattr(weight_model, 'rule',None)!='gauss' or
            not hasattr(weight_model,'monomials') or
            not hasattr(weight_model,'_validate')):
            raise ValueError('pinned W6 positive-Gauss encoder required')
        if type(mix) not in (float,int) or not math.isfinite(mix) or not 0<mix<=1:
            raise ValueError('mix must be finite and in (0,1]')
        if type(boundary_rtol) not in (float,int) or not math.isfinite(boundary_rtol) or not 0<=boundary_rtol<1e-3:
            raise ValueError('invalid active-set boundary tolerance')
        self.encoder=weight_model
        self.mix=float(mix)
        self.boundary_rtol=float(boundary_rtol)

    def encode_geometry(self, D: Tensor) -> Tensor:
        return self.encoder.encode_geometry(D)

    def _data(self, z: Tensor, c: Tensor):
        self.encoder._validate(z,c)
        m=self.encoder.monomials.to(device=c.device,dtype=c.dtype)
        B=self.encoder.native_B.to(device=c.device,dtype=c.dtype)
        q=c*B
        a=q@m.T
        t=torch.relu(a)
        W=z.sum(-1,keepdim=True)
        S=(z*t.square()).sum(-1,keepdim=True)
        u=(z*t)@m
        # Denominator only; active S>0 is handled separately. Safe under all-negative cuts.
        rootW=torch.sqrt(W.clamp_min(0))
        rootS=torch.sqrt(S.clamp_min(1e-24))
        on=(S>1e-22)&(W>0)
        return m,B,q,a,t,W,S,u,rootW,rootS,on

    def derivative_regime(self, z:Tensor, c:Tensor) -> tuple[str,...]:
        """Reject at node-switch boundaries. Does NOT certify any native topology."""
        _,_,q,a,_,W,S,_,_,_,_=self._data(z,c)
        radius=self.boundary_rtol*torch.linalg.vector_norm(q,dim=-1)
        out=[]
        for idx in range(len(z)):
            if bool((a[idx].abs()<=radius[idx]).any()):
                out.append('NODE_SIGN_BOUNDARY_UNDEFINED')
            elif bool(S[idx]<=1e-22 or W[idx]<=0):
                out.append('STRICT_EMPTY_OR_ZERO_WEIGHT_LOCAL')
            else:
                out.append('FIXED_ACTIVE_SET_SMOOTH_SURROGATE_ONLY')
        return tuple(out)

    def potential(self,z:Tensor,c:Tensor) -> Tensor:
        _,_,_,_,t,W,S,_,_,_,_=self._data(z,c)
        hard=(z*t).sum(-1)
        norm=torch.sqrt((W*S).clamp_min(1e-24)).squeeze(-1)
        positive=((W>0)&(S>1e-22)).squeeze(-1)
        return (1-self.mix)*hard+self.mix*torch.where(positive,norm,torch.zeros_like(norm))

    def moment(self,z:Tensor,c:Tensor) -> Tensor:
        m,_,_,a,t,W,S,_,rootW,rootS,on=self._data(z,c)
        hard=z*(a>0).to(z.dtype)
        soft=torch.where(on,rootW*z*t/rootS,torch.zeros_like(z))
        masses=(1-self.mix)*hard+self.mix*soft
        return masses@m

    def jacobian(self,z:Tensor,c:Tensor) -> Tensor:
        m,B,q,a,t,W,S,u,rootW,rootS,on=self._data(z,c)
        if any(x=='NODE_SIGN_BOUNDARY_UNDEFINED' for x in self.derivative_regime(z,c)):
            raise ValueError('NODE_SIGN_BOUNDARY_HAS_NO_AMBIENT_HESSIAN')
        active=z*(a>0).to(z.dtype)
        gram=torch.einsum('bn,ni,nj->bij',active,m,m)
        hess=(gram/rootS[:,:,None] -
              u[:,:,None]*u[:,None,:]/rootS[:,:,None]**3)
        hess=torch.where(on[:,:,None],self.mix*rootW[:,:,None]*hess,torch.zeros_like(hess))
        # This is ∂r/∂c, not q: Jc=Jq B. Cross-column factors 2 are vital.
        return hess*B.view(1,1,10)

    def forward(self,D:Tensor,c:Tensor)->Tensor:
        return self.moment(self.encode_geometry(D),c)

    def real_parameter_count(self)->int:
        return sum(p.numel()*(2 if p.is_complex() else 1)
                   for p in self.parameters() if p.requires_grad)

    def derivative_contract(self)->dict:
        return {'source':'W5_CONE_VALUED_PIECEWISE_CONVEX_HOMOGENEOUS_SURROGATE',
                'projective_positive_scale_invariance':True,
                'necessary_discrete_moment_cone_by_construction':True,
                'integrable_symmetric_PSD_Jq_only_on_open_fixed_node_active_sets':True,
                'nodal_activation_switch_continuous_derivative_certified':False,
                'global_C2_or_smooth_native_ambient_guaranteed':False,
                'native_cherchi_derivative_admitted':False,
                'CAD_geometry_or_3D_volume_certified':False,
                'no_training_from_W2_uncertified_J':True}
