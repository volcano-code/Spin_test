# M7c — PINO SO(3)-covariance consistency loss

## Motivation

M7b found that data augmentation alone barely improves arbitrary-orientation generalization. The next step is to encode the exact tensor transformation law directly into the PINO training objective.

## Exact covariance targets

For a proper rotation R, let S_R transform native quadric coefficients and T_R transform the ten raw moments. Then:

`r(R·D, S_R c) = T_R r(D,c)`

`J(R·D, S_R c) = T_R J(D,c) S_R^{-1}`

These transformations are implemented in `equivariance.py` and are applied to model predictions in the consistency loss.

## Loss

For each training minibatch, sample a deterministic SO(3) rotation per sample, rotate the four-channel voxel geometry by trilinear resampling, transform native coefficients exactly, and compare rotated model outputs with the transformed unrotated model outputs.

The residual is normalized by detached target RMS values to prevent mass and Jacobian scale differences from dominating:

`L_eq = ||r_R - T_R r||² / RMS(T_R r)² + 0.25 ||J_R - T_R J S_R^{-1}||² / RMS(T_R J S_R^{-1})²`

Training objective:

`L_total = L_data + 0.05 L_moment_physics + 0.25 L_admitted_J + lambda_eq L_eq`

Only synthetic analytic P0 Jacobians are used in this experiment; no W2/Cherchi diagnostic data is admitted.

## Matched conditions

1. PINO baseline: no rotation augmentation, lambda_eq=0.
2. SO(3) augmentation only: augmentation enabled, lambda_eq=0.
3. Consistency loss only: no augmentation, lambda_eq=0.05.
4. SO(3) augmentation + consistency: augmentation enabled, lambda_eq=0.05.

All conditions use the same fit/validation/test geometry IDs, seeds 131/137/139, optimizer steps, batch size and deterministic arbitrary-SO(3) held-out test transforms.

## Risks and limits

- The voxel input is trilinearly resampled, so `L_eq` includes a small discretization/interpolation component.
- A low consistency loss does not certify the physical Jacobian; it only enforces the known rotation covariance of the model.
- No Newton admission, arbitrary quadric certification or native Spin end-to-end acceleration is claimed.
- If consistency loss improves rotated error but harms unrotated accuracy, tune lambda only on validation data and keep the held-out test untouched.
