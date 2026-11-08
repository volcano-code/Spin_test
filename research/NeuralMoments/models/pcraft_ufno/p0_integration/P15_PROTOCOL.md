# W6 P15: first actual 128^3 native P-CRAFT PINO training pilot

This follows the successful P14 16/32/64 three-seed, 40-step CPU
training matrix. P15 is not another random-weight forward/backward
capacity smoke: it invokes the complete train_seed loop at actual
128^3 Fourier resolution with all 75k PINO parameters trainable.

## Memory controls and data integrity
- width=8, modes=4, n_layers=4, native 128^3 U-FNO/F-FNO grid;
  512 positive quadrature atoms; exact same P-CRAFT SpinPINO heads.
- All spectral U-FNO blocks use PyTorch activation checkpointing.
- Train batch=1; validation/test/fit metric evaluation chunk=1.
- Fit augmentation rotates once per geometry ID, applying the same
  exact signed-permutation SO(3) transform to all coefficient queries
  and corresponding analytic r/J labels. This fixes the earlier
  sample-wise augmentation inconsistency.
- One new seed 271, 6 box + 6 sphere fit-pool geometries, 4 held-out
  ellipsoid geometries, two coefficient queries each, 12 optimizer
  updates. This is a capacity/learning pilot, not a statistical result.
- Fit-only diagonal moment/J residual preconditioning.
- Full SpinPINOLoss: analytic data r/J supervision, convex potential
  physics identities, symmetry/PSD and mass bounds.
- Original P-CRAFT PINO trunk only; GINO, QuadrANN, UQNO off.
- Checkpoint saved only as CI artifact, not committed to source repo.

## Labels and acceptance
The P0 analytic continuum labels are exact only for box/sphere and
ellipsoid strictly interior vertical-plane cuts. No W2/Cherchi labels.
Held-out ellipsoids and separately SO(3)-rotated ellipsoid evaluation.
Also independently compare predictions against cell-centered hard
voxel-cut moments; rasterization error is not continuous Cherchi truth.
No Newton admission, arbitrary quadric/event derivative certification,
real CAD, structural FEM or 512^3 claims.

## If the 128 pilot passes
Run 3 seeds with larger geometry splits and 20-40 steps if memory
permits; compare to 64 using a matched dataset protocol. Then couple
the trained checkpoint to the DensiCrafter density layer, but keep
the independent physical feasibility filter. A 128 training pass
does not automatically authorize 256/512.
