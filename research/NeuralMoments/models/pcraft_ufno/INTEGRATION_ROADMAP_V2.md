# W6 Spin-MPNO + MMDO — comprehensive integration roadmap v2

Date: 2026-11-06
Branch: research/neuralmoments-w6-pcraft-20261019
Baseline W6 head: 864d9decd25ab1f9ae3b757e014d0fb6c96e8bad

## 0. Executive decision

Upgrade W6 from a single U-FNO adaptation into a modular Spin-specific Multi-Physics Neural Operator (Spin-MPNO), paired with a separate Moment-aware Manufacturable Density Optimization module (MMDO). Do not concatenate all candidate networks into one monolith. Reuse source code where license and dependency audits allow it, and select the best model per representation family using matched ablations.

Spin-MPNO is responsible for geometry-conditioned variable-domain ten raw moments, uncertainty, event-aware derivative screening, adaptive quadrature proposals and safe interaction with the exact solver. MMDO is responsible for density-field design, mass/COM/support objectives and manufacturability. A separate validated FEM/PINN mechanics solver is required for stress/strain/yield claims.

Current verified starting point:
- W6 P0 adapters: GINO/UQNO, QuadrANN and Algoim have CPU smoke evidence; they are not trained on admitted Spin/Cherchi labels.
- R4.2: exact-rational event/range classification on a restricted axis-aligned box; derivative withheld.
- DensiCrafter: source and MIT license audited, but no W6 adapter implemented.
- W2: latest manifest remains diagnostic-only with zero admitted training samples and no admitted J_D. This blocks formal Cherchi-supervised training and derivative use.

## 1. System architecture and module contracts

### 1.1 Geometry ingestion and canonical representation

Input adapters:
- Mesh: triangle mesh, component/material IDs, coordinate frame, watertightness and source hash.
- Voxel: occupancy, density, signed distance, material ID and optional boundary/support masks.
- Sparse voxel: fVDB/Kaolin sparse structures where CUDA is available.
- Point cloud: sampled surface and volume points with normals, curvature and local density features.
- Implicit geometry: quadric/level-set coefficients and exact event descriptors.

Every adapter must output a canonical geometry package containing world transform, units, bounds, orientation, material map, density map, topology diagnostics and deterministic content hash. Preserve the user's mesh/voxel-only task scope when the experiment requires it; point clouds are an encoder representation, not a replacement output format.

### 1.2 Multi-resolution geometry encoder

Create a shared interface with interchangeable branches:
- Dense grid branch: current W6 U-FNO/FNO baseline.
- Geometry-to-latent branch: NeuralOperator GINO/FNOGNO.
- Geometry-aware attention branch: PhysicsNeMo GeoTransolver.
- Point-grid branch: FIGConvNet and DoMINO.
- Sparse voxel/SDF branch: fVDB; Kaolin SPC/SDF as preprocessing and comparison.
- Surface point branch: GINOT, PyTorch3D sampling and PyG graph features, subject to license/permission.
- Equivariant branch: e3nn; EqGINO as a paper/code reference pending source-license clearance.

Do not execute every branch in the production forward pass. Train and compare them separately first; then use a small routing/gating model or a two-branch ensemble only if it improves accuracy-cost-risk trade-offs.

### 1.3 Operator experts

Keep a controlled expert set:
- Spectral: U-FNO/FNO and NeuralOperator FNO variants.
- Geometry-informed: GINO/FNOGNO.
- Physics attention: Transolver++ and PhysicsNeMo GeoTransolver.
- Multi-scale point-grid: FIGConvNet/DoMINO.
- Graph/mesh: MeshGraphNet/VFGN and permission-cleared GAOT/GAOT-3D/PhysGTO/GINOT.
- Equivariant: e3nn features and EqGINO-style spectral equivariance.

Use the Neural-Solver-Library as a baseline suite where source and environment are compatible; avoid duplicating Transolver implementations unnecessarily.

### 1.4 Moment output and mathematical structure

Freeze W0's native coefficient order and ten raw moment order. The variable-domain output is r_D in R^10. The derivative is J_D in R^(10x10), with the exact coordinate transform between native coefficients and the chosen monomial basis applied explicitly.

Research the Convex Moment Potential hypothesis: learn a scalar potential whose gradient yields r_D and whose Hessian yields the coefficient-space Jacobian in regular smooth regions. Test symmetry and positive-semidefinite structure only where the mathematical assumptions hold. This is not a substitute for event classification, neighborhood certification or exact fallback.

Fixed material moments r_F must be computed/cached separately. Combine r_total = r_F + r_D and J_total = J_D only under the W0 contract. Never let an upstream adapter self-authorize Newton use.

### 1.5 Quadrature and exact reference layer

- Cherchi remains the authoritative Spin teacher and exact production fallback.
- Algoim is an independent implicit-geometry numerical comparator; its current unit-sphere ten-moment CPU smoke is not a Spin Boolean/Cherchi validation.
- QuadrANN is a learned point-cloud quadrature baseline; train it on the same teacher budget and geometry split as other models.
- NQR contributes geometry-aware neural quadrature and autoregressive adaptive sampling ideas. Its repository was inspected, but a root license was not verified; no source copying until permission is established.
- torchquad is GPL-3.0 and remains an isolated external benchmark, not a W6 core dependency.

Learned samplers may propose sample locations/weights, but must obey positivity/normalization constraints and be checked against independent references. They must not become their own label oracle.

### 1.6 Uncertainty, active learning and safe Newton

- UQNO or deep ensembles predict per-moment residual uncertainty.
- Split-conformal calibration uses a strictly held-out calibration set; small-sample cases must fail closed rather than claim finite coverage.
- PhysicsNeMo active-learning utilities and the 2026 active-operator-learning paper inform selection of expensive teacher queries.
- Query priority should combine calibrated uncertainty, proximity to geometric event strata, expected Newton-step sensitivity and expected reduction in final optimization risk.
- Event gate uses R4.2 classifications and later general-quadric/multi-component extensions. Unknown, singular, tangent, topological-change or unverified neighborhoods withhold J_D and trigger exact native evaluation.

### 1.7 Density design and manufacturability: MMDO

Port DensiCrafter's differentiable density logits, mass penalty, COM/contact losses and surface-protection idea as a separate module. Generalize fixed 64^3 assumptions, remove global CUDA state, replace wraparound torch.roll boundary behavior, make gravity/support frame explicit, and separate non-differentiable topology extraction from differentiable density optimization.

Connect the resulting density field to W6 material integration: compute fixed and variable material moments separately, then use W6's exact/learned moment machinery to evaluate the Spin objective. DensiCrafter's contact stability is not a general strength solver.

Add mechanics as a separate optional branch: validated FEM/PINN or a source-verified stress-constrained neural field. The September 2026 differentiable graph neural field paper for manufacturable stress-constrained topology optimization and the July 2026 PI-GINOT hyperelasticity preprint are method references; verify code/license and reproduce before adopting. No strength claim from mass/COM/contact alone.

## 2. Candidate-by-candidate integration policy

| Candidate | Target module | Action | Current constraint/status |
|---|---|---|---|
| P-CRAFT U-FNO | Dense-grid spectral expert | Preserve as baseline and ablate improvements | Existing W6 adaptation; original source is internal and not root-license-cleared for redistribution |
| NeuralOperator GINO/FNOGNO | Geometry encoder/operator | Keep current adapter; add matched GINO/FNOGNO baselines | MIT; current adapter smoke passed, not trained |
| NeuralOperator UQNO | Uncertainty head | Keep wrapper; calibrate on held-out labels | MIT; no Spin calibration yet |
| QuadrANN | Learned quadrature | Train and compare under equal teacher budget | MIT; 3D smoke passed, untrained |
| Algoim | Independent exact/numerical reference | Expand plane/sphere/quadric and Spin-specific paired tests | Custom BSD-style; current sphere smoke passed |
| Transolver++ | Physics-attention expert | Add independent adapter and matched ablation | MIT; not integrated |
| PhysicsNeMo GeoTransolver | Geometry-attention expert | Add adapter and multi-scale geometry context | Apache-2.0; not integrated |
| PhysicsNeMo DoMINO | Multi-scale surface/volume encoder | Add only if it beats GINO/GeoTransolver on cost/error | Apache-2.0; not integrated |
| PhysicsNeMo FIGConvNet | Factorized point-grid encoder | Compare with DoMINO; avoid redundant dual production branches | Apache-2.0; not integrated |
| PhysicsNeMo MeshGraphNet/VFGN | Mesh graph dynamics/geometry | Evaluate for unstructured mesh features and mechanics branch | Apache-2.0 framework; task suitability must be demonstrated |
| PhysicsNeMo active learning | Teacher query strategy | Adapt strategy utilities after W2 labels admitted | Apache-2.0; no admitted W2 training labels |
| PhysicsNeMo GLOBE/AeroJEPA | Boundary/representation pretraining | Research-only ablation after stable P0/P1 adapters | Experimental APIs; avoid core dependency until stable |
| fVDB | Sparse voxel/SDF backend | Prototype API in cloud; CUDA benchmark locally | Apache-2.0; local GPU required for performance |
| Kaolin | Mesh/SPC/SDF conversion | Preprocessing comparison against fVDB/dense voxel | Apache-2.0; not integrated |
| PyTorch3D | Mesh sampling/geometry utilities | Reuse narrow sampling utilities | BSD-style; not a solver |
| PyG | Graph substrate | Dependency, not a separate model contribution | MIT; use as dependency where required |
| e3nn | Equivariant layers | Add rigid-rotation covariance ablation | MIT; not integrated |
| EqGINO | Equivariant geometry operator | Reproduce method and request/verify source rights | Root license unresolved; no copying yet |
| GINOT | Point-cloud geometry transformer | Add as strong irregular-geometry baseline after license review | CMAME 2026 paper; repository root license not verified |
| GAOT / GAOT-3D | Multiscale graph operator | Method comparison; seek permission before code import | Root license not found |
| PhysGTO | Manifold graph transformer | Method comparison; seek permission before code import | Root license not found |
| UNOP | Physics-constrained unsupervised operator | Reproduce integral constraints independently; verify license | README badge but root license missing |
| NQR | Adaptive neural quadrature | Reproduce design independently; seek license confirmation | SIGGRAPH 2026; root license not verified; assets/runtime required |
| TorchOpt | Differentiable optimization | Optional unrolled/implicit-gradient ablation | Apache-2.0; never replaces certified native Newton |
| torchquad | Integration baseline | Isolated environment/process benchmark only | GPL-3.0; do not vendor into W6 core |
| DensiCrafter | Density-field design/MMDO | Port losses and masks; generalize coordinates/resolution | MIT; source audited, adapter not implemented |
| 2026 stress-constrained differentiable GNN neural fields | Mechanics/topology design | Independently reproduce method; request code/data | September 2026 paper; code not verified in this audit |
| PI-GINOT | Physics-informed nonlinear mechanics | Evaluate as PINN/neural-operator mechanics reference | July 2026 preprint; not yet independently validated |
| Transolver-3 / Opt-RNO watchlist | Large geometry / optimization-aware operator | Track only until exact official repository and license verified | No verified reusable source in current audit |

## 3. Original research contributions to test

These are hypotheses, not completed results:

1. **Multi-Resolution Geometry-Conditioned Moment Operator (MR-GCMO):** fuse dense spectral, surface point and sparse voxel features through a shared geometry latent interface; select experts by input complexity and latency budget.
2. **Convex Moment Potential (CMP):** predict a scalar coefficient-space potential and derive moments/Jacobian by gradient/Hessian in smooth certified neighborhoods.
3. **Event-Aware Uncertainty-Gated Quadrature (EA-UQ):** combine event distance, UQNO/ensemble uncertainty and NQR/QuadrANN-style adaptive sampling to allocate expensive integration work.
4. **Teacher-Budget-Aware Active Learning (TBAL):** select Cherchi queries by uncertainty, event proximity and expected optimization sensitivity, only after formal W0/W2 label admission.
5. **Moment-aware Manufacturable Density Optimization (MMDO):** couple DensiCrafter mass/COM/support objectives with W6 moment/inertia constraints and surface/wall-thickness constraints.
6. **Risk-Gated Exact Newton (RGEN):** neural proposals are accepted only after event, derivative-neighborhood and physical consistency checks; otherwise exact Cherchi/native fallback.
7. **Sparse-to-Dense Resolution Continuation (SDRC):** optimize/query on sparse coarse geometry, refine locally near high curvature/event/support regions, and verify conservation across resolutions.

Novelty must be established against the cited papers and baselines; do not claim novelty solely from combining named repositories.

## 4. Detailed work packages and acceptance gates

### WP0 — Reproducibility and source governance
- Freeze upstream commits, blob SHAs, licenses, dependency versions and third-party notices.
- Create one adapter package per upstream family; no broad unreviewed repository copy.
- Add import, unit, integration and performance smoke tests.
- Resolve the known pre-existing M1 density-gradient smoke failure separately; do not mask it in global suite results.
Acceptance: clean CI on pinned CPU environment; license/provenance manifest complete; no hidden training on import.

### WP1 — Canonical geometry/material contract
- Define coordinate frame, units, transform, material IDs, density semantics, surface/interior/support masks and content hash.
- Test equivalent geometry under rigid transforms and voxel resolutions.
- Keep mesh/voxel source identity and avoid lossy point-cloud conversion as the authoritative geometry.
Acceptance: round-trip and frame-transform tests; deterministic preprocessing; conservation checks.

### WP2 — Geometry/operator model tournament
- Baselines: current U-FNO, GINO, Transolver++, GeoTransolver, one of DoMINO/FIGConvNet, QuadrANN and exact numerical baseline.
- Same train/validation/test geometry families, coefficient samples, teacher-call budget, parameter budget and random seeds.
- Add GINOT/GAOT/PhysGTO only after permission is resolved; e3nn/EqGINO as an equivariance ablation.
Acceptance: held-out geometry and orientation results, ten-moment error, Jacobian directional error where labels admitted, cold/warm latency, peak memory and parameter count.

### WP3 — Quadrature and event certification
- Extend Algoim references to multiple boxes, regular quadrics, intersections and adversarial near-tangent cases.
- Compare learned quadrature proposals against independent references and Cherchi when W2 can provide formally admitted cases.
- Extend R4.2 event classification to multi-component/general implicit geometry; explicitly classify singular and topology-change neighborhoods.
Acceptance: false regular-event acceptance target zero on the enumerated test suite; derivative withheld for unresolved cases; independent moment agreement.

### WP4 — CMP and uncertainty
- Implement a convex-potential prototype in coefficient coordinates; test gradient/Hessian against analytic and finite-difference references.
- Compare direct moment/Jacobian heads against potential-derived outputs.
- Add UQNO/deep ensemble and split-conformal calibration on a held-out calibration split.
Acceptance: moment error, Jacobian directional error, Hessian symmetry/PSD where assumptions apply, calibration coverage and risk-coverage curves.

### WP5 — Adaptive teacher query
- Build a query pool from synthetic analytic/Algoim cases first.
- Rank candidate labels by uncertainty, event proximity, Newton sensitivity and expected value of information.
- Integrate actual Cherchi query accounting only after W2/W0 formal admission.
Acceptance: same label budget versus random sampling; show reduced held-out error or lower failure risk, not just lower training loss.

### WP6 — MMDO / DensiCrafter port
- Extract mass, COM, support-contact and surface-protection losses without importing TRELLIS/MuJoCo/Blender into W6 core.
- Generalize arbitrary dimensions, anisotropic voxel spacing, world transforms and gravity/support direction.
- Replace wraparound neighbor operations; test boundary gradients and finite differences.
- Add W6 moment/inertia objective and maintain separate fixed/variable material moments.
- Keep FEM/PINN stress constraints as a separate validated mechanics adapter.
Acceptance: DensiCrafter-only, W6-moment-only and coupled MMDO ablations; mass, COM, contact, surface deviation, moment residual and printability metrics.

### WP7 — Sparse/high-resolution backend
- Compare dense U-FNO, fVDB sparse representation and Kaolin SPC/SDF preprocessing.
- Add local refinement around surfaces, thin walls, high-curvature areas and event-sensitive regions.
- Benchmark 64^3, 128^3, 256^3 and 512^3 with peak VRAM, preprocessing/cache size and moment error.
Acceptance: accuracy-constrained speed/memory comparison; no extrapolation from CPU smoke to GPU claims.

### WP8 — Mechanics/strength branch
- Evaluate September 2026 differentiable graph neural field for stress-constrained manufacturable topology optimization.
- Evaluate July 2026 PI-GINOT physics-informed hyperelastic neural operator as a mechanics surrogate reference.
- Choose a validated FEM/PINN reference and define material constitutive law, loads, supports, stress/strain and failure criteria.
- Couple stress constraints to MMDO only after validation against FEM/physical tests.
Acceptance: displacement/stress error, equilibrium/traction residuals, compliance, safety factor and held-out load/geometry tests.

### WP9 — Real Spin end-to-end acceptance
- Test agreed Heart, Teapot, Noodles and multi-target cases with frozen inputs and identical stopping criteria.
- Measure full wall time, exact Cherchi calls, Newton iterations, fallback rate, terminal mass/COM/inertia/physical residuals and failure rate.
- Compare native exact baseline, current W6 U-FNO, best single expert, selected ensemble and full risk-gated system.
Acceptance: no correctness regression; lower end-to-end time at matched physical accuracy; all failures and fallback cases reported.

## 5. Execution order and cloud/local split

| Stage | Deliverable | Cloud CPU | Local 4090 / native | Dependency |
|---|---|---|---|---|
| S0 | source/license/dependency audit and adapter scaffolding | Yes | Optional | none |
| S1 | canonical geometry/material contracts and unit tests | Yes | Optional | none |
| S2 | GINO/U-FNO/QuadrANN/Transolver++/GeoTransolver CPU baselines | Small smoke and low resolution | Full training/GPU timing | adapters |
| S3 | Algoim analytic and event/quadric numerical references | Yes, CPU build | Native pairing recommended | exact reference |
| S4 | CMP, UQNO calibration, synthetic active learning | Yes, small datasets | scale training | synthetic labels |
| S5 | DensiCrafter/MMDO 16^3/32^3 prototype | Yes | larger grids | S1/S3 |
| S6 | DoMINO/FIGConvNet and graph/equivariant ablations | interface/small CPU | full GPU | license/adapter |
| S7 | fVDB/Kaolin 128^3–512^3 | API design only | Required | CUDA toolchain |
| S8 | FEM/PINN stress-constrained design | code/CPU small tests | Required for realistic cases | validated mechanics reference |
| S9 | Cherchi teacher training and Newton acceptance | blocked until admission | Required for native teacher | W0/W2 formal admission |
| S10 | Heart/Teapot/Noodles end-to-end benchmark | analysis/reporting | Required | all gates |

Cloud work should continue on code review, CPU algorithms, tests, synthetic datasets, small models, documentation and CI. Local 4090 is required for meaningful high-resolution GPU timing, fVDB CUDA validation, full TRELLIS generation and native Cherchi/Spin acceptance.

## 6. Fair comparison protocol

Every model comparison must freeze:
- same geometry source hashes and train/validation/test split by geometry family (not random voxel patches from the same object);
- same coefficient distribution, material density and coordinate normalization;
- same admitted teacher-label budget and same excluded diagnostic/event set;
- same model-selection budget, random seeds and stopping rules;
- same precision target and same end-to-end solver acceptance.

Report:
- ten raw moment absolute/relative errors and worst component;
- Jacobian directional derivative errors only on admitted smooth neighborhoods;
- event classification confusion matrix and false-regular acceptance;
- uncertainty calibration, risk-coverage and fallback frequency;
- cold geometry preprocessing, warm encoding, moment query and derivative query time;
- exact teacher calls saved, Newton iterations, full wall time and peak CPU/GPU memory;
- mass, COM, inertia, support/contact, surface deviation, wall thickness and, when a validated mechanics solver exists, stress/strain/compliance.

Do not report only neural forward latency or average loss. A model is promoted only if it wins at matched accuracy, risk, data and compute budgets.

## 7. Immediate next 3 milestones

1. **W6 architecture scaffold:** add canonical geometry/material contracts, model registry, adapter protocol, test harness and a configuration-driven expert tournament. Cloud CPU.
2. **MMDO D1–D3:** port DensiCrafter mass/COM/contact/surface-preservation losses with arbitrary resolution, coordinate-aware gravity/support frame and no-wrap boundary tests; connect to W6 ten-moment CPU integration. Cloud CPU.
3. **P1 operator expansion:** add Transolver++ and PhysicsNeMo GeoTransolver adapters, then DoMINO/FIGConvNet comparison. Cloud CPU smoke first; local GPU for meaningful scale.

After these three, add NQR-inspired adaptive quadrature and the convex-potential prototype, then active learning and sparse GPU backends. Do not start full Cherchi training until W2/W0 formal admission is recorded.

## 8. Explicit non-claims

- This roadmap is not evidence that all listed projects have been integrated.
- A source adapter or forward smoke is not a trained Spin model.
- DensiCrafter is not a general FEM strength solver.
- Algoim is not the authoritative Cherchi teacher.
- UQNO calibration is not a physical or derivative certificate.
- No neural Jacobian enters Newton unless the W0/W2/event gates explicitly admit it.
- No 43% material reduction, 512^3 performance or end-to-end Spin speedup is attributed to W6 without reproducing it on Spin's own test cases.
