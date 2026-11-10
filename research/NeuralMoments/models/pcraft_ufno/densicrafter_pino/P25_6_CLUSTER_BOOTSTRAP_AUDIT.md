# W6 P25.6 — Geometry-cluster bootstrap audit

## Reproducible CI evidence

- Workflow: [Run 42774416874](https://github.com/volcano-code/Spin_test/actions/runs/42774416874)
- Source commit: `c9657a584b851d281b3ee9c24528bfa4b4692a1f`
- Result: all workflow steps passed, including UQNO contract tests, baseline tests, marginal-query gate tests, frozen-data verification, retraining, gate evaluation, baseline comparison and artifact upload.
- Bootstrap: 2,000 geometry-cluster resamples, deterministic seed 20261110.
- Test set: 59 held-out geometries, 236 query rows.

## P25.6 results at error tolerance 0.30

| Metric | Hard-cut | Analytic P0 |
|---|---:|---:|
| Query fallback fraction | 47.03% | 35.17% |
| Geometry-bootstrap 95% CI | 38.98%–55.08% | 27.12%–44.07% |
| Unsafe acceptance fraction | 0.80% | 1.31% |
| Geometry-bootstrap 95% CI | 0%–2.63% | 0%–3.36% |
| Empirical upper-bound coverage (in-domain) | 93.99% | 97.85% |
| Geometry-bootstrap 95% CI | 89.08%–97.86% | 95.61%–99.57% |

The confidence intervals resample whole geometries, not individual query rows, to preserve within-geometry dependence. They quantify test-sample uncertainty conditional on this fitted model and this calibration split; they do not account for model retraining, a new data collection campaign, or distribution shift.

## Geometry-family coverage at tolerance 0.30

| Family | Hard-cut coverage (95% cluster CI) | Analytic P0 coverage (95% cluster CI) |
|---|---:|---:|
| Box | 94.83% (86.54%–100%) | 91.38% (82.76%–98.28%) |
| Ellipsoid | 94.79% (85.42%–100%) | 100% (100%–100%) |
| Sphere | 92.41% (84.81%–98.73%) | 100% (100%–100%) |

The analytic P0 Box family remains the clearest calibration weakness. Family sample sizes are small, so the wide intervals must be retained rather than treating point estimates as precise.

## Reproducibility note

A separate P25.5 run (Run 42774166552) and this P25.6 run both passed. Their point metrics differ slightly despite the same nominal training seed and frozen input. This run-to-run drift must be investigated with repeated deterministic training and split audits before any production claim.

## Decision

- P25.6: **cluster-bootstrap audit implemented and CI passed**.
- UQNO: retain as a pilot risk head; P-CRAFT PINO remains the primary moment predictor.
- Production gate: **not approved**.
- Next work: repeat geometry-disjoint splits/training seeds, investigate run-to-run drift, improve the Analytic P0 Box subgroup, and benchmark actual PINO + UQNO + exact-fallback runtime. Cherchi/Newton and 512³ remain outstanding.
