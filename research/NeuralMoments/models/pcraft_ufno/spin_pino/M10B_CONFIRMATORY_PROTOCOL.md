# W6 M10b/32 confirmatory CPU experiment

Date: 2026-11-07. Frozen parent W6 M10b source: 0226582d176126fd5fbd7907f462c8cd3a882457.
This is a *separate independent experiment*, not silent replacement of
the 16^3 first pilot. No hyperparameter adjustment after reading test results.

## Predetermined follow-up
- Source cell-centered analytic P0 voxel samples: 32^3, P-CRAFT U-FNO
  factorized trunk: fixed coarse 8^3, optional detail levels 8 and 32.
- Two training families: boxes+spheres, 12 unique instances each.
  Geometry identity disjoint validation (3 each) and fit (9 each).
- Entire held-out test family: 8 distinct ellipsoids.
- Two native vertical cut controls per geometry (and exact analytic r/J).
- Three independently seeded data splits and model init: 131,137,139.
- Three arms: baseline PINO, PINO+fine ten-moment summary, PINO+local
  sparse multiscale features; the last two have identical allocated
  parameters. Same P-CRAFT PINO initialization, label counts, optimizer
  observations/updates (180) and validation-only model selection for all.
- Report per seed full r/J metrics and process peak RSS, training/encoding
  and query timing, exact source content digest and failure counts.
- Guard against the limitation of previous 60-step runs, whose best
  augmented-arm checkpoint occurred at the budget limit.
- No complete 512^3 trained PINO, no fVDB/FIGConv source and no
  native Cherchi or optimization-speed claim.

## Promotion threshold
Do not change the production default unless the multiscale arm produces
genuine replicated held-out error improvements on *both* r and J compared
with both fair controls, with useful accuracy/cost and no unexpected
per-seed deterioration. Both 16^3 and 32^3 results must be discussed;
repeatedly tuning on the held-out ellipsoid test is prohibited.
