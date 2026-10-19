"""M6 positive-homogeneous convex potential with Gauss or midpoint quadrature.

Only changes the spatial integration rule and (optionally) the supervised
occupancy prior; it inherits M5's analytic ten-moment r/J derivatives. In
particular Phi(q) is 1-homogeneous convex and Jc @ B^-1 is symmetric PSD in
smooth ambient nonzero-q regions. These mathematical properties do not certify
exact CAD material, physical realizability of Phi's gradient, or W2 labels.

Gauss nodes are *fixed*, strictly inside [-1,1]^3 and the tensor-product
volume weights are strictly positive, with sum=8. Learned corrections remain
nonnegative and <= the corresponding volume weight. No expensive field
reconstruction, native solver, or repeated encoder calls per parameter query.
"""
from __future__ import annotations

import math

import numpy as np
import torch
from torch import Tensor
from torch.nn import functional as F

from .m5_potential import ConvexPotentialMoment, MONOMIAL_POWERS


def gauss_rule(points_per_axis: int = 6, *, dtype=torch.float32) -> tuple[Tensor, Tensor, Tensor]:
    """(world xyz[N,3], monomials[N,10], volume weights[N]) on [-1,1]^3."""
    if type(points_per_axis) is not int or points_per_axis < 2:
        raise ValueError('Gauss grid requires integer points_per_axis >=2')
    xs, ws = np.polynomial.legendre.leggauss(points_per_axis)
    xyz = np.stack(np.meshgrid(xs, xs, xs, indexing='ij'), axis=-1).reshape(-1, 3)
    weight = np.prod(np.stack(np.meshgrid(ws, ws, ws, indexing='ij'), axis=-1), axis=-1).reshape(-1)
    points = torch.as_tensor(xyz.copy(), dtype=dtype)
    monomials = torch.stack([points[:, 0] ** a * points[:, 1] ** b * points[:, 2] ** c
                              for a, b, c in MONOMIAL_POWERS], dim=-1)
    return points, monomials, torch.as_tensor(weight.copy(), dtype=dtype)


class GaussPotentialMoment(ConvexPotentialMoment):
    """Same parameter count, W0 r/J semantics and M5 spectral trunk.

    rule='midpoint' exactly restores the M5 6^3 quadrature weights and nodes.
    rule='gauss' uses Gauss-Legendre nodes/positive integration weights.
    prior_fraction>0 blends the non-trainable input occupancy sample with the
    trainable positive mass weights. For a sparse 8^3 binary input occupancy
    it is a coarse *prior*, never independent material/Boolean evidence.
    """

    def __init__(self, *, rule: str = 'gauss', prior_fraction: float = 0.0,
                 points_per_axis: int = 6, grid_size: int = 8, hidden: int = 32,
                 smoothing: float = 0.04):
        if rule not in ('gauss', 'midpoint'):
            raise ValueError('rule must be gauss or midpoint')
        if (not isinstance(prior_fraction, (float, int)) or
            not math.isfinite(prior_fraction) or not 0 <= prior_fraction < 1):
            raise ValueError('prior_fraction must be finite and in [0,1)')
        super().__init__(variant='bottleneck', grid_size=grid_size,
                         points_per_axis=points_per_axis, hidden=hidden,
                         smoothing=smoothing)
        self.rule = rule
        self.prior_fraction = float(prior_fraction)
        if rule == 'gauss':
            xyz, phi, weights = gauss_rule(points_per_axis)
            self.monomials = phi  # re-register existing persistent buffer
            self.voxel_volume = weights  # tensor-product integration, sum=8
        else:
            xs = (torch.arange(points_per_axis, dtype=torch.float32) + .5) * (2./points_per_axis)-1.
            xyz = torch.stack(torch.meshgrid(xs,xs,xs,indexing='ij'),dim=-1).reshape(-1,3)
            weights = self.voxel_volume.expand(points_per_axis**3).clone()
        self.register_buffer('quadrature_xyz', xyz, persistent=True)
        # grid_sample's last axis is xyz grid in (W=z, H=y, D=x) order.
        voxel_sampling = torch.stack((xyz[:,2], xyz[:,1], xyz[:,0]), -1).reshape(1,-1,1,1,3)
        self.register_buffer('_voxel_sampling_grid', voxel_sampling, persistent=False)
        if not bool((weights > 0).all()) or not math.isclose(float(weights.sum()),8.,rel_tol=2e-6):
            raise RuntimeError('invalid positive quadrature rule')

    def encode_geometry(self, D: Tensor) -> Tensor:
        features = self.encoder.encode_geometry(D)
        learned = torch.sigmoid(self.weight_head(features))
        if self.prior_fraction:
            if D.ndim != 5 or D.shape[1] != 4:
                raise ValueError('4-channel W6 voxel geometry required')
            occupancy = D[:,1:2]
            if not bool(torch.isfinite(occupancy).all()) or not bool(((occupancy>=0)&(occupancy<=1)).all()):
                raise ValueError('occupancy prior requires finite voxel probability in [0,1]')
            nodes = F.grid_sample(occupancy,self._voxel_sampling_grid.expand(D.shape[0],-1,-1,-1,-1),
                                  mode='bilinear', padding_mode='zeros',align_corners=True).flatten(1)
            learned = (1.0-self.prior_fraction)*learned+self.prior_fraction*nodes
        return learned * self.voxel_volume
