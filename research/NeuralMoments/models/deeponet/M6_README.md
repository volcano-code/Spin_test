# W5 M6 — budgeted fail-closed analytic P0 decision replay

Repository: `volcano-code/Spin_test`; **only write branch** `research/neuralmoments-w5-deeponet-20261019`.
Parent W5 commit: `c4dcde3d21edc51f5b0f9f96cffe65919859de9c`; frozen common core `0bcc187b3005478baa586a6d6f450e73811ca342`.
Read-only coordination commits observed October 19, 2026: W0 `8466202ee23eb0ffc1eb655988b97a1ce098783c`, W2 `df3641280c0f7dde16e53a3f64a1529ccef2b5b4`.

## Scope and nonclaims

W2's read-only manifest still states `w2-cherchi-teacher-v1-pre-w0`, `ADAPTER_SMOKE_ONLY`, 0 native runs and 0 training samples. M6 **does not** merge W0/W2, use synthetic network-created teacher labels, run Cherchi, train models, validate original/F/D CAD, or claim a neural-vs-native speedup. The explicit W2 manifest gate never admits pre-W0 records, even if someone increases self-reported counts.

M6 uses a reproducible **analytic smooth sphere-cap** oracle solely on the *one-dimensional horizontal-cut manifold*, with W0's native ten-component symmetric-entry coefficient `c`, retained-positive beta and undoubled `r=[M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY]`. This is not a general 10D CAD optimization. The oracle identity SHA is a hash of the analytic specification, **not** the bytes of original CAD or certified Boolean material. It accepts only unit-norm positive-z vertical-plane coefficients, never arbitrary quadrics or open Teapot CAD.

The M5 proposal gate has a caller-supplied `identity_verified` Boolean, which alone **does not** certify true native identities. The new M6 analytic wrapper sets it only after enforcing its local, restricted analytic domain; it must **not** be used to promote W2 records. A future native path must use an externally established W0/W2 material seal and independently replayed native oracle rather than copying this Boolean.

## New production-like interfaces

- `m6_analytic_rollout.py`: `ReplayPolicy(max_truth_calls=4,max_backtracks=2)`, `AnalyticCapOracle`, `check_w2_manifest`, and `guarded_analytic_step`. Validates candidate domain and native `c`, constructs the 10×1 orthonormal `dc/dh` tangent, passes physically normalized `r,Jc` to the existing M5 damped Gauss–Newton solver, and checks each candidate or backtrack with *analytic truth evaluated independently of the untrusted prediction*. Rejects non-improving or invalid updates, preserves the original on fallback, bills failed truth requests, and NEVER commits material changes. `accepted=True` means only the analytic objective decreased; `requires_external_commit=True` remains mandatory.
- `m6_model_adapter.py`: evaluation-only, CPU-only DeepONet/Geometry-MLP adapter that encodes D once, queries the cached head, and differentiates using `jacrev` without re-encoding. Its network weights are **not** authenticated as trained on native data. Refuses model-training mode and invalid native coefficients.
- `m6_budget_audit.py`: fixed CPU seeds `7,19,31`; three cut heights; six scenarios: exact analytic predictor, controlled perturbations, reversed derivative, zero derivative, and both **random/untrained** networks. Each case tracks analytic oracle budget, physical-normalized `r/Jc` MAE, true objective decrease and uncompiled timing. Never counts analytic queries as native Cherchi calls. The 54 per-case records, all seed labels, configurations, query counts and failure/acceptance reasons are stored in `m6_p0_budget_seed7_19_31_cpu.json`.

## Reproduce exact local M6 plus pre-existing regression

From repository root (Python 3.13, PyTorch 2.10+cpu, NumPy 2.3.5, pytest 9.0.2):

```bash
python -m pytest -q \
 tests/python/test_w5_deeponet_smoke.py \
 tests/python/test_w5_m2_contract_and_gate.py \
 tests/python/test_w5_m3_mesh_and_p0.py \
 tests/python/test_w5_m5_decision_gate.py \
 tests/python/test_w5_m6_analytic_rollout.py \
 tests/python/test_w5_m6_model_adapter.py \
 tests/python/test_w5_m6_budget_audit.py
# local: 73 passed, 38 subtests passed; NOT a GitHub CI claim.

python -m research.NeuralMoments.models.deeponet.m6_budget_audit \
 --out research/NeuralMoments/models/deeponet/m6_p0_budget_seed7_19_31_cpu.json
```

Existing M4's own held-out analytic-training suite was not rerun during M6: no corresponding M4 trainer checkpoint is treated as W5 M6 trained weights. M1–M3 and M5 code used for local regression was reconstructed from exact GitHub blob SHAs; M6 files themselves were byte-hash checked before remote commit. The experiment runs CPU one thread; no CUDA, native build, native Cherchi call, CGAL, or hardware-constrained competing job was performed. Wall-time numbers measure **this Python analytic/model path only**, not any Cherchi speedup.

## Observed 54-case audit

| Case | Analytic accepted / cases | Mean P0 oracle calls | Meaning |
|---|---:|---:|---|
| Exact analytic prediction | 9/9 | 2.00 | Same closed-form family as the analytic verifier; control baseline |
| Controlled noisy r/J | 9/9 | 2.00 | Fixed-seed perturbation only; not a trained neural prediction |
| Reversed analytic derivative | 0/9 | 4.00 | All non-improving candidates rejected; maximum query budget reached |
| Zero derivative | 0/9 | 1.00 | No meaningful surrogate candidate; immediate fallback |
| Random, untrained DeepONet | 5/9 | 2.89 | **Interface safety test, not neural accuracy** |
| Random, untrained Geometry-MLP | 4/9 | 3.11 | **Interface safety test, not neural accuracy** |

Never promote these numbers to native full-material, physical geometry, 10D convergence, faster-than-Cherchi or viable W2 training results. Timings and full errors are in the exact JSON audit; uncertainty and domain assumptions are explicit there.

## Next blocked milestone

A *genuine*, separately pinned W2 record catalogue containing independently verified original/F/D hashes, native-module SHA, frame and density, legitimate topology and derivative neighborhood proofs, allowed train/test family splits and real Cherchi calls is required. Then validate W0 contract, compare trained W5 networks against true `r_D,J_D` and directional tangents, independently evaluate candidate material, record total wall/memory/CPU/GPU/native-query cost, and only after that measure solver-level decisions and any speedups. Native admission is blocked until such evidence exists.
