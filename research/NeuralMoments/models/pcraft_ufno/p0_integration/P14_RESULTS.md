# W6 P14 — Native 16³ / 32³ / 64³ trained P-CRAFT Spin-PINO

Date: 2026-11-08. Branch: research/neuralmoments-w6-pcraft-20261019.
Source: P14 code at 26dcd2853ba2731173224b1d970b9b10901ecae3.
Final successful matrix run:
https://github.com/volcano-code/Spin_test/actions/runs/42450889982
All three jobs succeeded: native 16³, 32³ and 64³. Each job ran
two P14 tests, trained three fresh seeds for 40 optimizer steps each,
and uploaded three model checkpoints plus one JSON receipt.

## Fixed architecture and protocol

- Primary and only neural-operator backbone: P-CRAFT SpinPINO,
  factorized Fourier U-FNO/F-FNO.
- Width 8, modes 4, n_layers 4, 75,040 trainable parameters.
- Native internal Fourier grid and input grid both equal 16³, 32³
  or 64³. No initial adaptive pool to 8³.
- Eight quadrature points per axis: 512 positive quadrature atoms.
- Seeds 271,277,281; per seed 8 box + 8 sphere train-pool geometry
  instances split by geometry ID into fit/validation; 6 held-out
  ellipsoid geometry instances; two coefficient queries per geometry.
- 40 Adam updates per seed, batch 2; fit-only diagonal residual
  preconditioning; exact cube augmentation of fit samples; separate
  SO(3)-rotated ellipsoid evaluation.
- Every PINO parameter is trainable. External GINO, QuadrANN, UQNO
  are disabled: this is the clean high-resolution PINO reference.
- Full SpinPINOLoss is used: moment data loss, analytic P0 Jacobian
  supervision and the convex-potential identities (complement,
  radial invariance, Hessian symmetry/PSD, mass bounds).
- P0 source is analytic continuum box/sphere/ellipsoid vertical-plane
  cuts strictly inside the object. It is NOT W2/Cherchi teacher data.

## Aggregate results

| Metric (mean over three seeds) | 16³ | 32³ | 64³ |
|---|---:|---:|---:|
| Held-out ellipsoid r relative L2 ↓ | 0.214504 | 0.133473 | **0.094538** |
| Held-out ellipsoid J relative L2 ↓ | 0.302595 | 0.233949 | **0.201146** |
| SO(3)-rotated ellipsoid r relative L2 ↓ | 0.284766 | 0.183798 | **0.138641** |
| SO(3)-rotated ellipsoid J relative L2 ↓ | 0.359774 | 0.272130 | **0.228134** |
| Independent voxel hard-cut vs continuum r relative L2 ↓ | 0.162084 | 0.097265 | **0.043978** |
| SpinPINOLoss physics identity residual | 3.33e-16 | 8.71e-16 | 8.57e-16 |
| Trainable parameters | 75,040 | 75,040 | 75,040 |
| Mean 40-step training seconds per seed | 1.594 | 9.398 | 93.516 |

The 64³ model improves mean held-out r/J relative error by 55.9%/33.5%
against 16³. The corresponding SO(3)-rotated errors improve by
51.3%/36.6%. These are comparisons under the same nominal optimizer
budget and model parameter count; grid size changes representation
and computational cost.

## Per-seed held-out ellipsoid r/J relative L2

| Seed | 16³ r / J | 32³ r / J | 64³ r / J |
|---|---:|---:|---:|
| 271 | 0.224380 / 0.314718 | 0.138382 / 0.240572 | 0.097748 / 0.206305 |
| 277 | 0.222650 / 0.306404 | 0.119274 / 0.226547 | 0.094803 / 0.201341 |
| 281 | 0.196483 / 0.286664 | 0.142764 / 0.234728 | 0.091063 / 0.195793 |

All nine seed/grid checkpoints selected step 40; there was no early
stopping at a zero-update/random initialization.

## Independent physical interpretation

- The independent hard-cut comparison is a cell-centered voxel
  discretization against analytic continuum P0 labels. It measures
  rasterization/representation error and is NOT Cherchi continuous
  Boolean integration.
- Physics-identity residuals are near machine precision because the
  SpinPINOLoss checks structural identities of the convex moment
  parameterization. They do not certify accuracy against real CAD.
- Rotated test inputs use SO(3) voxel resampling; interpolation/clipping
  diagnostics are retained in the per-seed JSON.
- Despite improvement, 64³ Jacobian error remains 20.1% on held-out
  ellipsoids and 22.8% on rotated ellipsoids. These models are NOT
  eligible for Newton or exact-solver bypass.
- No W2/Cherchi labels, arbitrary quadric event derivatives, CAD,
  structural FEM, native Spin-it Faster speedup or 128/512 trained
  model is established by P14.

## Artifacts and SHA-256

| Resolution | Artifact | ZIP SHA-256 |
|---|---|---|
| 16³ | w6-p14-native-PINO-grid-16 | 2ecdc2fa27c641edefa415e82fc4d6fa0f60394d7769ba9099ca4a9930816b01 |
| 32³ | w6-p14-native-PINO-grid-32 | e31c2d409aeb0d513819a391f7343b522c2150b80920ef19fadfe52b38743f9f |
| 64³ | w6-p14-native-PINO-grid-64 | 597ef4c2725b958976998d3912242b2a9e13953b4de193fcb408cc70ad08bf75 |

Each artifact contains its exact per-seed trained checkpoint files and
the aggregate/per-seed JSON report.

## Next

P15 starts the first actual native 128³ training pilot with all PINO
parameters trainable, activation checkpointing on all U-FNO spectral
blocks, batch 1 and chunked evaluation. If that succeeds, expand seeds
and steps. Only after trained 128³ accuracy and memory are stable should
we couple the selected pure-PINO checkpoint with QuadrANN/DensiCrafter.
W0/W2 formal Cherchi admission is still required for CAD Newton.
