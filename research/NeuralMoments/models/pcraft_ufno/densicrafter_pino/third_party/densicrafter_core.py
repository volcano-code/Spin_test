"""Pinned MIT DensiCrafter loss core extracted without global CUDA state.

Original:
  https://github.com/idvxlab/DensiCrafter/tree/21e6d8dc646129a9b21a38c2d5bee5bef2704d98
  loss.py: mass_penalty
  physical.py: compute_mass_center
  geometry.py: get_smooth_bottom_contact_region

Retained original formulas. Generalization and boundary checks live in
../bridge.py; the contact weight exponent is explicitly float-compatible
with current PyTorch, unlike an implicit integer negative power.
Original copyright/license: third_party/DENSICRAFTER_LICENSE.
"""
import torch


def mass_penalty(rho):
    return rho.mean()


def compute_mass_center(rho_field, GRID):
    mass = rho_field.sum(dim=[-3, -2, -1])
    X = GRID[..., 0]
    Y = GRID[..., 1]
    Z = GRID[..., 2]
    mass_center = torch.stack([
        (X * rho_field).sum(dim=[-3, -2, -1]),
        (Y * rho_field).sum(dim=[-3, -2, -1]),
        (Z * rho_field).sum(dim=[-3, -2, -1]),
    ]) / mass
    return mass_center


def get_smooth_bottom_contact_region(rho, ground_level, exp=4):
    rho_used = rho[..., ground_level:]
    weight = torch.arange(
        0, rho_used.shape[-1], device=rho.device, dtype=rho.dtype
    )
    weight = float(exp) ** (-weight)
    rho_used = weight * rho_used
    z_plane = rho_used.max(dim=-1).values
    return z_plane
