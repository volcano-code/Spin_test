# W6 P19: actual 128³ DensiCrafter × transferred trained P-CRAFT PINO

P19 advances the P18 verified trained-64³ design to a real 128³
input and internal Fourier grid. It uses a trained P14 seed-271
64³ checkpoint and strict-loads all weights into the same P-CRAFT
SpinPINO architecture configured at grid_size=128. No alternative
neural operator replaces the PINO trunk.

## Fixed experiment
- P14 source artifact run 42450889982, seed 271, 64³ trained checkpoint.
- Target input and P-CRAFT F-FNO/U-FNO internal grid both 128³.
- Width 8, modes 4, four U-FNO layers, 75,040 parameters.
- Strict state_dict load; no interpolation/drop of any learned weight.
- 512 positive quadrature atoms, same as the P14 source checkpoint.
- Freeze all PINO parameters; optimize only DensiCrafter density logits.
- Enable non-reentrant activation checkpointing for PINO blocks during
  density-input backpropagation. InstanceNorm has no running stats in
  this architecture, so train/eval mode does not alter normalization.
- DensiCrafter bottom-contact exponential decay is measured in equivalent
  64-grid voxels: exactly the original DensiCrafter weighting at 64³,
  while 128³ uses half the per-index exponent so the same physical height
  receives the same contact weight. This avoids a resolution-induced empty
  support region when the original index-based 4^-k decay is used unchanged.
- One analytic P0 sphere at 128³, one cut query.
- Four-cell shell at 128³ approximates the two-cell shell scale at 64³
  (same normalized voxel count scale); it is not a millimeter wall.
- Four arms: Densi-only, PINO-only, soft joint, feasible joint.
- Three optimizer steps per design arm, Adam lr=.03.
- Independent cell-centered hard-cut ten-moment and normalized full
  material nine-moment ledger.
- Predeclared tolerances: model cut-r <=2%, independent cut-r <=2%,
  normalized full-material 9-moment L2 <=2%.
- CI artifacts save the trained PINO state and all four final density
  fields/independent ledgers.

## Acceptance and limits
P19 is accepted only if the 128³ source grid is preserved, strict
64->128 checkpoint transfer succeeds, density-input gradients are
finite, protected shell remains exact, and the feasible-joint final
state passes all three independent 2% screens. A failed screen is a
valid negative result and must not be hidden.

This is still analytic P0 synthetic sphere geometry. No W2/Cherchi
teacher, continuous CAD Boolean certification, FEM/FEA strength,
millimeter wall, Newton admission or 512³ GPU claim is made.
