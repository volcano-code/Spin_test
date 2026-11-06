# Spin-PINO v1 — one-month constrained development plan

**Hard window:** 2026-11-06 to 2026-12-06 (30 days).  
**Primary rule:** P-CRAFT PINO/UFNO remains the only production backbone. Other projects are borrowed modules, optional adapters or comparison baselines; none replaces PINO.

## 1. What is being completed in 30 days

Target deliverable is a reproducible research prototype, not a claim that every original long-term Spin objective is fully production-certified.

By 2026-12-06 deliver:
1. A Spin-specific PINO model using the pinned P-CRAFT UFNO3d factorized-Fourier U-shaped trunk.
2. A PINO-style moment physics loss, with data supervision plus exact moment-potential identities.
3. Reproducible analytic/Algoim synthetic training and held-out geometry evaluation.
4. Matched comparisons against the existing W6 M13 U-FNO baseline, W5 DeepONet snapshot, and a small number of borrowed plug-ins.
5. UQNO/uncertainty and exact-fallback interfaces; no unadmitted derivative can enter Newton.
6. A small DensiCrafter/MMDO CPU prototype (16^3/32^3) connected to the same moment contract.
7. A local 4090 runbook and a final report with accuracy, latency, memory, failure and fallback measurements.

Not promised within this month: full 512^3 training, every one of the 27 candidate repositories ported, all permission-held models imported, general FEM/PINN strength validation, or formal Cherchi training if W0/W2 have not admitted labels.

## 2. Architecture freeze

### Core (must remain PINO)
- Primary trunk: P-CRAFT UFNO3d / F-FNO factorized spectral blocks and U-shaped multi-resolution encoder-decoder.
- Spin task head: positive geometry-conditioned quadrature weights feeding a smooth convex moment potential; output ten raw moments and analytic model Jacobian.
- PINO training: L_total = L_data + lambda_phys L_moment_physics + lambda_J L_admitted_J.
- Moment physics residuals: complement identity, projective radial identity, monomial-coordinate Hessian symmetry/PSD, and mass bounds.
- Geometry/material input: frozen four-channel geometry contract initially; do not expand to many modalities until the base task is stable.

Original P-CRAFT PINO elasticity loss is not reused verbatim: equilibrium and constitutive residuals for displacement/stress are not the governing equations of Spin's moment-integration task. The PINO principle is retained, while the physics residual is replaced with mathematically valid moment identities.

### Borrowed modules (strictly subordinate to PINO)

| Module | Borrowed project | 30-day use |
|---|---|---|
| Geometry adapter | GINO (already CPU-smoked), PI-GANO method, optionally one GeoTransolver/Transolver++ adapter | Optional geometry conditioning/ablation; PINO remains trunk |
| Quadrature proposal | QuadrANN (already CPU-smoked), NQR method | Optional positive node/weight proposal; compare to PINO potential quadrature |
| Independent reference | Algoim (already compiled and sphere-smoked), analytic plane/box references | Generate/verify synthetic labels; not Cherchi replacement |
| Uncertainty | UQNO (already CPU-smoked) | Residual-scale estimate and held-out calibration |
| Sparse geometry | fVDB/Kaolin | Interface design only; local CUDA smoke if time |
| Density design | DensiCrafter | Port mass/COM/support/surface losses into isolated MMDO package |
| Mechanics | stress-constrained GNN / PI-GINOT / FEM/PINN | Paper-level method review only; no full strength claim in 30 days |

Do not integrate DoMINO, FIGConvNet, GAOT, GAOT-3D, PhysGTO, GINOT and EqGINO all at once. Keep them in the candidate register; only one optional geometry plug-in is selected after the PINO baseline is stable. License/permission-held code is not copied.

## 3. Day-by-day milestones

| Dates | Milestone | Deliverable and exit gate |
|---|---|---|
| Nov 6–8 | M0: PINO source freeze and Spin-PINO core | Exact source pin, PINO feature trunk, moment head, SpinPINOLoss, CPU tests; PINO must be the primary model |
| Nov 9–12 | M1: reference data pipeline | Deterministic analytic plane/box and Algoim sphere/quadric samples; geometry-family train/val/test split; source hashes |
| Nov 13–16 | M2: first training loop | Train Spin-PINO on synthetic labels; 3 seeds; checkpoint, logs, loss decomposition and held-out metrics |
| Nov 17–20 | M3: fair baseline tournament | Compare current W6 M13 U-FNO, Spin-PINO, W5 DeepONet, GINO adapter and QuadrANN under same split/budget; select one optional geometry plug-in |
| Nov 21–23 | M4: borrowed module integration | Add at most one of GeoTransolver/Transolver++ as a feature plug-in; UQNO calibration and QuadrANN/NQR proposal ablation |
| Nov 24–27 | M5: MMDO prototype | DensiCrafter loss port, arbitrary grid-size/coordinate/gravity frame, no-wrap boundary tests, 16^3/32^3 moment coupling |
| Nov 28–Dec 2 | M6: local GPU/native handoff | Run 64^3/128^3 PINO and MMDO on 4090; collect peak VRAM/time; integrate Cherchi only if W0/W2 formally admit records |
| Dec 3–6 | M7: final v1 freeze | Three-seed results, ablations, failure cases, model card, reproduction commands, final GitHub release/commit and next-stage gap report |

## 4. Fair evaluation protocol

Freeze the same geometry hashes, material density, coefficient distribution, source labels, data split, random seeds, optimizer budget and stopping rules for all models.

Report:
- ten raw moment MAE/relative error, per component and worst case;
- Jacobian directional error only on independently admitted smooth cases;
- moment-potential complement/radial/symmetry/PSD residuals;
- UQNO calibration coverage and risk-coverage;
- cold geometry encoding, warm query and derivative latency;
- model parameters, CPU RAM, GPU VRAM and preprocessing time;
- exact reference/teacher calls and fallback frequency;
- end-to-end native Spin time only when the same local native environment and stopping criteria are used.

Do not compare only neural forward latency. Do not pool M13 results with old privileged-geometry M9 results or changed input/label protocols.

## 5. Teacher and derivative gate

The latest observed W2 state in the preceding project audit was diagnostic-only with zero admitted training samples and no admitted J_D. Recheck this at the start of M1 and before any training data import.

If W2/W0 admission is still blocked:
- use analytic/Algoim labels only for the synthetic method prototype;
- keep diagnostic W2 observations excluded;
- do not call the run Cherchi-supervised training;
- do not send any model Jacobian to Newton;
- complete all cloud-side model, loss, benchmark and MMDO work anyway.

If W2 formally admits a validated dataset during the month, add it as a separate dataset version with source manifest, exact native run IDs, validator receipt and derivative status. Do not silently merge it with synthetic labels.

## 6. Cloud/local split

**Cloud CPU:** source integration, model/loss implementation, unit tests, small 8^3/16^3/32^3 data, synthetic label generation, 3-seed CPU training, adapter smoke, uncertainty calibration, DensiCrafter loss port, documentation and GitHub CI.

**Local 4090:** 64^3/128^3 training and timing, any fVDB CUDA, TRELLIS/MuJoCo/Blender reproduction, high-resolution memory profiling and native Cherchi/Spin end-to-end acceptance.

Cloud can finish the code and low-resolution prototype. It cannot certify the user's local CUDA stack, native Cherchi Boolean implementation or 512^3 memory/performance.

## 7. Scope-control decisions

- PINO trunk and PINO-style moment physics loss are mandatory.
- GINO, Transolver, GeoTransolver, DoMINO and FIGConvNet are not alternative backbones in the final v1; they are optional adapters/ablations.
- QuadrANN/NQR may propose integration nodes/weights but cannot replace the PINO moment model or exact reference.
- UQNO estimates prediction residuals; it does not certify physical correctness or derivatives.
- DensiCrafter is a separate density-design module, not a PINO replacement and not a structural-strength solver.
- Full FEM/PINN stress constraints are deferred unless the validated mechanics reference and implementation are already available.
- Every milestone is committed to the W6 branch with tests, logs, changed-file list and a short gap report.

## 8. Month-end success definition

Success on Dec 6 means a PINO-centered Spin model can be trained/replayed on deterministic synthetic geometry, passes physics-identity tests, is compared fairly against the selected baselines, has a bounded uncertainty/fallback interface, and has a small MMDO integration prototype with reproducible evidence.

It does not mean the full long-term Spin research goal is closed if formal Cherchi teacher admission, arbitrary CAD/quadric derivative certification or native end-to-end acceptance remains blocked.

## M0 implementation status — 2026-11-06

- P-CRAFT UFNO3d-style factorized-Fourier U-shaped PINO trunk has been added under `spin_pino/`.
- Spin moment potential head and PINO-style moment physics loss are implemented.
- GitHub Actions run 42186600269 passed: Spin-PINO 9/9 tests; existing NeuralOperator/QuadrANN 8/8; Algoim C++ 1/1 with maximum absolute error 7.50e-11.
- This is architecture/identity smoke only; no Spin/Cherchi training or Newton admission yet.
- M0 status: implementation and CPU smoke passed; source license/ownership clearance and real training remain open.

## M1 implementation started — 2026-11-06

- Added `spin_pino/dataset.py`: deterministic exact-continuum P0 samples for boxes/spheres/ellipsoids, geometry-ID-disjoint fit/validation split, fully held-out ellipsoid test family, SHA-256 dataset receipts and explicit non-Cherchi label provenance.
- Added `spin_pino/train.py`: reproducible PINO training loop with data + moment-physics + analytic-Jacobian loss, 3-seed CLI, held-out metrics and optional checkpoints.
- Added `spin_pino/tests/test_dataset.py`: split/provenance smoke and a tiny CPU training smoke.
- Scope is deliberately restricted to strictly interior vertical-plane cuts, where the existing analytic reference supplies exact r and J. General quadratic cuts and W2 labels are not silently mixed into this first dataset.
- CI validation for this M1 addition is pending.
## M1 validation result — 2026-11-06

- Dataset family/identity split tests and tiny training smoke: **11 passed, 0 failed**.
- Full three-seed analytic CPU training completed in GitHub Actions run 42188044841; all jobs succeeded and checkpoints/report were uploaded as artifact 13488726149.
- Dataset: 52 fit samples, 12 validation samples, 16 held-out ellipsoid samples; 8^3 geometry input; exact analytic vertical-plane r/J labels only.
- Mean held-out ellipsoid r MAE 0.04069, J MAE 0.03461; mean relative L2 r 0.4250, J 1.5802. These are preliminary and not yet satisfactory, especially for J.
- M1 is functionally complete, but M2 must improve resolution/quadrature/smoothing and compare against the frozen W6 M13 U-FNO baseline before claiming useful predictive performance.
## M2 implementation started — controlled PINO refinement

- Parameterized the existing Spin-PINO training loop by grid resolution, positive quadrature node count and convex-potential smoothing.
- Added `spin_pino/sweep.py` with three matched configurations: baseline 8^3/4^3/0.04; 8^3/6^3/0.02; 16^3/4^3/0.02.
- Added a three-seed, 120-step cloud CPU sweep job with retained JSON artifact.
- Added sweep configuration smoke tests. The sweep uses identical seed splits and optimizer budget; selects by held-out r/J relative L2.
- M2 comparison to frozen W6 M13 U-FNO and W5 DeepONet remains a separate mandatory subtask; no alternative backbone replaces PINO.