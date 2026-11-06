# Spin-PINO v1 — PINO-first model

Primary model: P-CRAFT UFNO3d / F-FNO factorized Fourier backbone, adapted to Spin's ten raw moments.

- `pino_backbone.py`: source-pinned P-CRAFT UFNO3d-style factorized spectral U-shaped encoder.
- `spin_pino.py`: geometry-conditioned positive quadrature weights, smooth convex moment potential, ten moments and analytic coefficient Jacobian.
- `SpinPINOLoss`: data term plus moment-specific physics identities. The original elasticity equilibrium/constitutive PINO losses are not reused because they do not describe Spin's moment integral.
- `tests/test_spin_pino.py`: CPU smoke and mathematical identity tests.

Borrowed GINO, Transolver, QuadrANN, UQNO, NQR, fVDB and DensiCrafter components are optional plug-ins or baselines. None replaces the PINO trunk.

See `PINO_CORE_SOURCE_AUDIT.md` and `SPIN_PINO_30DAY_PLAN.md` at the parent model directory for provenance, scope and the 30-day exit criteria.

Current status: first implementation slice added; CI validation pending. Not trained on W2/Cherchi labels and not admitted to native Newton.
