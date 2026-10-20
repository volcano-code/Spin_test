# W5 M10 — Positive-measure moment quadrature and authentic H8f 81-point exclusion

**Writable GitHub branch only:** `research/neuralmoments-w5-deeponet-20261019`, `volcano-code/Spin_test`.
**Parent to update (lease):** `670636df1783c11c45e3c9018a830ffba123b7ac`.  Frozen common source `0bcc187b3005478baa586a6d6f450e73811ca342`. **No W0/W2/W6/main writes or original failed CI mutation.**

## M10 delivered

- `m10_positive_quadrature.py`: PositiveQuadratureMoment reuses the **unaltered**, byte-pinned W6 M6 Gauss spectral geometry encoder and learned nonnegative quadrature weights (`13,448` trainable real parameters). Its W5-owned moment head returns `r=Σ w_k sigmoid((Bc·m_k)/(eps||Bc||)) m_k`; each result is a nonnegative **discrete measure** supported on W6's Gauss nodes inside known `[-1,1]^3`. Thus mass cannot be negative, and the resulting mass/first/second moments satisfy necessary known-box moment inequalities up to floating-point rounding. This is NOT an exact CAD volume or a guarantee of correct physical 3D material. The raw ten coordinates are W0's undoubled `M,Lx,Ly,Lz,Qxx,Qyy,Qzz,Qyz,Qxz,Qxy`. Cross coefficients of native c map to polynomial q via `B=diag(1,1,1,1,1,1,1,2,2,2)`.
- A closed-form `dr/dc_native` including `||Bc||` terms is checked independently against PyTorch autograd. Positive projective scaling preserves r, `Jc*c≈0`. **The discrete sigmoid head is not a scalar potential; Jc B^-1 need not be symmetric/PSD**, and its local derivative must NEVER be treated as a W2 native continuum Jacobian. A conservative exact-`Fraction` cube interval check proves strictly all-empty/full polynomials under an explicitly caller-grounded cube and returns (r,J)=(0,0) or (Σw m,0) only within these strict sign regions. The branch transition is not a smooth continuum proof.
- `m10_archive_gate.py`: Byte-pinned read-only W0 M9 **real H8f 81-point** JSON report (Git blob `177fe9126d76d94236ecdca2d4750232f78f627a`) plus W2 M8 genuine H8e 25-point manifest. The W0 original run `39123384402` remains **failure**, 81 material integrals were independently reverified by W0, point60 has an actual source construction branch change, full smooth neighborhood/terminal Newton is NOT certified, and both archives admit **zero** native smooth J training labels. This W5 step reads pinned **summary files only**, not the original 81-point/25-point ZIP materials. The original material arithmetic is W0/W2's accomplishment and was not recomputed in W5.
- `m10_experiment.py` & `m10_merge.py`: Source-checked same-4-channel 8³ analytic P0 training for W5 voxel DeepONet, W6 Gauss epsilon .04, and positive-quadrature epsilon .04/.12. Training inputs, W0 native c, analytic continuum r/J targets, fit/validation geometry ID split, held-out ellipsoid family, fixed minibatch schedule, optimizer, gradient loss, and up-to-100-step budget are identical. All models are **13,448–13,939 real parameters (3.65% spread)**. Reports are three individual executed seeds 19/23/29 and a hash-indexed recomputation from their raw records. Each run **actually verifies equality with its published M9 dataset SHA**. W0+W2 historical evidence is only a gated exclusion, NOT training data.

## Real executed tests and training

Environment: Python 3.13.5, PyTorch 2.10.0+cpu, NumPy 2.3.5, pytest 9.0.2, single CPU thread, GPU hours 0. CPU timing is small-network host-dependent and not a Cherchi speedup measurement.

From a checked-out W5 working tree, arrange **unmodified read-only** W6 M4/M5/M6 source files and W0/W2 reports in separate directories (do not vendor or edit them into the Git branch). Our smoke uses:

```bash
export PYTHONPATH=.
export W5_M7_READONLY_W6_ROOT=/path/to/pinned/W6
export W5_M8_READONLY_W6_ROOT="$W5_M7_READONLY_W6_ROOT"
export W5_M9_READONLY_W6_ROOT="$W5_M7_READONLY_W6_ROOT"
export W5_M9_READONLY_W2_MANIFEST=/path/to/pinned/W2/teacher_manifest.json
export W5_M10_READONLY_W6_ROOT="$W5_M7_READONLY_W6_ROOT"
export W5_M10_READONLY_W0_REPORT=/path/to/pinned/W0/contracts/contract_smoke_m9.json
export W5_M10_READONLY_W2_MANIFEST="$W5_M9_READONLY_W2_MANIFEST"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m pytest -q tests/python/test_w5_*.py
# Local assembled byte-identical W5/W6 source mirror: 125 passed, 42 subtests passed.

for seed in 19 23 29; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m research.NeuralMoments.models.deeponet.m10_experiment \
    --w6-root "$W5_M10_READONLY_W6_ROOT" \
    --w0-report "$W5_M10_READONLY_W0_REPORT" \
    --w2-manifest "$W5_M10_READONLY_W2_MANIFEST" \
    --seeds "$seed" --steps 100 --per-family 20 --repeats 3 \
    --expected-m9-dir research/NeuralMoments/models/deeponet \
    --output "research/NeuralMoments/models/deeponet/m10_seed${seed}.json"
done
python -m research.NeuralMoments.models.deeponet.m10_merge \
   research/NeuralMoments/models/deeponet/m10_seed19.json \
   research/NeuralMoments/models/deeponet/m10_seed23.json \
   research/NeuralMoments/models/deeponet/m10_seed29.json \
   --output research/NeuralMoments/models/deeponet/m10_seed19_23_29_full.json
```

### Independent held-out ellipsoid analytic P0 means (seeds 19/23/29)

| Model | r MAE ↓ | Jc MAE ↓ | necessary physical pass ↑ | analytic-one-step true-objective acceptance after physical gate ↑ | empty c=(-1,0,...) mass | warm Jc CPU ms ↓ |
|---|---:|---:|---:|---:|---:|---:|
| W5 voxel DeepONet | **0.02298** | **0.01328** | 34.2% | 34.2% | -0.38571 | 0.965 |
| W6 Gauss convex scalar potential eps .04 | 0.05216 | 0.03160 | 98.3% | 64.2% | -0.000852 | **0.206** |
| W5 **positive discrete** eps .04 | 0.04251 | 0.02970 | **100%** | 83.3% | **0** | 0.413 |
| W5 **positive discrete** eps .12 | 0.04297 | 0.02914 | **100%** | **99.2%** | **0** | 0.357 |

The acceptance test is **only** the existing M9 held-out **one-dimensional smooth analytic P0 height decision**, re-evaluated with independent analytic true moments and mandatory necessary-moment veto at both start/candidate. It is NOT a full 10D optimization success rate or a native Cherchi/Spin outcome. All four use the same originally generated r/J labels, which correspond to ideal analytic solids rather than 8³ sampled input Boolean material.

New positive quadrature achieves guaranteed **discrete** material cone at the cost of **higher error than DeepONet** and loss of W0 continuous-Hessian integrability symmetry; the W6 convex Gauss has an analytic potential and faster warm derivative but violates exact empty cut mass. No single model is proven superior overall. Smooth surrogate radial invariance is numerical only at finite precision; real CAD and solver convergence require new native evidence.

Mean *actually measured* time for encoding once and 8 sequential (r,Jc) queries (CPU): DeepONet 9.24ms; W6 Gauss 3.91ms; positive quadrature eps .04 5.65ms and eps .12 5.55ms. Full cold r alone is slower for positive quadrature (~1.03–1.10ms vs DeepONet .46ms). Times exclude native Boolean and the guard/check itself.

## Regression and scientific failures retained

1. W0's original H8f 81-point workflow remains `failure`; point 60 is an actual topology/source-feature exception. No `J` teacher label is promoted, despite numerical finite-difference agreement and 81 independent material moment integrations. W2 M8 25-point H8e remains `failure` with 8 source-hash drifts. **New W5 Cherchi calls: 0; training samples from archived real native J: 0**.
2. Passing necessary moment-cone inequalities certifies **neither** actual CAD solid nor correct Boolean orientation, physical frame, final optimized geometry, manufacturing, original Spin objectives or converged Newton/KKT. No new production native or GPU runs.
3. A physically positive sigmoid quadrature head gives neither a symmetric `Jq` nor guaranteed low derivative/decision error, and inherits spatial quadrature resolution limits. The strict empty/full branch is only sound on the independently grounded source cube; an unknown CAD bounding box must fail closed upstream.
4. Comparison remains on a tiny 8³, three-seed, 100-step analytic task, not on out-of-family real CAD or independent randomized heldout hyperparameter-blind replication. Epsilon .12 is an exploratory candidate and its large one-step acceptance must be confirmed independently.
5. The restored local regression ran with byte-identical source Git blobs for the critical W5/W6 modules and pinned W0/W2 reports, but **a fresh GitHub remote CI checkout has not been executed**. Report actual GitHub status separately; do not claim green CI without workflow records.

## Next suggested M11

Add a better joint **cone-valued + integrable** model that retains P-CRAFT's Hessian structure without W6's negative-mass pathology, or switch carefully between a positive discrete head and a certified derivative mode. Validate on new analytic families and real W2 native material `r_D` where eligible; do not train on uncertified J. Evaluate complete 10D trust-region/optimization only after W0/W2 neighborhood/native proof and an independent terminal oracle. Preserve every failed CI.
