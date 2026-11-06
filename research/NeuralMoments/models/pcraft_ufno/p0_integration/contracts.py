"""Frozen ten-raw-moment interface shared by P0 adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import Tensor

MOMENT_NAMES = ("mass", "x", "y", "z", "xx", "yy", "zz", "yz", "xz", "xy")
NATIVE_COEFFICIENT_ORDER = ("const", "x", "y", "z", "xx", "yy", "zz", "yz", "xz", "xy")


def _finite(name: str, value: Tensor) -> None:
    if not isinstance(value, Tensor) or not value.is_floating_point():
        raise TypeError(f"{name} must be a floating-point tensor")
    if not bool(torch.isfinite(value).all()):
        raise ValueError(f"{name} must be finite")


def raw_monomials(points: Tensor) -> Tensor:
    """Return the ten undoubled raw monomials in W0 order."""
    _finite("points", points)
    if points.ndim < 2 or points.shape[-1] != 3:
        raise ValueError("points must have shape [..., N, 3]")
    x, y, z = points.unbind(dim=-1)
    return torch.stack((torch.ones_like(x), x, y, z, x*x, y*y, z*z, y*z, x*z, x*y), dim=-1)


def native_quadric_value(points: Tensor, coefficients: Tensor) -> Tensor:
    """Evaluate the native polynomial; cross coefficients have factor two."""
    _finite("points", points)
    _finite("coefficients", coefficients)
    if points.shape[-1] != 3 or coefficients.shape[-1] != 10:
        raise ValueError("expected points[...,3] and native coefficients[...,10]")
    x, y, z = points.unbind(dim=-1)
    c = coefficients
    components = []
    for index in range(10):
        value = c[..., index]
        while value.ndim < x.ndim:
            value = value.unsqueeze(-1)
        components.append(value)
    return (components[0] + components[1]*x + components[2]*y + components[3]*z
            + components[4]*x*x + components[5]*y*y + components[6]*z*z
            + 2*components[7]*y*z + 2*components[8]*x*z + 2*components[9]*x*y)


@dataclass(frozen=True)
class MomentQuadratureResult:
    moments: Tensor
    jacobian: Optional[Tensor] = None
    uncertainty: Optional[Tensor] = None
    source: str = "unspecified"
    derivative_status: str = "WITHHELD"
    training_admitted: bool = False

    def __post_init__(self) -> None:
        _finite("moments", self.moments)
        if self.moments.shape[-1] != 10:
            raise ValueError("moments must end in ten raw components")
        if self.jacobian is not None:
            _finite("jacobian", self.jacobian)
            if self.jacobian.shape[-2:] != (10, 10):
                raise ValueError("jacobian must end in [10,10]")
        if self.uncertainty is not None:
            _finite("uncertainty", self.uncertainty)
            if self.uncertainty.shape[-1] != 10 or bool((self.uncertainty < 0).any()):
                raise ValueError("uncertainty must be nonnegative with ten components")
        # An upstream adapter cannot grant derivative/training admission.
        if self.training_admitted:
            raise ValueError("P0 adapters cannot admit training or Newton derivatives")
        if self.jacobian is not None:
            raise ValueError("P0 adapters must withhold J_D until W0/W2 certification")
