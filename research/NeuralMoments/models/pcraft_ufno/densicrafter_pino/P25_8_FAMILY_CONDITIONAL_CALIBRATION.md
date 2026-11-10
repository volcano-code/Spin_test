# W6 P25.8 — family-conditional UQNO calibration

## Reproducible evidence

- Full calibration/evaluation workflow: [Run 42780445015](https://github.com/volcano-code/Spin_test/actions/runs/42780445015) — success.
- Gate contract workflow: [Run 42780445237](https://github.com/volcano-code/Spin_test/actions/runs/42780445237) — success.
- Frozen source: P25.1 nine shards, 2,880 rows; 240 unique geometries; 960 aggregated geometry/query/resolution cases.
- Split 0: 125 train / 56 calibration / 59 test geometries; 236 test query rows.
- Both trained UQNO checkpoints, calibration report, gate report and baseline report were downloaded and inspected.

## Method

P25.8 adds family-conditional one-sided query-marginal residual quantiles for Box, Sphere and Ellipsoid. The model weights and PINO moment-prediction backbone are unchanged in role; only the uncertainty calibration and gate selection become family-aware.

For each family, calibration rows are restricted to the calibration geometries of that family. A family with fewer than eight calibration geometries falls back to the global query quantile. A conservative floor prevents a family quantile from shrinking below the global quantile:

`q_f = max(q_global, q_family)`

This can widen a family interval but cannot make it narrower than the previous global query bound. It is a conservative heuristic for subgroup stability, not a guarantee against distribution shift.

## Calibration sample sizes and q95

| Target | Family | Calibration geometries | Calibration query rows | Family q95 | Applied q95 |
|---|---|---:|---:|---:|---:|
| Hard-cut | Box | 19 | 76 | 1.0968 | 1.0968 |
| Hard-cut | Ellipsoid | 17 | 68 | 0.7703 | 0.9494 |
| Hard-cut | Sphere | 20 | 80 | 0.9520 | 0.9520 |
| Analytic P0 | Box | 19 | 76 | 1.2654 | 1.2654 |
| Analytic P0 | Ellipsoid | 17 | 68 | 0.8391 | 0.8905 |
| Analytic P0 | Sphere | 20 | 80 | 0.7024 | 0.8905 |

The global q95 floors are 0.9494 for Hard-cut and 0.8905 for Analytic P0.

## Held-out test results

Empirical upper-bound coverage among in-domain test queries:

| Family | Hard-cut | Analytic P0 |
|---|---:|---:|
| Box | 96.55% | 100.00% |
| Ellipsoid | 94.79% | 100.00% |
| Sphere | 92.41% | 100.00% |
| Overall | 94.42% | 100.00% |

At error tolerance 0.30:

| Metric | Hard-cut | Analytic P0 |
|---|---:|---:|
| Query fallback fraction | 49.15% | 42.37% |
| Accepted queries | 120 / 236 | 136 / 236 |
| Unsafe accepted queries | 1 / 120 (0.83%) | 0 / 136 (0%) |
| In-domain upper-bound coverage | 94.42% | 100.00% |

The family-conditional method improves the weakest Analytic P0 subgroup in this split, but Hard-cut Sphere remains below nominal 95% empirical coverage. The overall Hard-cut coverage is 94.42%, so the gate is still pilot-only.

## Stability and reproducibility

P25.7 repeated experiments showed exact checkpoint reproducibility for the same split/seed configuration. Different geometry splits moved query coverage and error metrics more than changing the initialization on a fixed split. P25.8 does not remove that split sensitivity; it makes subgroup calibration explicit and auditable.

## Decision

- P25.7 repeatability audit: PASS.
- P25.8 family-conditional calibration implementation and CI: PASS.
- UQNO production gate: **not approved**.
- Keep PINO as the primary moment predictor; UQNO remains a family-aware uncertainty head.
- The current gate is still based on the P25.1 synthetic Box/Sphere/Ellipsoid pilot set. It does not establish generalization to unseen shape families, 512^3, or the actual Cherchi/Newton exact fallback runtime.
- Next: add a second geometry-generation campaign and more held-out families, then benchmark end-to-end wall time and fallback cost with a real exact backend. Do not label the current caller-supplied voxel hard-cut callback as Cherchi.
