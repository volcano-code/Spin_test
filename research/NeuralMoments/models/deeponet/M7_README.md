# W5 M7 — source-pinned P-CRAFT / DeepONet / MLP cross-framework audit

**Only writable branch:** `research/neuralmoments-w5-deeponet-20261019` of `volcano-code/Spin_test`. Parent `3686c921bcda2f3815bceadba04604df0c449ea0`; frozen common baseline `0bcc187b3005478baa586a6d6f450e73811ca342`. Changes are confined to the W5 `deeponet` subdirectory and `tests/python/test_w5_m7_cross_framework.py`. No edits, merges, or uploads to W6, W2, W0, `main`, or `volcano-code/test`.

## Why W6 P-CRAFT is included now

W5 M6 audited bounded native-query fallback and only the two W5 models. **W6 has already run its own P-CRAFT U-FNO candidate experiments in parallel** and reported matched synthetic P0 comparisons (W6 M4/M5). Ignoring W6 would not answer the cross-framework research question. M7 brings its published W6 results and its actual source-pinned architectures into W5's decision ledger, **without turning this window into a second W6 writer**.

### This turn's independent executable source audit (not model training)

`m7_cross_framework.py` refuses to load a W6 mirror/checkout unless these *Git blob hashes* match the W6 commit `8bc72fe0c2d88bf2cd4de1922242a4745c141891`:

- `pcraft_ufno/m4_lite_model.py`: `853ea92054e5895abe06d33092615a0be4b58772`
- `pcraft_ufno/m5_potential.py`: `b5f976af0b2ef0621fd3f557ea93ae08a48ba99a`

These two files were read via the GitHub connector and locally mirrored byte-for-byte; `git hash-object` matched both original Git blob SHA values. **The external W6 source is not committed into W5**. A custom private import namespace prevents module-path collision with W5's `research` modules. Symlinks, missing files and byte differences are rejected.

All five models use the same deterministic synthetic four-channel 8³ tensor and the same native 10D coefficient vector. **W5 sees only W6's label-free nine-dimensional voxel statistics**, whereas the three W6 models see the four raw voxel channels. Thus this is an **API/compute-path comparison, NOT information-parity model accuracy**. The models are random initialized and `training_applied=false`. W6 convex potential uses `points_per_axis=6, hidden=32`, exactly the matched W6 M5 configuration, not its 22,800-parameter default `hidden=60`. Parameter counts are DeepONet 13,674; Geometry-MLP 13,482; W6 bottleneck U-FNO 13,746; W6 local-only 14,098; W6 convex potential 13,448: maximum/minimum ratio 1.0483.

Fresh local single-thread CPU, seed 19, nine repetitions, median elapsed milliseconds:

| Untrained model | Params | Cold moment ms | Cached Jc ms | Jq max asymmetry |
|---|---:|---:|---:|---:|
| W5 DeepONet | 13,674 | 0.079 | 0.781 | 0.0211 |
| W5 Geometry-MLP | 13,482 | 0.050 | 0.641 | 0.1048 |
| W6 bottleneck U-FNO | 13,746 | 0.786 | 1.223 | 0.0208 |
| W6 local-only (no FFT) | 14,098 | 0.504 | 1.056 | 0.0434 |
| W6 convex potential 6³ | 13,448 | 0.900 | 0.224 | <1e-6 |

The exact full-precision data, source-shas, and input tensor identities are in `m7_cross_framework_cpu.json`. Timings are CPU-only, microsecond-scale and sensitive to host configuration; no GPU timings/VRAM recorded. `Jq=Jc B^-1` structure is applicable only to mathematically smooth ambient continuum maps, not arbitrary native topology changes. The convex model guarantees this derivative identity as **a model structural property**, not a Cherchi material certificate.

### Previously executed W6 M5 400-step *trained analytic P0* crosswalk

`m7_w6_published_400step_snapshot.json` contains a selected subset of numbers **extracted from W6's already-published** `m5_summary.json` (Git blob `2e0d186933cf4f8579b1e012e74df714f5ae2bbc`). The parent W6 report used train box/sphere, heldout ellipsoid, seeds `[19,23,29]`, up to 400 Adam steps, validation-only early stopping, same labeled geometry/c budget, six capacities within 3%. W6 compared the W5 model source snapshots and its own U-FNO / convex potential variants. This W5 turn did **not** rerun 400-step W6 training. The extracted subset is **not byte-for-byte the upstream full JSON**; its origin is identified, but the subset cannot be cryptographically authenticated merely by storing the source SHA string.

| Upstream trained model (W6 prior report) | Heldout r MAE | Jc MAE | Warm cached Jc ms | Jq max asym. |
|---|---:|---:|---:|---:|
| W5 DeepONet | **0.01562** | **0.01530** | 1.111 | 0.09787 |
| W5 Geometry-MLP | 0.02463 | 0.02087 | 0.787 | 0.07266 |
| W6 free bottleneck U-FNO | 0.01989 | 0.01680 | 1.288 | 0.34842 |
| W6 convex potential 4³ | 0.03337 | 0.02779 | **0.149** | ~2.4e-9 |
| W6 convex potential 6³ | 0.02267 | 0.01810 | 0.226 | ~1.6e-9 |
| W6 convex potential 8³ | 0.02064 | 0.02461 | 0.366 | ~1.0e-8 |

**No model dominates every axis**. W5 DeepONet wins these sampled `r` and `J` metrics; W6 convex potential has more consistent integrable `Jq` and shorter cached Jacobian, at substantial cold-encoder overhead. W6 M4 also explored dual FFT and no-FFT local baselines under 100-step analytic P0 (see W6 `README_M4.md`). No other external candidates are silently claimed to have been trained or benchmarked. Other possible GNO/Transformer/PINO frameworks remain proposals without verified matched-task code/weights; never report their fictitious scores.

The W5 nine-summary/W6 voxel input mismatch **limits causal architectural conclusions**. A genuinely fair representation-parity comparison must provide every architecture the same 4-channel geometry information, with geometry IDs, sample count, teacher calls, optimizer settings, seeds, train/val/test splits and cold/steady-state amortization held constant. A same-task 3D field PINO cannot be treated as a mass-moment predictor without retraining and changing its output objective.

## Tests executed

```bash
export W5_M7_READONLY_W6_ROOT=/path/to/read-only-W6-checkout
PYTHONPATH=. python -m pytest -q \
  tests/python/test_w5_deeponet_smoke.py \
  tests/python/test_w5_m2_contract_and_gate.py \
  tests/python/test_w5_m3_mesh_and_p0.py \
  tests/python/test_w5_m5_decision_gate.py \
  tests/python/test_w5_m6_analytic_rollout.py \
  tests/python/test_w5_m6_model_adapter.py \
  tests/python/test_w5_m6_budget_audit.py \
  tests/python/test_w5_m7_cross_framework.py
# 86 passed, 38 subtests passed (isolated local mirror)

PYTHONPATH=. python -m research.NeuralMoments.models.deeponet.m7_cross_framework \
  --w6-root "$W5_M7_READONLY_W6_ROOT" --seed 19 --repeats 9 \
  --output /tmp/w5_m7_cross_framework_cpu.json

PYTHONPATH=. python -m research.NeuralMoments.models.deeponet.m7_evidence_audit \
  research/NeuralMoments/models/deeponet/m7_w6_published_400step_snapshot.json
```

This test scope covers M1–M3, M5–M7; W5 M4's 500-step trainer was not reconstructed or rerun here. Do not claim remote GitHub CI, production Cherchi, exact CAD, native solver integration, material valid-at-boundary, GPU speedup or manufacturing results from this run. The W2 manifest currently reports `native_teacher_runs=0`, `training_samples=0`. Native labels are still **blocked**; W0 geometry/moment/source seals alone do not authorize them. Source-pinned P-CRAFT read-only inference is permitted without that dependency.

## Next gate

Once W2 issues independently admissible real CAD same-call `r_D,J_D` records with valid geometry/F/D hashes, frame/density, smooth-ambient vs tangent labels, duplicate-free family holdouts and explicit runtime receipts, train/replay all shortlisted architectures on the **same** geometry representation and exact native objective. Until then only compare analytic benchmark and inference costs. Full original P-CRAFT FEM stress predictor and its original weights are **not** a mass-moment baseline and are not claimed reproduced.
