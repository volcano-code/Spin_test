# W6 P14: native high-resolution P-CRAFT Spin-PINO training

P14 moves beyond P13's one-pass capacity probes to actual supervised
training of the entire P-CRAFT PINO model at native 16^3,32^3,64^3
Fourier grids. No plugin can replace the PINO trunk.

## Locked training
- New geometry seeds 271,277,281.
- Per resolution: 8 box + 8 sphere train-pool geometries, split by
  geometry ID into fit/validation; 6 entirely held-out ellipsoids.
  Two cut queries per geometry.
- The same geometry IDs and analytic c/r/J labels are regenerated
  at each source grid; voxel inputs are sampled at 16^3,32^3,64^3.
  Dataset hashes differ by grid, geometry IDs must match.
- P-CRAFT SpinPINO width=8, modes=4, n_layers=4, internal Fourier
  grid equals source grid; points_per_axis=8 (512 positive quadrature atoms).
- 40 optimizer steps/seed, batch=2; all PINO weights trainable.
- Full existing SpinPINOLoss: supervised moments + admitted analytic
  Jacobian supervision + exact convex-potential physics identities
  (complement, radial, Hessian symmetry/PSD, mass bounds).
- Fit-only diagonal residual preconditioning; exact cube augmentation
  of fit samples; no external geometry adapter, no GINO/QuadrANN/UQNO.
- Evaluate fit, validation, unseen ellipsoid, and SO(3)-rotated ellipsoid.
  Checkpoints selected on validation only.
- Compare predicted moments/Jacobians against the separate hard
  cell-centered voxel-cut integral and analytic continuum labels.
- Save per-seed model checkpoints as GitHub Actions artifacts, not
  into the public source repository.

## Scientific scope
P0 analytic teacher gives exact continuum labels only for box/sphere
and ellipsoid vertical-plane cuts strictly inside the object. This is
NOT W2/Cherchi teacher data, not arbitrary quadric event derivatives,
not CAD exact integration. SO(3) test inputs use voxel resampling and
the script records clipping diagnostics.

## Acceptance / no hidden resolution downgrade
The script asserts encoder preparation retains exactly the configured
N^3 tensor and records 512 fixed quadrature atoms. The spectral U-FNO
uses its native N^3 grid (with normal U-Net half/quarter scale stages);
there is no initial adaptive pooling to 8^3. A successful training CI
is actual high-resolution PINO training, not a forward/backward smoke.

## Cloud vs local
Cloud CPU matrix 16^3/32^3/64^3 training is the immediate P14 goal.
If 64^3 is too slow or exceeds runner memory, report the failure and
adjust batch/checkpointing; do not claim an unexecuted grid.
Local GPU remains required for efficient multi-epoch 128^3/256^3/512^3
and official fVDB CUDA; W0/W2 Cherchi admission is still required for
real Newton and full Spin-it Faster claims.
