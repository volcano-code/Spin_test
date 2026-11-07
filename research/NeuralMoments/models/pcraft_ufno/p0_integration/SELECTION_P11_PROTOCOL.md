# W6 P11: selected GINO + QuadrANN + UQNO, PINO remains sole backbone

Source W6 branch HEAD at start: `61583ee543e6db7372af5dae52dd47a839bfc9b5`.
All P0 upstream pins/third-party notice files stay unmodified.

## Implementation
- `selected_pino.py`: the original pinned NeuralOperator **GINO**
  encoder proposes a bounded, trainable positive adjustment to PINO's
  *existing quadrature node weights*. W6's pinned MIT QuadrANN core
  independently proposes a nonnegative geometry-only node weighting.
- **Only the existing P-CRAFT PINO moment_from_weights and
  jacobian_from_weights** evaluate the cut c. The correction weights are
  geometry-only, not coefficient-dependent, so model derivative equations
  remain unchanged by construction. No new geometry adapter can invent
  material at a zero-support PINO node.
- Optional **original UQNO** wrapper retains the PINO mean and predicts
  a ten-channel positive uncertainty scale. A geometry-ID-aware conformal
  calibration rejects training/calibration identity overlap and groups all
  coefficient queries of one geometry before scoring, avoiding false
  independence.
- `MomentQuadratureResult` does not expose model J because P0 adapters
  lack W0/W2/Cherchi-certified material differentiability. A separate
  `diagnostic_model_jacobian` is for research *only*.
- No exact Cherchi runtime is supplied here. A decision to fall back
  requests an exact evaluation but does not claim one was performed.

## Tests / promotion criteria
1. Instantiate official GINO via pinned NeuralOperator and vetted
   QuadrANN source in the *same* PINO composition, UQNO optional.
2. Verify all gates initialized at zero give bit-exact r/J compared
   with original PINO and positive residual scale.
3. With active gates, quadrature remains nonnegative, complement
   and projective radial identities of the PINO head still pass.
4. Validate groupwise conformal leakage prevention, finite-sample
   calibration size and *no Newton admission under any calibration*.
5. Benchmark one-seed small analytic P0 fit/validation/test to collect
   experimental inference and risk statistics. Experimental upstream
   adapters remain **untrained** at this step; no held-out accuracy
   improvement can be claimed from mere fusion or random gates.

## Next stage
Freeze this experimental port, then train one upstream adapter at a
time with identical P0 teacher/split/step budgets and predeclared new
geometry held-out tests. Do not promote if cold/warm time or accuracy
regresses. The original PINO baseline and exact fallback stay primary.
