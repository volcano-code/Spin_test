# W6 P17: couple DensiCrafter to the actually trained 64³ Spin-PINO

P17 replaces the random P13 PINO with the trained P14 native 64³
checkpoint. It keeps PINO frozen and optimizes only the density logits.
The trained P-CRAFT SpinPINO remains the only neural operator.

## Source and setup
- Download Actions artifact `w6-p14-native-PINO-grid-64` from run
  42450889982; strict-load seed-271 checkpoint.
- 64³ analytic sphere occupancy from the same P0 data source.
- Derive a two-voxel protected shell using nonperiodic morphological
  erosion. Design cells are strictly inside the solid; outside cells
  remain exactly zero. This is a voxel-count wall, NOT mm-certified.
- Initialize density near one (logit=4) to match P14 training density.
- Pino weights frozen; Densi material density logits trainable.
- Use original MIT DensiCrafter mass/COM/smooth-bottom-contact losses.
- Compare Densi-only, PINO-only, soft joint, and hard-feasibility joint.
- Hard feasibility uses both the trained PINO's moment response and
  independent cell-centered Boolean cut ten-moment integral, plus
  normalized full-material nine-moment shape ledger. Tolerances fixed
  at 2% before training. Step shrinkage and rollback on violations.

## Claims and limits
This is a real trained-PINO × DensiCrafter differentiable design
experiment at 64³. It does not certify true continuous CAD geometry,
stress/FEM, printable minimum wall in mm, Cherchi event derivatives or
native Newton. P0 labels remain analytic, not W2 teacher observations.
