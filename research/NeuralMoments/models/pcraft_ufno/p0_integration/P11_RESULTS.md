# W6 P11/P11b — pinned upstream GINO + QuadrANN + UQNO, PINO-first integration

**Date:** 2026-11-07. **Only branch:** `research/neuralmoments-w6-pcraft-20261019`.
**Core remains P-CRAFT Spin-PINO** with its original coefficient-normalized
ten-moment and model-internal analytic Jacobian head. GINO, QuadrANN and
UQNO are optional *original-source-derived* P0 experimental components,
not standalone replacements for the PINO backbone.

## Source lineage and real cloud execution

- Source/contract commit:
  https://github.com/volcano-code/Spin_test/commit/693b1c38880ac25496a0734114e23d9acbf94325
- Matched analytic CPU pilot commit:
  https://github.com/volcano-code/Spin_test/commit/1fcdce26d8ac12c26c1ed28335d18e14c7056272
- Zero-gate inference overhead repair commit:
  https://github.com/volcano-code/Spin_test/commit/cdb0cde4246f34982f6b15e1073b8f22cd122235
- Existing W6 pinned NeuralOperator, QuadrANN and Algoim versions:
  `p0_integration/UPSTREAM_PINS.json`, licenses in
  `p0_integration/third_party/`. The official original models are
  used through `neuraloperator_adapter.py` and
  `quadrann_adapter.py`; original main source archives were
  not untraceably copied.
- Latest independent CI:
  https://github.com/volcano-code/Spin_test/actions/runs/42368822123
  **SUCCESS**; 12 PINO/upstream/contract tests passed, 0 failed
  (3.77 s). 20-update analytic pilot executed; evidence artifact
  `w6-p11-selected-upstream-pilot/w6_p11_selected_upstream.json`.
  Raw JSON SHA-256:
  `51cc4bb33327fc7f16f9f62989ade31c06d7933871a272f0b6db244c9bbeba51`.
  Downloaded ZIP SHA-256:
  `64e1605b97bacf939a76f4199254f201ecac522267f3afa3d7b1dfb81548de12`.
- Original P0 integration parent CI at implementation commit:
  https://github.com/volcano-code/Spin_test/actions/runs/42368484456
  **SUCCESS**; 14 upstream contract tests passed, 0 failed.
  Other W6 full workflow status is a separate gate.

## What was actually integrated

1. Optional **NeuralOperator GINO** geometry encoder, with bounded
   geometry-only positive corrections to the *original PINO quadrature
   weights*. Uses actual pinned GINO code and W6 GINO point/voxel adapter.
2. Optional original **QuadrANN** graph quadrature-weight proposal on
   the PINO native quadrature node positions. Its weights remain
   geometry-only; the physical cut coefficient `c` is applied by the
   original PINO logistic-atom/convex-head math, not by an unverified
   arbitrary derivative formula.
3. Optional original **UQNO** residual-scale wrapper around the exact
   PINO moment head. Geometry-ID **groupwise** conformal
   screening is available and disallows overlap with fit/calibration
   geometry IDs.
4. **P11b**: if gate=0 and the model is in eval mode, skip GINO/QuadrANN
   computation entirely. In train mode, still evaluate the modules
   with zero gate, so gate gradients can be learned.
5. The W6 `MomentQuadratureResult` public API **withholds**
   `J_D`; the model's analytic `J_model` is exposed in a
   deliberately separate diagnostic field only.

## Actual same-core/P0 experiment (one seed; NOT learned adapters)

Seed 131; 20 optimizer updates of **PINO-only** on exact analytic
continuum P0 vertical-plane labels; 12 geometry-disjoint fit instances,
4 calibration geometries, 4 held-out ellipsoids, 2 coefficient queries
per geometry. One PINO checkpoint and one held-out test split are used
for all four inference settings. GINO/QuadrANN/UQNO additional weights
are randomly initialized and never trained in this experiment.

| Condition (fixed random gates) | Held-out r relative L2 | Held-out J_model relative L2 | 8 held-out query CPU time |
|---|---:|---:|---:|
| PINO, both gates zero | 0.4509811103 | 0.5091977715 | 0.045359 s |
| GINO gate 0.2 only | 0.5639925003 | 0.5970696807 | 1.108022 s |
| QuadrANN gate 0.2 only | 0.4509382546 | 0.5091636777 | 0.059155 s |
| Both gates 0.2 | 0.5639587045 | 0.5970438719 | 1.119262 s |

Zero-gate CPU PINO mean and diagnostic J differ from the separately
batched full-vector PINO reference by max 5.96046e-8 (roundoff).
Upstream optional modules are now skipped if their gate is exactly
zero in eval mode. In this small test, activating random GINO
substantially increases cost and worsens accuracy. QuadrANN random
gate's negligible metric change is NOT an independently proven gain.
The fixed 0.2 gates are nonzero interface probes, not validation-tuned
or trained weights; their poor outcome is not proof trained upstream
networks cannot work.

## Small-sample UQ screening: no physical or derivative certification

- Groupwise conformal alpha=0.25, 4 held-out calibration geometry IDs,
  grouped across coefficient queries. Fitted simultaneous score
  threshold qhat = 0.83730358.
- Measured full-ten-component group coverage 4/4 on the separate
  held-out ellipsoid geometries. Four groups are far too few for a
  robust generalization or distribution-free guarantee in realistic
  Spin applications; exchangeability is unverified.
- Predeclared absolute simultaneous-radius threshold 0.05:
  **exact evaluation requested** `RADIUS_ABOVE_THRESHOLD`.
  No exact Cherchi calculation is executed by this module.
- **Native Newton derivative admitted = false** under every
  calibration setting. The diagnostic J_model stays outside the
  P0 result contract and never becomes a W0/W2-certifiable J_D merely
  because a neural uncertainty interval is small.

## Environment

Cloud CPU: GINO/QuadrANN/UQNO original upstream installation,
physics safety tests, current P0 synthetic pilot: completed.
Cloud CPU future: new geometry/cut distribution, adapter fine-tuning
under equal teacher/query budget; three seeds; true cold/warm
geometry caching and risk-coverage.
Local GPU future: fVDB official source CUDA build isolated from W6's
PyTorch 2.5.1 CI; genuine 64/128/256/512 sparse shape stress with
peak VRAM and trained high-resolution geometry; native Cherchi,
Heart/Teapot/Noodles and full solver measurements.
The fVDB compatibility matrix from its pinned official source is
recorded in `candidate_projects/FVDB_LOCAL_COMPATIBILITY_20261107.md`.

## Admission decision and next development

**Accept P11 as a source-pinned optional interface/safety smoke; do
not promote GINO, QuadrANN or UQNO into the PINO default.**

Next P12: train **one adapter at a time** using identical fit
labels, PINO checkpoint, random seeds, validation-only selection and
held-out new geometry families. Report r/J, training/cold/ warm
encoding, peak CPU/GPU RAM, material conservation, calibration,
risk/coverage, and exact-fallback frequency. GINO needs explicit
geometry latent caching for many c queries; otherwise the
1.108 s / 8-query overhead is not compelling. QuadrANN needs a
cut-aware proposal study but any c-conditioned reweighting must
derive a mathematically valid J_model or withhold it.

**Remaining original goal gaps:** W0/W2 admitted Cherchi teachers,
real CAD derivatives and event neighborhoods, 512^3 GPU training/
generalization, native exact-speed comparison, Heart/Teapot/Noodles
end-to-end optimization and fabrication all unverified.
