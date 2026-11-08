# W6 P24.5 — QuadrANN domain/resolution diagnosis

## Motivation

P24 completed three matched native-128 comparisons. The pure P-CRAFT
SpinPINO + DensiCrafter arm accepted all 18 updates. The frozen P23
QuadrANN proposal arm accepted 0/18 updates and failed the predeclared
2% PINO-moment consistency screen in all three seeds. This is a negative
material-design result; it is not evidence that P23's held-out ellipsoid
moment result was invalid.

## Questions

P24.5 isolates two confounders before any QuadrANN retraining:

1. **Geometry-family/domain transfer:** P23 reports held-out ellipsoid
   improvements. P24's design input is a sphere. Compare the same trained
   PINO/QuadrANN checkpoints on analytic sphere and ellipsoid families.
2. **Resolution transfer:** compare each identical analytic geometry at
   64^3 and 128^3. The geometry ID must match across resolutions.

## Fixed protocol

- Matched P14 PINO seed and P23 QuadrANN seed:
  (271,883), (277,887), (281,991).
- Strictly load the matching P14 checkpoint and verify its SHA256 against
  the P23 checkpoint metadata.
- P-CRAFT PINO is the only ten-moment and diagnostic-Jacobian backbone.
- Reuse the original MIT QuadrANN core and its P23-selected gate; freeze it.
- Reproduce P24's initial DensiCrafter material state: protected shell=1,
  interior density=sigmoid(4), occupancy unchanged.
- For each seed, evaluate sphere and ellipsoid at both 64^3 and 128^3.
- Compare PINO and PINO+QuadrANN moments/Jacobians against analytic P0
  continuum labels; report componentwise absolute-error deltas.
- Report positive proposal weight min/max/mean/std/CV, zero fraction,
  normalized entropy and effective sample size.
- Keep original geometry IDs identical across the 64/128 pair.
- Retain per-seed JSON evidence and an aggregate report.

## Interpretation guardrails

- P24.5 is a diagnosis, not a model-promotion experiment.
- Analytic P0 is not W2/Cherchi supervision.
- The model Jacobian remains diagnostic and is not Newton-admitted.
- No FEM/FEA, printability, millimeter-wall, or 512^3 claim is made.
- Do not change the P24 2% feasibility thresholds to make QuadrANN pass.

## Possible follow-up decisions

- If sphere degrades but ellipsoid improves at both resolutions, treat the
  issue as geometry-family conditionality; investigate a fail-closed
  family-aware gate and calibration, not global activation.
- If 128^3 degrades relative to 64^3 for both families, investigate
  resolution-dependent support sampling and scale-aware coordinate
  features before any high-resolution retraining.
- If both families degrade, audit checkpoint loading, proposal semantics,
  and the P23/P24 training objective mismatch before further experiments.
- Any corrected design must repeat matched three-seed P24 feasibility tests.
