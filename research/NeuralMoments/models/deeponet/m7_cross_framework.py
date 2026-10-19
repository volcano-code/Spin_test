"""M7 read-only cross-window executable model-interface audit.

Loads the *actual* W6 P-CRAFT source by pinned Git blob SHA from a separately
supplied checkout/mirror. Does not vendor, copy, modify, train, or commit W6.
The local microbenchmark measures random-initialized model paths only. No
accuracy, trained-weight, Cherchi or real-CAD performance is implied.

Usage:
  python -m research.NeuralMoments.models.deeponet.m7_cross_framework \
    --w6-root /path/to/W6-checkout --output /tmp/w5_m7_runtime.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys
import time
import types

import numpy as np
import torch

from .model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment

W6_PINNED_COMMIT = "8bc72fe0c2d88bf2cd4de1922242a4745c141891"
W5_PARENT_COMMIT = "3686c921bcda2f3815bceadba04604df0c449ea0"
W6_FILES = {
    "m4_lite_model.py": "853ea92054e5895abe06d33092615a0be4b58772",
    "m5_potential.py": "b5f976af0b2ef0621fd3f557ea93ae08a48ba99a",
}
B = np.array([1.] * 7 + [2.] * 3)


class UntrustedW6Source(ValueError):
    pass


def git_blob_sha(content: bytes) -> str:
    """Git object SHA-1, not a raw file SHA-1; verify pinned read-only bytes."""
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def load_pinned_w6(w6_root: str | Path):
    """Supply a read-only W6 repository root; import two verified files only.

    Uses a private import namespace to prevent namespace-package collision with
    this W5 worktree. No W6 __init__, training or teacher code is executed.
    """
    base = Path(w6_root).resolve() / "research/NeuralMoments/models/pcraft_ufno"
    for filename, expected in W6_FILES.items():
        path = base / filename
        if not path.is_file() or path.is_symlink():
            raise UntrustedW6Source(f"W6_PINNED_FILE_ABSENT_OR_SYMLINK: {filename}")
        if git_blob_sha(path.read_bytes()) != expected:
            raise UntrustedW6Source(f"W6_GIT_BLOB_MISMATCH: {filename}")
    pkg_name = "_w5_readonly_pcraft_ufno"
    module = sys.modules.get(pkg_name)
    if module is not None and list(getattr(module, "__path__", [])) != [str(base)]:
        raise UntrustedW6Source("W6_IMPORT_NAMESPACE_CONFLICT")
    if module is None:
        module = types.ModuleType(pkg_name)
        module.__path__ = [str(base)]
        module.__package__ = pkg_name
        sys.modules[pkg_name] = module
    m4 = importlib.import_module(pkg_name + ".m4_lite_model")
    m5 = importlib.import_module(pkg_name + ".m5_potential")
    return m4, m5


def shared_voxel(seed: int, n: int = 8) -> torch.Tensor:
    """One public deterministic 4-channel input used by all candidates.

    Research-only synthetic tensor; neither real CAD nor accurate density/
    physical SDF. W5 consumes 9D pooled statistics; W6 consumes all channels.
    """
    if n != 8:
        raise ValueError("M7_CPU_GRID_FIXED_AT_8")
    generator = torch.Generator(device="cpu").manual_seed(int(seed))
    xyz = torch.stack(torch.meshgrid(*[torch.linspace(-1, 1, n)] * 3,
                                     indexing="ij"))
    x, y, z = xyz
    center = torch.rand(3, generator=generator) * 0.4 - 0.2
    sdf = torch.sqrt((x-center[0])**2 + (y-center[1])**2 +
                     (z-center[2])**2 + 1e-8) - 0.85
    occupancy = (sdf <= 0).float()
    density = occupancy * (0.6 + 0.2*x + 0.1*y).clamp_min(0.1)
    boundary_proxy = torch.exp(-sdf.abs() * 8)
    return torch.stack((density, occupancy, sdf, boundary_proxy))[None].float()


def median_ms(action, repeats: int) -> float:
    values = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        action()
        values.append((time.perf_counter_ns() - start) * 1e-6)
    return float(statistics.median(values))


def _metrics(model, geom, c, repeats: int) -> dict:
    model.eval()
    # Warm up dispatch/J kernels before measuring; fixed device/threads.
    with torch.no_grad():
        z = model.encode_geometry(geom)
        output = model.moment(z, c)
    with torch.enable_grad():
        jc = model.jacobian(z, c)
    if output.shape != (1, 10) or jc.shape != (1, 10, 10):
        raise ValueError("INVALID_MODEL_CONTRACT")
    if not bool(torch.isfinite(output).all() and torch.isfinite(jc).all()):
        raise ValueError("NONFINITE_OUTPUT")

    def cold():
        with torch.no_grad():
            zz = model.encode_geometry(geom)
            return model.moment(zz, c)

    def encode():
        with torch.no_grad():
            return model.encode_geometry(geom)

    def moment():
        with torch.no_grad():
            return model.moment(z, c)

    def jac():
        with torch.enable_grad():
            return model.jacobian(z, c)

    # Same encoded tensor used across distinct native c requests.
    controls = torch.cat([c, c*1.05, c*0.97], dim=0)
    with torch.no_grad():
        multiple = [model.moment(z, ci.reshape(1, 10)) for ci in controls]
    if not all(t.shape == (1, 10) and torch.isfinite(t).all() for t in multiple):
        raise ValueError("INVALID_REPEATED_QUERY")
    j = jc.detach().cpu().numpy()[0].astype(np.float64)
    native_c = c.detach().cpu().numpy()[0].astype(np.float64)
    jq = j / B[None, :]
    return {
        "real_parameters": int(sum(p.numel()*(2 if p.is_complex() else 1)
                                   for p in model.parameters() if p.requires_grad)),
        "encode_ms": median_ms(encode, repeats),
        "cold_moment_ms": median_ms(cold, repeats),
        "warm_moment_ms": median_ms(moment, repeats),
        "warm_jacobian_ms": median_ms(jac, repeats),
        "r_shape": list(output.shape), "Jc_shape": list(jc.shape),
        "jacobian_q_max_asymmetry": float(np.max(np.abs(jq-jq.T))),
        "jacobian_q_min_symmetric_eigenvalue": float(np.linalg.eigvalsh((jq+jq.T)/2)[0]),
        "radial_null_max_abs": float(np.max(np.abs(j @ native_c))),
        "positive_scale_r_max_abs_difference": float((multiple[0]-multiple[1]).abs().max().item()),
        "weights_trained": False,
    }


def run_comparison(*, w6_root: str | Path, seed: int = 19, repeats: int = 9) -> dict:
    if not 3 <= repeats <= 1000 or type(seed) is not int:
        raise ValueError("INVALID_TIMING_PROTOCOL")
    if torch.cuda.is_available():
        # Force CPU regardless; no GPU resources consumed by this study.
        pass
    torch.set_num_threads(1)
    m4, m5 = load_pinned_w6(w6_root)
    voxels = shared_voxel(seed)
    geom9 = m4.voxel_statistics9(voxels)
    c = torch.zeros((1, 10), dtype=voxels.dtype)
    c[:, 0], c[:, 3] = -0.22, 1.0
    c = c / torch.linalg.vector_norm(c, dim=-1, keepdim=True)
    model_factories = (
        ("w5_deeponet", lambda: DeepONetMoment(geometry_dim=9), geom9),
        ("w5_geometry_mlp", lambda: GeometryMLPMoment(geometry_dim=9), geom9),
        ("w6_lite_bottleneck", lambda: m4.LiteUFNOMoment("bottleneck"), voxels),
        ("w6_lite_local_only", lambda: m4.LiteUFNOMoment("local_only"), voxels),
        # Original W6 M5 CONFIG lite_potential_6 uses hidden=32, NOT default 60.
        ("w6_convex_potential6", lambda: m5.ConvexPotentialMoment(
            points_per_axis=6, hidden=32, smoothing=0.04), voxels),
    )
    rows = {}
    for name, factory, geometry in model_factories:
        torch.manual_seed(seed)
        model = factory()
        rows[name] = _metrics(model, geometry, c, repeats)
    npar = [r["real_parameters"] for r in rows.values()]
    if max(npar) / min(npar) > 1.05:
        raise ValueError("CANDIDATE_CAPACITY_EXCEEDS_FIVE_PERCENT")
    return {
        "schema": "W5_M7_EXTERNAL_FRAMEWORK_RUNTIME_V1", "seed": seed,
        "repeats": repeats, "device": "cpu", "torch_threads": torch.get_num_threads(),
        "python": platform.python_version(), "torch": torch.__version__,
        "source": {"w5_parent_commit": W5_PARENT_COMMIT,
                   "w6_readonly_commit": W6_PINNED_COMMIT,
                   "w6_external_source_git_blobs": W6_FILES},
        "source_4channel_grid_sha256": hashlib.sha256(voxels.numpy().tobytes()).hexdigest(),
        "source_9d_lossy_summary_sha256": hashlib.sha256(geom9.numpy().tobytes()).hexdigest(),
        "capacity_max_over_min": max(npar)/min(npar),
        "same_geometry_input_information": False,
        "shared_underlying_voxels": True,
        "training_applied": False, "cherchi_native_evaluations": 0,
        "accuracy_comparison_allowed": False,
        "results": rows,
        "caveat": "Untrained exact-source W6 and W5 API/caching/CPU timing smoke only; "
                  "W5 uses nine density statistics, W6 full four-channel voxels. "
                  "Cannot infer trained error, Cherchi throughput or solver acceleration."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--w6-root", required=True)
    parser.add_argument("--seed", type=int, default=19)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = run_comparison(w6_root=args.w6_root, seed=args.seed, repeats=args.repeats)
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output is not None:
        args.output.write_text(rendered+"\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
