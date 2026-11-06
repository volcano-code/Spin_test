# Spin-PINO M8 — Transolver++ auxiliary adapter tournament

Date: 2026-11-06
Workflow: [42212744843](https://github.com/volcano-code/Spin_test/actions/runs/42212744843)
Implementation commit: `21e8bbf584a96e0827922b6d17a2c8f53abbf57c`
Artifact ID: `13498934052`
Upstream: `thuml/Transolver_plus@d5a23bc734a0ebac56384cf72049a26af9673452` (MIT)

## Adapter design

Ported `Physics_Attention_1D_Eidetic` and `Transolver_plus_block` into an auxiliary geometry-token branch. The P-CRAFT PINO UFNO3d trunk and Spin moment head remain primary. The adapter output is fused by a zero-initialized trainable residual gate; the initial function is exactly PINO-only.

## Same-data three-seed results

| Model | Parameters | Training seconds | Unrotated r/J rel L2 | SO(3) r/J rel L2 | Combined SO(3) score |
|---|---:|---:|---:|---:|---:|
| PINO-only | 21,888 | 1.90 | 0.20602 / 0.31466 | 0.37123 / 0.44952 | 0.410375 |
| PINO + Transolver++ adapter | 40,731 | 6.78 | 0.20522 / 0.31405 | 0.37090 / 0.44936 | 0.410130 |

## Decision

**Do not promote Transolver++ into the default Spin-PINO v1 configuration.** The SO(3) combined score improves by only ~0.06%, while parameter count increases ~86% and CPU training time increases ~3.6×. The learned residual gate remains close to zero (mean -0.0183), consistent with the plugin contributing little useful information on this task.

Keep the adapter and MIT provenance as an optional ablation. This is a useful negative result: a strong PDE geometry-attention module does not automatically help a PINO whose task is coefficient-conditioned ten-moment integration.

## Next direction

Prioritize PINO-specific rotation covariance consistency (M7c) and PINO training strategies (PI-CViT/HyPINO/TensorPILS method transfer) over further backbone/attention stacking. GeoTransolver remains a paper/code candidate, but the current PhysicsNeMo main dependency floor (Python >=3.11, torch >=2.13) is incompatible with the pinned W6 CI environment (Python 3.10, torch 2.5.1).

## Limits

Analytic continuum P0 only; no W2/Cherchi labels, arbitrary quadric certification, Newton admission or real Spin end-to-end acceleration.
