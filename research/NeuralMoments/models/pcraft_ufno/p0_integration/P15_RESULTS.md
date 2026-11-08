# W6 P15 — Actual native 128³ P-CRAFT PINO training pilot (negative result)

Date: 2026-11-08. Research branch only.
Run: https://github.com/volcano-code/Spin_test/actions/runs/42451942337
Commit tested: `da3d74cee881af78fda1128fcf46a1cdfa22b112`.
Status: **SUCCESS** — two tests passed; full 128³ PINO training completed,
and a trained checkpoint plus JSON artifact were uploaded.

Artifact: `w6-p15-native-128-trained-pino`, id 13606431677.
Downloaded ZIP SHA-256:
`f9e6aff260cd53abccec2c6a9ee41f88f58365838cadc88e219a0454666c61a6`.
Raw JSON SHA-256:
`d5dd935c0b25ad392b128a1dfbc5494911ba7f24efcd352ba632b7e6f67f9cea`.

## Actual configuration

- Input and internal P-CRAFT Fourier grid: **128³** (not a downsampled 8³).
- Primary backbone only: P-CRAFT factorized F-FNO/U-FNO.
- Width=8, modes=4, n_layers=4, 75,040 trainable parameters.
- 512 positive quadrature atoms (8 points/axis).
- Every PINO parameter trainable; GINO/QuadrANN/UQNO off.
- Activation checkpointing enabled for all spectral blocks.
- Train batch=1, chunked evaluation batch=1.
- Groupwise exact cube rotation augmentation (same geometry ID shares
  one rotation); separate SO(3)-resampled ellipsoid evaluation.
- 12 optimizer steps, one new seed 271; 10 fit samples from 10
  geometry IDs, 4 validation samples / 2 geometry IDs, 8 held-out
  ellipsoid samples / 4 geometry IDs.
- Full SpinPINOLoss, diagonal residual preconditioner fit split only.
- Labels: analytic P0 continuum, strictly interior vertical-plane
  box/sphere cuts. NOT W2/Cherchi.

## Measured result

| Metric | Result |
|---|---:|
| Training optimizer time | 662.47 s |
| End-to-end wall time | 1305.42 s |
| Peak process RSS | 5,796,388 KiB (about 5.53 GiB) |
| Selected checkpoint step | **1 of 12** |
| Validation r relative L2 | 0.51738 |
| Validation J relative L2 | 0.58354 |
| Held-out ellipsoid r relative L2 | **0.48074** |
| Held-out ellipsoid J relative L2 | **0.53901** |
| SO(3)-rotated held-out r relative L2 | 0.51066 |
| SO(3)-rotated held-out J relative L2 | 0.56510 |
| Independent voxel hard-cut vs continuum r relative L2 | 0.02330 |
| SpinPINOLoss physics identity residual | 1.73e-16 |

The validation-selected step was 1 because step 10/12 worsened the
validation score. Training loss decreased sharply initially, but the
held-out prediction remained poor. The independent cell-centered
voxel cut approximates the analytic continuum labels to about 2.33%;
therefore the dominant 48% model r error is NOT explained by voxel
rasterization alone.

**Decision: 128³ scratch checkpoint is NOT accepted as a useful
predictor and must not be promoted to DensiCrafter, QuadrANN, or
native Newton.** The training path proves 128³ training can execute
on cloud CPU, but the single-seed small-data pilot has severe
generalization error. This is an informative negative result, not
a successful accuracy milestone.

## Why it failed / next hypothesis

The 128³ run had only 10 fit samples and 4 validation samples for
a 75k-parameter model. This is too small to support generalization.
The random-init 128³ pilot also selected step 1, suggesting that
the higher-dimensional input is not rescued by simply training
more updates on the same tiny dataset. Do not blindly increase
steps without increasing independent geometry coverage.

The next P16 experiment warm-starts from the already trained
64³ P14 checkpoint (same width/modes/layers/quadrature), strictly
loads all parameters into the native 128³ Fourier grid, verifies
the same geometry IDs across 64³/128³, reports zero-shot transfer,
and then fine-tunes all PINO weights with a conservative learning
rate. This separates representation transfer from scratch training.
P14 64³ remains the best verified model until P16 shows improvement.

No W2/Cherchi supervision, arbitrary quadric/event derivative
certification, native Newton admission, 512³ training, structural
FEM or full Spin-it Faster end-to-end acceleration is established.
