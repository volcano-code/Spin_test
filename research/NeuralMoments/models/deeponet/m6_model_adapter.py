"""One-encode cached DE-DeepONet/Geometry-MLP inference for M6 P0 gates.

This is an inference adapter, NOT a teacher certificate or an assertion that
weights were trained on real Cherchi labels. Tensor inputs are single-geometry,
CPU-only to avoid competing with other windows' native/GPU workloads.
"""
from __future__ import annotations

import math
import time

import numpy as np
import torch


def cached_prediction(model: torch.nn.Module, geometry_features, native_c) -> dict:
    """Encode exactly once and return network r[10], dr/dc[10,10], timing.

    The caller must separately validate W0 geometry/frame/teacher provenance and
    then independently evaluate an oracle before any proposed optimizer step.
    """
    if model.training:
        raise ValueError("MODEL_MUST_BE_IN_EVAL_MODE")
    try:
        parameter = next(model.parameters())
    except StopIteration as exc:
        raise ValueError("MISSING_MODEL_PARAMETERS") from exc
    if parameter.device.type != "cpu":
        raise ValueError("M6_CPU_ONLY_RESOURCE_POLICY")
    dim = getattr(model, "geometry_dim", None)
    if type(dim) is not int or dim <= 0:
        raise ValueError("UNSUPPORTED_MODEL_GEOMETRY_DIMENSION")
    try:
        g = np.asarray(geometry_features, dtype=np.float64)
        c = np.asarray(native_c, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError("INVALID_FEATURES_OR_CONTROL") from exc
    if (g.shape != (dim,) or c.shape != (10,) or
            not np.isfinite(g).all() or not np.isfinite(c).all()):
        raise ValueError("INVALID_FEATURES_OR_CONTROL")
    if abs(np.linalg.norm(c)-1) > 1e-9:
        raise ValueError("NATIVE_C_NOT_NORMALIZED")
    x = torch.as_tensor(g, dtype=parameter.dtype, device=parameter.device)
    control = torch.as_tensor(c, dtype=parameter.dtype, device=parameter.device)
    start=time.perf_counter()
    with torch.no_grad():
        z=model.encode_geometry(x)
    encoded=time.perf_counter()
    with torch.no_grad():
        prediction=model.moment(z,control)
    moment_done=time.perf_counter()
    with torch.enable_grad():
        J=model.jacobian(z,control)
    jacobian_done=time.perf_counter()
    if prediction.shape != (10,) or J.shape != (10,10):
        raise ValueError("INVALID_MODEL_OUTPUT_SHAPE")
    p=prediction.detach().cpu().numpy().astype(np.float64)
    j=J.detach().cpu().numpy().astype(np.float64)
    if not np.isfinite(p).all() or not np.isfinite(j).all():
        raise ValueError("NONFINITE_MODEL_OUTPUT")
    return {"predicted_r":p, "predicted_Jc":j,
            "encoder_invocations":1,
            "parameter_count":sum(t.numel() for t in model.parameters()),
            "weights_verified_for_native_cherchi":False,
            "encode_seconds":encoded-start,
            "warm_moment_seconds":moment_done-encoded,
            "warm_jacobian_seconds":jacobian_done-moment_done}
