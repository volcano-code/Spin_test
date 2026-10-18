"""Independent analytic smoke teacher; NOT the W0 Spin material contract.

D = [one_hot(box,sphere,ellipsoid), center_xyz, semiaxes_xyz].
The ten monomials phi are 1,x,y,z,x^2,y^2,z^2,xy,xz,yz.
A *synthetic* density rho_c(x) = 1 + dot(c, phi(x)) is defined
on the fixed solid.  r_i = integral_D phi_i(x) rho_c(x) dx,
J_ij = integral_D phi_i(x) phi_j(x) dx. c has ten coordinates.

This construction has independent closed-form labels but DOES NOT model
Boolean carving, moving intersections, or original Spin control variables.
"""

from __future__ import annotations

import math
from typing import Sequence

import torch

FAMILIES = ("box", "sphere", "ellipsoid")
FEATURE_EXPONENTS: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
    (2, 0, 0), (0, 2, 0), (0, 0, 2),
    (1, 1, 0), (1, 0, 1), (0, 1, 1),
)


def make_geometry(family: str, center: Sequence[float], axes: Sequence[float]) -> torch.Tensor:
    """Construct a checked 9-vector; sphere requires equal semiaxes."""
    if family not in FAMILIES:
        raise ValueError(f"unknown analytic family {family!r}")
    if len(center) != 3 or len(axes) != 3:
        raise ValueError("center and axes must be 3-vectors")
    one_hot = [float(name == family) for name in FAMILIES]
    d = torch.tensor([*one_hot, *center, *axes], dtype=torch.float64)
    validate_geometry(d)
    return d


def validate_geometry(d: torch.Tensor) -> str:
    if d.shape != (9,) or not torch.isfinite(d).all():
        raise ValueError("D must be a finite 9-vector")
    tags = d[:3].tolist()
    if tags.count(1.0) != 1 or any(v not in (0.0, 1.0) for v in tags):
        raise ValueError("D must use exactly one valid family indicator")
    if torch.any(d[6:] <= 0):
        raise ValueError("analytic semiaxes must be positive")
    family = FAMILIES[tags.index(1.0)]
    if family == "sphere" and not torch.allclose(d[6:], d[6].expand(3), atol=1e-12, rtol=0):
        raise ValueError("sphere semiaxes must agree")
    return family


def _central_moment(family: str, axes: tuple[float, float, float], powers: tuple[int, int, int]) -> float:
    if any(p & 1 for p in powers):
        return 0.0
    degree = sum(powers)
    if degree == 0:
        return 1.0
    if family == "box":
        return math.prod(a ** p / (p + 1) for a, p in zip(axes, powers))
    # Uniform solid ball/ellipsoid, mapped from the unit 3-ball:
    # E[u_i^2] = a_i^2/5; E[u_i^4] = 3a_i^4/35;
    # E[u_i^2 u_j^2] = a_i^2 a_j^2/35.
    if degree == 2:
        i = powers.index(2)
        return axes[i] ** 2 / 5.0
    if degree == 4:
        if 4 in powers:
            i = powers.index(4)
            return 3.0 * axes[i] ** 4 / 35.0
        if powers.count(2) == 2:
            return math.prod(a ** p for a, p in zip(axes, powers)) / 35.0
    raise ValueError(f"unsupported central moment: {powers}")


def _raw_expectation(family: str, center: tuple[float, float, float],
                     axes: tuple[float, float, float], powers: tuple[int, int, int]) -> float:
    """Binomial expansion of shifted moments (total degree <= 4)."""
    if sum(powers) > 4:
        raise ValueError("smoke oracle supports polynomial degree at most four")
    total = 0.0
    for kx in range(powers[0] + 1):
        for ky in range(powers[1] + 1):
            for kz in range(powers[2] + 1):
                ks = (kx, ky, kz)
                central = _central_moment(family, axes, ks)
                if central == 0.0:
                    continue
                coefficient = math.prod(
                    math.comb(p, k) * m ** (p - k)
                    for p, k, m in zip(powers, ks, center)
                )
                total += coefficient * central
    return total


def analytic_moment_data(d: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Return b=(integral phi) and G=(integral phi phi^T) in float64.

    Valid for axis-aligned solids, including off-origin centers. G is PSD;
    unlike learned predictions, the analytic teacher is never trained.
    """
    d = torch.as_tensor(d, dtype=torch.float64)
    family = validate_geometry(d)
    center = tuple(float(v) for v in d[3:6])
    axes = tuple(float(v) for v in d[6:9])
    volume = (8.0 if family == "box" else 4.0 * math.pi / 3.0) * math.prod(axes)
    powers = set(FEATURE_EXPONENTS)
    powers.update(tuple(a + b for a, b in zip(e1, e2)) for e1 in FEATURE_EXPONENTS for e2 in FEATURE_EXPONENTS)
    moments = {p: volume * _raw_expectation(family, center, axes, p) for p in powers}
    b = torch.tensor([moments[p] for p in FEATURE_EXPONENTS], dtype=torch.float64)
    g = torch.tensor([
        [moments[tuple(a + b for a, b in zip(e1, e2))] for e2 in FEATURE_EXPONENTS]
        for e1 in FEATURE_EXPONENTS
    ], dtype=torch.float64)
    return b, g


def analytic_labels(d: torch.Tensor, c: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Independent teacher (r[10], J[10,10]) for one geometry/control."""
    c = torch.as_tensor(c, dtype=torch.float64)
    if c.shape != (10,) or not torch.isfinite(c).all():
        raise ValueError("c must be a finite 10-vector")
    b, g = analytic_moment_data(d)
    return b + g @ c, g


def sample_families(families: Sequence[str], per_family: int, *, seed: int,
                    queries_per_geometry: int = 2) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Deterministic, independently labeled samples; no neural pseudo-labels.

    The returned D/c/r/J are respectively [N,9], [N,10], [N,10],
    [N,10,10] float64 tensors. The caller assigns disjoint family splits.
    """
    if not families or per_family < 1 or queries_per_geometry < 1:
        raise ValueError("nonempty families and positive sample counts required")
    rng = torch.Generator(device="cpu").manual_seed(seed)
    records: list[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = []
    for family in families:
        if family not in FAMILIES:
            raise ValueError(f"unknown family {family!r}")
        for _ in range(per_family):
            center = (0.3 * torch.rand(3, generator=rng, dtype=torch.float64) - 0.15).tolist()
            axes = (0.3 * torch.rand(3, generator=rng, dtype=torch.float64) + 0.4).tolist()
            if family == "sphere":
                axes = [axes[0]] * 3
            d = make_geometry(family, center, axes)
            b, g = analytic_moment_data(d)
            for _ in range(queries_per_geometry):
                c = 0.06 * torch.rand(10, generator=rng, dtype=torch.float64) - 0.03
                records.append((d, c, b + g @ c, g))
    return tuple(torch.stack([row[k] for row in records], dim=0) for k in range(4))  # type: ignore[return-value]
