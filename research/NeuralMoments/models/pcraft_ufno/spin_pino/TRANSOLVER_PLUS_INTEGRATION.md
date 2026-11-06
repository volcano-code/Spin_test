# M8 — Transolver++ auxiliary adapter inside Spin-PINO

## Decision

Use the standalone MIT Transolver++ eidetic physical-state attention as an optional geometry-feature adapter. It does not replace P-CRAFT PINO. The primary UFNO3d trunk, Spin moment head, support-masked positive quadrature and PINO loss remain the core model.

## Upstream provenance

- Repository: https://github.com/thuml/Transolver_plus
- Commit: `d5a23bc734a0ebac56384cf72049a26af9673452`
- Source: `models/Transolver_plus.py` (`0fd97ae9a570ee500556929ce47d918f8bef9473`)
- License: MIT (`83787cb894a379be3f9babe7e701d5e7d338ec9f`)
- Reused components: `Physics_Attention_1D_Eidetic`, `Transolver_plus_block`.

## W6 adapter

1. Flatten the same four-channel canonical voxel geometry into point tokens and append xyz positions.
2. Apply a small input projection and Transolver++ eidetic physical-state attention blocks.
3. Pool mean/max token features and project to the P-CRAFT PINO latent dimension.
4. Fuse as `h = h_PINO + tanh(g) * h_TransolverPlus`, with `g=0` at initialization.
5. Feed the fused latent into the existing PINO support-masked positive quadrature head.

The zero gate guarantees the initial forward function is exactly PINO-only. Training can open the residual gate if the plugin improves the objective.

## Why standalone Transolver++ rather than current PhysicsNeMo GeoTransolver

PhysicsNeMo is Apache-2.0 and offers GeoTransolver with GALE attention, structured-grid support and an optional Transolver++/FLARE++ path. However, the currently audited PhysicsNeMo main pyproject requires Python >=3.11 and torch >=2.13, while W6 CI is pinned to Python 3.10 and torch 2.5.1. Upgrading the whole framework would destabilize the one-month W6 environment. Therefore M8 uses the standalone MIT Transolver++ code and leaves GeoTransolver as a later optional comparison.

## M8 experiment

Compare:
- PINO-only logistic-atom baseline.
- P-CRAFT PINO + gated Transolver++ geometry adapter.

Same analytic geometry-family splits, seeds 131/137/139, 120 steps, batch size 8, 8^3 geometry input, 6^3 midpoint atoms, smoothing 0.02 and identical arbitrary-SO(3) held-out transforms.

Report ten-moment r/J MAE and relative L2, parameter count, training time, unrotated and SO(3) test results. Promote only if the plugin improves accuracy or rotation robustness enough to justify added parameters/latency.

## Limits

All labels remain analytic continuum P0, not Cherchi. This plugin does not certify Jacobians or enable Newton. No CFD checkpoint or learned PDE weights are transferred; only the original attention mechanism and block structure are reused.

## M8 result — 2026-11-06

The CPU adapter tests and three-seed matched tournament passed in workflow [42212744843](https://github.com/volcano-code/Spin_test/actions/runs/42212744843).

- PINO-only: 21,888 parameters; 1.90 s mean CPU training; SO(3) r/J relative L2 0.37123/0.44952.
- PINO + Transolver++: 40,731 parameters; 6.78 s; SO(3) r/J relative L2 0.37090/0.44936.
- Combined SO(3) score improves by only ~0.06%, while parameters rise ~86% and training time ~3.6×.

Decision: retain the MIT adapter as an optional ablation, but do not promote it into default Spin-PINO v1. The P-CRAFT PINO trunk remains primary and the default configuration remains PINO-only.
