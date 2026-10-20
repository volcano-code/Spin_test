"""M9 atom-resolution ablation: bounded nonnegative weights, 0/1/2 supports.

Explicitly consumes *geometry-only* anti-aliased capacities from m9_antialias.
This is a non-neural diagnostic adapter with a neutral gate=0.5 by default;
not a claim of pretrained M7 neural weights or a fair W5 GPU comparison.
Optional trilinear transfer of a single cached learned gate lets a frozen M7
trunk amortize geometry across multiple atom resolutions without retraining.

The moment r(c) is the W0 raw moment of a nonnegative atomic measure. The
native 10x10 Jacobian is the derivative of the normalized smooth M7 surrogate,
NOT W2 native derivative. Ambient Jc B^-1 is not generally symmetric.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import torch
from torch import Tensor
from .m9_antialias import CapacityGrid
from .m7_teacher_gate import NativeTeacherNotReady
from .m6_moment_guard import physical_moment_diagnostic,PhysicalAdmissibilityFailure

_NATIVE_B=torch.tensor([1.]*7+[2.]*3,dtype=torch.float64)
_SCALE=torch.tensor([8.]+[16.]*3+[32.]*6,dtype=torch.float64)


def transfer_legacy_gate(model, D:Tensor, target:CapacityGrid)->Tensor:
    """Encode learned gate ONCE, multilinearly interpolate gauss tensor gate.

    Returns a geometry-dependent bounded gate, not a native/geometry seal.
    Source M7 Gaussian nodes form a tensor product grid and may use any n>=2.
    """
    if not isinstance(D,Tensor) or D.ndim!=5 or D.shape[1]!=4 or D.shape[0]!=1:
        raise ValueError('single 4-channel D is required for frozen gate transfer')
    if D.dtype!=model.monomials.dtype or D.device!=model.monomials.device:
        raise ValueError('D must match M7 dtype and device')
    with torch.no_grad():
        features=model.encoder.encode_geometry(D)
        source=torch.sigmoid(model.weight_head(features)).flatten().double().cpu().numpy()
    n=round(len(source)**(1/3))
    if n**3!=len(source):raise ValueError('M7 atom grid must be tensor-product cube')
    grid=model.quadrature_xyz.detach().cpu().numpy().reshape(n,n,n,3)
    xs=grid[:,0,0,0]
    if not np.all(np.diff(xs)>0):raise ValueError('nonmonotone M7 Gauss nodes')
    dest=target.xyz.detach().cpu().numpy()
    bins=np.clip(np.searchsorted(xs,dest,side='right')-1,0,n-2)
    t=np.clip((dest-xs[bins])/(xs[bins+1]-xs[bins]),0,1)
    gate=source.reshape(n,n,n)
    result=np.zeros(len(dest))
    for mask in range(8):
        s=np.array([(mask>>j)&1 for j in range(3)],dtype=np.int64)
        ijk=bins+s
        weight=np.prod(np.where(s,t,1-t),axis=1)
        result+=weight*gate[ijk[:,0],ijk[:,1],ijk[:,2]]
    return torch.as_tensor(result,dtype=torch.float64).clamp(0,1)


@dataclass(frozen=True)
class M9AdapterAudit:
    query_count:int
    loss_before:float
    loss_after:float
    iterations:int
    support_mass_exceeds_estimated_capacity:bool
    source:str='ANALYTIC_CONTINUUM_P0_ONLY'


class BoundedCellMoment:
    def __init__(self, grid:CapacityGrid, *, gate:Tensor|None=None,temperature:float=.12):
        if not isinstance(grid,CapacityGrid):raise TypeError('CapacityGrid required')
        if not math.isfinite(temperature) or temperature<=0:raise ValueError('positive temperature')
        self.grid=grid
        cap=grid.estimated_capacity
        if gate is None:gate=torch.full_like(cap,.5)
        if gate.shape!=cap.shape or gate.dtype!=cap.dtype or not bool(torch.isfinite(gate).all()):
            raise ValueError('gate shape, dtype and finite values required')
        if not bool(((gate>=0)&(gate<=1)).all()):raise ValueError('gate outside [0,1]')
        self.capacity=cap.clone()
        self.weights=(cap*gate).clone()
        self.temperature=float(temperature)
        self.monomials=grid.moment_basis

    def _alpha(self,c:Tensor)->tuple[Tensor,Tensor,Tensor]:
        if c.ndim==1:c=c[None]
        if c.ndim!=2 or c.shape[1]!=10 or c.dtype!=torch.float64 or not bool(torch.isfinite(c).all()):
            raise ValueError('finite native c[B,10] float64 required')
        norm=c.norm(dim=-1,keepdim=True)
        if bool((norm<=1e-12).any()):raise ValueError('zero control c')
        B=_NATIVE_B.to(c.device)
        beta=(c*B) @ self.monomials.to(c.device).T
        alpha=torch.sigmoid(beta/(norm*self.temperature))
        return alpha,norm,beta

    def moment(self,c:Tensor,*,weights:Tensor|None=None)->Tensor:
        alpha,_,_=self._alpha(c)
        z=self.weights if weights is None else weights
        if z.shape!=self.capacity.shape or bool((z<0).any() or (z>self.capacity+1e-12).any()):
            raise ValueError('invalid capacity-bounded atom weights')
        return (alpha*z[None])@self.monomials

    def jacobian(self,c:Tensor,*,weights:Tensor|None=None)->Tensor:
        alpha,norm,beta=self._alpha(c)
        if c.ndim==1:c=c[None]
        z=self.weights if weights is None else weights
        if z.shape!=self.capacity.shape or bool((z<0).any() or (z>self.capacity+1e-12).any()):
            raise ValueError('invalid capacity-bounded atom weights')
        bm=self.monomials*_NATIVE_B
        grad=bm[None]-(beta/norm.square())[:,:,None]*c[:,None,:]
        coeff=z[None]*alpha*(1-alpha)/(norm*self.temperature)
        return torch.einsum('bn,ni,bnj->bij',coeff,self.monomials,grad)

    def fit(self,support_c:Tensor,support_r:Tensor,*,source:str, ridge:float=1e-4,max_iterations:int=5)->M9AdapterAudit:
        if source!='ANALYTIC_P0':
            raise NativeTeacherNotReady('W2 H8f 81 archived candidates are excluded; native admission requires independently validated seals')
        if (support_c.ndim!=2 or support_c.shape[-1]!=10 or
            support_r.shape!=support_c.shape or support_c.shape[0] not in (0,1,2) or
            support_c.dtype!=torch.float64 or support_r.dtype!=torch.float64 or
            not bool(torch.isfinite(support_c).all() and torch.isfinite(support_r).all())):
            raise ValueError('support must be float64 [K,10], K=0/1/2, finite')
        if not math.isfinite(ridge) or ridge<=0 or type(max_iterations) is not int or max_iterations<1 or max_iterations>20:
            raise ValueError('invalid ridge or iteration budget')
        k=len(support_c)
        if k==0:return M9AdapterAudit(0,0.,0.,0,False)
        checks=physical_moment_diagnostic(support_r,tol=1e-6)
        if not bool(checks['necessary_conditions_pass'].all()):
            raise PhysicalAdmissibilityFailure('analytic support violates material-moment necessary conditions')
        alpha,_,_=self._alpha(support_c)
        design=(alpha[:,:,None]*self.monomials[None]).permute(0,2,1)
        a=(design/_SCALE[None,:,None]).reshape(k*10,-1)
        target=(support_r/_SCALE[None]).reshape(-1)
        def loss(w):return (a@w-target).square().mean()
        before=float(loss(self.weights))
        now=self.weights.clone()
        value=before
        n_moves=0
        eye=torch.eye(k*10,dtype=torch.float64)
        if before>1e-28:
            for _ in range(max_iterations):
                residual=target-a@now
                gram=(a*self.capacity[None])@a.T
                delta=self.capacity*(a.T@torch.linalg.solve(gram+ridge*eye,residual))
                candidate=(now+delta).clamp(min=0).minimum(self.capacity)
                chosen=now;chosen_value=value
                for step in (1.,.5,.25,.125):
                    trial=now+step*(candidate-now)
                    err=float(loss(trial))
                    if math.isfinite(err) and err<chosen_value-1e-16:
                        chosen=trial;chosen_value=err
                if chosen is now:break
                now=chosen;value=chosen_value;n_moves+=1
        self.weights=now
        return M9AdapterAudit(k,before,float(loss(now)),n_moves,
              bool(float(support_r[:,0].max())>float(self.capacity.sum())+1e-7))
