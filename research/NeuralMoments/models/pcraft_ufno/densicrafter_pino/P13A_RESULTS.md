# W6 P13a — Original DensiCrafter physical density core coupled to Spin-PINO

Date: 2026-11-07. Branch `research/neuralmoments-w6-pcraft-20261019`.
Primary source: `idvxlab/DensiCrafter@21e6d8dc646129a9b21a38c2d5bee5bef2704d98` (MIT copyright Shengqi Dang 2025).
**PINO is still the only primary neural operator.**

## What actually changed

- DensiCrafter original MIT physical primitives `mass_penalty`,
  `compute_mass_center`, `get_smooth_bottom_contact_region`
  extracted in `third_party/densicrafter_core.py` with full original
  MIT license. Float tensor exponent adapted for PyTorch.
- New `DensiCrafterSpinPINOBridge`: learnable interior density logits,
  hard-preserved outer shell, nonperiodic optional smoothing, configurable
  world-axis gravity, COM/contact/mass/height losses, differentiable
  input-density full-material 10-moment ledger and PINO-produced
  variable-cut 10 moments + *diagnostic-only* 10x10 J.
- Critically, a PINO moment mismatch penalty backpropagates to the
  density field; this is no longer a disconnected "proposal" document.
- Does NOT replace or rewrite P-CRAFT U-FNO/F-FNO with DensiCrafter.
  Does NOT copy original TRELLIS image/text generation, 3D mesh export,
  or original CUDA/global 64³ main.py into the W6 core.
- Does not guarantee fixed world-unit density, manufacturing-safe wall
  thickness, structural FEM strength, native Cherchi J_D admission,
  or preservation of the desired inertia in an optimized print.

## Real GitHub Actions CPU acceptance

Integration commit `690fe36832d74bd53b33856a67dc12d6dfced3f4`,
finite-sigmoid/non-wrap assertion correction
`c43ae81c7169d45612883e31df7f03652ca8a918`,
joint benchmark and candidate catalog update
`17f608e2675f3de8602b4f91ef76cc24433262db`.

- [Initial corrected 21-test CI](https://github.com/volcano-code/Spin_test/actions/runs/42383420598):
  21 tests passed, 0 failed (gradient, surface, orientation,
  non-wrap, material mass, original PINO regressions).
- [Full 21-test + 8³/16³ measured smoke](https://github.com/volcano-code/Spin_test/actions/runs/42383677468):
  success; 21 passed, 0 failed; JSON artifact
  `w6-p13a-densicrafter-pino/w6_p13a_density_pino.json`.
- Downloaded artifact ZIP SHA256:
  `3db1bd26b5cb0a2e57bb2a508a07ae71dd017ed4bfe0788decdb8e4c3d5d2813`.

### Two reproducible CPU synthetic density optimization cases

All weights are from random/untrained PINO; *only density logits*
are optimized with Adam lr .1 for 12 updates. Target ten moments are
the initial model's cut-moment output, not native Cherchi r/J or an
independently validated geometry optimum.

| Metric | 8³ | 16³ |
|---|---:|---:|
| Initial objective | 0.964985 | 0.844730 |
| Final objective | 0.891639 | 0.675622 |
| Initial discretized full-material mass | 6.31250 | 5.32031 |
| Final discretized full-material mass | 5.57378 | 3.95600 |
| Relative mass reduction | 11.70% | 25.64% |
| PINO r to material-logit gradient norm | 0.14118 | 0.13869 |
| Cut r prediction displacement from initial target, L2 | 0.30335 | 0.07605 |
| Fixed shell cells | 296 | 1352 |
| Optimize duration, same CI host | 0.464 s | 0.093 s |

**Important:** the printed mass reductions are from tiny synthetic
random-initialized cases, NOT published DensiCrafter's mass-reduction
score and not ready-to-print designs. The cut-moment target was NOT
maintained exactly. The 8³ case in particular shows significant
`||r_pred_new-r_pred_initial||=0.303`, so reducing material and
lowering weighted objective are NOT evidence of preserved
moment/inertia physics.

## Admission decision

**Admit the DensiCrafter-PINO interface and gradient contract as a
reproducible W6 optional density-design module; do NOT promote it as
a production, full-fidelity DensiCrafter or native Spin optimizer.**

Next P13b should compare:
1. DensiCrafter-only mass/support losses,
2. PINO-only moment preservation,
3. Weighted coupled density+PINO,
4. Hard-constrained mass/moment optimization plus independent exact
   geometry/moment verification.

Audit outer surface and minimum wall thickness, physical grid
coordinates, ten-moment tolerance, contact footprint, gradient
finite-difference and numerical projection under topology change.
Use only new held-out geometries for comparisons. Formal
Cherchi teacher and Newton derivative admission remain W0/W2
dependencies, not this interface's automatic result.

Cloud can do P13b 16³/32³ CPU and analytic reference.
Local GPU is required for fVDB actual CUDA, true 512³ training,
TRELLIS/MuJoCo/Blender and real Heart/Teapot/Noodles native
geometry export and Spin-it Faster/Cherchi convergence.
