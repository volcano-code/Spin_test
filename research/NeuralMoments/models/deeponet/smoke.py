"""W5 analytic-only experiment CLI: family holdout, optional tiny CPU training.

Usage (from repo root):
  python -m research.NeuralMoments.models.deeponet.smoke --steps 12

All labels are independent closed-form volume integrals on synthetic solids.
They MUST NOT be interpreted as Spin Boolean/Cherchi teacher measurements.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from typing import Any

import torch

from .adapt import SUPPORTED_QUERY_COUNTS, fit_residual_adapter
from .analytic import analytic_labels, make_geometry, sample_families
from .model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment


def _time_ms(fn: Any, repeats: int = 15, warmup: int = 3) -> float:
    for _ in range(warmup):
        fn()
    t0 = time.perf_counter()
    for _ in range(repeats):
        fn()
    return (time.perf_counter() - t0) * 1000.0 / repeats


def benchmark(model: torch.nn.Module, d: torch.Tensor, c: torch.Tensor,
              *, repeats: int = 15) -> dict[str, Any]:
    """Uncompiled single-thread CPU timings; head-only jacrev excludes encoding."""
    model.eval()
    with torch.no_grad():
        cached = model.encode_geometry(d).detach()
        cold_ms = _time_ms(lambda: model(d, c), repeats)
        warm_ms = _time_ms(lambda: model.moment(cached, c), repeats)
    jac_ms = _time_ms(lambda: model.jacobian(cached, c), max(3, repeats // 3), 1)
    result: dict[str, Any] = model.complexity()
    result.update({"cold_encode_plus_query_ms": cold_ms,
                   "warm_cached_query_ms": warm_ms,
                   "cached_jacrev_10x10_ms": jac_ms,
                   "estimated_flops_cold_linear_only": 2 * result["cold_query_macs"],
                   "estimated_flops_warm_linear_only": 2 * result["warm_query_macs"]})
    return result


def _to_f32(data: tuple[torch.Tensor, ...]) -> tuple[torch.Tensor, ...]:
    return tuple(x.float().contiguous() for x in data)


def _decision_metrics(model: torch.nn.Module, d: torch.Tensor, c: torch.Tensor,
                      r: torch.Tensor, j: torch.Tensor, step_radius: float = 0.05) -> dict[str, float]:
    """Synthetic regularized GN decision diagnostic (NOT a real optimizer)."""
    z = model.encode_geometry(d)
    pr = model.moment(z, c)
    pj = model.jacobian(z, c)

    def propose(rr: torch.Tensor, jj: torch.Tensor) -> torch.Tensor:
        # Tikhonov stabilization plus strict norm cap avoids extrapolation.
        a = jj.T @ jj + 1e-2 * torch.eye(10, dtype=jj.dtype, device=jj.device)
        step = torch.linalg.solve(a, -(jj.T @ rr))
        return step * min(1.0, step_radius / max(step.norm().item(), 1e-12))

    s_pred = propose(pr, pj)
    s_true = propose(r, j)
    oracle_next_pred = r + j @ s_pred
    oracle_next_true = r + j @ s_true
    true_obj_pred = 0.5 * oracle_next_pred.square().sum().item()
    true_obj_ref = 0.5 * oracle_next_true.square().sum().item()
    return {"step_l2_error": (s_pred - s_true).norm().item(),
            "post_step_true_objective_gap": true_obj_pred - true_obj_ref}


def evaluate(model: torch.nn.Module, test: tuple[torch.Tensor, ...]) -> dict[str, float]:
    """Held-out ellipsoid family: r, J and a synthetic decision error."""
    d, c, r, j = test
    model.eval()
    with torch.no_grad():
        z = model.encode_geometry(d)
        pred = model.moment(z, c)
    # jacrev is not wrapped in no_grad (forward AD must remain available).
    jac = model.jacobian(z.detach(), c)
    direction = torch.arange(1, 11, device=c.device, dtype=c.dtype)
    direction = direction / direction.norm()
    dr_true = torch.einsum("bij,j->bi", j, direction)
    dr_pred = torch.einsum("bij,j->bi", jac, direction)
    idx = 0
    with torch.enable_grad():
        diagnostic = _decision_metrics(model, d[idx], c[idx], r[idx], j[idx])
    return {"r_mae": (pred - r).abs().mean().item(),
            "r_relative_l2": ((pred - r).norm() / r.norm().clamp_min(1e-9)).item(),
            "J_mae": (jac - j).abs().mean().item(),
            "J_relative_l2": ((jac - j).norm() / j.norm().clamp_min(1e-9)).item(),
            "directional_derivative_mae": (dr_pred - dr_true).abs().mean().item(),
            **diagnostic}


def train_tiny(model: torch.nn.Module, train: tuple[torch.Tensor, ...],
               *, steps: int, derivative_enhanced: bool, seed: int, batch_size: int = 8) -> dict[str, float]:
    if steps < 0:
        raise ValueError("steps must be nonnegative")
    d, c, r, j = train
    rng = torch.Generator().manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=0.003)
    started = time.perf_counter()
    last_r = float("nan")
    last_j = float("nan")
    model.train()
    for _ in range(steps):
        idx = torch.randint(len(d), (batch_size,), generator=rng)
        zd = model.encode_geometry(d[idx])
        pred = model.moment(zd, c[idx])
        loss_r = (pred - r[idx]).square().mean()
        loss = loss_r
        if derivative_enhanced:
            j_pred = model.jacobian(zd, c[idx])
            loss_j = (j_pred - j[idx]).square().mean()
            loss = loss + 0.5 * loss_j
            last_j = loss_j.item()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        last_r = loss_r.item()
    return {"steps": steps, "batch_size": batch_size,
            "derivative_enhanced": derivative_enhanced,
            "last_train_r_mse": last_r if steps else None,
            "last_train_J_mse": last_j if steps and derivative_enhanced else None,
            "cpu_train_seconds": time.perf_counter() - started,
            "gpu_seconds": 0.0}


def adaptation_metrics(model: torch.nn.Module, *, seed: int) -> dict[str, dict[str, float]]:
    """One fixed ellipsoid with 8 independent support queries and 16 holdout queries."""
    d = make_geometry("ellipsoid", (0.11, -0.07, 0.04), (0.58, 0.43, 0.67)).float()
    g = torch.Generator().manual_seed(seed)
    support = (torch.rand((8, 10), generator=g) - 0.5) * 0.06
    target = (torch.rand((16, 10), generator=g) - 0.5) * 0.06
    support_r = torch.stack([analytic_labels(d.double(), x.double())[0].float() for x in support])
    test_r = torch.stack([analytic_labels(d.double(), x.double())[0].float() for x in target])
    z = model.encode_geometry(d).detach()
    results: dict[str, dict[str, float]] = {}
    for k in SUPPORTED_QUERY_COUNTS:
        fit = fit_residual_adapter(model, z, support[:k], support_r[:k])
        with torch.no_grad():
            prediction = fit.predict(target)
        results[str(k)] = {"r_mae": (prediction - test_r).abs().mean().item(),
                           "oracle_query_count": float(k)}
    return results


def run(*, seed: int = 19, steps: int = 12, repeats: int = 9,
        per_family: int = 20) -> dict[str, Any]:
    torch.set_num_threads(1)  # avoid contending with other research windows
    train = _to_f32(sample_families(("box", "sphere"), per_family, seed=seed,
                                    queries_per_geometry=2))
    test = _to_f32(sample_families(("ellipsoid",), per_family, seed=seed + 1,
                                   queries_per_geometry=2))
    report: dict[str, Any] = {
        "status": "synthetic_architecture_smoke_only",
        "teacher": "closed_form_axis_aligned_polynomial_density_moments_not_W0_not_W2",
        "source_branch_freeze_sha": "0bcc187b3005478baa586a6d6f450e73811ca342",
        "seed": seed,
        "train_geometry_families": ["box", "sphere"],
        "test_geometry_families": ["ellipsoid"],
        "train_examples": len(train[0]), "test_examples": len(test[0]),
        "torch_version": torch.__version__, "python_version": platform.python_version(),
        "device": "cpu", "cpu_threads": torch.get_num_threads(),
        "no_real_spin_label_or_W0_contract": True,
        "model_results": {},
    }
    for architecture, cls in (("deeponet", DeepONetMoment), ("geometry_mlp", GeometryMLPMoment)):
        report["model_results"][architecture] = {}
        for derivative_enhanced in (False, True):
            torch.manual_seed(seed)
            model = cls().float()
            train_record = train_tiny(model, train, steps=steps, seed=seed,
                                      derivative_enhanced=derivative_enhanced)
            metrics = evaluate(model, test)
            timings = benchmark(model, test[0][0], test[1][0], repeats=repeats)
            adaptation = adaptation_metrics(model, seed=seed + 100)
            report["model_results"][architecture]["derivative_enhanced" if derivative_enhanced else "residual_only"] = {
                "training": train_record, "heldout_metrics": metrics,
                "performance": timings, "adaptation": adaptation,
            }
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=19)
    p.add_argument("--steps", type=int, default=12)
    p.add_argument("--repeats", type=int, default=9)
    p.add_argument("--per-family", type=int, default=20)
    args = p.parse_args()
    print(json.dumps(run(seed=args.seed, steps=args.steps, repeats=args.repeats,
                         per_family=args.per_family), indent=2, sort_keys=True,
                     allow_nan=False))


if __name__ == "__main__":
    main()
