# M7d — Validation-selected SO(3) covariance-loss weight sweep

## Purpose

M7c showed only a small gain at lambda_equivariance=0.05. M7d tests whether the consistency loss was simply underweighted.

## Conditions

- lambda_equivariance: 0.0, 0.05, 0.2, 0.5, 1.0.
- Three seeds: 131, 137, 139.
- 300 optimizer steps, batch size 8.
- P-CRAFT PINO logistic-atom head; no generic geometry adapter.
- Same analytic geometry-family splits and deterministic arbitrary-SO(3) held-out transforms.

## Selection protocol

Choose lambda using mean validation `r_mae + 0.25 * J_mae` only. The held-out SO(3) test is confirmatory and must not be used for hyperparameter selection.

Report unrotated and SO(3) r/J relative L2, selected steps, CPU training time, final covariance residual and parameter count.

## Decision gate

Promote a nonzero lambda only if it produces a meaningful validation improvement and confirms a rotated-test improvement without unacceptable unrotated regression or excessive runtime. If not, stop tuning this loss and move to an intrinsically rotation-aware PINO geometry representation.

All labels remain analytic continuum P0; no W2/Cherchi, arbitrary CAD/quadric or Newton admission is implied.
