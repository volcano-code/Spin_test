# W6 P25.1 — Geometry-disjoint UQNO calibration pilot

## Purpose

P25.1 does not replace P-CRAFT PINO and does not alter the moment/Jacobian
backbone. It builds a reliability estimator for the optional
PINO+QuadrANN prediction using signals from three matched P14/P23 model
pairs. It forecasts two distinct error targets:

1. ensemble moment error against the independent cell-centered voxel
   hard-cut reference;
2. ensemble moment error against analytic continuum P0 labels.

The two targets must remain separate because the analytic solid and its
voxelized approximation are not identical.

## Collection design

- Matched seed pairs: (271,883), (277,887), (281,991).
- Shared deterministic dataset seed: 20261108.
- Families: box, sphere, ellipsoid.
- 80 unique geometries per family; 2 coefficient queries per geometry.
- Resolutions: 64^3 and 128^3.
- Total unique geometries: 240.
- Total geometry/query/resolution groups: 960.
- Every model pair evaluates the same geometry IDs and query coefficients.
- Geometry ID, not individual query or resolution row, determines the
  train/calibration/test split.

## UQNO features

The calibration feature vector includes:

- ensemble mean and standard deviation of QuadrANN-enhanced ten moments;
- ensemble mean and standard deviation of diagnostic Jacobians;
- mean absolute PINO-to-QuadrANN moment and Jacobian changes;
- QuadrANN proposal CV, normalized effective sample size, entropy,
  minimum, maximum and zero fraction;
- geometry occupancy fraction, bounding-box extent and center;
- geometry-family one-hot encoding, resolution and learned gate statistics.

## Split and calibration

A deterministic SHA-256 split on geometry_id assigns all rows for one
geometry to exactly one partition:
- train: hash bucket 0–5;
- calibration: bucket 6–7;
- untouched test: bucket 8–9.

A small heteroscedastic MLP predicts log error mean and variance. Its
standardized absolute residuals on the calibration partition produce
finite-sample conformal 90% and 95% intervals. Test geometry IDs are never
used for fitting, normalization, model selection or conformal calibration.

## Acceptance and interpretation

This is a pilot calibration experiment, not a production gate. Report:
- test interval coverage at 90% and 95%;
- log-error MAE and median-error MAE;
- risk-coverage AURC;
- train/calibration/test unique-geometry counts;
- separate metrics for analytic P0 and independent voxel hard-cut targets.

Do not claim a reliable safety gate unless held-out coverage is close to its
nominal level, risk ordering is useful, and results reproduce across seeds
and geometry families. If coverage is poor, revise the uncertainty model or
collect more calibration geometries; do not tune on the test split.

## Limits

- Analytic P0 is vertical-cut continuum truth only.
- The voxel hard-cut reference is discrete, not W2/Cherchi.
- Jacobians are features/diagnostics only and are not Newton-admitted.
- No FEM/FEA, printability, millimeter-wall or 512^3 claim.
- UQNO estimates model error; it does not itself compute exact moments.


## P25.1b sample-size expansion

The initial 72-geometry pilot yielded only 17 calibration geometries, causing
both 90% and 95% conformal quantiles to equal the maximum calibration score.
P25.1b expands to 80 geometries per family (240 unique geometries total),
providing a larger geometry-disjoint calibration and test set. This is a
new data collection run; the original pilot remains archived and must not
be overwritten.
