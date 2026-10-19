"""W6 M5: convex, positive-homogeneous scalar-potential ten-moment surrogate.

Analytic *model property*, NOT proof of a physical Cherchi/Boolean teacher.
For native c, q=Bc, B=diag(1,...,1,2,2,2). Define

    Phi(z,q) = sum_k w_k(z)/2 * [q.m_k + sqrt((q.m_k)^2 + eps^2 ||q||^2)]

where m_k=(1,x,y,z,x²,y²,z²,yz,xz,xy) at 4^3 fixed nodes, w>=0.
Then predicted raw r=dPhi/dq and Jc=(d²Phi/dq²) B.
Phi is convex and positively one-homogeneous for q!=0, so Jq is
symmetric positive semidefinite and Jc c=0 (within floating-point error).
This convex potential is a biased smooth approximation of a voxel hinge
integral; it does NOT by itself certify actual material or exact integrals.
No 64^3 field decoder and no recalculation of geometry per query.
"""
from __future__ import annotations

import math
import torch
from torch import nn, Tensor
from torch.nn import functional as F

from .m4_lite_model import LiteUFNOMoment, num_real_parameters

MONOMIAL_POWERS = ((0,0,0),(1,0,0),(0,1,0),(0,0,1),
                   (2,0,0),(0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))


def quadrature_monomials(points_per_axis: int = 4) -> Tensor:
    """Fixed 3D nodes in world [-1,1]^3, W0 undoubled raw-moment order."""
    if not isinstance(points_per_axis, int) or points_per_axis < 2:
        raise ValueError('quadrature grid must be an integer >=2')
    coords = (torch.arange(points_per_axis, dtype=torch.float64) + 0.5) * (2.0 / points_per_axis) - 1.0
    xyz = torch.stack(torch.meshgrid(coords, coords, coords, indexing='ij'), -1).reshape(-1,3)
    return torch.stack([xyz[:,0]**a * xyz[:,1]**b * xyz[:,2]**c
                        for a,b,c in MONOMIAL_POWERS], -1).to(torch.float32)


class ConvexPotentialMoment(nn.Module):
    """Reuse M4 spectral geometry trunk; learn 64 nonnegative quadrature weights.

    Public interface: encode_geometry(D)->weights[B,64] (cached once),
    moment(weights,c)->r[B,10], jacobian(weights,c)->Jc[B,10,10].
    We explicitly discard the old M4 10-output head, rather than count an
    unused head's parameters or claim its weights were transferred/trained.
    """

    def __init__(self, *, variant: str = 'bottleneck', grid_size: int = 8,
                 points_per_axis: int = 4, hidden: int = 60, smoothing: float = 0.04):
        super().__init__()
        if not math.isfinite(smoothing) or smoothing <= 0 or smoothing > 1:
            raise ValueError('finite smoothing in (0,1] required')
        if points_per_axis < 2 or hidden < 1:
            raise ValueError('invalid points_per_axis or hidden')
        self.encoder = LiteUFNOMoment(variant, grid_size=grid_size)
        self.encoder.head = nn.Identity()
        self.points_per_axis = points_per_axis
        self.smoothing = float(smoothing)
        n = points_per_axis**3
        self.weight_head = nn.Sequential(nn.Linear(24, hidden), nn.GELU(),
                                         nn.Linear(hidden, hidden), nn.GELU(),
                                         nn.Linear(hidden, n))
        self.register_buffer('monomials', quadrature_monomials(points_per_axis), persistent=True)
        self.register_buffer('native_B', torch.tensor([1.]*7+[2.]*3), persistent=True)
        self.register_buffer('voxel_volume', torch.tensor(8.0/n), persistent=True)

    def encode_geometry(self, D: Tensor) -> Tensor:
        """Cache nonnegative occupancy-like quadrature weights once per D."""
        features = self.encoder.encode_geometry(D)
        # Each w in (0, voxel volume); convexity/PSD remain valid under training.
        return torch.sigmoid(self.weight_head(features)) * self.voxel_volume

    def _validate(self, z: Tensor, c: Tensor) -> None:
        if (not isinstance(z, Tensor) or not isinstance(c, Tensor) or
            z.ndim != 2 or z.shape[1] != self.monomials.shape[0] or
            c.ndim != 2 or c.shape != (z.shape[0], 10)):
            raise ValueError('z[B,n_nodes], c[B,10] are required')
        if z.device != c.device or z.dtype != c.dtype or not z.is_floating_point():
            raise ValueError('z and c must share floating dtype and device')
        if not bool(torch.isfinite(z).all() and torch.isfinite(c).all()):
            raise ValueError('nonfinite geometry weights or c')
        if bool((z < 0).any()) or bool((torch.linalg.vector_norm(c, dim=-1) <= 1e-12).any()):
            raise ValueError('negative quadrature weights or invalid zero c')

    def _core(self, z: Tensor, c: Tensor):
        self._validate(z, c)
        q = c * self.native_B
        m = self.monomials.to(dtype=c.dtype)
        a = torch.einsum('bi,ki->bk', q, m)
        norm2 = q.square().sum(-1, keepdim=True)
        eps2 = self.smoothing**2
        s = torch.sqrt(a.square() + eps2 * norm2)  # strictly >0 for q!=0
        n = a.unsqueeze(-1) * m.unsqueeze(0) + eps2 * q.unsqueeze(1)
        return q, m, a, s, n, eps2

    def potential(self, z: Tensor, c: Tensor) -> Tensor:
        """Phi(z,q=Bc), scalar [B]. Its gradient in q equals moment(z,c)."""
        q, m, a, s, n, eps2 = self._core(z,c)
        return (z * (a+s)*0.5).sum(-1)

    def moment(self, z: Tensor, c: Tensor) -> Tensor:
        q, m, a, s, n, eps2 = self._core(z,c)
        dq = 0.5 * (m.unsqueeze(0) + n / s.unsqueeze(-1))
        return torch.einsum('bk,bki->bi', z, dq)

    def jacobian(self, z: Tensor, c: Tensor) -> Tensor:
        q, m, a, s, n, eps2 = self._core(z,c)
        eye = torch.eye(10, device=c.device, dtype=c.dtype)
        mm = m.unsqueeze(-1) * m.unsqueeze(-2)
        hess = 0.5 * ((mm.unsqueeze(0) + eps2*eye) / s[...,None,None]
                       - (n.unsqueeze(-1)*n.unsqueeze(-2)) / s[...,None,None]**3)
        Jq = torch.einsum('bk,bkij->bij', z, hess)
        return Jq * self.native_B.view(1,1,10)

    def forward(self, D: Tensor, c: Tensor) -> Tensor:
        return self.moment(self.encode_geometry(D), c)

    def real_parameter_count(self) -> int:
        return num_real_parameters(self)
