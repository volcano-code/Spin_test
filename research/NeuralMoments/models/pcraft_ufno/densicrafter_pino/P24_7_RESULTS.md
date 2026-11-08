# W6 P24.7 — Multi-geometry QuadrANN generalization results

Run: https://github.com/volcano-code/Spin_test/actions/runs/42479034389  
All three seed jobs and the aggregate job completed successfully.  
Aggregate artifact: 13616693320.

## Protocol

- Three matched P14/P23 model pairs: (271,883), (277,887), (281,991).
- Geometry families: box, sphere, ellipsoid.
- Three geometry instances per family and seed.
- Resolution pairs: 64^3 and 128^3 with identical geometry IDs.
- Total: 3 seeds x 3 families x 3 geometries x 2 resolutions = 54 geometry-resolution observations.
- Analytic labels are vertical-cut continuum P0 only.
- Independent cell-centered voxel hard-cut moments are reported separately.
- No material optimization, Cherchi, Newton or FEM/FEA is included.

## Three-seed aggregate means

All entries are relative L2 errors; lower is better. Delta is QuadrANN minus PINO; negative means improvement.

| Family | Grid | PINO r analytic | PINO+Q r analytic | Delta | PINO J | PINO+Q J | Delta J |
|---|---:|---:|---:|---:|---:|---:|---:|
| Box | 64^3 | 0.21922 | 0.19577 | -0.02344 | 0.21007 | 0.18256 | -0.02751 |
| Box | 128^3 | 0.21460 | 0.19180 | -0.02280 | 0.20477 | 0.17846 | -0.02631 |
| Sphere | 64^3 | 0.13606 | 0.13627 | +0.00020 | 0.23307 | 0.19744 | -0.03563 |
| Sphere | 128^3 | 0.14139 | 0.14352 | +0.00214 | 0.22831 | 0.19253 | -0.03578 |
| Ellipsoid | 64^3 | 0.12104 | 0.11566 | -0.00537 | 0.19311 | 0.15465 | -0.03845 |
| Ellipsoid | 128^3 | 0.12119 | 0.11970 | -0.00149 | 0.18626 | 0.14812 | -0.03814 |

## Independent voxel hard-cut results

| Family | Grid | PINO hard-cut error | PINO+Q hard-cut error | Delta |
|---|---:|---:|---:|---:|
| Box | 64^3 | 0.20055 | 0.17960 | -0.02094 |
| Box | 128^3 | 0.19477 | 0.17380 | -0.02096 |
| Sphere | 64^3 | 0.13373 | 0.14418 | +0.01045 |
| Sphere | 128^3 | 0.14633 | 0.15537 | +0.00904 |
| Ellipsoid | 64^3 | 0.12062 | 0.13155 | +0.01093 |
| Ellipsoid | 128^3 | 0.11316 | 0.12649 | +0.01333 |

## Interpretation

1. Jacobian diagnostic error improves in all six family/resolution groups.
2. Box moment error improves consistently against both analytic P0 and the independent voxel hard-cut reference.
3. Sphere moment error is nearly neutral against analytic P0 but degrades against voxel hard-cut.
4. Ellipsoid analytic-continuum moment error improves slightly on average, but voxel hard-cut error degrades.
5. This analytic-vs-discrete discrepancy is material: continuum P0 and cell-centered voxel hard-cut are different targets because the voxel geometry is a sampled approximation of the analytic solid. They must not be conflated.
6. The three-seed mean conceals seed-level heterogeneity. Conditional activation is plausible, but this report does not define a validated gate.
7. Proposal effective sample size is about 293–345 of 512 nodes; normalized entropy is about 0.946–0.963. There is no evidence of catastrophic proposal collapse.

## Decision

- Keep P-CRAFT PINO as the primary moment/Jacobian backbone.
- Keep QuadrANN optional and fail-closed.
- Do not promote it to a global default.
- P24.7 supports family-conditional behavior and motivates P25 uncertainty calibration.
- Any learned activation rule must be trained/calibrated on geometry-disjoint data and evaluated on untouched test geometries.

## Limitations

- Only three geometry instances per family per seed.
- Only vertical cut planes have analytic P0 labels.
- The independent voxel hard-cut integral is discrete and is not W2/Cherchi continuous Boolean integration.
- Jacobian values remain diagnostic-only; no Newton admission.
- No FEM/FEA, physical printability, millimeter wall, 256^3/512^3 or end-to-end Spin-it speed claim.
