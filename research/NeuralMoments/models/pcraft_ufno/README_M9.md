# W6 M9 — anti-aliased per-cell material capacity and bounded few-query ablation

**Write scope:** `volcano-code/Spin_test`, only `research/neuralmoments-w6-pcraft-20261019`, only `research/NeuralMoments/models/pcraft_ufno/`.
**Parent:** `2e5f8b66017dc342a0692d8a4c4a5d61fee74232` (M8). Frozen core `0bcc187b3005478baa586a6d6f450e73811ca342`, external P-CRAFT U-FNO reference `volcano-code/test@24eda3e9b3f87ba16251a9025761986d6cfe3079`.

## Original W6 charter gap assessment

Implemented: independent U-FNO, once-only cached geometry, `r[10]`/native `J[10,10]` (or legal tangent `10x9`), no nine-field FEM stress reconstruction or obsolete PINO constitutive losses, 0/1/2-query few-shot, analytic family holdout, W5 DeepONet and Geometry-MLP CPU comparisons, explicit complex-real DOF accounting.

**Still unfulfilled in production:** no admitted W0/W2 independently sealed real Cherchi material/derivative training set; no genuine CAD/mesh/Cherchi smooth-stratum or Newton terminal A/B; no GPU latency/peak VRAM and no demonstrated *end-to-end* native speedup; no accuracy win over W5 on real geometry. M8's capacity-deficit failure blocks useful complex-geometry adaptation and M7's atomic legality does not establish continuous legal material.

At start of M9, W0 read-only HEAD `83f9709c220e51a5927e053537bdd98ecc20f7c0`; W2 read-only HEAD `4b1301c6b478437f29836e78be0b773b9d145787`. W2 M12 manifest still declares **0 admitted teacher labels / 0 new native runs / 81 excluded archived H8f candidates**, and `J_D` unpublished. No W2 archive is used for this work.

## What M9 actually adds

1. `m9_antialias.py`: independent *geometry-only* cell occupancy. Exact axis-aligned **box** overlap, and **ellipsoid/sphere** numerically conservative lower/estimated/upper occupancy based on interval distance bounds plus adaptive octree-like subdivision. Stable nonnegative cell volumes, positive density, moment monomials in W0's *undoubled* `(M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY)` order. The 3D domain is fixed `[-1,1]^3`. The strict inside/outside interval test uses finite-precision bounds with a margin; **this is not exact rational/Cherchi Boolean certification**.
2. `m9_bounded_atoms.py`: nonnegative, capacity-clipped atomic weights at cell centers; optional *single-encoding* interpolation of a frozen M7 gate from its Gauss tensor grid to 8³/16³/24³ cells. The main geometry-capacity experiment instead uses **untrained constant 0.5 gates** to isolate geometry representation. `0/1/2` *independent analytic* support queries fit only bounded atomic weights via low-rank ridge and backtracking, with no target-query training. Analytic M7 surrogate `J` and `Jc*c≈0` are checked; this is NOT an admitted native Cherchi derivative, and ambient `Jc B^-1` is NOT claimed symmetric.
3. `m9_experiment.py`: same **analytic held-out ellipsoid specs**, independent support and target cut streams as M8. Six seeds, 20 ellipsoid geometries/seed, 2 support c/r and 8 disjoint evaluation c/r/J per geometry; no trained neural checkpoint or FEM weights. Checks frozen M3 train SHA for seeds 19/23/29 and original M8 heldout identities. Repeats across cell resolutions 8³, 16³, 24³ at subdivision depth 2. Preserves original old M8 8³ binary-point/Gauss-6 capacity as a diagnostic baseline. Logs full mass estimate/bounds, all adaptation errors, query counts and CPU timings.
4. `test_m9.py`: 24 new regressions (box exact overlap, small sphere missed by old points, bounds, gradients, cache, leakage/provenance gate, support monotonicity and 0/1/2 constraints). Existing M4–M8 regression suite re-executed (112 tests). No modification of those earlier modules.

**Essential fairness disclosure:** the M9 sampler is given a full analytic primitive shape specification (center/axes). That specification **cannot be inferred uniquely from M8's 8³ binary density/occupancy input**. These results are a *geometry-privileged upper-bound/ablation*, NOT a fair head-to-head M8/W5 deployment result, not a claim of AI inference improvement, and not a real CAD quadrature interface. The resolution experiment changes atom count (512/4096/13824) and uses no additional neural weights; it therefore cannot be claimed size-matched to W5.

## Executed commands (CPU, Python 3.13.5/PyTorch 2.10.0+cpu)

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m unittest \
 research.NeuralMoments.models.pcraft_ufno.test_m4 \
 research.NeuralMoments.models.pcraft_ufno.test_m5 \
 research.NeuralMoments.models.pcraft_ufno.test_m6 \
 research.NeuralMoments.models.pcraft_ufno.test_m7 \
 research.NeuralMoments.models.pcraft_ufno.test_m8 \
 research.NeuralMoments.models.pcraft_ufno.test_m9 -v

OMP_NUM_THREADS=1 python -m research.NeuralMoments.models.pcraft_ufno.m9_experiment \
  --seeds 19,23,29 --per-family 20 --resolutions 8,16,24 \
  --depth 2 --eval-queries 8 --output /tmp/m9_first.json
OMP_NUM_THREADS=1 python -m research.NeuralMoments.models.pcraft_ufno.m9_experiment \
  --seeds 31,37,41 --per-family 20 --resolutions 8,16,24 \
  --depth 2 --eval-queries 8 --output /tmp/m9_confirm.json
```

**Actually executed locally:** `136/136` combined regression tests passed, exit 0, in 2.703 s; M9's 24/24 tests passed independently. `python -m compileall` on four new `.py` files exit 0. Both three-seed experiment processes exit 0. Earlier M4–M8 source/test files in the local mirror had exact Git blob matches for all M4–M8 code/test files explicitly checked. The three older M2 imports (`analytic_cut.py`, `fixed_moments.py`, `teacher_gate.py`) were **locally reconstructed to match frozen semantics, not byte-for-byte copies**; M3 frozen tensors for seeds 19/23/29 match their documented SHA-256. This local mirror is not a remote GitHub Actions checkout/CI.

### Six seeds, 120 distinct held-out ellipsoids (120×8 independent test queries, each resolution)

| Metric | M8 legacy 8³ binary point / Gauss-6 | M9 cell 8³ | M9 cell 16³ | M9 cell 24³ |
|---|---:|---:|---:|---:|
| mean **full-shape capacity relative error** | **42.730%** | **0.2469%** | **0.06243%** | **0.02355%** |
| mean (upper-lower) / true mass, depth=2 | n/a | **51.22%** | **25.59%** | **17.06%** |
| support-geometry mass over capacity, K=1 | 49/120 | 0/120 | 0/120 | 0/120 |
| support-geometry mass over capacity, K=2 | 78/120 | 0/120 | 0/120 | 0/120 |

The bound width **remains large** despite the very accurate center estimates; the bracket by itself is too loose to certify precise native material moments. For depth 0/1/2/3 the interval width shrinks; see `m9_depth_interval_cpu.json`. At 8³ its mean width decreases 208.7% → 103.5% → 51.6% → 25.8% of full mass (20 seed-19 shapes); at 16³ depth 3 it is still 12.89%.

| Heldout metric (untrained 0.5-gate, 120 shapes) | K=0 | K=1 | K=2 |
|---|---:|---:|---:|
| M9 cell 8³ `r_MAE` | 0.028479 | 0.008123 | 0.006358 |
| M9 cell 16³ `r_MAE` | 0.028753 | 0.008242 | 0.006335 |
| M9 cell 24³ `r_MAE` | 0.028809 | 0.008292 | 0.006365 |
| M9 cell 8³ `J_MAE` | 0.011394 | 0.006602 | 0.005220 |

The 0→1→2 improvements **are not directly comparable to M8's trained** 0.0256 metrics because M9 has a geometry oracle and untrained neutral weights. Crucially, **higher resolution does not monotonically improve actual r/J test error**; remaining losses reflect soft-cut bias, finite atomic locations and fitting/training design, not only full-mass capacity.

Every predicted result passed the checked necessary nonnegative atomic moment conditions; adaptation never exceeded its estimated cell capacity and never intentionally fabricated a W2 teacher. `r_total = r_F + r_D` remains an external W0 contract operation, not implemented or certified here. CPU-only mean geometry sampling: 8³ ≈1.44 ms, 16³ ≈4.20 ms, 24³ ≈9.21 ms per shape; test invocation process peak RSS approx 357620 KiB (process-level, not model VRAM). Native/GPU runs: **none**.

## Remain blocked / recommended next

- Replace analytic primitive spec with *verifiable, geometry-bound source* (e.g. authenticated mesh or a signed-distance representation with proven bounds), not arbitrary relabeled samples. A float interval classifier alone cannot certify Cherchi exact Boolean topology or CAD legality.
- Fit transferred **trained** M7 gates on identical information/budgets; continue comparing to W5 DeepONet + Geometry-MLP with the same geometry input. A D8-only preprocessing change cannot regenerate lost subvoxel information.
- W0/W2 must grant real independently sealed native `(r,J)` by geometry source SHA, full material F/D split, smooth derivative category and Newton terminal validation before any true-teacher or real optimizer timing experiment.
- Do not infer actual Faster speedup, model capacity advantage, GPU VRAM benefit, or percentage-error guarantee from these analytic geometry-only ablations.
