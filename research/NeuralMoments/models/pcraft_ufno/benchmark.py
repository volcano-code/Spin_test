"""Reproducible untrained CPU/GPU smoke timings; JSON, no fabricated W5 speedups.

Run: python -m research.NeuralMoments.models.pcraft_ufno.benchmark --output PATH
The output must stay in W6's exclusive subtree when committed.
"""
import argparse
import json
import platform
import resource
import statistics
import time

import torch

from .model import UFNOMoment, count_real_parameters
from .synthetic import slab_coefficients, solid_box_geometry


def benchmark(*, device="cpu", grid_size=8, repetitions=5) -> dict:
    torch.manual_seed(20261019)
    if device == "cpu":
        torch.set_num_threads(1)
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    model = UFNOMoment(width=2, modes=3, latent_dim=12, head_width=24,
                       grid_size=grid_size).eval().to(device)
    d = solid_box_geometry(grid_size=grid_size, device=device)
    c = slab_coefficients(torch.tensor([.5], device=device))

    def synchronize():
        if device == "cuda":
            torch.cuda.synchronize()

    def measure(fn):
        values = []
        for _ in range(repetitions):
            synchronize()
            start = time.perf_counter()
            with torch.no_grad():
                fn()
            synchronize()
            values.append((time.perf_counter()-start)*1000)
        return {"median_ms":statistics.median(values), "min_ms":min(values),
                "max_ms":max(values), "repetitions": repetitions}

    with torch.no_grad():
        model.encode_geometry(d)
        z = model.cache_geometry(d)
        model.moment(z,c)
        model.jacobian(z,c)
    synchronize()
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    encode = measure(lambda: model.encode_geometry(d))
    cached_head = measure(lambda: model.moment(z,c))
    jacobian = measure(lambda: model.jacobian(z,c))
    mem = (torch.cuda.max_memory_allocated()/1024**2 if device == "cuda" else None)
    return {
        "schema": "w6_smoke_perf_v1", "trained": False, "seed": 20261019,
        "source_pin": "volcano-code/test@24eda3e9b3f87ba16251a9025761986d6cfe3079",
        "target_contract": "W0 MomentContractV1 pending",
        "teacher": "none; analytic reference only", "data": "unit_cube_[0,1]^3",
        "geometry_split": "not_applicable_untrained_smoke", "parameter_counts_real": count_real_parameters(model),
        "inference_device": device, "cpu": platform.processor() or platform.machine(),
        "torch": torch.__version__, "batch": 1, "voxel_resolution": grid_size,
        "coefficient_dim": 10, "moment_dim": 10, "frozen_geometry_reused": True,
        "encoding": encode, "cached_head_forward": cached_head, "cached_head_jacrev_10x10": jacobian,
        "cuda_peak_allocated_mb": mem,
        "cpu_peak_process_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "comparison_W5": {"state": "PENDING_W5_BASELINE", "speedup_claim": None,
                          "protocol": "same hardware, seed, teacher budget, geometry-family split, params, cold/warm/J timings"},
        "limitations": ["No W2 teacher labels", "No trained weights", "CPU RSS is process-wide peak, not phase VRAM",
                        "Performance is untrained smoke, not accuracy or optimization speedup"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--grid-size", type=int, default=8)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    result = benchmark(device=args.device, grid_size=args.grid_size,
                       repetitions=args.repetitions)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(text+"\n")
    print(text)


if __name__ == "__main__":
    main()
