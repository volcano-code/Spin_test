# W6 P25.7 — repeated geometry split and training seed audit

## CI evidence

- Workflow: [Run 42774854590](https://github.com/volcano-code/Spin_test/actions/runs/42774854590)
- Result: all steps passed.
- Source data: frozen nine P25.1 shards, 2,880 rows, 240 geometries, 960 aggregated geometry/query/resolution cases.
- Six experiment configurations; twelve checkpoints archived.

## Split sensitivity

| Configuration | Train / calibration / test geometries | Hard-cut 95% query coverage | Analytic P0 95% query coverage |
|---|---:|---:|---:|
| Split 0, seed 0 | 125 / 56 / 59 | 100% | 100% |
| Split 1, seed 0 | 136 / 58 / 46 | 100% | 100% |
| Split 2, seed 0 | 147 / 50 / 43 | 97.67% | 97.67% |
| Split 0, seed 100 | 125 / 56 / 59 | 100% | 100% |
| Split 0, seed 200 | 125 / 56 / 59 | 100% | 100% |
| Split 0 repeat | 125 / 56 / 59 | 100% | 100% |

The split-2 test coverage is lower. This indicates geometry partition sensitivity and supports repeating more geometry splits before any production gate claim.

## Initialization sensitivity with fixed Split 0

| Target | Metric | Seed 0 | Seed 100 | Seed 200 |
|---|---|---:|---:|---:|
| Hard-cut | Median-error MAE | 0.07727 | 0.07574 | 0.07624 |
| Hard-cut | Query q95 | 0.93897 | 0.98396 | 0.88482 |
| Analytic P0 | Median-error MAE | 0.05831 | 0.05954 | 0.05919 |
| Analytic P0 | Query q95 | 0.89443 | 0.89055 | 0.90139 |

The point-prediction metrics vary modestly across initializations. Calibration quantiles also move, so the threshold itself must be treated as part of model variability.

## Deterministic repeat

The same Split 0 / Seed 0 configuration was executed twice.

- Hard-cut checkpoint SHA-256 matched exactly.
- Analytic P0 checkpoint SHA-256 matched exactly.
- Test median-error MAE matched exactly for both targets.

Thus the CPU pipeline is reproducible under the pinned runtime and current implementation.

## Decision

- P25.7: **PASS** for repeatability and split-sensitivity audit.
- UQNO: retain as pilot uncertainty/risk head.
- Production gate: not approved.
- Main issue: geometry split sensitivity remains; family-conditional calibration is the next targeted improvement.
- P-CRAFT PINO remains the primary moment predictor.
