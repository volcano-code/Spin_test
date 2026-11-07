# DensiCrafter × Spin-MPNO integration assessment

Audit date: 2026-11-06
Upstream: https://github.com/idvxlab/DensiCrafter
Pinned upstream commit: 21e6d8dc646129a9b21a38c2d5bee5bef2704d98
License: MIT (retain copyright and license notice)

## Decision

Integrate as a complementary differentiable density-field design module, not as a geometry neural-operator backbone and not as a structural-strength/FEM solver.

The inspected source implements mass regularization, density-based center of mass, a smooth bottom-contact map, a center-of-mass-to-contact-region distance penalty, negative contact-area reward, center-of-mass height penalty, and a restricted design field intended to preserve the outer surface.

The AAAI 2026 paper reports lightweight, self-supporting hollow structure generation and up to 43% material mass reduction in its text-to-3D setting. This figure belongs to its own evaluation and must not be transferred to Spin without reproduction.

## What transfers to W6

1. Density-field parameterization and optimization loop from obj.py: optimize rho_score, use sigmoid density, optional smoothing, Adam and a restricted design mask.
2. Mass/COM/contact losses from loss.py and physical.py: preserve as a baseline and generalize to physical coordinates.
3. Surface-protection/design-domain idea from Rho.build_the_optimize_field: keep the outer shell fixed while optimizing the interior and explicitly permitted support region.
4. Validation pattern from evaluation.py: separate geometric fidelity, mass, stability and simulation outcomes. MuJoCo stability is evaluation, not a differentiable training loss.

## What must not be copied unchanged

- Hard-coded 64×64×64 shapes and reshapes.
- Assumption that z is the ground axis and XY is the support plane.
- torch.roll neighbor operations, which wrap values across opposite volume boundaries unless boundary handling is corrected.
- NumPy/SciPy topology operations in geometry.py as if they were differentiable.
- Global mutable GRID/config and CUDA-only initialization.
- TRELLIS generation, Blender and MuJoCo dependencies in the W6 neural-moment core.

The inspected DensiCrafter files do not implement general FEM stress/strain or arbitrary load-case strength analysis. Do not represent it as a structural-strength solver.

## Proposed adapter boundary

```text
source mesh / voxel / SDF
        |
surface + interior + support masks
        |
continuous density logits rho_score
        |
DensiCrafter-style differentiable design objective
  - mass
  - COM/contact stability
  - surface preservation
  - optional user load/support constraints
        |
optimized density rho(x)
        |
W6 material integration
  - fixed material r_F[10], separately cached
  - variable material r_D[10], J_D[10,10]
        |
Spin objective / inertia / exact Cherchi-Newton acceptance
```

W0 convention remains authoritative. Do not conflate DensiCrafter's COM/contact objective with the signed-quadric moment objective.

## Proposed original contribution: Moment-aware Manufacturable Density Optimization (MMDO)

Jointly optimize a density field under DensiCrafter-style mass and support/contact objectives, W6 ten-moment constraints and moment-potential derivatives, outer-surface preservation and minimum feature/wall-thickness constraints. Optional load-case stress constraints require a validated mechanics solver or FEM/PINN module; DensiCrafter alone does not provide this.

A risk-aware outer loop can choose between a cheap density/moment surrogate and exact W6/Cherchi evaluation. This is a research hypothesis, not an implemented or validated contribution.

## Cloud/local plan

### Cloud CPU — can start now
- extract and unit-test pure mass/COM/contact loss formulas;
- remove hard-coded 64³ assumptions and global CUDA config;
- implement coordinate-aware voxel integration and surface-mask contracts;
- connect density fields to W6 ten-moment CPU reference integration;
- finite-difference test density gradients and verify boundary behavior;
- run small 16³/32³ synthetic density optimization and ablations.

### Local GPU — required for full reproduction
- integrate original TRELLIS generation pipeline and checkpoints;
- benchmark 64³/128³/256³ and later 512³ density optimization;
- profile memory/runtime;
- reproduce MuJoCo/Blender validation and printable mesh export.

### Separate mechanics dependency
For actual strength/repair claims, add a validated FEM/PINN stress solver and material/load boundary conditions. Do not infer strength from COM/contact stability or mass reduction alone.

## Acceptance gates

1. MIT notice and upstream commit pinned.
2. Coordinate-frame tests: rotate gravity/support direction and verify equivalent COM/contact outcomes.
3. Boundary tests: no wraparound coupling across opposite voxel faces.
4. Density-gradient finite differences for mass, COM and contact terms.
5. Surface preservation and material mass measured independently.
6. W6 ten-moment integration agrees with independent exact/numerical reference.
7. Compare DensiCrafter-only, W6-moment-only and coupled MMDO on identical geometries and budgets.
8. If claiming structural strength, include separate stress/strain/yield or failure-load evidence.
9. Real Heart/Teapot/Noodles results are reported separately; do not transfer DensiCrafter's 43% figure.

## Current status

Source and MIT license pinned at upstream commit `21e6d8d`.
**P13a incremental update (2026-11-07): integrated**, not merely planned.

- Original MIT `mass_penalty`, `compute_mass_center` and smooth-bottom-contact core extracted under `densicrafter_pino/third_party/`, retaining full license and original commit/blob traceability.
- Implemented differentiable density logits, protected shell, gravity-axis-aware contact/COM loss and physically parameterized ten full-material moments, feeding canonical four-channel density directly to the original P-CRAFT Spin-PINO encoder and moment/Jacobian heads.
- Confirmed actual gradient from PINO r back to density design variables, protected-shell invariance, valid arbitrary gravity axes, no periodic wrap, and a descending joint density/moment objective.
- GitHub Actions P13a run: https://github.com/volcano-code/Spin_test/actions/runs/42383420598 — 21 passed, 0 failed.
- These are *source-level and gradient* integration achievements; TRELLIS/MuJoCo/Blender, 512³ CUDA, native Cherchi, strength/FEM, printable-model end-to-end and full DensiCrafter paper reproduction remain unverified.
- Updated current candidate status: `P13A_ORIGINAL_MIT_LOSS_CORE_COUPLED_TO_PINO_CPU_21_TESTS_PASSED_NOT_FULL_REPRODUCTION`.

