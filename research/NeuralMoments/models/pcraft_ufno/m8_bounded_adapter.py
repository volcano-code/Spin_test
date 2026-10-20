"""W6 M8 -- bounded 0/1/2-query adaptation of cached *discrete* material atoms.

Unlike output-space residual adapters, this adjusts nonnegative nodal weights
only inside independently re-sampled density*occupancy*positive quadrature
capacities. For every control c, the ten outputs remain moments of a
nonnegative, bounded atomic measure on the M7 [-1,1]^3 quadrature grid.
The corrected native J is analytic for the smooth *surrogate*; ambient
Jc B^-1 is generally NOT symmetric. Tangent and projective rules remain.

Inputs labelled ANALYTIC_P0 are independently generated continuum labels,
never native Cherchi. Requests for native/W2 training are *always rejected*
until a separately authenticated W0/W2 material & derivative contract is
integrated. No 81 archived excluded H8f samples may be used as supports.

The fitting objective is a low-rank ridge update followed by conservative
box projection and a deterministic backtracking improvement test. Monotone
SUPPORT loss is enforced, NOT guaranteed improvement on unseen c or CAD.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from torch import Tensor
from torch.nn import functional as F

from .m7_realizable import RealizableUFNOMoment
from .m6_moment_guard import (physical_moment_diagnostic,
                              PhysicalAdmissibilityFailure)
from .m7_teacher_gate import NativeTeacherNotReady


class SupportAdmissionError(ValueError):
    pass


@dataclass(frozen=True)
class AdapterAudit:
    query_count: int
    support_loss_before: tuple[float, ...]
    support_loss_after: tuple[float, ...]
    iterations: tuple[int, ...]
    support_mass_exceeds_sampled_capacity: tuple[bool, ...]
    source: str
    training_admitted_native: bool = False


class BoundedAtomAdapter:
    """Immutable cached adapted weights, no network training or geometry reruns.

    Explicitly pass D even with precomputed z to bind the fixed quadrature
    *capacity*. It is read once during fitting and never re-encoded for c.
    The caller must bind that D and z to the SAME frozen geometry externally;
    this smoke class cannot verify a CAD/file identity or an independent seal.
    """
    def __init__(self, model: RealizableUFNOMoment, D: Tensor, z: Tensor,
                 support_c: Tensor, support_r: Tensor, *,
                 source: str, ridge: float = 1e-4, max_iterations: int = 5):
        if not isinstance(model, RealizableUFNOMoment):
            raise TypeError('only M7 realizable atomic model supported')
        if source != 'ANALYTIC_P0':
            raise NativeTeacherNotReady('M8 native/W2 support admission requires independent W0/W2 seals; historical 81 H8f samples are excluded')
        if not isinstance(ridge,(float,int)) or not math.isfinite(float(ridge)) or ridge<=0:
            raise ValueError('strictly positive finite ridge required')
        if type(max_iterations) is not int or not 1 <= max_iterations <= 20:
            raise ValueError('max_iterations must be an integer in [1,20]')
        if not isinstance(D,Tensor) or not isinstance(z,Tensor) or (
             D.ndim!=5 or D.shape[1]!=4 or z.ndim!=2 or
             z.shape!=(D.shape[0],model.monomials.shape[0]) or
             D.device!=z.device or D.dtype!=z.dtype or
             D.device!=model.monomials.device or D.dtype!=model.monomials.dtype or
             not bool(torch.isfinite(D).all() and torch.isfinite(z).all())):
            raise ValueError('matching finite D[B,4,X,Y,Z] and z[B,N] required')
        if bool((D[:,0]<0).any() or (D[:,1]<0).any() or (D[:,1]>1).any()):
            raise ValueError('invalid density or occupancy')
        if (not isinstance(support_c,Tensor) or not isinstance(support_r,Tensor)
            or support_c.ndim!=3 or support_c.shape[0]!=len(D)
            or support_c.shape[-1]!=10 or support_r.shape!=support_c.shape
            or support_r.device!=D.device or support_c.device!=D.device
            or support_r.dtype!=D.dtype or support_c.dtype!=D.dtype
            or support_c.shape[1] not in (0,1,2)):
            raise ValueError('support tensors must be [B,K,10], K=0/1/2, same dtype/device')
        if not bool(torch.isfinite(support_c).all() and torch.isfinite(support_r).all()):
            raise ValueError('nonfinite support controls/moments')
        if support_c.shape[1] and bool((support_c.norm(dim=-1)<=1e-12).any()):
            raise ValueError('zero support native c')
        self.model=model
        self.ridge=float(ridge)
        self.query_count=int(support_c.shape[1])
        with torch.no_grad():
            sample_grid=model._voxel_sampling_grid.expand(D.shape[0],-1,-1,-1,-1)
            density_nodes=F.grid_sample(D[:,0:1],sample_grid,mode='bilinear',padding_mode='zeros',align_corners=True).flatten(1)
            occupancy_nodes=F.grid_sample(D[:,1:2],sample_grid,mode='bilinear',padding_mode='zeros',align_corners=True).flatten(1)
            cap=model.voxel_volume*density_nodes*occupancy_nodes
            if bool((cap<0).any() or (z<0).any() or (z>cap+1e-6).any()):
                raise SupportAdmissionError('z is not bounded by supplied D sampling capacity')
            # Small tolerated numerical roundoff on the encoder bound.
            base=z.detach().clone().clamp_min(0).minimum(cap)
            self.capacity=cap.detach().clone()
            before=[];after=[];iterations=[];mass_violates=[]
            if self.query_count:
                valid=physical_moment_diagnostic(support_r.reshape(-1,10),tol=1e-6)
                if not bool(valid['necessary_conditions_pass'].all()):
                    raise PhysicalAdmissibilityFailure('support label violates necessary nonnegative material conditions')
            adapted=base.detach().clone()
            for b in range(len(D)):
                if self.query_count==0:
                    before.append(0.);after.append(0.);iterations.append(0);mass_violates.append(False)
                    continue
                c=support_c[b].to(dtype=torch.float64)
                target=support_r[b].to(dtype=torch.float64)
                cap_b=cap[b].double()
                base_b=base[b].double()
                a=self._design(c).reshape(-1,base_b.numel())
                # Normalized components: W0 rho_ref*L_ref^3/4/5 on [-1,1]^3,
                # with density_ref fixed to 1 for synthetic analytic P0.
                scale=torch.tensor([8.]+[16.]*3+[32.]*6,dtype=torch.float64,device=c.device)
                a=(a.reshape(self.query_count,10,-1)/scale[None,:,None]).reshape(-1,len(base_b))
                y=(target/scale[None]).reshape(-1)
                def loss(w:Tensor)->Tensor:
                    return (a@w-y).square().mean()
                current=base_b
                initial=float(loss(current))
                best=initial
                moves=0
                if bool((cap_b>0).any()) and initial>1e-28:
                    eye=torch.eye(a.shape[0],dtype=a.dtype,device=a.device)
                    for _ in range(max_iterations):
                        resid=y-a@current
                        gram=(a*cap_b[None,:])@a.T
                        try:
                            delta=cap_b*(a.T@torch.linalg.solve(gram+self.ridge*eye,resid))
                        except RuntimeError as exc:
                            raise SupportAdmissionError('low-rank ridge solve failed') from exc
                        candidate=(current+delta).clamp(min=0).minimum(cap_b)
                        # Ensure no deterioration of support fit after box projection.
                        chosen=current;chosen_loss=best
                        for t in (1.,.5,.25,.125):
                            trial=current+t*(candidate-current)
                            value=float(loss(trial))
                            if math.isfinite(value) and value<chosen_loss-1e-15:
                                chosen=trial;chosen_loss=value
                        if chosen is current:
                            break
                        current=chosen
                        best=chosen_loss
                        moves+=1
                adapted[b]=current.to(base.dtype)
                before.append(initial)
                after.append(float(loss(adapted[b].double())))
                iterations.append(moves)
                mass_violates.append(bool(float(target[:,0].max())>float(cap_b.sum())+1e-6))
            self.weights=adapted.detach()
        self.audit=AdapterAudit(query_count=self.query_count,
            support_loss_before=tuple(before),support_loss_after=tuple(after),
            iterations=tuple(iterations),
            support_mass_exceeds_sampled_capacity=tuple(mass_violates),source=source)

    def _design(self,c:Tensor)->Tensor:
        """[K,10,N], exactly matches model.moment's soft-cut alpha."""
        m=self.model.monomials.to(dtype=c.dtype)
        bc=m*self.model.native_B.to(dtype=c.dtype)
        unit=c/torch.linalg.vector_norm(c,dim=-1,keepdim=True)
        logits=(unit@bc.T)/self.model.temperature
        alpha=torch.sigmoid(logits)
        return alpha[:,None,:]*m.T[None,:,:]

    def predict(self,c:Tensor)->Tensor:
        return self.model.moment(self.weights,c)

    def jacobian(self,c:Tensor)->Tensor:
        return self.model.jacobian(self.weights,c)

    def tangent_jacobian(self,c:Tensor)->tuple[Tensor,Tensor]:
        return self.model.tangent_jacobian(self.weights,c)

    def safe_predict(self,c:Tensor)->dict:
        return self.model.safe_predict(self.weights,c)
