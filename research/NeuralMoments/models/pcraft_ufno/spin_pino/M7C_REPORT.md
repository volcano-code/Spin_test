# Spin-PINO M7c — SO(3)-covariance consistency loss

Date: 2026-11-06
Workflow: [42213624290](https://github.com/volcano-code/Spin_test/actions/runs/42213624290)
Artifact ID: `13499623485` (`spin-pino-m7c-so3-covariance.zip`)
CPU tests: **36 passed in 2.59 s**.

## Experiment

Added a paired SO(3) covariance loss using exact transformations of native coefficients, ten raw moments and Jacobians. Four conditions were compared on identical geometry splits, seeds and held-out arbitrary-SO(3) transforms:

1. PINO baseline.
2. SO(3) augmentation only.
3. Covariance consistency loss only (lambda=0.05).
4. SO(3) augmentation + covariance consistency loss (lambda=0.05).

## Three-seed results

| Condition | Fit samples | CPU seconds | Unrotated r/J relative L2 | SO(3) r/J relative L2 | Combined SO(3) score |
|---|---:|---:|---:|---:|---:|
| Baseline | 52 | 1.55 | 0.20602 / 0.31466 | 0.37123 / 0.44952 | 0.410375 |
| SO(3) augmentation | 104 | 1.51 | 0.20557 / 0.31428 | 0.37066 / 0.44891 | 0.409785 |
| Covariance loss only | 52 | 4.02 | 0.20525 / 0.31405 | **0.37045 / 0.44870** | **0.409575** |
| Augmentation + covariance loss | 104 | 4.05 | 0.20569 / 0.31434 | 0.37068 / 0.44891 | 0.409797 |

## Interpretation

- The consistency loss alone improves the combined SO(3) score by only ~0.20% versus baseline, while increasing CPU training time ~2.6×.
- Combining augmentation and consistency loss does not outperform consistency loss alone.
- The improvement is too small to promote lambda=0.05 as the default. Retain it as an optional method ablation.
- The residual orientation gap remains large: SO(3) r/J relative L2 is still about 0.370/0.449.
- The moment-physics residual is already near machine zero due to the parameterization; the limiting factor is geometry-conditioned approximation, not violation of the analytic moment identities.

## Next M7d

Test a controlled lambda sweep (0.1, 0.5, 1.0) and longer training budget on the same splits, with validation-only selection. If no material improvement appears, stop spending time on consistency-loss tuning and prioritize a more intrinsically rotation-aware PINO geometry representation.

## Limits

Analytic continuum P0 vertical-plane cuts only; no W2/Cherchi labels, arbitrary quadric/CAD certification, Newton admission or real Spin end-to-end speedup.
