# W6 P25.3 — Geometry-conditional QuadrANN activation

## Objective

Use QuadrANN only when independent evidence supports its use for a geometry
family and a validated UQNO hard-cut error predictor judges the current input
to be within an application-supplied error tolerance. P-CRAFT SpinPINO remains
the default and primary moment/Jacobian backbone.

## Evidence motivating conditional activation

P24.7 reports:
- Box: mean moment and independent hard-cut error improve at 64^3 and 128^3.
- Sphere: analytic P0 moment error is near-neutral, but independent voxel
  hard-cut error worsens.
- Ellipsoid: analytic P0 moment error slightly improves, but independent
  voxel hard-cut error worsens.
- Diagnostic Jacobian error improves for all three families.

P24.7 contains only three geometry instances per family per seed, so these
results are hypothesis-generating. They are not sufficient to create a
production allow-list. The policy therefore requires an externally supplied
validation receipt and defaults to PINO-only when the receipt is absent or
not VALIDATED.

## Runtime routes

1. PINO_PLUS_QUADRANN: family is admitted by an independent validation
   receipt, the receipt targets hard-cut error, and the validated UQNO
   upper error bound is within the caller's tolerance.
2. PINO_ONLY: family is not admitted, receipt is not validated, target
   is wrong, or predicted QuadrANN risk exceeds tolerance.
3. EXACT_FALLBACK: caller explicitly requires exact computation, or
   UQNO reports OOD/invalid features.

The exact callback is caller-supplied. In cloud pilots it may be the
independent cell-centered voxel hard-cut integral only; it is not Cherchi.

## Anti-leakage requirements for future validation receipt

- Train/calibrate on geometry IDs disjoint from policy validation.
- Evaluate family-level activation on untouched geometries.
- Record per-family hard-cut error, unsafe acceptance, fallback fraction,
  and wall-clock cost.
- Do not derive admitted_families from P24.7 test means alone.
- Require multiple independent geometries and seeds per family.
- Freeze the receipt and policy before final test evaluation.

## Current status

The policy engine and unit contracts are implemented. No geometry family
is currently production-admitted. Until P25.1b calibration and an independent
P25.3 validation report pass, the only valid production route is PINO-only
or exact fallback.

## Limits

No Cherchi certification, Newton admission, FEM/FEA, printability, physical
millimeter-wall, 512^3, or end-to-end Spin-it speed claim is made.
