"""M9 experimental finite-grid conservative rotation for a PINO geometry input.

This is a bounded discrete mass-transport projection, not a continuum CAD
integration or an exactly SO(3)-equivariant encoder. The physical support must
remain representable inside the ORIGINAL voxel cube; otherwise it fails closed.
"""
from __future__ import annotations

from typing import Dict
import torch
from torch import Tensor

from .equivariance import (
    _check_rotation, rotate_geometry_voxels, transform_raw_moments,
)


def _validate(D: Tensor) -> None:
    if D.ndim != 5 or D.shape[1] != 4 or min(D.shape[2:]) < 4:
        raise ValueError("expected geometry [B,4,X,Y,Z] with each axis >=4")
    if not D.is_floating_point() or not bool(torch.isfinite(D).all()):
        raise ValueError("geometry must be finite floating point")
    rho, occ = D[:, 0], D[:, 1]
    if bool(((rho < 0) | (rho > 1) | (occ < 0) | (occ > 1)).any()):
        raise ValueError("mass transport requires density and occupancy in [0,1]")
    if bool(((rho * occ).sum((1, 2, 3)) <= 0).any()):
        raise ValueError("mass transport requires nonempty positive material")


def _grid(nxyz, dtype, device):
    return torch.stack(torch.meshgrid(*(
        torch.linspace(-1, 1, n, device=device, dtype=dtype)
        for n in nxyz
    ), indexing="ij"), dim=-1).reshape(-1, 3)


def sampled_material_moments(D: Tensor) -> Tensor:
    """Ten uniform NODE-QUADRATURE moments; NOT analytic continuum moments."""
    _validate(D)
    coords = _grid(D.shape[-3:], D.dtype, D.device)
    x, y, z = coords.unbind(-1)
    phi = torch.stack((torch.ones_like(x), x, y, z, x*x, y*y, z*z,
                       y*z, x*z, x*y), -1)
    material = (D[:, 0] * D[:, 1]).flatten(1)
    return (material @ phi) * (8.0 / coords.shape[0])


def _bounded_projection(values: Tensor, caps: Tensor, target: Tensor) -> Tensor:
    """Project onto 0<=u<=caps, sum(u)=target, with scalar dual bisection.

    Only support cells receive positive capacity. All operations use float64
    to avoid accumulating large float32 grid-sum errors.
    """
    if values.ndim != 2 or caps.shape != values.shape or target.shape != (values.shape[0],):
        raise ValueError("invalid bounded projection shapes")
    if bool(((target < 0) | (target > caps.sum(-1) + 1e-8)).any()):
        raise ValueError("bounded rotated support cannot represent source mass")
    lo = -values.amax(-1, keepdim=True) - 1.0
    hi = caps.amax(-1, keepdim=True) + target.unsqueeze(-1) + 1.0
    for _ in range(58):
        mid = (lo + hi) * 0.5
        total = torch.clamp(values + mid, min=0).minimum(caps).sum(-1, keepdim=True)
        lo = torch.where(total < target.unsqueeze(-1), mid, lo)
        hi = torch.where(total >= target.unsqueeze(-1), mid, hi)
    return torch.clamp(values + (lo + hi) * 0.5, min=0).minimum(caps)


def conservative_rotate_geometry(D: Tensor, R: Tensor) -> tuple[Tensor, Dict[str, float]]:
    """Conservatively splat original occupied voxel-center samples under R.

    Forward trilinear splatting produces raw occupancy and material mass
    at destination nodes. Capped-simplex projections redistribute any local
    overlaps ONLY among already reached nodes; final rho*occ equals projected
    bounded material mass. No off-grid occupied sample may be silently clipped.

    It preserves discrete SUM(occ) and SUM(rho*occ) when feasible. The first and
    second moments are audited, not constrained; auxiliary proxy channels are
    rotated by the prior trilinear pull interpolation. No CAD certificate.
    """
    _validate(D)
    _check_rotation(R)
    R = R.to(dtype=D.dtype, device=D.device)
    B, _, nx, ny, nz = D.shape
    xyz = _grid((nx, ny, nz), D.dtype, D.device)
    material = D[:, 0].flatten(1) * D[:, 1].flatten(1)
    occ = D[:, 1].flatten(1)
    ref_moments = transform_raw_moments(sampled_material_moments(D), R)
    identity = torch.eye(3, dtype=D.dtype, device=D.device)
    if torch.equal(R, identity):
        return D.clone(), {"mass_relative_error": 0.0,
                           "occupancy_relative_error": 0.0,
                           "moment_covariance_relative_l2": 0.0,
                           "raw_max_occupancy": float(occ.max()),
                           "source_nodes_outside": 0}

    dst_xyz = xyz @ R.T
    outside = (dst_xyz.abs() > 1.0 + 1e-7).any(-1)
    count_outside = int(((occ > 1e-10) & outside.unsqueeze(0)).sum().item())
    if count_outside:
        raise ValueError("occupied source samples exit target cube: cannot conserve without extending domain")
    scale = torch.tensor([(nx - 1)/2, (ny - 1)/2, (nz - 1)/2],
                         dtype=D.dtype, device=D.device)
    idx_float = ((dst_xyz + 1.0) * scale).to(torch.float64)
    idx_low = torch.floor(idx_float).long()
    part = idx_float - idx_low
    splat_occ = torch.zeros((B, nx*ny*nz), dtype=torch.float64, device=D.device)
    splat_mass = torch.zeros_like(splat_occ)
    occ64 = occ.to(torch.float64)
    mass64 = material.to(torch.float64)
    sizes = torch.tensor([nx, ny, nz], device=D.device)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                corner = torch.tensor((dx, dy, dz), device=D.device)
                dest = idx_low + corner
                valid = ((dest >= 0) & (dest < sizes)).all(-1)
                weight = torch.where(corner.bool(), part, 1.0 - part).prod(-1)
                weight = torch.where(valid, weight, torch.zeros_like(weight))
                dest = dest.maximum(torch.zeros_like(dest)).minimum(sizes - 1)
                linear = dest[:, 0] * (ny*nz) + dest[:, 1]*nz + dest[:, 2]
                indexes = linear.unsqueeze(0).expand(B, -1)
                splat_occ.scatter_add_(1, indexes, occ64 * weight)
                splat_mass.scatter_add_(1, indexes, mass64 * weight)
    if not torch.allclose(splat_occ.sum(-1), occ64.sum(-1), atol=1e-8, rtol=1e-9):
        raise ArithmeticError("splat occupancy did not conserve discrete sum")
    if not torch.allclose(splat_mass.sum(-1), mass64.sum(-1), atol=1e-8, rtol=1e-9):
        raise ArithmeticError("splat material did not conserve discrete sum")
    caps = (splat_occ > 1e-12).to(torch.float64)
    occ_projected = _bounded_projection(splat_occ, caps, occ64.sum(-1))
    material_projected = _bounded_projection(splat_mass, occ_projected, mass64.sum(-1))
    rho_projected = torch.where(occ_projected > 1e-12,
                                material_projected / occ_projected.clamp_min(1e-12),
                                torch.zeros_like(material_projected))
    rho_projected = rho_projected.to(dtype=D.dtype).reshape(B, nx, ny, nz)
    occ_projected = occ_projected.to(dtype=D.dtype).reshape(B, nx, ny, nz)
    proxy = rotate_geometry_voxels(D, R)[:, 2:]
    out = torch.cat((rho_projected.unsqueeze(1), occ_projected.unsqueeze(1), proxy), 1)
    if not bool(torch.isfinite(out).all()) or bool(((out[:, :2] < 0) | (out[:, :2] > 1)).any()):
        raise ArithmeticError("conservative rotation yielded invalid physical channels")
    before_mass = material.sum(-1)
    after_mass = (out[:, 0] * out[:, 1]).flatten(1).sum(-1)
    before_occ = occ.sum(-1)
    after_occ = out[:, 1].flatten(1).sum(-1)
    mass_rel = float(((after_mass-before_mass).abs() / before_mass.clamp_min(1e-12)).max())
    occ_rel = float(((after_occ-before_occ).abs() / before_occ.clamp_min(1e-12)).max())
    if mass_rel > 2e-5 or occ_rel > 2e-5:
        raise ArithmeticError("bounded transport failed float32 conservation tolerance")
    actual = sampled_material_moments(out)
    covariance = float((torch.linalg.vector_norm(actual-ref_moments, dim=-1)
                / torch.linalg.vector_norm(ref_moments,dim=-1).clamp_min(1e-12)).max())
    return out, {"mass_relative_error": mass_rel,
                 "occupancy_relative_error": occ_rel,
                 "moment_covariance_relative_l2": covariance,
                 "raw_max_occupancy": float(splat_occ.max()),
                 "source_nodes_outside": count_outside}
