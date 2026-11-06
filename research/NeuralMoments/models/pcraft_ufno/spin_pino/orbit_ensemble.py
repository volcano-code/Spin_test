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
                  rotations: Iterable[Tensor], *, with_jacobian: bool = True):
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
    moments, jacobians = [], []
    for R in views:
        R = R.to(device=device, dtype=dtype)
        D_R = rotate_geometry_voxels(geometry, R)
        c_R = transform_native_coefficients(coefficients, R)
        z_R = model.encode_geometry(D_R)
        r_R = model.moment_from_weights(z_R, c_R)
        moments.append(transform_raw_moments(r_R, R.T))
        if with_jacobian:
            J_R = model.jacobian_from_weights(z_R, c_R)
            jacobians.append(transform_native_jacobian(J_R, R.T))
    result = {
        "moments": torch.stack(moments, dim=0).mean(dim=0),
        "views": torch.tensor(len(views), device=device),
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
