# W6 P25.2 — Calibrated UQNO abstention and exact fallback

## Role

UQNO is a reliability estimator, not a moment/Jacobian operator. P-CRAFT
SpinPINO remains the primary prediction backbone. QuadrANN remains optional
and fail-closed. UQNO may abstain from using an approximate prediction when
its calibrated upper error bound exceeds an application-supplied tolerance.

## Two distinct targets

- hardcut target: relative error to the independent cell-centered voxel
  hard-cut moment integral;
- analytic P0 target: relative error to continuum vertical-cut analytic
  moments.

A checkpoint is bound to exactly one target. A hardcut checkpoint cannot be
loaded as an analytic-P0 predictor or vice versa.

## Runtime contract

1. Caller supplies the feature vector using the exact P25.1 feature schema.
2. UQNO returns median, lower and upper calibrated error bounds at 90% or 95%.
3. Caller supplies an application-specific positive error tolerance.
4. If the calibrated upper bound exceeds tolerance, abstain and invoke the
   caller-supplied exact fallback.
5. Otherwise return the P-CRAFT PINO approximate result.
6. Nonfinite or malformed features are errors and must not silently permit
   approximate execution.

## Current fallback provenance

Cloud pilot fallback may use only the independent voxel hard-cut reference.
It is not W2/Cherchi continuous Boolean integration. A future native Cherchi
callback must be separately integrated, provenance-tagged, and validated
against W0/W2 before it is called Cherchi-certified.

## Safety and acceptance

- The gate must not silently replace the PINO backbone.
- Error tolerance is supplied by the consuming task; it is not tuned on test.
- Calibration coverage and risk-coverage must be reported on geometry-disjoint
  test geometries.
- A pilot checkpoint is not a production safety certificate.
- If calibration data are missing, out-of-distribution checks fail, or
  predicted risk exceeds tolerance, fail closed to the exact callback.

## Tests

P25.2 unit tests cover target/schema separation, finite ordered intervals,
low-risk approximate pass-through, high-risk fallback, and rejection of
nonfinite features.


## Distribution-shift abstention

The checkpoint stores train-only 1st/99th percentile feature bounds. At runtime,
any feature outside this envelope triggers exact fallback before approximate
prediction is returned. Malformed or nonfinite features also fail closed.
This envelope is a conservative pilot OOD check, not a formal guarantee of
coverage under arbitrary distribution shift.
