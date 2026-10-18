"""W0 fixed-material composition. F is computed by a trusted evaluator once.

The surrogate predicts only the design's r_D(c), J_D(c). It may *never*
recalculate the fixed region F or add its mass twice. This helper does not
establish the provenance or physical validity of the supplied fixed moments.
"""
from __future__ import annotations

import torch
from torch import Tensor


def merge_fixed_moments(r_D: Tensor, J_D: Tensor, cached_r_F: Tensor) -> tuple[Tensor, Tensor]:
    """Return (r_F + r_D, J_D), with explicit per-geometry fixed cached vector."""
    if (r_D.ndim!=2 or r_D.shape[1]!=10 or J_D.shape!=(r_D.shape[0],10,10)
            or cached_r_F.shape!=r_D.shape):
        raise ValueError("require r_D/r_F[B,10] and ambient J_D[B,10,10]")
    if not (r_D.device==J_D.device==cached_r_F.device and
            r_D.dtype==J_D.dtype==cached_r_F.dtype):
        raise ValueError("fixed and variable tensors must have matching dtype and device")
    if not all(bool(torch.isfinite(x).all()) for x in (r_D,J_D,cached_r_F)):
        raise ValueError("nonfinite fixed or variable moments")
    return r_D+cached_r_F, J_D
