# W6 P12 first controlled upstream training: GINO vs geometry-aware QuadrANN vs PINO head

Date: 2026-11-07. W6 research branch ONLY.
Parent PINO fixed: P-CRAFT UFNO/F-FNO, logistic positive moment head,
analytic model J. The external original upstream sources remain pinned
via `p0_integration/UPSTREAM_PINS.json` and MIT notices.

## Three separate adaptation arms
- P-CRAFT `pino_head`: frozen U-FNO trunk, 12 updates of the original
  PINO support-masked quadrature-weight head. This is a *nontrivial* matched
  label-budget baseline, unlike P11's zero-update reference.
- `gino`: same pretrained/frozen PINO checkpoint per seed; original
  upstream GINO encoder + positive residual weight proposal trained.
- `quadrann`: same pretrained/frozen PINO; original pinned MIT QuadrANN
  core trained on **occupied-material voxel centres**, with positive
  kernel transfer onto the fixed PINO quadrature points. Unlike P11's
  geometry-independent fixed-node port, this adapter sees source shape.
- All three share identical analytic P0 fit observations/label calls,
  update indices, learning rate, steps and validation-only checkpoint
  selection. **Model parameter/FLOP budgets are NOT matched**, and
  must be reported before any promotion judgment.

## Teacher and splits
Only exact analytic continuum restricted vertical-plane box/sphere
labels are used in fit/validation. Entire ellipsoid family is held out.
Repeated native coefficient queries per geometry share the SAME
geometry identity and cannot cross fit/validation/test. Each seed
trains an independent PINO baseline (40 updates); then every arm
gets exactly 12 matched additional fit queries/updates, without
reusing test labels for selection. Seeds 131/137/139; 10 geometry
instances/family for fit+val, 6 held-out ellipsoids. 8^3 P0 only.

Validation metric r_MAE+0.25 J_MAE, recorded at steps 0,1,4,8,12.
Per arm report mean relative L2 r/J and MAE, pretraining budget,
per-arm trainable parameters, cold geometry encoding for unique
geometry IDs, warm coefficient+J query times, seed-level failures.

## UQNO separate scope
Train the original UQNO residual-scale head using fit-only
PINO residual labels (24 updates per seed), then calibrate a
groupwise simultaneous radius on the distinct validation geometry IDs.
Report coverage and 0.05 cutoff exact-request rate on held-out
ellipsoids, with 3-seed results. The held-out ellipsoid test labels
are used for report metrics ONLY, not fitting/calibration.
This is statistical screening only, not physical proof. Every
native Newton request MUST select exact evaluation; no W0/W2
derivative admission is present.

## Promotion
Do not enable either external adapter by default merely for
unit-test success or a small one-seed metric: require reproducible
benefit on both r and J, a new geometry/quadric distribution,
comparable model capacity and latency, and W0/W2 provenance.
No claimed 512^3 full GPU model or native exact speedup.
Cloud CPU can execute this experiment; official fVDB CUDA
and native Cherchi/Heart/Teapot/Noodles remain local.

## Commands (CI handles dependencies)
```bash
python -m pytest -q research/NeuralMoments/models/pcraft_ufno/p0_integration/tests/test_p12_train.py
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
 python -m research.NeuralMoments.models.pcraft_ufno.p0_integration.p12_train \
 --seeds 131,137,139 --base-steps 40 --adapter-steps 12 --uq-steps 24 \
 --output /tmp/w6_p12_three_seed_pino_upstream.json
```
