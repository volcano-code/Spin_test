# W6 P25.5 — Query-marginal UQNO calibration

## Evidence

- Source workflow: [Run 42773823319](https://github.com/volcano-code/Spin_test/actions/runs/42773823319)
- Source commit: `a19e5082c159d66f9176fde6ce156f2e9c0bbcb9`
- Frozen input: P25.1 nine-shard collection, 2,880 source rows
- Aggregated samples: 960 geometry/query/resolution cases
- Unique geometries: 240
- Geometry-disjoint split: 125 train / 56 calibration / 59 test geometries
- Test rows: 236
- Feature dimension: 349
- Both model checkpoints and reports were downloaded from the successful Actions artifact and inspected.

## P25.5 calibration design

The former gate used a geometry-level maximum standardized residual for every query and resolution belonging to a geometry. This is appropriate for simultaneous geometry-level protection, but it produced very wide upper bounds and 100% fallback at all previously tested tolerances.

P25.5 adds a separate one-sided query-marginal upper bound:

`U(x)=\exp(\hat\mu_{\log e}(x)+q_{1-\alpha})`

where `q` is the finite-sample quantile of positive log-error residuals `max(0, log(e)-mu)` on the calibration partition. Train/calibration/test geometry IDs remain disjoint.

**Interpretation boundary:** this is a marginal-query pilot, not simultaneous coverage of every query/resolution for a whole geometry. Multiple queries from the same geometry are clustered; empirical test coverage is reported, but it must not be represented as a formal independent-query guarantee or production certification.

The geometry-calibrated OOD gate remains active and forces exact fallback for out-of-envelope inputs.

## Actual P25.5 CI results

Calibration residual quantiles:

| Target | q90 | q95 |
|---|---:|---:|
| Voxel hard-cut error | 0.7535 | 0.9390 |
| Analytic P0 error | 0.7240 | 0.8944 |

Per-query fallback results from the held-out 236 test rows:

| Error tolerance | Hard-cut fallback | Analytic P0 fallback |
|---|---:|---:|
| 0.10 | 92.37% | 98.31% |
| 0.20 | 66.53% | 60.17% |
| 0.30 | 43.64% | 36.02% |
| 0.50 | 25.85% | 21.61% |
| 1.00 | 8.05% | 6.36% |

Unsafe acceptance among accepted test queries:

| Error tolerance | Hard-cut | Analytic P0 |
|---|---:|---:|
| 0.10 | 5.56% (1/18) | 0% (0/4) |
| 0.20 | 1.27% (1/79) | 1.06% (1/94) |
| 0.30 | 0.75% (1/133) | 1.32% (2/151) |
| 0.50 | 0% (0/175) | 0% (0/185) |
| 1.00 | 0% (0/217) | 0% (0/221) |

These are empirical rates on one held-out test partition; denominators are modest and should be accompanied by confidence intervals in later acceptance work.

Post-run audit of the archived model weights and test cases gave marginal 95% upper-bound coverage:

| Geometry family | Hard-cut | Analytic P0 |
|---|---:|---:|
| Box | 96.67% (58/60) | 91.67% (55/60) |
| Sphere | 92.50% (74/80) | 100% (80/80) |
| Ellipsoid | 95.83% (92/96) | 98.96% (95/96) |
| Overall | 94.92% (224/236) | 97.46% (230/236) |

This family breakdown is a post-run calculation from the archived checkpoint and report; it is not yet a gate in the CI workflow. The Box analytic and Sphere hard-cut gaps motivate P25.5l family-level coverage diagnostics.

## Baseline comparison

| Target | Model | Risk Spearman | AURC | Absolute-error MAE |
|---|---|---:|---:|---:|
| Hard-cut | Ridge | 0.6773 | 0.09575 | 0.09853 |
| Hard-cut | UQNO | 0.7690 | 0.08925 | 0.07727 |
| Analytic P0 | Ridge | 0.7053 | 0.09084 | 0.09889 |
| Analytic P0 | UQNO | 0.7920 | 0.08494 | 0.05831 |

UQNO improves both risk ordering and median-error prediction over the train-only Ridge baseline on this held-out split. It remains a reliability head; P-CRAFT PINO remains the moment-prediction backbone.

## Decision

- P25.5 query-marginal gate: **pilot evidence improved; not production-approved**.
- Geometry-simultaneous gate: still conservative and must remain separately identified.
- Cherchi teacher, native Newton correction, and 512^3 evaluation: not completed by this milestone.
- Next: add family-specific empirical coverage to the gate report, add confidence intervals / repeated geometry-held-out seeds, then evaluate real end-to-end runtime and fallback cost before P26 admission.
