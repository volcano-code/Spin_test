# W6 P25.3 — Conditional QuadrANN policy implementation status

## Implementation

- Added `p25_3_quadrann_policy.py`: a fail-closed policy engine.
- Added seven unit tests covering validated receipt admission, family exclusion,
  high-risk PINO-only routing, OOD exact fallback, target mismatch, and
  caller-required exact execution.
- Added CI workflow `.github/workflows/w6-p25-3-quadrann-conditional-policy.yml`.
- Protocol: `P25_3_PROTOCOL.md`.

## CI evidence

Workflow: https://github.com/volcano-code/Spin_test/actions/runs/42587170313  
Conclusion: SUCCESS. The policy-contract job passed.

## Routing contract

| Condition | Route |
|---|---|
| Independent validation receipt absent/not VALIDATED | PINO_ONLY |
| Receipt target is not hardcut | PINO_ONLY |
| Geometry family not admitted by independent receipt | PINO_ONLY |
| Admitted family + calibrated hardcut UQNO upper bound within tolerance | PINO_PLUS_QUADRANN |
| UQNO predicts high QuadrANN risk | PINO_ONLY |
| UQNO reports OOD/invalid features | EXACT_FALLBACK |
| Caller explicitly requires exact evaluation | EXACT_FALLBACK |

## Promotion status

No geometry family is production-admitted. P24.7's three geometries per
family are hypothesis-generating only and cannot create a validation receipt.
P25.1b expanded calibration has not completed: in workflow run
42582167200, seeds 271 and 277 were cancelled and seed 281 remained in
progress at the last check. No expanded calibration report or checkpoint
is available from that run.

Therefore the policy engine is implemented and its routing contracts pass,
but QuadrANN conditional activation is not yet validated for production.
PINO-only remains the safe default; exact fallback remains caller supplied.

## Next gate

1. Complete P25.1b signal collection for all three model seeds.
2. Train separate hardcut and analytic-P0 UQNO predictors.
3. Evaluate geometry-simultaneous 90%/95% coverage on untouched geometries.
4. Evaluate fallback fraction and unsafe acceptance at predeclared tolerances.
5. Produce an independent family-admission receipt only if the hardcut
   predictor meets its coverage/unsafe-acceptance criteria.
6. Only then use P25.3 to activate QuadrANN on admitted families.

## Scope limits

No Cherchi certification, Newton admission, FEM/FEA, physical printability,
512^3, or end-to-end Spin-it speed claim is made.
