# W6 P20: three-seed native 128^3 trained-PINO x DensiCrafter confirmation

P20 repeats P19 with three independently trained P14 seed checkpoints
and three distinct P0 sphere geometries. Every run strictly transfers
the matching 64^3 P-CRAFT PINO checkpoint to a true 128^3 Fourier grid.

## Fixed matrix
- Seeds 271, 277, 281; matching P14 trained 64^3 checkpoints.
- Input and internal P-CRAFT Fourier grid: native 128^3.
- Width 8, modes 4, four U-FNO layers, 512 positive quadrature atoms.
- Freeze every PINO weight; optimize only DensiCrafter density logits.
- Distinct sphere geometry from seed+707 for each seed.
- Four-cell protected shell; same normalized thickness as P18 two-cell shell at 64^3.
- Densi-only, PINO-only, soft-joint, feasible-joint arms.
- Six Adam updates per active arm, learning rate 0.06.
- Resolution-aware DensiCrafter bottom-contact weighting.
- Independent cell-centered hard-cut ten-moment reference and normalized
  full-material nine-moment ledger.
- Predeclared limits: PINO cut-r <=2%; independent hard-cut r <=2%;
  normalized full-material nine-moment L2 <=2%.
- Three seeds run in parallel. Per-seed model/design tensors, JSON
  receipts and source-checkpoint SHA256 are retained.
- Aggregate reports mean/std/min/max and total accepted/rejected steps.

## Acceptance
All three seeds must complete. Every feasible-joint final design must
pass all three independent 2% screens and preserve its protected shell.
Rejected intermediate steps are recorded, never hidden. A failed seed
is a negative result; aggregate is not marked successful.

## Scientific limits
Analytic P0 sphere labels only. Not W2/Cherchi continuous CAD
integration, not FEM/FEA, not millimeter-certified wall thickness,
not printability or Newton admission. Six updates are a repeatability
confirmation, not a full lightweighting convergence study.
