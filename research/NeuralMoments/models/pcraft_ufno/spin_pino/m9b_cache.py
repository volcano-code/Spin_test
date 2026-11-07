"""M9b opt-in, source-bound LRU caches for fixed-geometry Spin-PINO queries.

All cache keys include exact tensor bytes. No train-mode/gradient reuse is
allowed. Float32/complex buffers are hashed as raw bytes, preventing stale
entries when geometry, rotation, or model state changes. These caches do not
certify physical correctness or derivative neighborhoods.
"""
from __future__ import annotations

from collections import OrderedDict
from hashlib import sha256

import torch
from torch import Tensor

from .mass_transport import conservative_rotate_geometry


def _raw_tensor_digest(x: Tensor) -> str:
    if not isinstance(x, Tensor):
        raise TypeError("tensor required for source-bound cache")
    y = x.detach().contiguous()
    h = sha256()
    h.update(str((tuple(y.shape), str(y.dtype), str(y.device))).encode())
    h.update(y.view(torch.uint8).cpu().numpy().tobytes())
    return h.hexdigest()


def _model_digest(model) -> str:
    h = sha256()
    for name, param in sorted(model.state_dict().items()):
        h.update(name.encode("utf-8"))
        h.update(_raw_tensor_digest(param).encode("ascii"))
    return h.hexdigest()


class SourceBoundRotationCache:
    """Cache M9 bounded transport for a fixed source and exact rotation.

    Cached output is cloned on retrieval so the caller cannot alter entries.
    Cache memory is capped; large tensors must use an external sparse path.
    """

    def __init__(self, max_entries: int = 8, max_input_bytes: int = 8 << 20):
        if not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be positive")
        if not isinstance(max_input_bytes, int) or max_input_bytes < 1:
            raise ValueError("max_input_bytes must be positive")
        self.max_entries = max_entries
        self.max_input_bytes = max_input_bytes
        self._entries = OrderedDict()
        self.hits = 0
        self.misses = 0

    def rotate(self, geometry: Tensor, rotation: Tensor):
        if geometry.requires_grad or rotation.requires_grad or torch.is_grad_enabled():
            raise RuntimeError("rotation cache is inference-only: use torch.no_grad()")
        if geometry.numel() * geometry.element_size() > self.max_input_bytes:
            raise ValueError("dense input exceeds cache limit; use sparse bridge")
        key = (_raw_tensor_digest(geometry), _raw_tensor_digest(rotation))
        if key in self._entries:
            self.hits += 1
            self._entries.move_to_end(key)
            out, stats = self._entries[key]
            return out.clone(), dict(stats), True
        out, stats = conservative_rotate_geometry(geometry, rotation)
        self._entries[key] = (out.detach().clone(), dict(stats))
        self._entries.move_to_end(key)
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)
        self.misses += 1
        return out.clone(), dict(stats), False

    def clear(self):
        self._entries.clear()

    @property
    def entries(self):
        return len(self._entries)


class PinnedPINOQueryCache:
    """Reuse PINO material quadrature weights across different coefficients c.

    Freeze an eval() model for the lifetime of the cache; changing even one
    weight/buffer causes a fail-closed error, never stale predictions.
    The 10x10 Jacobian is always computed using the model's own head.
    """

    def __init__(self, model, max_entries: int = 8, max_input_bytes: int = 8 << 20):
        if model.training:
            raise ValueError("cache requires model.eval()")
        if not isinstance(max_entries, int) or max_entries < 1:
            raise ValueError("max_entries must be positive")
        if not isinstance(max_input_bytes, int) or max_input_bytes < 1:
            raise ValueError("max_input_bytes must be positive")
        self.model = model
        self.frozen_model_digest = _model_digest(model)
        self.max_entries = max_entries
        self.max_input_bytes = max_input_bytes
        self._entries = OrderedDict()
        self.hits = 0
        self.misses = 0

    def evaluate(self, geometry: Tensor, coefficients: Tensor, *, with_jacobian=True):
        if torch.is_grad_enabled() or geometry.requires_grad or coefficients.requires_grad:
            raise RuntimeError("query cache is inference-only: use torch.no_grad()")
        if self.model.training or _model_digest(self.model) != self.frozen_model_digest:
            raise RuntimeError("model mutated or resumed training; rebuild PINO cache")
        if geometry.ndim != 5 or geometry.shape[1] != 4:
            raise ValueError("geometry must be [B,4,X,Y,Z]")
        if coefficients.shape != (geometry.shape[0], 10):
            raise ValueError("coefficients must be [B,10]")
        if geometry.numel() * geometry.element_size() > self.max_input_bytes:
            raise ValueError("dense input exceeds cache limit; use sparse bridge")
        key = _raw_tensor_digest(geometry)
        if key in self._entries:
            z = self._entries[key]
            self._entries.move_to_end(key)
            self.hits += 1
            hit = True
        else:
            z = self.model.encode_geometry(geometry).detach().clone()
            self._entries[key] = z
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
            self.misses += 1
            hit = False
        r = self.model.moment_from_weights(z, coefficients)
        J = self.model.jacobian_from_weights(z, coefficients) if with_jacobian else None
        return r, J, {"geometry_hit": hit, "cached_geometries": len(self._entries)}

    def clear(self):
        self._entries.clear()
