"""W6 M7: provably *discrete-measure-realizable* U-FNO ten-moment operator.

A learned nonnegative, geometry-masked atomic measure is cached once per D:
  w_k(D) = positive_rule_weight_k * density_k * occupancy_k * sigmoid(head_k(z_D)).
For a nonzero native c and B=diag(1,...,1,2,2,2), define
  alpha_k(c)=sigmoid((B*c).dot(m_k)/(temperature * ||c||_2)),
  r_D(D,c)=sum_k w_k(D)*alpha_k(c)*m_k.
Thus r_D comes from a nonnegative bounded atomic measure in [-1,1]^3;
0 <= w_k*alpha_k <= w_k. Positive projective re-scaling of c does not
change r_D; changing c to -c is *not* identified. The explicitly computed
Jacobian is the derivative of this *smooth discrete surrogate* in native c.

Because temperature depends on ||c||, ambient Jc B^-1 is NOT generally
symmetric. Its double projection into the q=Bc tangent hyperplane is a
symmetric PSD Gram; do NOT treat ambient Jc as a continuum Hessian, or a
native Cherchi derivative. tangent_jacobian() returns a 10x9 Jacobian and
an orthonormal native 10x9 basis compatible with W0's tangent shape.

No fixed F contribution is recomputed; all results concern variable D.
Neither the sampled D, atomic moments nor checks are an exact CAD/material
certificate, geometry embedding proof, native derivative or Newton result.
"""
from __future__ import annotations

import math
import torch
from torch import Tensor, nn
from torch.nn import functional as F
from .m6_gauss_potential import GaussPotentialMoment
from .m6_moment_guard import physical_moment_diagnostic, PhysicalAdmissibilityFailure
from .m6_safe_inference import region_states


class RealizableUFNOMoment(GaussPotentialMoment):
    """Same trainable trunk/head parameter count as M6 Gauss candidate."""

    def __init__(self, *, rule: str = 'gauss', points_per_axis: int = 6,
                 grid_size: int = 8, hidden: int = 32, temperature: float = 0.2):
        if not isinstance(temperature,(int,float)) or not math.isfinite(temperature) or temperature <= 0:
            raise ValueError('positive finite temperature required')
        super().__init__(rule=rule, points_per_axis=points_per_axis, grid_size=grid_size,
                         hidden=hidden, smoothing=0.04, prior_fraction=0.0)
        self.temperature = float(temperature)

    def encode_geometry(self, D: Tensor) -> Tensor:
        """One-time caching of physically nonnegative nodal D weights.

        Reject non-finite/negative density and invalid occupancy; never let a
        learned head introduce matter where sampled D has zero support.
        """
        if (not isinstance(D,Tensor) or D.ndim != 5 or D.shape[1] != 4 or
            not D.is_floating_point() or D.device != self.monomials.device or
            D.dtype != self.monomials.dtype or not bool(torch.isfinite(D).all())):
            raise ValueError('D must be finite [B,4,X,Y,Z] matching model dtype/device')
        rho, occ = D[:,0:1], D[:,1:2]
        if bool((rho < 0).any() or (occ < 0).any() or (occ > 1).any()):
            raise ValueError('negative density or occupancy outside [0,1]')
        features = self.encoder.encode_geometry(D)
        learned_gate = torch.sigmoid(self.weight_head(features))
        coords = self._voxel_sampling_grid.expand(D.shape[0],-1,-1,-1,-1)
        density_nodes = F.grid_sample(rho,coords,mode='bilinear',padding_mode='zeros',align_corners=True).flatten(1)
        occ_nodes = F.grid_sample(occ,coords,mode='bilinear',padding_mode='zeros',align_corners=True).flatten(1)
        return self.voxel_volume * density_nodes * occ_nodes * learned_gate

    def _atom_data(self, z: Tensor, c: Tensor):
        self._validate(z,c)  # stable W6 tensor shape, dtype, device and positive weights
        m = self.monomials.to(dtype=c.dtype)
        basis_native = m * self.native_B.to(c.dtype)
        quadric = torch.einsum('bi,ki->bk', c, basis_native)
        norm = torch.linalg.vector_norm(c,dim=-1,keepdim=True)
        tau = self.temperature*norm
        u = quadric / tau
        alpha = torch.sigmoid(u)
        return m,basis_native,quadric,norm,tau,alpha

    def moment(self,z: Tensor,c: Tensor)->Tensor:
        m,bm,a,n,t,alpha = self._atom_data(z,c)
        return torch.einsum('bk,ki->bi',z*alpha,m)

    def jacobian(self,z: Tensor,c: Tensor)->Tensor:
        """Exact native ambient derivative of THIS surrogate, not native teacher J.

        This J is projective (Jc*c = 0) but Jc B^-1 is not generally
        symmetric; use tangent_jacobian for W0-style tangent reporting.
        """
        m,bm,a,n,t,alpha=self._atom_data(z,c)
        grad_beta = bm[None,:,:]-(a/(n*n))[:,:,None]*c[:,None,:]
        coeff = z*alpha*(1-alpha)/t
        return torch.einsum('bk,ki,bkj->bij',coeff,m,grad_beta)

    @staticmethod
    def native_tangent_basis(c: Tensor)->Tensor:
        """Stable deterministic Householder 10x9 orthonormal c-orthogonal basis."""
        if c.ndim!=2 or c.shape[1]!=10 or not c.is_floating_point() or not bool(torch.isfinite(c).all()) or bool((c.norm(dim=-1)<=1e-12).any()):
            raise ValueError('finite nonzero native c[B,10] required')
        unit=c/c.norm(dim=-1,keepdim=True)
        axis=torch.zeros_like(unit);axis[:,0]=1
        signed=torch.where(unit[:,0:1]>=0,torch.ones_like(unit[:,0:1]),-torch.ones_like(unit[:,0:1]))
        v=unit+signed*axis
        normsq=v.square().sum(dim=-1,keepdim=True)
        eye=torch.eye(10,dtype=c.dtype,device=c.device)
        householder=eye.unsqueeze(0)-2*(v[:,:,None]*v[:,None,:])/normsq[:,:,None]
        return householder[:,:,1:]

    def tangent_jacobian(self,z:Tensor,c:Tensor)->tuple[Tensor,Tensor]:
        basis=self.native_tangent_basis(c)
        return self.jacobian(z,c) @ basis,basis

    def projected_q_gram(self,z:Tensor,c:Tensor)->Tensor:
        """P*Jq*P, P projects onto tangent to ||B^-1*q||=constant."""
        Jq=self.jacobian(z,c)/self.native_B.to(c.dtype)[None,None,:]
        n=c/self.native_B.to(c.dtype)
        proj=torch.eye(10,dtype=c.dtype,device=c.device)-n[:,:,None]*n[:,None,:]/n.square().sum(-1)[:,None,None]
        return proj @ Jq @ proj

    def safe_predict(self,z:Tensor,c:Tensor,*,low=(-1.,-1.,-1.),high=(1.,1.,1.)) -> dict:
        """Strict all-empty/all-full corrected; undecided retains soft atoms.

        WARNING: classification assumes the caller has independently bound
        the geometry support to the given box. It does not validate CAD.
        """
        self._validate(z,c)
        if tuple(float(x) for x in low)!=(-1.,-1.,-1.) or tuple(float(x) for x in high)!=(1.,1.,1.):
            raise ValueError('M7 sampled nodes only certified in fixed [-1,1]^3 coordinates')
        states=region_states(c,low=low,high=high)
        r=self.moment(z,c)
        J=self.jacobian(z,c)
        empty=torch.tensor([s=='CERTIFIED_EMPTY' for s in states],device=z.device)
        full=torch.tensor([s=='CERTIFIED_FULL' for s in states],device=z.device)
        full_r=z@self.monomials.to(z.dtype)
        r=torch.where(empty[:,None],torch.zeros_like(r),torch.where(full[:,None],full_r,r))
        J=torch.where((empty|full)[:,None,None],torch.zeros_like(J),J)
        diagnostic=physical_moment_diagnostic(r,low=low,high=high,tol=1e-6)
        if not bool(diagnostic['necessary_conditions_pass'].all()):
            raise PhysicalAdmissibilityFailure('M7 atomic moment violated numeric feasibility gate')
        return {'r':r,'Jc':J,'region_state':states,
                'necessary_conditions_pass':diagnostic['necessary_conditions_pass'],
                'moment_representation':'NONNEGATIVE_BOUNDED_QUADRATURE_ATOMS_ONLY',
                'jacobian_semantics':'SURROGATE_TANGENT_NOT_NATIVE_CONTINUUM_CERTIFICATE',
                'native_teacher_certified':False,'admitted_for_real_optimizer':False,
                'strict_case_derivative_zero':empty|full}

    def forward(self,D:Tensor,c:Tensor)->Tensor:
        return self.moment(self.encode_geometry(D),c)
