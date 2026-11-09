"""P26.2a: sparse canonical geometry contract independent of an FVDB install.

This is a coordinate/value interchange representation, not an fVDB backend.
It stores occupied voxel coordinates and four canonical geometry channels
without allocating a dense [B,4,X,Y,Z] tensor. A future pinned fVDB adapter
must round-trip this contract and preserve coordinates, values and bounds.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import torch
from torch import Tensor


@dataclass(frozen=True)
class SparseGeometryBatch:
    """Batched sparse four-channel geometry.

    coords: int64 [N,4] columns (batch,x,y,z), unique and lexicographically
            sorted by torch.nonzero ordering.
    values: floating [N,4] columns (density, occupancy, normalized SDF,
            internal boundary).
    spatial_shape: (X,Y,Z); batch_size is explicit so empty batch members
                   can be represented even when they have no occupied cells.
    """

    coords: Tensor
    values: Tensor
    batch_size: int
    spatial_shape: tuple[int, int, int]

    def __post_init__(self):
        if self.coords.dtype != torch.int64 or self.coords.ndim != 2 or self.coords.shape[1] != 4:
            raise ValueError("coords must be int64 [N,4] (batch,x,y,z)")
        if self.values.ndim != 2 or self.values.shape != (self.coords.shape[0], 4):
            raise ValueError("values must be floating [N,4]")
        if not self.values.is_floating_point() or not bool(torch.isfinite(self.values).all()):
            raise ValueError("sparse geometry values must be finite floating-point")
        if self.coords.device != self.values.device:
            raise ValueError("coords and values must share device")
        if self.batch_size < 1 or len(self.spatial_shape) != 3 or any(int(x) < 1 for x in self.spatial_shape):
            raise ValueError("invalid batch_size or spatial_shape")
        if self.coords.numel():
            limits = torch.tensor(
                (self.batch_size, *self.spatial_shape),
                device=self.coords.device, dtype=torch.int64,
            )
            if bool((self.coords < 0).any()) or bool((self.coords >= limits).any()):
                raise ValueError("sparse coordinates out of bounds")
            linear = (
                ((self.coords[:, 0]*self.spatial_shape[0]+self.coords[:, 1])
                 *self.spatial_shape[1]+self.coords[:, 2])
                *self.spatial_shape[2]+self.coords[:, 3]
            )
            if torch.unique(linear).numel() != linear.numel():
                raise ValueError("duplicate sparse voxel coordinates")

    @classmethod
    def from_dense(cls, geometry: Tensor, *, occupancy_threshold: float = 0.5):
        if geometry.ndim != 5 or geometry.shape[1] != 4:
            raise ValueError("dense geometry must have shape [B,4,X,Y,Z]")
        if not geometry.is_floating_point() or not bool(torch.isfinite(geometry).all()):
            raise ValueError("dense geometry must be finite floating-point")
        if not 0.0 <= occupancy_threshold <= 1.0:
            raise ValueError("occupancy_threshold must be in [0,1]")
        occupied = geometry[:, 1] > occupancy_threshold
        coords = torch.nonzero(occupied, as_tuple=False).to(torch.int64)
        if coords.numel():
            batch_xyz = coords
            b, x, y, z = batch_xyz.unbind(-1)
            values = geometry[b, :, x, y, z]
        else:
            values = geometry.new_empty((0, 4))
        return cls(
            coords=coords, values=values,
            batch_size=int(geometry.shape[0]),
            spatial_shape=tuple(int(x) for x in geometry.shape[2:]),
        )

    def to_dense(self) -> Tensor:
        """Materialize dense tensor for small tests/debug only; not 512^3 path."""
        dense = self.values.new_zeros(
            (self.batch_size, 4, *self.spatial_shape)
        )
        if self.coords.numel():
            b, x, y, z = self.coords.unbind(-1)
            dense[b, :, x, y, z] = self.values
        return dense

    def occupancy_fraction(self) -> float:
        total = self.batch_size
        for dim in self.spatial_shape:
            total *= dim
        return float(self.coords.shape[0] / total)

    def active_counts(self) -> Tensor:
        counts = torch.bincount(
            self.coords[:, 0], minlength=self.batch_size
        )
        return counts

    def to(self, device=None, dtype=None):
        return SparseGeometryBatch(
            coords=self.coords.to(device=device),
            values=self.values.to(device=device, dtype=dtype or self.values.dtype),
            batch_size=self.batch_size,
            spatial_shape=self.spatial_shape,
        )
