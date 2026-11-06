# W6 M7c/M7d/M8 evidence review and promotion decisions

Date: 2026-11-06
Primary backbone: P-CRAFT PINO UFNO3d. All labels in these experiments are analytic continuum P0 vertical-plane labels, not W2/Cherchi.

## M7b: arbitrary SO(3) augmentation

Workflow: https://github.com/volcano-code/Spin_test/actions/runs/42211797282

| Training condition | r rel L2 unrotated | J rel L2 unrotated | r rel L2 SO(3) | J rel L2 SO(3) |
|---|---:|---:|---:|---:|
| No augmentation | 0.206020 | 0.314656 | 0.371231 | 0.449518 |
| Cube augmentation | 0.205555 | 0.314324 | 0.370718 | 0.449004 |
| SO(3) augmentation | 0.205568 | 0.314284 | 0.370660 | 0.448910 |

Conclusion: arbitrary orientation is materially harder than the aligned test, and augmentation alone improves it only marginally. Keep augmentation as a data option, not as a claimed solution.

## M7c: covariance consistency loss

Workflow: https://github.com/volcano-code/Spin_test/actions/runs/42214212548 (job spin-pino-m7c-so3-covariance-loss).
Definition: r(RD,S_R c) ≈ T_R r(D,c), and J(RD,S_R c) ≈ T_R J(D,c) S_R^-1.

| Condition | SO(3) r rel L2 | SO(3) J rel L2 | Combined | CPU training seconds |
|---|---:|---:|---:|---:|
| PINO baseline | 0.371231 | 0.449518 | 0.410375 | 3.11 |
| SO(3) augmentation only | 0.370660 | 0.448910 | 0.409785 | 3.14 |
| covariance loss λ=0.05 | 0.370453 | 0.448698 | 0.409575 | 8.94 |
| augmentation + covariance λ=0.05 | 0.370679 | 0.448915 | 0.409797 | 8.89 |

Conclusion: consistency loss provides only a tiny change and roughly triples CPU training time. Do not promote as default.

## M7d: validation-selected covariance weight sweep

Workflow: https://github.com/volcano-code/Spin_test/actions/runs/42214212548 (job spin-pino-m7d-equivariance-weight-sweep).
Lambda grid: 0, 0.05, 0.2, 0.5, 1.0; three seeds; 300 maximum steps. Lambda selected using validation r_mae + 0.25 J_mae; held-out SO(3) remains confirmatory.

| λ | SO(3) r rel L2 | SO(3) J rel L2 | Combined | Mean train seconds |
|---:|---:|---:|---:|---:|
| 0 | 0.371207 | 0.449489 | 0.410348 | 6.27 |
| 0.05 | 0.370433 | 0.448679 | 0.409556 | 18.82 |
| 0.2 | 0.371296 | 0.449230 | 0.410263 | 18.63 |
| 0.5 | 0.378744 | 0.455744 | 0.417244 | 18.74 |
| 1.0 | 0.384387 | 0.460171 | 0.422279 | 18.76 |

Conclusion: λ=0.05 is nominally best, but the combined SO(3) gain is about 0.00079 absolute for about 3x training cost. This is not a compelling trade-off and should remain an optional ablation, not a default PINO loss.

## M8: Transolver++ as a gated PINO auxiliary adapter

Workflow: https://github.com/volcano-code/Spin_test/actions/runs/42212744843.

| Model | Parameters | SO(3) r rel L2 | SO(3) J rel L2 | Combined | CPU training seconds |
|---|---:|---:|---:|---:|---:|
| PINO only | 21,888 | 0.371231 | 0.449518 | 0.410375 | 1.895 |
| PINO + Transolver++ | 40,731 | 0.370901 | 0.449359 | 0.410130 | 6.784 |

Conclusion: the gated plugin barely changes the score while increasing parameters by about 86% and CPU training time by about 3.6x. Keep the MIT adapter for future ablation, but do not promote it into the 30-day default architecture. PINO remains the trunk.

## M7e next experiment: test-time SO(3) orbit averaging

Rather than adding more training losses, compare one, two and four rotated inference views. For each view, rotate the geometry and native coefficients together, predict moments/Jacobian, transform outputs back to the original frame, and average. Report voxel interpolation mass drift separately. This is a test-time ensemble hypothesis, not exact equivariance or a Newton certificate.

## Scope

No experiment in this report uses Cherchi labels, certifies arbitrary CAD/quadric derivatives, enters Newton or proves real Spin end-to-end speedup.
