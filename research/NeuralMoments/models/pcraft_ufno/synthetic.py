"""Untrained, purely analytic smoke reference data; NOT W2 teacher evidence.

Coordinates use unit cube [0,1]^3 and the Spin_test native ten raw moment
ordering [mass,x,y,z,xx,yy,zz,yz,xz,xy], density=1.
"""
from __future__ import annotations

import math
import torch
from torch import Tensor


def slab_coefficients(t: Tensor) -> Tensor:
    """q(x)=x-t; q<=0 retains the slab [0,t] x [0,1]^2."""
    if t.ndim != 1 or not bool(((t > 0) & (t < 1)).all()):
        raise ValueError("t must be one-dimensional and inside (0,1)")
    c = torch.zeros((t.shape[0], 10), dtype=t.dtype, device=t.device)
    c[:, 0] = -t
    c[:, 1] = 1.0
    return c


def slab_moments(t: Tensor) -> Tensor:
    """Exact raw moments for unit-cube slab x in [0,t], no voxel quadrature."""
    return torch.stack((t, t.square() / 2, t / 2, t / 2,
                        t.pow(3) / 3, t / 3, t / 3, t / 4,
                        t.square() / 4, t.square() / 4), -1)


def slab_dr_dt(t: Tensor) -> Tensor:
    return torch.stack((torch.ones_like(t), t, t*0 + .5, t*0 + .5,
                        t.square(), t*0 + 1/3, t*0 + 1/3, t*0 + .25,
                        t / 2, t / 2), -1)


def ellipsoid_raw_moments(axes: tuple[float,float,float],
                           center: tuple[float,float,float] = (0.,0.,0.),
                           density: float = 1.) -> tuple[float, ...]:
    """Exact full homogeneous ellipsoid moments, including translated cross terms."""
    a, b, c = axes
    x, y, z = center
    if min(axes) <= 0 or density <= 0:
        raise ValueError("ellipsoid axes and density must be positive")
    m = 4 * math.pi * a * b * c * density / 3
    return (m, m*x, m*y, m*z, m*(x*x + a*a/5), m*(y*y + b*b/5),
            m*(z*z + c*c/5), m*y*z, m*x*z, m*x*y)


def solid_box_geometry(batch: int = 1, grid_size: int = 16,
                       device: str = "cpu") -> dict[str, Tensor]:
    """A deterministic full unit cube, leaving internal boundary unspecified."""
    if batch < 1 or grid_size < 8:
        raise ValueError("batch>=1 and grid_size>=8 required")
    rho = torch.ones(batch, 1, grid_size, grid_size, grid_size, device=device)
    return {"density": rho}
