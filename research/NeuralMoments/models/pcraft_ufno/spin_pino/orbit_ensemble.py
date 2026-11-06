"""SO(3) orbit-averaged inference for the PINO-first Spin moment model.

Each view rotates geometry and native quadric coefficients together. Predicted
moments/Jacobians are transformed back to the canonical frame before averaging.
This is a test-time equivariant ensemble, not a claim that the backbone itself
is exactly equivariant. Voxel resampling error must be reported separately.
"""
from __future__ import annotations
from typing import Iterable, Optional
import torch
from torch import Tensor
from .equivariance import (
    cube_rotation_matrices, random_so3_rotation, rotate_geometry_voxels,
    transform_native_coefficients, transform_raw_moments,
    transform_native_jacobian,
)

def orbit_average(model, geometry: Tensor, coefficients: Tensor,
                  rotations: Iterable[Tensor], *, with_jacobian: bool = True,
                  max_relative_mass_drift: Optional[float] = None):
    """Predict in rotated views and average outputs in the original frame."""
    if geometry.ndim != 5 or geometry.shape[1] != 4:
        raise ValueError("geometry must be [B,4,X,Y,Z]")
    if coefficients.ndim != 2 or coefficients.shape != (geometry.shape[0], 10):
        raise ValueError("coefficients must be [B,10]")
    views = list(rotations)
    if not views:
        raise ValueError("orbit must contain at least one rotation")
    dtype, device = geometry.dtype, geometry.device
    eye = torch.eye(3, dtype=dtype, device=device)
    if not any(torch.allclose(r.to(device=device,dtype=dtype), eye, atol=1e-7, rtol=1e-7) for r in views):
        views.insert(0, eye)
    # M7f: a fail-closed, opt-in *discrete* material mass drift screen.
    # This does not recover continuum moments or certify arbitrary rotations.
    reference_mass = None
    if max_relative_mass_drift is not None:
        limit = float(max_relative_mass_drift)
        if not (0.0 <= limit < float("inf")):
            raise ValueError("max_relative_mass_drift must be finite and nonnegative")
        reference_mass = (geometry[:, 0] * geometry[:, 1]).sum(dim=(1, 2, 3))
        if not bool(torch.isfinite(reference_mass).all()) or bool((reference_mass <= 0).any()):
            raise ValueError("mass drift screen requires positive finite sampled material mass")
    requested_views = len(views)
    rejected_views = 0
    moments, jacobians = [], []
    for R in views:
        R = R.to(device=device, dtype=dtype)
        D_R = rotate_geometry_voxels(geometry, R)
        if reference_mass is not None and not torch.allclose(
            R, eye, atol=1e-7, rtol=1e-7
        ):
            sampled_mass = (D_R[:, 0] * D_R[:, 1]).sum(dim=(1, 2, 3))
            relative_drift = ((sampled_mass - reference_mass).abs()
                              / reference_mass.abs().clamp_min(1e-12))
            # Reject for the entire batch: averaging must use the same views
            # for all samples, preserving a well-defined batch output.
            if (not bool(torch.isfinite(relative_drift).all())
                    or bool((relative_drift > limit).any())):
                rejected_views += 1
                continue
        c_R = transform_native_coefficients(coefficients, R)
        z_R = model.encode_geometry(D_R)
        r_R = model.moment_from_weights(z_R, c_R)
        moments.append(transform_raw_moments(r_R, R.T))
        if with_jacobian:
            J_R = model.jacobian_from_weights(z_R, c_R)
            jacobians.append(transform_native_jacobian(J_R, R.T))
    result = {
        "moments": torch.stack(moments, dim=0).mean(dim=0),
        "views": torch.tensor(len(moments), device=device),
        "requested_views": torch.tensor(requested_views, device=device),
        "rejected_views": torch.tensor(rejected_views, device=device),
    }
    if with_jacobian:
        result["jacobian"] = torch.stack(jacobians, dim=0).mean(dim=0)
    return result

def make_cube_orbit(*, dtype=torch.float32, device=None, max_views: Optional[int] = None):
    rotations = list(cube_rotation_matrices(dtype=dtype, device=device))
    if max_views is not None:
        if max_views < 1:
            raise ValueError("max_views must be >=1")
        indices = torch.linspace(0, len(rotations)-1, min(max_views, len(rotations))).round().long().tolist()
        selected = [rotations[i] for i in indices]
        identity = torch.eye(3, dtype=dtype, device=device)
        if not any(torch.allclose(r, identity) for r in selected):
            selected[0] = identity
        rotations = selected
    return rotations

def make_so3_orbit(count: int, *, seed: int, dtype=torch.float32, device=None):
    if count < 1:
        raise ValueError("count must be >=1")
    return [torch.eye(3, dtype=dtype, device=device)] + [
        random_so3_rotation(seed + i, dtype=dtype, device=device)
        for i in range(count - 1)
    ]
