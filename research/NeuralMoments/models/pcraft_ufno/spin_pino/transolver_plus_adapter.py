# SPDX-FileCopyrightText: Copyright (c) 2025 THUML @ Tsinghua University
# SPDX-License-Identifier: MIT
#
# Adapted from thuml/Transolver_plus@d5a23bc734a0ebac56384cf72049a26af9673452
# models/Transolver_plus.py (Physics_Attention_1D_Eidetic and Transolver_plus_block).
# The adapter below preserves the eidetic physical-state slicing mechanism but
# exposes a residual geometry-feature port to the P-CRAFT PINO trunk. It does
# not replace the PINO backbone or its ten-moment physics head.

from __future__ import annotations

import math

import torch
from torch import Tensor, nn
import torch.distributed as dist
import torch.distributed.nn as dist_nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint


def gumbel_softmax(logits: Tensor, temperature: Tensor, *, stochastic: bool) -> Tensor:
    if stochastic:
        u = torch.rand_like(logits).clamp_(1e-8, 1.0 - 1e-8)
        noise = -torch.log(-torch.log(u))
        logits = logits + noise
    return F.softmax(logits / temperature, dim=-1)


def _distributed_sum(x: Tensor) -> Tensor:
    if dist.is_available() and dist.is_initialized() and dist.get_world_size() > 1:
        return dist_nn.all_reduce(x, op=dist.ReduceOp.SUM)
    return x


class PhysicsAttention1DEidetic(nn.Module):
    """Faithful single-process-capable port of Transolver++ eidetic slicing."""

    def __init__(self, dim: int, *, heads: int = 4, dim_head: int = 8,
                 dropout: float = 0.0, slice_num: int = 16):
        super().__init__()
        if dim != heads * dim_head:
            raise ValueError("dim must equal heads * dim_head")
        if min(dim, heads, dim_head, slice_num) < 1:
            raise ValueError("attention dimensions must be positive")
        inner_dim = dim_head * heads
        self.dim_head = dim_head
        self.heads = heads
        self.dropout = nn.Dropout(dropout)
        self.bias = nn.Parameter(torch.ones(1, heads, 1, 1) * 0.5)
        self.proj_temperature = nn.Sequential(
            nn.Linear(dim_head, slice_num),
            nn.GELU(),
            nn.Linear(slice_num, 1),
            nn.GELU(),
        )
        self.in_project_x = nn.Linear(dim, inner_dim)
        self.in_project_slice = nn.Linear(dim_head, slice_num)
        nn.init.orthogonal_(self.in_project_slice.weight)
        self.to_q = nn.Linear(dim_head, dim_head, bias=False)
        self.to_k = nn.Linear(dim_head, dim_head, bias=False)
        self.to_v = nn.Linear(dim_head, dim_head, bias=False)
        self.to_out = nn.Sequential(nn.Linear(inner_dim, dim), nn.Dropout(dropout))

    def forward(self, x: Tensor) -> Tensor:
        if x.ndim != 3:
            raise ValueError("Transolver++ tokens must have shape [B,N,C]")
        batch, tokens, _ = x.shape
        x_mid = self.in_project_x(x).reshape(
            batch, tokens, self.heads, self.dim_head
        ).permute(0, 2, 1, 3).contiguous()
        temperature = (self.proj_temperature(x_mid) + self.bias).clamp_min(0.01)
        slice_weights = gumbel_softmax(
            self.in_project_slice(x_mid), temperature, stochastic=self.training
        )
        slice_norm = _distributed_sum(slice_weights.sum(2))
        slice_token = torch.einsum("bhnc,bhng->bhgc", x_mid, slice_weights).contiguous()
        slice_token = _distributed_sum(slice_token)
        slice_token = slice_token / (
            (slice_norm + 1e-5).unsqueeze(-1).expand(-1, -1, -1, self.dim_head)
        )
        q, k, v = self.to_q(slice_token), self.to_k(slice_token), self.to_v(slice_token)
        out_slice = F.scaled_dot_product_attention(q, k, v, dropout_p=0.0)
        out_tokens = torch.einsum("bhgc,bhng->bhnc", out_slice, slice_weights)
        out_tokens = out_tokens.permute(0, 2, 1, 3).reshape(batch, tokens, -1)
        return self.to_out(out_tokens)


class TransolverPlusBlock(nn.Module):
    """Transolver++ pre-norm eidetic attention + residual MLP block."""

    def __init__(self, dim: int, *, heads: int, dim_head: int,
                 slice_num: int, mlp_ratio: int = 2, dropout: float = 0.0):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attention = PhysicsAttention1DEidetic(
            dim, heads=heads, dim_head=dim_head,
            dropout=dropout, slice_num=slice_num
        )
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(
            nn.Linear(dim, dim * mlp_ratio),
            nn.GELU(),
            nn.Linear(dim * mlp_ratio, dim),
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: Tensor) -> Tensor:
        if self.training and x.requires_grad:
            attn = checkpoint(self.attention, self.norm1(x), use_reentrant=True)
            x = x + attn
            mlp = checkpoint(self.mlp, self.norm2(x), use_reentrant=True)
            return x + mlp
        x = x + self.attention(self.norm1(x))
        return x + self.mlp(self.norm2(x))


class TransolverPlusGeometryAdapter(nn.Module):
    """Auxiliary geometry token branch fused residually into the PINO latent.

    Input: canonical [B,4,X,Y,Z] density/occupancy/SDF/boundary channels.
    Output: [B,pino_feature_dim], same feature dimension as the P-CRAFT PINO
    pooled latent. This branch is optional and never replaces the PINO trunk.
    """

    def __init__(self, *, pino_feature_dim: int, hidden_dim: int = 32,
                 heads: int = 4, slice_num: int = 16, n_layers: int = 2,
                 mlp_ratio: int = 2, dropout: float = 0.0):
        super().__init__()
        if hidden_dim % heads:
            raise ValueError("hidden_dim must be divisible by heads")
        self.input_projection = nn.Sequential(
            nn.Linear(7, hidden_dim * 2),
            nn.GELU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
        )
        self.position_projection = nn.Linear(3, hidden_dim)
        self.placeholder = nn.Parameter(torch.zeros(1, 1, hidden_dim))
        self.blocks = nn.ModuleList([
            TransolverPlusBlock(
                hidden_dim, heads=heads, dim_head=hidden_dim // heads,
                slice_num=slice_num, mlp_ratio=mlp_ratio, dropout=dropout
            ) for _ in range(n_layers)
        ])
        self.norm = nn.LayerNorm(hidden_dim)
        self.readout = nn.Sequential(
            nn.Linear(hidden_dim * 2, pino_feature_dim),
            nn.GELU(),
            nn.Linear(pino_feature_dim, pino_feature_dim),
        )

    def forward(self, geometry: Tensor) -> Tensor:
        if geometry.ndim != 5 or geometry.shape[1] != 4:
            raise ValueError("geometry must be canonical [B,4,X,Y,Z]")
        batch, _, nx, ny, nz = geometry.shape
        axes = [
            torch.linspace(-1.0, 1.0, n, dtype=geometry.dtype, device=geometry.device)
            for n in (nx, ny, nz)
        ]
        xyz = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=-1)
        xyz = xyz.reshape(1, nx * ny * nz, 3).expand(batch, -1, -1)
        values = geometry.permute(0, 2, 3, 4, 1).reshape(batch, nx * ny * nz, 4)
        tokens = torch.cat((values, xyz), dim=-1)
        x = self.input_projection(tokens) + self.position_projection(xyz) + self.placeholder
        for block in self.blocks:
            x = block(x)
        x = self.norm(x)
        pooled = torch.cat((x.mean(dim=1), x.amax(dim=1)), dim=-1)
        return self.readout(pooled)
