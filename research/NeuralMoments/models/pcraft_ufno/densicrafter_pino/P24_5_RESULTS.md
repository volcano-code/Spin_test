# W6 P24.5 — QuadrANN domain/resolution diagnostic results

Run: https://github.com/volcano-code/Spin_test/actions/runs/42477473603  
Result: SUCCESS; all three seed diagnostics and aggregate completed.  
Aggregate artifact: 13616640114; ZIP SHA256  
2836444de19b19775ef01322326497cbd89b7b1e9a56f9abbd4ec9fc23c28908.

## Aggregate analytic-P0 and independent hard-cut comparison

Mean relative L2 errors over three matched seeds:

| Family | Grid | PINO r vs analytic P0 | PINO+QuadrANN r vs analytic P0 | PINO J | PINO+QuadrANN J |
|---|---:|---:|---:|---:|---:|
| Sphere | 64^3 | 0.15852 | 0.15324 | 0.25577 | 0.21963 |
| Sphere | 128^3 | 0.17734 | 0.17325 | 0.24777 | 0.21153 |
| Ellipsoid | 64^3 | 0.18920 | 0.19138 | 0.22269 | 0.18539 |
| Ellipsoid | 128^3 | 0.19315 | 0.19836 | 0.21110 | 0.17432 |

Independent cell-centered hard-cut relative L2 errors:

| Family | Grid | PINO | PINO+QuadrANN | Mean error change |
|---|---:|---:|---:|---:|
| Sphere | 64^3 | 0.15121 | 0.14875 | -0.00246 |
| Sphere | 128^3 | 0.17857 | 0.17536 | -0.00320 |
| Ellipsoid | 64^3 | 0.23690 | 0.24708 | +0.01018 |
| Ellipsoid | 128^3 | 0.18180 | 0.19201 | +0.01020 |

Negative change means QuadrANN reduced error; positive means it increased error.

## Interpretation

1. There is no large 64-to-128 resolution-specific sign reversal in this controlled comparison. The mean QuadrANN effect is similar at both grids.
2. The average moment effect is family dependent: sphere improves modestly; ellipsoid degrades modestly on this three-seed/single-geometry-per-seed diagnostic.
3. Diagnostic Jacobian error improves in all four family/resolution groups.
4. Seed-level outcomes are heterogeneous. The mean does not justify unconditional QuadrANN activation.
5. Proposal weights remain positive and dense; mean effective sample size is about 292–299 of 512 PINO quadrature nodes, with CV about 0.84–0.87. This does not indicate catastrophic collapse of the mapped proposal.

## Critical P24 acceptance finding

P24's original model_r_rel compared the augmented model output to the initial pure-PINO output. It did not compare the augmented prediction to the independent hard-cut integral. Therefore a useful correction to the PINO prediction could be rejected solely because it moved away from the baseline prediction. P24.6 replaces that test with current-model versus current independent hard-cut consistency, while retaining the independent cut-conservation and material-shape constraints.

## Limits

- These are analytic P0 and cell-centered voxel hard-cut references, not W2/Cherchi continuous Boolean integration.
- One sphere and one ellipsoid per seed are diagnostic samples, not a broad CAD generalization study.
- Jacobians remain diagnostic-only; no Newton admission.
- No FEM/FEA, printability, physical millimeter wall, or 512^3 claim.
- QuadrANN remains optional and is not promoted to production default.
