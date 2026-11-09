# W6 P25.1 — Initial 72-geometry UQNO pilot results

Run: https://github.com/volcano-code/Spin_test/actions/runs/42565079021  
All three signal-collection jobs and the train/calibrate job completed successfully.  
Artifact: w6-p25-1-uqno-calibration-pilot (ID 13651394784).

## Dataset and split

- 72 unique geometries: 24 each from box, sphere and ellipsoid.
- 2 coefficient queries per geometry.
- 64^3 and 128^3.
- 288 geometry/query/resolution groups, ensemble across three matched model seeds.
- Geometry-disjoint split: 37 train, 17 calibration, 18 test geometries.
- Feature dimension: 349.
- Two separate targets: independent voxel hard-cut error and analytic continuum P0 error.

## Held-out test results

| Metric | Hard-cut error predictor | Analytic P0 error predictor |
|---|---:|---:|
| Row-wise 90% interval coverage | 84.72% | 95.83% |
| Row-wise 95% interval coverage | 84.72% | 95.83% |
| Geometry-simultaneous 90% coverage | 77.78% | 94.44% |
| Geometry-simultaneous 95% coverage | 77.78% | 94.44% |
| Log-error MAE | 0.5475 | 0.4169 |
| Median-error MAE | 0.0799 | 0.0542 |
| Risk-coverage AURC | 0.1036 | 0.1085 |

Calibration used the maximum standardized residual per geometry across
queries and resolutions. There were only 17 calibration geometries, so
the finite-sample 90% and 95% conformal quantiles both equal the maximum
calibration score. This is statistically coarse and must not be presented
as a mature calibration result.

## Decision

- Analytic P0 predictor is a promising pilot, but still needs a larger
  independent geometry set and external validation.
- Hard-cut error predictor fails the target coverage, especially at
  geometry-simultaneous level.
- No UQNO predictor is admitted as a production safety gate.
- The runtime wrapper remains fail-closed and experimental.
- P25.1b expands to 80 geometries per family (240 total), increasing
  calibration and test geometry counts.

## Limits

This pilot does not establish Cherchi error prediction, Newton safety,
FEM/FEA safety, printability or 512^3 generalization.
