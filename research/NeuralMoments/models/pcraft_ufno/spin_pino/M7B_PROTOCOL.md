# M7b — Fair arbitrary-SO(3) generalization protocol

Date: 2026-11-06
Primary model: P-CRAFT PINO trunk + support-masked logistic realizable-atom head.

## Why M7b replaces the first M7 comparison

The first M7 run did not use a common rotated test distribution: the no-augmentation and cube-augmentation conditions evaluated cube rotations, while the SO(3)-augmentation condition evaluated arbitrary SO(3). It also evaluated a concatenated original+rotated test tuple, mixing unrotated and rotated samples. Those results are exploratory only and must not be used for a fair augmentation claim.

## Corrected protocol

Three training conditions:
1. No rotation augmentation.
2. 24 exact cube-preserving rotations during training.
3. Haar-uniform arbitrary SO(3) training augmentation.

All three conditions use exactly the same held-out ellipsoid geometries, seeds, optimizer steps and the same deterministic Haar-SO(3) test rotations (seed + 900001). The rotated test metric is evaluated only on the appended rotated samples, not on a concatenation with original samples.

## Label and representation handling

- Native quadric coefficients: exact transform under x'=R x.
- Ten raw moments: exact tensor transform.
- Native Jacobian: exact chain-rule transform J'=T_R J S_R^{-1}.
- Four-channel voxel geometry: trilinear resampling on the fixed [-1,1]^3 domain.
- Voxel interpolation and geometric clipping are not exact; they are reported separately.

Each transformed geometry records:
- fraction of source occupied voxel centers mapped outside the target cube;
- ratio of soft occupancy mass after/before resampling;
- rotation matrix and source geometry ID.

## Acceptance and interpretation

Report unrotated and rotated held-out r/J relative L2, MAE, training time, clipped occupied-center fraction and occupancy mass ratio for every seed and condition.

Do not claim arbitrary-orientation invariance if voxel clipping/interpolation is large. If clipping exceeds the agreed tolerance, redesign the canonical spatial domain (padded physical bounds) before interpreting model generalization.

All labels remain ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI for strictly interior vertical-plane cuts transformed by exact coordinate rules. No arbitrary quadric, CAD event, Cherchi teacher or Newton admission is claimed.
