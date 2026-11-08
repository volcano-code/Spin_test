# W6 P24.6 — Truth-based native-128 QuadrANN physical gate

## Motivation

P24 used `model_r_rel` to compare the augmented PINO prediction against the initial pure-PINO prediction. This is a baseline-output preservation constraint, not an accuracy test. P24.5 showed that QuadrANN can move the prediction closer to or farther from the independent hard-cut reference depending on seed and geometry family. A correction toward the independent reference could therefore be rejected by the old P24 test.

## Corrected acceptance definition

For current density rho and coefficients c:

- `r_model = PINO_or_QuadrANN(rho,c)`
- `r_cut = independent_cell_centered_hard_cut(rho,c)`
- `E_model = relative_L2(r_model, r_cut)`
- `E_cut = relative_L2(r_cut, r_cut_initial)`
- `E_shape = normalized_full_material_9moment_L2(rho,rho_initial)`

A candidate update is feasible iff:

1. `E_model <= E_model_initial_pure_PINO + 0.005` (no more than 0.5 percentage points of model-vs-hardcut error regression);
2. `E_cut <= 0.02`;
3. `E_shape <= 0.02`;
4. the protected outer shell remains exactly unchanged.

The model-vs-hardcut check is now against the current independent hard-cut integral, not the baseline model output. The independent cut-conservation and material-shape thresholds remain unchanged at 2%.

## Fixed experiment

- Matched P14/P23 seeds: (271,883), (277,887), (281,991).
- Native 128^3 input and P-CRAFT Fourier grid.
- P-CRAFT PINO frozen; optional P23 QuadrANN frozen; only DensiCrafter density logits train.
- Same analytic P0 sphere geometry per matched seed, same initialization, six updates and learning rate 0.06.
- Preserve all accepted/rejected line-search steps and final tensor artifacts.
- Aggregate three seeds; no production promotion unless all three seeds pass and show a positive feasible design.

## Limits

Analytic P0 and independent voxel hard-cut only; no Cherchi/W2, no native Newton, no FEM/FEA, no physical millimeter wall, no printability or 512^3 claim.
