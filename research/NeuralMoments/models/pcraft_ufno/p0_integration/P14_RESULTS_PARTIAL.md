# W6 P14 — Native high-resolution P-CRAFT PINO training (partial verified results)

Date: 2026-11-08. Research branch only.
Source commit: `26dcd2853ba2731173224b1d970b9b10901ecae3`.
Run: https://github.com/volcano-code/Spin_test/actions/runs/42450889982
Matrix jobs 16^3 and 32^3 completed SUCCESS; 64^3 native training
is still in progress at the time of this report.

## What is actually trained
This is NOT the P13 single-forward capacity smoke. It invokes the
existing Spin-PINO `run_seed()` end-to-end training loop with every
PINO parameter trainable, on actual native 16^3 and 32^3 U-FNO/F-FNO
Fourier grids. Width=8, modes=4, four U-FNO layers, 512 fixed
quadrature atoms (8 points/axis), 75,040 parameters.

- Fresh seeds 271,277,281; same geometry IDs and same analytic
  continuum c/r/J labels regenerated at each grid. Geometry family
  split: fit/validation boxes+spheres; held-out ellipsoid family.
- 40 optimizer updates/seed, batch size 2.
- Fit-only diagonal moment/J residual preconditioner.
- Exact cube rotation augmentation on fit data; independent SO(3)
  rotated ellipsoid test set.
- Full `SpinPINOLoss`: data moment supervision, convex-potential
  physics identities (complement/radial/symmetry/PSD/mass bounds),
  plus analytic P0 Jacobian supervision. All PINO parameters train.
- External GINO, QuadrANN, UQNO adapters are disabled: this is the
  pure PINO high-resolution reference backbone.
- P0 analytic Jacobians are only strictly interior vertical-plane
  box/sphere cuts. This is NOT Cherchi/W2 supervision.

## Verified 16^3 job

Artifact `w6-p14-native-PINO-grid-16`, three checkpoint files and
JSON. ZIP SHA256:
`2ecdc2fa27c641edefa415e82fc4d6fa0f60394d7769ba9099ca4a9930816b01`.

| Metric (mean over 3 seeds) | Result |
|---|---:|
| Held-out ellipsoid r relative L2 | 0.214504 |
| Held-out ellipsoid J relative L2 | 0.302595 |
| SO(3)-rotated ellipsoid r relative L2 | 0.284766 |
| SO(3)-rotated ellipsoid J relative L2 | 0.359774 |
| Independent voxel hard-cut vs continuum r relative L2 | 0.162084 |
| SpinPINOLoss physics-identity residual | 3.33e-16 |
| Trainable PINO parameters | 75,040 |
| Mean 40-step training time / seed | 1.594 s |

All three seeds selected step 40.

## Verified 32^3 job

Artifact `w6-p14-native-PINO-grid-32`, three checkpoint files and
JSON. ZIP SHA256:
`e31c2d409aeb0d513819a391f7343b522c2150b80920ef19fadfe52b38743f9f`.

| Metric (mean over 3 seeds) | Result |
|---|---:|
| Held-out ellipsoid r relative L2 | **0.133473** |
| Held-out ellipsoid J relative L2 | **0.233949** |
| SO(3)-rotated ellipsoid r relative L2 | **0.183798** |
| SO(3)-rotated ellipsoid J relative L2 | **0.272130** |
| Independent voxel hard-cut vs continuum r relative L2 | **0.097265** |
| SpinPINOLoss physics-identity residual | 8.71e-16 |
| Trainable PINO parameters | 75,040 |
| Mean 40-step training time / seed | 9.398 s |

All three seeds selected step 40. Relative to the 16^3 model, the
32^3 model reduced held-out r/J relative L2 by about 37.8%/22.7%,
and SO(3)-rotated r/J relative L2 by about 35.5%/24.4% in this
specific training setup. The independently discretized voxel cut
error also fell from 16.2% to 9.7%, reflecting finer voxelization.

## Interpretation and limits
- This is a genuine improvement in native high-resolution PINO
  training, not merely accepting a larger input then pooling to 8^3.
- The near-zero PINO physics-identity residuals are expected from
  the mathematical parameterization and do NOT establish that the
  model's predictions equal true CAD/continuous physics.
- The hard cell-centered voxel cut vs continuum difference is a
  separate rasterization/discretization measure, not a Cherchi exact
  integral and not the same as model prediction error.
- SO(3) voxel inputs are resampled; rotation diagnostics record
  clipping/interpolation effects. They are not exact grid rotations.
- Relative errors remain substantial, especially for J; none of
  these models is eligible for native Newton or real Spin speedup.
- 64^3 is not reported here until the corresponding three-seed job
  and artifacts finish. No resolution is silently downgraded.

## Next
Complete the native 64^3 training job. If its CPU cost or peak RAM
is excessive, use activation checkpointing and chunked evaluation
while preserving the same model grid, train/test geometry identities
and 40-step budget. Then run a longer multi-seed 32/64 convergence
study and integrate the best trained pure-PINO checkpoint with
DensiCrafter and the optional source-pinned QuadrANN branch.
Formal W0/W2 Cherchi teacher admission, arbitrary quadric/event
derivatives, 128^3 trained model, 512^3 GPU/fVDB and end-to-end
Heart/Teapot/Noodles remain unverified.
