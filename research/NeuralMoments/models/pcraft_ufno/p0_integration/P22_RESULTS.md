# W6 P22 — Original NeuralOperator GINO as optional residual around P-CRAFT PINO

Run: https://github.com/volcano-code/Spin_test/actions/runs/42460854472
Result: SUCCESS; 5 GINO/PINO contract tests passed; 40 training updates.
Artifact ID: 13610010674.
Artifact SHA256: `7002b627b44c8d16edb3e41cb32b65609342d4a59158ae07e8f0c5dc9260b864`.

## Provenance and architecture

- Upstream NeuralOperator GINO commit
  `a6648eeeb60fe0837f2d7d021517a945a159a0c8`, MIT license preserved.
- P14 trained 64³ P-CRAFT SpinPINO seed 271, strict loaded and frozen.
- Original GINO encoder is used to produce a geometry code from a
  deterministic 64-point geometry/material feature cloud.
- GINO correction and zero-initialized scalar residual gate modify only
  positive PINO quadrature weights. PINO remains the sole ten-moment
  and coefficient-Jacobian backbone.
- 11,873 GINO/gate trainable parameters; training seed 887, 40 steps,
  batch 2, Adam lr 5e-4; best validation step 40.
- Analytic P0 boxes/spheres for fit/validation, held-out ellipsoid family.
- Gate selected: -0.0055030. Negative sign is a learned residual direction,
  not a failure; zero gate remains exact pure-PINO parity.

## Held-out ellipsoid results

| Metric | Pure PINO | PINO + GINO | Relative improvement |
|---|---:|---:|---:|
| Ten raw moments relative L2 | 0.107520 | 0.104518 | 2.79% |
| Jacobian relative L2 | 0.209245 | 0.206885 | 1.13% |

- Validation r relative L2: 0.166841 → 0.164898.
- Validation J relative L2: 0.176232 → 0.175415.
- Negative predicted mass fraction: zero for both.
- Training time: 72.82 s; peak RSS about 1.23 GiB.

## Decision

GINO has a small positive single-seed signal, much weaker than the
P21 QuadrANN signal. Keep it as an optional candidate for multi-seed
testing; do not promote it to the default. The two experiments use
different training seeds/splits, so their raw scores are not a
controlled head-to-head comparison.

No Cherchi supervision, continuous CAD certification, native Newton,
FEM/FEA, millimeter wall or 512³ claim is made.
