# W5 M13 — Continuous voxel-cell integrals, W6 M7 matched benchmark and true remaining gaps

**2026-10-20** · GitHub `volcano-code/Spin_test` · **sole writable ref** `research/neuralmoments-w5-deeponet-20261019` · parent reviewed `56befd05baf403a2371be8483d7564f69ffca0d8` · frozen native source `0bcc187b3005478baa586a6d6f450e73811ca342`. All new committed files are inside W5's `research/NeuralMoments/models/deeponet/` and independent `tests/python/test_w5_m13_*`. Read-only W6 M7 files remain external and are **not vendored/modified in W5**. Do not overwrite prior W0/W2/W3/W6/main branches, native CI failures or CAD artifacts.

## Gap to W5's original charter (answered before M13 execution)

**Completed research prototype:** geometry caching, 10D native c -> undoubled r[10] -> Jc[10,10], W5 DE-DeepONet and Geometry-MLP, per-shape validation splits, exact analytic box/ball/ellipsoid P0 supervision, derivative-enhanced/value-only training and 0/1/2/4/8-query adaptation, small CPU cost measurements and W6/P-CRAFT comparison. The original charter does **not** demand original-paper pretrained checkpoint reproduction.

**Not completed as a scientific surrogate:** real CAD teacher training and smooth derivative admissibility; W0/W2 signed source/F/D/scale/retained-side native independent seals; arbitrary quadratic cut integration; thin-wall/internal-surface/topology behavior and multi-scale accuracy; physically valid optimization beyond a one-dimensional analytic height step; total end-to-end Cherchi/Faster runtime and 10D terminal Newton/KKT. A tiny CPU r/J latency or a moment-cone feasibility check does not establish actual geometry, continuous Jacobian or solver acceleration. There is **no universal 1% threshold** published in W0.

## Materially new M13 work

### 1. `m13_cell_integrals.py`: exact whole-cell polynomial integration

A known four-channel `[rho,occ,level,proximity]` volume, treated as a **new, frozen piecewise-constant density per voxel cell** in `[-1,1]^3`, is bound to a byte SHA-256. Effective density is nonnegative `rho*occ` (not a claim of exact CAD material). Per-geometry cache computes the 25 × n x/y integrated layer moments *once*, and every subsequent positive vertical W0 native cut `c=(-h,0,0,b,0,...), b>0` evaluates

- all ten undoubled continuous **cell-volume** moments, including partially clipped cells, through exact polynomial antiderivatives;
- the full **local surrogate** native Jacobian `Jc=(1/b) ∫_{z=h} w(x,y,z)m mᵀdA × B`, `B=diag(1×7,2×3)`, hence symmetric PSD `Jc B⁻¹` and `Jc c≈0` strictly inside a single z-cell layer;
- a strict **UNAVAILABLE** Jacobian at any z-cell interface/contact, for nonvertical signed quadrics, invalid saved native `c`, missing valid input density, or altered numeric cache. Strict all-empty/all-full gives the exact moments/zero derivative for the declared cell-volume source, **not** the true original CAD source.

This uses no neural model and is a diagnostic volume reference for the discretized density. It is not a new W2 Cherchi teacher nor general arbitrary-quadric evaluator.

### 2. Same-source resolution and capacity experiment

`m13_resolution_benchmark.py` compares **the same analytic ideal primitive oracle** to (i) center-sampled whole-cell volumes at 8³/16³/24³, (ii) deliberate misuse of W5 M8's `linspace` *node* samples as 8³ full cells, and (iii) the untrained **maximum Gauss node material capacity** underlying W6 M7 (hard Heaviside; **J unavailable**, not W6 learned predictions). Train/heldout splits are not used to tune these deterministic geometric integrators. New independent seeds `[67,71,73]`, 6 geometries in each box/sphere/ellipsoid family per seed, 2 cuts per geometry, all source tensor/geometry digests saved. This is an **analytic ideal-vs-voxel approximation** benchmark, not a true CAD validation.

| volume proxy | n | r MAE ↓ | Jc MAE ↓ | mean single cached r+J CPU ms ↓ |
|---|---:|---:|---:|---:|
| center-sampled cell volume | 8 | **0.0149311** | **0.0076199** | **~0.18** |
| center-sampled cell volume | 16 | **0.0063428** | **0.0034524** | **~0.22** |
| center-sampled cell volume | 24 | **0.0042815** | **0.0022805** | **~0.28** |
| previous node-sampled W5 tensor *wrongly interpreted* as cell mass | 8 | **0.0342901** | **0.0117980** | not measured |

The Gauss maximum-capacity atom r MAEs on the same center-sampled inputs are **0.03679 / 0.02812 / 0.03309** at n=8/16/24; the n=24 deterioration demonstrates **fixed sparse Gauss atoms do not automatically converge with increased voxel-input resolution**. They are not W6 M7 trained model numbers. No Gauss hard-atom J comparisons are claimed.

### 3. Actual W6 M7 learned-model matched comparison

`m13_w6_m7_probe.py` validates the **original** external W6 M7 `m7_realizable.py` and `m6_safe_inference.py` Git blob SHA-1 (plus all earlier M4/M5/M6 dependencies) before import, without writing to W6. W6 M7 source commit `9d1758ea1ef527577b835f2b6bcfc5f0439d933d` is still accessible in current W6 branch. The model is actually trained **from fresh random initialization**; no original external pretrained weights are assumed.

`m13_m7_model_comparison.py` trains **all three** W5 4-channel DeepONet, W5 M10 positive measure, and original W6 M7 realizable U-FNO on exactly identical newly **center-cell-sampled** four-channel inputs and independent analytic **continuum** r/J labels. New seeds 67/71/73, 20 box +20 sphere geometries, two W0 native vertical cuts per geometry, 8 whole geometries reserved for validation, 20 unseen ellipsoid geometries, two cuts each. Trainable parameters respectively **13,939 / 13,448 / 13,448**, within **3.66%**. All see the same minibatch indices, Adam lr .003, batch8, loss `MSE(r)+0.5*MSE(Jc)`, max 100 training steps, validation-only checkpoint selection. No W2 archived data enter any fitting, selection or test targets. Three independent JSON runs plus strict merged report preserve per-seed dataset hashes and full training receipts.

| fresh trained architecture | mean r MAE ↓ | mean Jc MAE ↓ | analytic 1D candidate accepted ↑ | warm Jc CPU ms ↓ |
|---|---:|---:|---:|---:|
| W5 voxel DE-DeepONet | **0.020127** | **0.014252** | **85.83%** | **1.031** |
| W5 positive discrete quadrature | **0.046395** | **0.024789** | **98.33%** | **0.463** |
| **actual W6 M7 realizable U-FNO** | **0.0097865** | **0.0062720** | **74.17%** | **0.250** |

**New actual finding:** W6 M7 yields lower sampled analytic r/J error across these three seeds under this *new centered-input, 100-step* protocol, unlike earlier W6 comparisons on different legacy inputs/seeds. Nonetheless, W6 M7 has **lower one-step acceptance than W5 DeepONet in this experiment**, proving accuracy ranking is not an optimizer ranking. Model output is a nonnegative discrete atomic moment, but its smooth surrogate J is **not** independently certified native Cherchi J and its ambient `Jc B⁻¹` generally need not be symmetric. W6's mathematically projective **tangent** model identity is not evidence of W0-certified real material stratum. The center-cell geometry itself was synthesized from ideal analytic shapes and still differs from real CAD geometry.

### 4. Tests and provenance

- `test_w5_m13_cell_integrals.py`: independent exact uniform cuboid r/J, cross-column B factor, nonuniform density FD, PSD/symmetry, strict empty/full, cell-face Jacobian exclusion, finite signed native validation, source/hash tamper, nonnegative-density constraints.
- `test_w5_m13_resolution_and_m7.py`: W6 original source hash and hostile tamper, model forward/J/gradient, matched capacity, distinct geometry-family identities, resolution/atom diagnostics, real smoke training and same-data checks.
- `test_w5_m13_merge.py`: rejects duplicates, mismatched seed/protocol/source hashes, forged W2 native count and missing model results.
- All M13 code and data executed locally on Python 3.13 / torch 2.10 CPU / NumPy 2.3 / pytest 9; GPU training time 0. Independent group runs and raw logs in `m13_*json` and `m13_test_log.txt`. Full available W5 M1–M13 regression results are *actually rerun* with source-identical W5 code restored from archived milestone packages and W6 M4–M7 pinned original Git blobs. Older M4/M5 test scripts not present in the local archived ZIP were excluded from the restored-suite count; this must not be presented as the exhaustive remote W5 branch CI.

## Latest read-only upstream blockers

- W0/W3: 81 previously archived real H8f moment integrals were independently checked, but point60 exhibits an actual construction feature branch; there is no certified continuous gradient or accepted Newton endpoint. No new native four-side Cherchi labels are available.
- W2 HEAD observed on 2026-10-20 `4b1301c6b478437f29836e78be0b773b9d145787`, latest `teacher_manifest.json` blob `41e7c4dc65a029a3cc7ce746c694bc8a03cdad70`, status `M13_PRIMITIVE_POSITIVE_PROJECTIVE_ALGEBRA_READY_W0_FORMAL_ACCEPTANCE_PENDING`, still `native_teacher_runs=0`, `training_samples=0`, all H8f 81 excluded. A positive-projective ray identity is NOT a new native sampling identity or derivative approval. **Native Cherchi calls in W5 M13: 0; formal J labels used: 0.**
- W6 M8 latest at `2e5f8b66017dc342a0692d8a4c4a5d61fee74232` investigates bounded 0/1/2 oracle support adaptation. W5 M13 only source-pins the unchanged W6 M7 core; no claim that W6's later adaptive study was repeated here.

## Remaining gap / scientific next

M13 makes **material-discretization error and sampling bias quantitatively visible**. The whole-cell moment cache offers a fast, exact reference for its own proxy volume and a mathematically sound local smooth vertical derivative, but **not** an operator supporting arbitrary c, topology changes or native CAD. W6 M7 shows improved supervised analytic accuracy on new centered inputs but weaker checked optimization decisions. Next W5 stage: extend analytic cell integration to nonvertical planar cuts and bounded error certificates, measure the real F/D-cached Cherchi cost and a full 10D optimizer with W0/W2 independently admitted materials; hold out complex mesh geometry families beyond ideal box/sphere/ellipsoid. Do not claim a trained surrogate replaces real Faster until these gates pass.
