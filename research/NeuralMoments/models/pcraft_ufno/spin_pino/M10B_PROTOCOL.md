# W6 M10b — CPU analytic P0 three-arm train/validation/test ablation

**W6 only**: branch research/neuralmoments-w6-pcraft-20261019. PINO is
the sole primary trunk, from P-CRAFT pinned original UFNO/F-FNO implementation.

## Hypothesis
M10 established the source-resolution geometry can change moment predictions
even when two 32^3 sparse inputs have exactly the same coarse PINO tensor.
M10b tests whether that information actually yields a **held-out analytic P0
accuracy gain after training**, over the otherwise identical PINO baseline and
the more privileged-but-coarse "source moment summary" control.

## Three fair conditions
1. **PINO**: same coarse grid from the full source sparse list.
2. **PINO+source moments**: same PINO and support-masked moment head, plus a
   bounded residual reweighting conditioned on fine-grid raw 10 moments and
   10-component fine-versus-coarse discrepancy, but *no local multiscale bins*.
3. **PINO+sparse multiscale**: identical head/module parameter shapes as #2,
   with additional mass-weighted grouped relative cell coordinates at
   two resolutions (coarse, source). The two augmented architectures have the
   same *allocated* parameter counts; inactive parameters in #2 are **not**
   equivalent to matched effective capacity, and runtime costs differ.

All three share the same pinned initial core PINO weights, analytic label source,
geometry IDs and native coefficient vectors, fit/validation/test sets, fit
observation order, steps, optimizer and early stopping metric.
Both augmented arms start with equal nonzero gate 0.2 *for training only*.
M10 public zero-gate identity behavior remains default.

## Dataset, caveats, and teacher
Synthetic **cell-centered** voxelization of source geometries at 16^3 (or
32^3 for a separate later experiment); 8^3 coarse PINO tensor is computed
from the same source. Analytic teacher calls use true continuum interior
**vertical-plane** cuts on boxes, spheres and ellipsoids. Fit and validation
are disjoint geometry identities and only boxes/spheres; entire ellipsoid
family is held out as the final test. Repeated coefficient queries share
a geometry ID and must never leak across splits.

Train with 3 seeds (131/137/139), 60 optimizer updates per arm and seed,
geometry-disjoint fit/validation split, and 2 coefficient queries/geometry.
Validation-only score = r_MAE + 0.25 J_MAE, tested at steps 1,10,20,...,60.
Same analytic label/query budget is counted and reported.
This is intentionally a **small-budget first CPU falsification**, not a
large trained network or an independent true CAD geometric derivative.

## Strict evidence and decisions
Log per-seed/data SHA-256, held-out r/J MAE & relative L2, worst components,
validation-selected steps, elapsed CPU training/encoding/query time,
allocated parameter counts, process memory RSS, source resolution, geometry
and query counts. Preserve all negative results.

**Promote only if:** the full multiscale arm improves r and J on held-out
ellipsoids over BOTH PINO and moment-summary arm at the same fit label
budget, across all three seeds with practical inference cost. Even then it
is an experimental P0 selection, NOT Cherchi/Newton admission.

## Reproduce
```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m pytest -q research/NeuralMoments/models/pcraft_ufno/spin_pino/tests/test_m10b_train.py

OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m research.NeuralMoments.models.pcraft_ufno.spin_pino.m10b_train \
  --seeds 131,137,139 --steps 60 --source-resolution 16 \
  --geometries-per-family 8 --test-ellipsoids 5 \
  --output /tmp/w6_m10b_three_arm_analytic_p0.json
```

All numerical results must come from actual CI or local execution;
no metrics can be claimed merely from code or tests passing.
No 512^3 spectral operator, fVDB/FIGConv source integration,
W2/Cherchi admitted labels, or native full Newton speedup.
