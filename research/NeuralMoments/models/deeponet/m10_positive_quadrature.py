"""W5 M10: a *discrete positive-measure* ten-moment surrogate.

This is a W5-owned read-only adapter around W6's SHA-pinned Gauss encoder.
At fixed quadrature nodes x_k in [-1,1]^3 and frozen geometry weights
w_k >= 0, define the W0 raw-moment vector

    r_D(c) = sum_k w_k sigmoid[(q.m_k)/(eps ||q||)] m_k, q=Bc.

Every output is the raw moment of a nonnegative *discrete* measure; hence
mass, covariance and known-box moment inequalities hold (up to roundoff).
Unlike the W6 convex scalar potential, the resulting Jq need NOT be symmetric
or positive semidefinite. This is a deliberate and measurable tradeoff.

Its closed-form Jc is the derivative of THIS SMOOTH DISCRETE SURROGATE ONLY.
It is NOT the native Cherchi continuum/Boolean Jc and must never be admitted
as W2 ground truth. Strict constant/bounding-cube empty/full cases use exact
rational sign bounds and explicit piecewise discrete moments with Jc=0.
Those sign shortcuts are valid only under caller-grounded [-1,1]^3 support,
not arbitrary CAD, and branch boundaries are not smooth derivative regions.
No original W6 file, network weight or checkpoint is modified.
"""
from __future__ import annotations

from fractions import Fraction
import math
import torch
from torch import Tensor, nn

B_NATIVE = (1.,) * 7 + (2.,) * 3


def cube_sign_states(c_native: Tensor) -> tuple[str, ...]:
    """Sufficient, conservative exact-binary-rational sign bounds on [-1,1]^3.

    For x,y,z in [-1,1], |x_i|, |x_i^2| and |x_ix_j| are <=1.
    The native symmetric cross terms appear TWICE in the polynomial.
    Returning UNDECIDED is always allowed; false EMPTY/FULL is not.
    """
    if not isinstance(c_native, Tensor) or c_native.ndim != 2 or c_native.shape[1] != 10:
        raise ValueError('native c[B,10] required')
    if not c_native.is_floating_point() or not bool(torch.isfinite(c_native).all()):
        raise ValueError('non-finite native coefficients')
    if not bool((c_native.norm(dim=1) > 1e-12).all()):
        raise ValueError('zero native c cannot be classified')
    states=[]
    for row in c_native.detach().cpu().tolist():
        a = [Fraction(float(x)) for x in row]
        wiggle = sum(abs(x) for x in a[1:7]) + 2*sum(abs(x) for x in a[7:10])
        lower, upper = a[0]-wiggle, a[0]+wiggle
        states.append('CERTIFIED_EMPTY' if upper < 0 else
                      'CERTIFIED_FULL' if lower > 0 else 'UNDECIDED')
    return tuple(states)


class PositiveQuadratureMoment(nn.Module):
    """Same W6 Gauss geometry trunk, weights and parameters; different head.

    Constructor accepts a caller-created SHA-pinned W6 GaussPotentialMoment.
    Do not construct untrusted W6 modules here. `encode_geometry` is called
    exactly once per D and `moment`/`jacobian` reuse its tensor output.
    """

    def __init__(self, weight_model: nn.Module, *, smoothing: float = 0.12,
                 certify_cube_sign: bool = True):
        super().__init__()
        if not isinstance(weight_model, nn.Module) or not hasattr(weight_model, 'encode_geometry'):
            raise ValueError('valid read-only W6-compatible weight encoder required')
        if not isinstance(smoothing, (float,int)) or not math.isfinite(smoothing) or not 0 < smoothing <= 1:
            raise ValueError('finite smoothing in (0,1] required')
        if not isinstance(certify_cube_sign,bool):
            raise ValueError('certify_cube_sign must be bool')
        if getattr(weight_model, 'rule',None)!='gauss':
            raise ValueError('requires positive Gauss rule; not raw FEM fields')
        self.encoder=weight_model
        self.smoothing=float(smoothing)
        self.certify_cube_sign=certify_cube_sign

    def encode_geometry(self, D: Tensor) -> Tensor:
        return self.encoder.encode_geometry(D)

    def _core(self, z:Tensor, c:Tensor):
        self.encoder._validate(z,c)
        if not torch.all(torch.isfinite(self.encoder.monomials)):
            raise ValueError('nonfinite fixed quadrature points')
        monomials=self.encoder.monomials.to(dtype=c.dtype,device=c.device)
        B=self.encoder.native_B.to(dtype=c.dtype,device=c.device)
        q=c*B
        qnorm=torch.linalg.vector_norm(q,dim=-1,keepdim=True)
        a=q@monomials.T
        s=a/(self.smoothing*qnorm)
        gate=torch.sigmoid(s)
        return monomials,B,q,qnorm,a,gate

    def _sign_masks(self,c:Tensor):
        if not self.certify_cube_sign:
            return torch.zeros(c.shape[0],device=c.device,dtype=torch.bool),torch.zeros(c.shape[0],device=c.device,dtype=torch.bool)
        states=cube_sign_states(c)
        return (torch.tensor([x=='CERTIFIED_EMPTY' for x in states],device=c.device),
                torch.tensor([x=='CERTIFIED_FULL' for x in states],device=c.device))

    def moment(self,z:Tensor,c:Tensor) -> Tensor:
        m,_,_,_,_,gate=self._core(z,c)
        measured=(z*gate)@m
        empty,full=self._sign_masks(c)
        if self.certify_cube_sign:
            full_r=z@m
            return torch.where(empty[:,None],torch.zeros_like(measured),
                               torch.where(full[:,None],full_r,measured))
        return measured

    def jacobian(self,z:Tensor,c:Tensor) -> Tensor:
        m,B,q,qnorm,a,gate=self._core(z,c)
        # d sigmoid(s)/d q_j = sigmoid(s)*(1-sigmoid(s)) *
        # [m_j/(eps ||q||) - (q.m) q_j/(eps ||q||^3)].
        dg=gate*(1.-gate)
        dsdq=(m[None,:,:]/(self.smoothing*qnorm[:,:,None])
              -a[:,:,None]*q[:,None,:]/(self.smoothing*qnorm[:,:,None]**3))
        Jq=torch.einsum('bn,ni,bnj->bij',z*dg,m,dsdq)
        Jc=Jq*B[None,None,:]
        empty,full=self._sign_masks(c)
        return torch.where((empty|full)[:,None,None],torch.zeros_like(Jc),Jc)

    def forward(self,D:Tensor,c:Tensor)->Tensor:
        return self.moment(self.encode_geometry(D),c)

    def counted_real_parameters(self)->int:
        return sum(p.numel()*(2 if p.is_complex() else 1)
                   for p in self.parameters() if p.requires_grad)

    def derivative_contract(self)->dict:
        return {'source':'POSITIVE_DISCRETE_QUADRATURE_SURROGATE',
                'native_B_diag':B_NATIVE,'local_surrogate_Jc_analytic':True,
                'native_Cherchi_Jc_certified':False,
                'ambient_continuum_Hessian_symmetry_guaranteed':False,
                'moment_measure_positive_discrete_only':True,
                'CAD_or_Boolean_material_certified':False,
                'sign_shortcuts_restricted_to_known_cube':self.certify_cube_sign,
                'no_W2_teacher_admission':True}
