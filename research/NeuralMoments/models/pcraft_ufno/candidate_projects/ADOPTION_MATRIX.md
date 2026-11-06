# W6 adoption matrix

## Decision key

- **Direct-reuse review ready:** repository license is identified; source still requires an adapter, tests and a W6 commit.
- **Existing adapter / incomplete:** a W6 adapter or previous experiment exists, but source build or production validation is incomplete.
- **Method reference / license hold:** code is visible but no root license was found; do not copy until permission is confirmed.
- **External benchmark only:** license or dependency model makes it unsuitable for the W6 core.
- **Watchlist:** source identity or code release is not verified.

| Priority | Candidate | W6 role | Code status | License status | Cloud vs local |
|---|---|---|---|---|---|
| P0 | Algoim | Independent implicit-geometry quadrature reference | R4 adapter exists; official source build unverified | Custom BSD-style; preserve full notice | CPU build/test can start in cloud; final native performance should be local |
| P0 | NeuralOperator GINO/UQNO | Geometry encoder and uncertainty baseline | Not integrated | MIT | CPU smoke and adapter in cloud; large-scale GPU local |
| P0 | QuadrANN | Learned geometric quadrature baseline | Prior W6 adapter reported; re-audit required | MIT | CPU reproduction in cloud; GPU performance local |
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