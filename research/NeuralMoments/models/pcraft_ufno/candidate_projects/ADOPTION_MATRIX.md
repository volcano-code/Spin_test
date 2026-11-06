# W6 adoption matrix

## Decision key

- **Direct-reuse review ready:** repository license is identified; source still requires an adapter, tests and a W6 commit.
- **Existing adapter / incomplete:** a W6 adapter or previous experiment exists, but source build or production validation is incomplete.
- **Method reference / license hold:** code is visible but no root license was found; do not copy until permission is confirmed.
- **External benchmark only:** license or dependency model makes it unsuitable for the W6 core.
- **Watchlist:** source identity or code release is not verified.

| Priority | Candidate | W6 role | Code status | License status | Cloud vs local |
|---|---|---|---|---|---|
| **CORE** | **P-CRAFT PINO / UFNO3d** | **Only primary Spin-PINO backbone: factorized F-FNO + U-shaped encoder/decoder + moment-specific PINO physics loss** | **Adapted under `spin_pino/`; CPU identity tests 9/9 passed; not trained yet** | **Internal source; upstream root LICENSE not found; keep internal pending ownership clearance** | **Cloud CPU prototype passed; local 4090 training and native Spin validation remain** |
| P0 | Algoim | Independent implicit-geometry quadrature reference | Pinned official source compiled; unit-sphere ten-moment CPU smoke passed (max abs error 7.50e-11) | Custom BSD-style; preserve full notice | Cloud compile/smoke passed; Spin/Cherchi pairing still requires native validation |
| P0 | NeuralOperator GINO/UQNO | Geometry encoder and uncertainty baseline | GINO moment adapter + UQNO residual-scale wrapper; CPU smoke passed; no trained weights transferred | MIT | Cloud CPU smoke passed; geometry-generalization training and GPU comparison remain |
| P0 | QuadrANN | Learned geometric quadrature baseline | Pinned MIT model core safely extracted; 3D adapter and CPU forward smoke passed; still untrained | MIT | Cloud CPU smoke passed; matched training/accuracy benchmark remains |
| P0 | PhysicsNeMo GeoTransolver | Geometry-aware operator baseline | Not integrated | Apache-2.0 | Small CPU interface tests in cloud; full model local GPU |
| P1 | Transolver++ | Physical-state attention baseline | Not integrated | MIT | Small CPU ablation in cloud; realistic mesh/GPU local |
| P1 | PhysicsNeMo DoMINO / FIGConvNet | Multi-scale point-grid geometry encoder | Not integrated | Apache-2.0 | CPU interface work in cloud; high-resolution local GPU |
| P1 | PhysicsNeMo active learning | Select costly teacher queries | Not integrated | Apache-2.0 | Strategy tests in cloud; actual Cherchi query requires W2/local native setup |
| P1 | fVDB | Sparse voxel/SDF backend | Not integrated | Apache-2.0 | API design in cloud; CUDA build/512^3 local |
| P1 | GAOT / GAOT-3D | Multiscale GNO/geometry-transformer baseline | Source inspected | Root license missing; permission hold | Method comparison only until rights cleared |
| P1 | GINOT | Point-cloud geometry encoder | Source inspected | Root license missing; permission hold | Method comparison only until rights cleared |
| P1 | PhysGTO | Manifold graph-transformer operator | Source inspected | Root license missing; permission hold | Method comparison only until rights cleared |
| P1 | NQR (SIGGRAPH 2026) | Adaptive neural quadrature and geometry sampling | Source inspected | Root license missing; permission hold | Paper-level design in cloud; no code copy |
| P2 | e3nn / EqGINO | Rotation-equivariant geometry features | e3nn library available; EqGINO source inspected | e3nn MIT; EqGINO license unresolved | Invariance tests in cloud; GPU performance local |
| P2 | PyG | Graph message-passing substrate | Dependency candidate | MIT | CPU and GPU |
| P2 | Kaolin / PyTorch3D | Mesh sampling, SPC and SDF preprocessing | Not integrated | Apache-2.0 / BSD-style | CPU interface in cloud; CUDA kernels local |
| P2 | TorchOpt | Implicit differentiation / optimizer ablation | Not integrated | Apache-2.0 | Small CPU differentiable tests in cloud; final Newton remains native |
| P3 | torchquad | Independent numerical integration benchmark | Not integrated | GPL-3.0 | Keep isolated; do not vendor into W6 core |
| Watch | UNOP | Unsupervised integral constraints / curvature gating | Source inspected | README MIT badge but root license missing | Method reference until license text is confirmed |
| Watch | Active operator learning UQ (JCP 2026) | Uncertainty-driven label selection | Paper only; no code repository verified | Not applicable | Implement independently from paper |
| Watch | Transolver-3 | Very-large geometry operator | Announced in Transolver README; separate code repo not verified | Not verified | Await official code |
| Watch | Opt-RNO | Optimization-aware operator | Expected repository path not resolved | Not verified | Await exact official repository |

## Rules for promotion

A candidate must pass all of the following before being called integrated:
1. Exact upstream commit and file SHA recorded.
2. License and bundled dependency notices reviewed.
3. W6 adapter exposes the frozen ten-moment coefficient/order contract.
4. The same geometry source, split, teacher-call budget and parameter budget are used in comparisons.
5. Moment, Jacobian, event and physical-structure tests pass.
6. Cold/warm geometry encoding, moment query, Jacobian query, peak memory and end-to-end cost are measured.
7. A W6 commit and reproducible report are created.

No candidate is selected just because its paper is recent or its benchmark is strong on CFD.

## New candidate: DensiCrafter

| Priority | Candidate | W6 role | Code status | License | Cloud vs local |
|---|---|---|---|---|---|
| P0/P1 | DensiCrafter | Differentiable density-field design, mass/COM/contact losses, surface-preserving hollowing | Source and MIT license audited; adapter not yet implemented | MIT | Loss port, coordinate generalization and 16³/32³ CPU prototypes can run in cloud; TRELLIS, 64³+ GPU and MuJoCo/Blender reproduction require local GPU/toolchain |

DensiCrafter complements W6; it is not another neural operator and the inspected code does not implement general FEM stress/strain. See DENSICRAFTER_INTEGRATION.md.


## Additional 2026 mechanics references (paper-level, not code-integrated)

| Priority | Work | W6/MMDO role | Evidence status | Action |
|---|---|---|---|---|
| P0 | Differentiable graph neural fields for manufacturable topology optimization under stress constraints, Computer Structures 330 (Sep 2026), DOI 10.1016/j.compstruc.2026.108360 | Stress-constrained AM topology optimization; FEM-mesh neural field, support filter, compliance/volume/stress constraints | Open-access article; no verified source repository in this audit | Reproduce method from article and seek data/code; keep separate from DensiCrafter |
| P1 | PI-GINOT, arXiv:2607.23299 (Jul 2026) | Physics-informed hyperelastic mechanics on parametric geometries | Preprint; no verified source/license in this audit | Method reference only; independently reproduce and compare against FEM |

These two entries expand the mechanics branch, but do not count as source-code integration. The reported errors/results are author-reported and must be independently validated.


## Additional PINO-first training and warm-start methods

| Priority | Candidate | W6 role | Current audit | 30-day use |
|---|---|---|---|---|
| P0 | PI-CViT (arXiv:2606.06164) | PINO loss balancing, gradient-conflict diagnosis, collocation sampling and causal weighting | Official code inspected; no root LICENSE found | Reimplement task-appropriate training strategy; do not import CViT backbone or copy code pending permission |
| P0 | TensorPILS | Preconditioned physics residual norm and PINO training conditioning | Apache-2.0 source inspected | Derive a positive-definite preconditioner for Spin moment residuals; do not reuse Poisson/Allen-Cahn/Stokes equations |
| P1 | PFEM (JMPS 214, 2026, 106682) | PINO warm-start for classical FEM/Newton iterations | Official code inspected; no root LICENSE found | Borrow warm-start acceptance pattern only; keep PINO as backbone and Cherchi/native solver as exact authority |
| P1 | HyPINO | Method of Manufactured Solutions and residual-based iterative refinement | MIT source inspected | Use MMS/analytic manufactured cases and residual refinement ideas; do not use Swin hypernetwork as Spin backbone |

All four are subordinate to P-CRAFT PINO. Full status, license caveats and acceptance gaps are in `../ALL_ADVANCED_SOLUTIONS_GAP_MATRIX.md`.
