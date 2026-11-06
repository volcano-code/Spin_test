# W6 advanced-scheme gap matrix — PINO-first, 30-day scope

Audit date: 2026-11-06. This matrix distinguishes source integration, adapter smoke, trained comparison, paper-only method transfer and unstarted work. The production backbone remains P-CRAFT PINO/UFNO.

## A. Primary PINO and PINO-training research

| Scheme | Intended W6 use | Current evidence/status | Remaining gap | 30-day decision |
|---|---|---|---|---|
| P-CRAFT UFNO3d / F-FNO | Mandatory primary trunk | Adapted; M0 CPU tests passed; internal source ownership/license clearance pending | Validate source rights; improve held-out geometry and orientation generalization; local 64³/128³ | Keep primary; no replacement |
| PI-CViT | PINO training diagnostics, gradient balancing and collocation strategy | Paper/code audited; root license hold; method only | Transfer only generic training diagnostics; no PDE-specific residuals | Small method ablation if time |
| TensorPILS | Preconditioned physics-informed loss | Method audited; Apache-2.0 candidate | M4 preconditioner/PCGrad did not beat baseline; design Spin-specific residual scaling | Retain optional; not default |
| HyPINO / MMS | Manufactured-solution synthetic data and refinement | MIT candidate; method reference, not integrated | Create Spin-specific manufactured cases and error estimator | High-value data/verification add-on |
| PFEM | PINO warm-start for finite-element mechanics | Method/source audited; license hold | Could warm-start mechanics solver; separate from moment integral head | Defer mechanics branch |
| Neural-Initialized Newton | Operator initialization followed by exact Newton correction | 2026 paper reference; not integrated | Transfer pattern to Spin: PINO initial proposal + exact Cherchi correction; test call savings | High-priority conceptual baseline, contingent on admitted teacher |
| GAPI-DeepONet | Geometry-conditioned branch/trunk as optional PINO feature adapter | 2026 paper reference; no W6 code integration | Test only if geometry adapter improves PINO | Paper-level comparison |

## B. Geometry encoders and neural-operator plugins (PINO remains trunk)

| Scheme | Intended W6 use | Current evidence/status | Remaining gap | 30-day decision |
|---|---|---|---|---|
| GINO / FNOGNO | Geometry feature adapter | GINO CPU adapter passed; not trained on Spin | Matched PINO plug-in ablation; FNOGNO separate test | Keep optional |
| Transolver++ | Physics-state attention adapter | Candidate MIT; not integrated | Adapter, CPU smoke, matched ablation | One of Transolver++/GeoTransolver only |
| PhysicsNeMo GeoTransolver | Geometry-aware attention | Apache-2.0 candidate; not integrated | Adapter and held-out geometry test | Select only if beats GINO |
| DoMINO | Multi-scale surface/volume geometry | Apache-2.0; not integrated | Input contract and GPU-heavy test | Defer unless selected adapter slot |
| FIGConvNet | Point-grid geometry encoder | Apache-2.0; not integrated | Point/grid conversion, resolution study | Defer unless selected adapter slot |
| Neural-Solver-Library | Baseline architecture suite | MIT; source candidate | Reproduce compatible PINO/FNO/UPT baselines without changing main trunk | Use selectively |
| GINOT | Geometry-informed point transformer | CMAME 2026 method reference; root license hold | Permission and implementation audit | No code copy; paper comparison only |
| GAOT / GAOT-3D | Graph adaptive operator | Method references; root license hold | Permission and compatible mesh benchmark | Defer |
| PhysGTO | Manifold graph transformer | 2026 method reference; root license hold | Permission and adapter | Defer |
| EqGINO | Equivariant geometry operator | ICML 2026 method reference; root license hold | Reproduce covariance properties; permission | Compare with our exact transform tests, no code copy |
| UNOP | Integral physics constraints and geometry adapter | IJCAI 2026 method reference; root license unclear | Adapt integral consistency ideas to moment identities; no unrelated PDE rollout | High-value paper transfer |
| GINTO | Geometry-informed transformer neural operator / PINTO-style | Physics of Fluids 2026 paper | Geometry point cloud + cross-attention adapter; code license not verified here | Paper method review; optional plugin |
| SINO | Scale-invariant neural operator | Sep 2026 preprint with public code link | Test scale-normalized dual spectral/spatial branch inside PINO, not as replacement | Method/ablation only |
| HiRefPOU | Localized partition-of-unity operator experts | Oct 2026 preprint | Local experts around interfaces/curvature; retain PINO spectral trunk | Strong candidate for event-local adapter |

## C. Quadrature, numerical reference and uncertainty

| Scheme | Intended W6 use | Current evidence/status | Remaining gap | 30-day decision |
|---|---|---|---|---|
| QuadrANN | Learned positive quadrature weights | 3D CPU smoke passed; untrained | Train same teacher split; compare r/J and inference cost | Keep baseline |
| NQR | Autoregressive adaptive quadrature | SIGGRAPH 2026 paper; source license unresolved | Reproduce sampling policy independently; compare against QuadrANN | Method transfer |
| Algoim | Independent implicit-geometry reference | Official source compiled; unit-sphere ten moments max error 7.50e-11 | Expand to plane/ellipsoid/general quadrics and pair with Cherchi | Keep reference only |
| Cherchi | Authoritative Spin teacher and exact fallback | W2 diagnostic run exists; formal admitted training samples remain zero in last verified W2 snapshot | W2/W0 formal evidence admission | Critical external dependency |
| UQNO | Residual uncertainty | Wrapper CPU smoke passed | Calibrate on held-out admitted labels; risk-coverage | Keep optional |
| Active Operator Learning (JCP 2026) | Teacher query selection by predictive uncertainty | Paper reference | Reproduce query ranking on synthetic labels; later Cherchi budget | High-value method transfer |
| torchquad | Independent quadrature baseline | GPL-3.0 | Isolated process/env only | Low priority |
| INO | Data-free weak-form operator learning and computable residual bound | Sep 2026 preprint, public code claim | Weak-form residual certificate may inspire residual bound; Spin task not a PDE weak form | Paper-level transfer only |

## D. Geometry backends, equivariance and optimization

| Scheme | Intended W6 use | Current evidence/status | Remaining gap | 30-day decision |
|---|---|---|---|---|
| fVDB | Sparse voxel/SDF backend | Apache-2.0; not CUDA-integrated | Local CUDA build, 128³–512³ memory/time | Local GPU only |
| Kaolin | SPC/SDF/Mesh preprocessing | Apache-2.0; not integrated | Compare preprocessing and conservation | Defer |
| PyTorch3D | Differentiable mesh sampling | BSD-style; not integrated | Narrow utility adapter | Optional |
| PyG | Graph substrate | Dependency in QuadrANN; not W6 operator | Pin versions and reuse only as needed | Dependency only |
| e3nn | E(3)-equivariant feature layers | MIT; not integrated | Compare exact SO(3) covariance augmentation with learned equivariance | Optional small ablation |
| TorchOpt | Differentiable/unrolled optimization | Apache-2.0; not integrated | Spin-specific implicit differentiation and stability | Defer |
| Exact rotation transforms | Transform coefficients, moments, Jacobians | Implemented; cube rotation augmentation M6 passed | Arbitrary SO(3) with interpolation error; full orientation-held-out family | Active next step |

## E. Density design and mechanics

| Scheme | Intended W6/MMDO use | Current evidence/status | Remaining gap | 30-day decision |
|---|---|---|---|---|
| DensiCrafter | Density field, mass/COM/contact, surface protection | MIT source audited; adapter not implemented | Arbitrary resolution/world frame, no-wrap boundaries, W6 moment coupling | Implement 16³/32³ prototype |
| Stress-constrained differentiable GNN neural fields (Sep 2026) | Manufacturable topology optimization with stress constraints | Paper reference; source code unverified | Reproduce stress loss and validate against FEM | Paper method only |
| PI-GINOT | Geometry-informed hyperelasticity | Jul 2026 preprint; code/license unverified | Constitutive law, equilibrium, boundary conditions, FEM validation | Defer full integration |
| FEM / PINN | Independent mechanics reference | No validated W6 mechanics adapter | Define material, loads, supports, stress/yield and benchmark | No strength claim before validation |

## F. Latest M2–M6 evidence and decisions

- M2b support masking: selected 8³ / 6³ nodes / smoothing 0.02; held-out r relative L2 0.2561 and J relative L2 0.8972. Better than pre-mask PINO; still not Newton quality.
- M3 same-data tournament: logistic PINO was not yet in that tournament; smooth PINO 6-node had best r (0.2561), while W6 M7 had best combined score (0.4651) and J relative L2 (0.4931).
- M3b: tensor-product Gauss nodes performed worse than midpoint nodes in the PINO voxel-mask setting; retain as negative ablation.
- M4: diagonal residual preconditioning and PCGrad did not improve held-out combined score; keep optional, not default.
- M5: PINO trunk + support-masked logistic realizable-atom head achieved r relative L2 0.2060 and J relative L2 0.3147 on the same analytic held-out ellipsoid benchmark; best current candidate. It is still analytic P0 only, not Cherchi or Newton admitted.
- M6 cube rotations: 24 exact grid-preserving rotations with exact label transforms. Initial no-augmentation vs cube augmentation metrics were nearly identical; arbitrary SO(3) remains untested at this audit.

## G. Next execution order (30-day constraint)

1. M7 arbitrary-SO(3) rotation augmentation with exact coefficient/moment/J transforms and explicitly measured voxel interpolation error; compare against cube-only augmentation.
2. M8 PINO-first local geometry adapter tournament: choose at most one of GeoTransolver or Transolver++ (GINO remains baseline). No DoMINO/FIGConvNet/fVDB unless time/GPU is available.
3. M9 DensiCrafter 16³/32³ loss port and W6 moment coupling; keep mechanics strength branch explicitly separate.
4. M10 held-out arbitrary quadric/event cases and Cherchi gate re-check. If W2 has no admitted labels, no Newton admission.
5. Local 4090 acceptance: 64³/128³ and native Spin/Heart/Teapot/Noodles timing. 512³ is stretch, not a one-month promise.

All candidate schemes remain visible here even when deliberately deferred. 'Paper transfer', 'adapter smoke', 'trained model' and 'production admission' are distinct statuses.
