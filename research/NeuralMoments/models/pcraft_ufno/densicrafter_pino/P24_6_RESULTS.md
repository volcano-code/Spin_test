# W6 P24.6 — Native-128 truth-based physical gate results

Run: https://github.com/volcano-code/Spin_test/actions/runs/42477910849  
Workflow conclusion: SUCCESS (all three seed jobs and aggregate completed).  
Aggregate artifact: 13616941237.

## Three-seed results

| Seed | Baseline model-vs-hardcut error | QuadrANN model-vs-hardcut error | QuadrANN accepted/rejected | Baseline mass reduction | QuadrANN mass reduction | Feasible |
|---|---:|---:|---:|---:|---:|---|
| 271 | 12.411% | 6.277% | 6 / 0 | 0.22547% | 0.22590% | Yes |
| 277 | 10.179% | 8.118% | 6 / 0 | 0.21284% | 0.21264% | Yes |
| 281 | 29.617% | 37.095% | 0 / 6 | 0.17445% | 0.00000% | No |

The model-vs-hardcut error is the relative L2 difference between the model's
current moment prediction and the independent cell-centered hard-cut
integral for the current density. It is not the analytic-continuum P0 error.

## Aggregate

- QuadrANN accepted updates: 12/18.
- QuadrANN rejected updates: 6/18.
- QuadrANN feasible seeds: 2/3.
- Mean baseline mass reduction: 0.20425%.
- Mean QuadrANN mass reduction: 0.14618%.
- Mean QuadrANN minus baseline mass-reduction fraction: -0.05807 percentage points.
- Mean model-vs-hardcut error delta (QuadrANN minus baseline): -0.2392 percentage points, but with large seed variation.
- The fail-closed aggregator correctly returns KEEP_OPTIONAL_FAIL_CLOSED.

## Interpretation

P24.6 is a mixed result, not a full pass.

Positive:
- The corrected truth-based gate admits all six QuadrANN updates for seeds
  271 and 277.
- Both seeds remain within the predeclared independent-cut and material-shape
  tolerances, with the protected shell unchanged.
- Their model-vs-hardcut errors improve.

Negative:
- Seed 281 rejects all six QuadrANN updates.
- Seed 281's QuadrANN model-vs-hardcut error is worse than baseline.
- Mean material mass reduction is lower with QuadrANN than with pure PINO.
- Therefore QuadrANN is not promoted to production/default material design.

Next:
- Keep QuadrANN optional and fail-closed.
- Continue P24.7 multi-geometry generalization across box/sphere/ellipsoid,
  three geometry instances per family and 64^3/128^3.
- Use per-seed evidence to design conditional activation; do not select a
  gate from the same test geometries used for reporting.
- P24.6 uses analytic P0 and independent voxel hard-cut only, not Cherchi,
  Newton certification, FEM/FEA or 512^3.
