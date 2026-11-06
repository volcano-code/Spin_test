# Spin-PINO v1 — PINO-first model

Primary model: P-CRAFT UFNO3d / F-FNO factorized Fourier backbone, adapted to Spin's ten raw moments.

- `pino_backbone.py`: source-pinned P-CRAFT UFNO3d-style factorized spectral U-shaped encoder.
- `spin_pino.py`: geometry-conditioned positive quadrature weights, smooth convex moment potential, ten moments and analytic coefficient Jacobian.
- `SpinPINOLoss`: data term plus moment-specific physics identities. The original elasticity equilibrium/constitutive PINO losses are not reused because they do not describe Spin's moment integral.
- `tests/test_spin_pino.py`: CPU smoke and mathematical identity tests.

Borrowed GINO, Transolver, QuadrANN, UQNO, NQR, fVDB and DensiCrafter components are optional plug-ins or baselines. None replaces the PINO trunk.

See `PINO_CORE_SOURCE_AUDIT.md` and `SPIN_PINO_30DAY_PLAN.md` at the parent model directory for provenance, scope and the 30-day exit criteria.

Current status: first implementation slice added; CI validation pending. Not trained on W2/Cherchi labels and not admitted to native Newton.

## M0 CPU validation

GitHub Actions run [42186600269](https://github.com/volcano-code/Spin_test/actions/runs/42186600269) passed: Spin-PINO 9/9 tests in 1.44 s; the existing GINO/QuadrANN smoke 8/8; Algoim C++ 1/1 with max absolute error 7.50e-11. This validates the initial architecture and identities only; no Spin/Cherchi training or Newton admission is claimed. See `VALIDATION_REPORT.md`.

## M1 analytic P0 data and training

The dataset builder uses the existing exact continuum vertical-plane references for boxes, spheres and ellipsoids. Fit/validation are split by geometry identity (boxes+spheres); the entire ellipsoid family is held out for testing. Labels are explicitly tagged `ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI`; the analytic Jacobian is only valid for strictly interior vertical-plane cuts.

Small CPU smoke:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m pytest -q \
  research/NeuralMoments/models/pcraft_ufno/spin_pino/tests/test_spin_pino.py \
  research/NeuralMoments/models/pcraft_ufno/spin_pino/tests/test_dataset.py
```

Three-seed training (CPU prototype):

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m research.NeuralMoments.models.pcraft_ufno.spin_pino.train \
  --seeds 131,137,139 --train-geometries-per-family 16 \
  --test-ellipsoid-geometries 8 --queries-per-geometry 2 \
  --steps 120 --grid-size 8 --device cpu \
  --output /tmp/spin_pino_m1_three_seed.json --save-checkpoints
```

These are synthetic analytic labels, not Cherchi supervision. The held-out family tests geometry generalization only within this restricted P0 vertical-plane task; no arbitrary quadric or native Newton claim is implied.

## M1 three-seed analytic training result

GitHub Actions run [42188044841](https://github.com/volcano-code/Spin_test/actions/runs/42188044841) passed all jobs. The 3-seed CPU run used 52 fit / 12 validation / 16 held-out ellipsoid samples, 8^3 geometry inputs and 120 steps. Mean held-out ellipsoid r MAE was 0.04069 and J MAE 0.03461; relative L2 errors were 0.4250 and 1.5802. This is a functional but preliminary baseline, not yet good enough for Newton use. Full metrics and caveats are in `M1_TRAINING_REPORT.md`; checkpoint/report artifact ID 13488726149.

## M2 controlled sweep

`sweep.py` runs three matched configurations on the same geometry-family splits and three seeds:

- baseline: 8^3 input, 4^3 positive nodes, smoothing 0.04;
- quadrature refinement: 8^3 input, 6^3 positive nodes, smoothing 0.02;
- resolution refinement: 16^3 input, 4^3 positive nodes, smoothing 0.02.

The selection metric is the mean of held-out ellipsoid r and J relative L2, with no validation/test leakage. Run:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m research.NeuralMoments.models.pcraft_ufno.spin_pino.sweep \
  --seeds 131,137,139 --steps 120 --batch-size 8 --device cpu \
  --output /tmp/spin_pino_m2_sweep.json
```

This sweep is designed to identify whether low M1 accuracy is caused by coarse geometry input, insufficient positive quadrature nodes or potential smoothing. It does not by itself prove performance on general quadrics or Cherchi geometry.

## M2b: support-masked quadrature measure

The initial M2 sweep showed a trade-off: increasing from 4^3 to 6^3 nodes reduced held-out Jacobian relative L2 from 1.580 to 0.961, but worsened moment relative L2 from 0.425 to 0.511. Increasing the voxel input from 8^3 to 16^3 did not improve the combined score.

Code review identified a missing physical constraint in the first Spin-PINO head: its positive learned quadrature weights were not explicitly masked by the input density/occupancy at the quadrature nodes. M2b fixes this. Each node weight is now

`w_k = (8/N^3) * rho(x_k) * occupancy(x_k) * sigmoid(g_theta(D)_k)`.

This prevents the network from creating discrete material atoms in sampled empty space. It is a discrete sampled-support constraint, not a continuum/CAD certificate. The M2b three-seed sweep reruns the same three configurations and is tracked separately from the pre-mask M2 results.
