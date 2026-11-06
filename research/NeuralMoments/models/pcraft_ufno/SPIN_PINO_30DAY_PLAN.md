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
## M2 result and M2b correction — 2026-11-06

- M2 cloud CI run 42189280656 passed. On the original unmasked head, 6^3 nodes / 8^3 grid / smoothing 0.02 improved held-out Jacobian relative L2 from 1.580 to 0.961 but worsened moment relative L2 from 0.425 to 0.511. The 16^3 grid configuration worsened the combined score to 1.466.
- Review found the first Spin-PINO learned quadrature weights were positive but not explicitly multiplied by sampled density/occupancy. This allowed atoms in empty space and weakened the intended discrete material-measure constraint.
- M2b now masks each PINO quadrature atom by density and occupancy at its spatial location, and adds empty-support and density-scaling tests. The same three-seed sweep is rerun to measure the effect.
- M2 pre-mask results are retained as an ablation; they are not overwritten or presented as post-mask performance.
## M2b result — support-masked quadrature selected

- The PINO quadrature head now multiplies each learned positive gate by sampled density and occupancy at the corresponding quadrature node.
- M2b three-seed sweep completed in workflow 42191687667. Selected configuration: 8^3 geometry input, 6^3 quadrature nodes, smoothing 0.02, 21,888 parameters.
- Held-out ellipsoid mean r relative L2 improved from 0.5112 (unmasked 6-node M2) to 0.2561; J relative L2 improved from 0.9614 to 0.8972. Mean r MAE 0.01693, J MAE 0.01891.
- The 16^3 / 4^3 configuration remains poor for Jacobian (relative L2 3.1908) and is not promoted.
- The model is still not Newton-ready: J relative L2 0.8972, labels are analytic vertical-plane P0 only, no Cherchi labels or arbitrary quadric certification.

## M3 started — same-data architecture tournament

- Added `spin_pino/tournament.py` to compare support-masked Spin-PINO (4-node parameter-matched and 6-node selected configs), W6 M7 Realizable U-FNO, and W5 voxel DeepONet.
- All models use the exact same analytic geometry-family fit/validation/test splits, coefficient inputs, r/J labels, seeds, Adam step budget and four-channel voxel input.
- The report includes parameter counts, held-out r/J error, per-component error and training time. Parameter counts are reported rather than artificially forced equal.
- This is a fair architecture comparison on the analytic P0 task; it is not a Cherchi/native Spin result.

## M3 result — same-data tournament completed

- GitHub Actions run 42192701882 passed the same-data tournament.
- The support-masked 6-node Spin-PINO has the best held-out moment r relative L2 (0.2561) but J relative L2 remains 0.8972.
- W6 M7 Realizable U-FNO has the best combined score (0.4651), J relative L2 0.4931 and lower parameter count (13,448 vs 21,888). W5 voxel DeepONet has r relative L2 0.7511 and J relative L2 0.6994.
- PINO remains the primary backbone. M7 is a comparator and source of candidate quadrature design, not a replacement.
- M3b next: port positive Gauss-Legendre quadrature nodes/weights from M7 into the PINO head as a selectable integration rule, retaining the PINO trunk, support mask and PINO physics loss. Compare against midpoint PINO under the same data protocol.


## M3b — borrow M7 Gauss-Legendre quadrature inside the PINO head

- M3 showed M7's best derivative accuracy and combined score. The selected response is to transfer only its positive tensor-product Gauss-Legendre quadrature nodes/weights into the P-CRAFT PINO head.
- `SpinPINO` now supports `quadrature_rule='midpoint'|'gauss'`. Both rules retain the same PINO U-shaped factorized-Fourier trunk, geometry-conditioned positive gate, sampled density/occupancy support mask, convex moment potential and PINO physics loss.
- Corrected the `grid_sample` coordinate port for tensors laid out as `[B,C,X,Y,Z]`: physical xyz nodes are converted to grid_sample's `(z,y,x)` coordinate order only at the sampling interface.
- Added tests for positive Gauss weights summing to volume 8 and for an asymmetric positive-X-only voxel support mask.
- M3b will compare midpoint-PINO vs Gauss-PINO on the same three-seed analytic split and retain W6 M7/W5 as reference baselines. No other backbone is promoted.


## M3b result — Gauss rule retained as a negative ablation

- The M3b same-data tournament passed its model and PINO unit-test jobs.
- Gauss-Legendre PINO (8³ / 6³ / eps 0.02) obtained held-out r relative L2 0.4727 and J relative L2 1.2022, worse than midpoint PINO (0.2320 / 0.8912).
- Therefore Gauss nodes are not promoted. M7's positive-measure/support constraint is retained, but its Gauss node distribution is not transferred blindly.
- M4 next: investigate PINO loss conditioning and gradient conflict, borrowing PI-CViT's PINO training diagnostics and TensorPILS's preconditioned-residual principle. PINO remains the backbone.


## M4 — PINO training conditioning (started 2026-11-06)

This work package borrows PI-CViT's findings on PINO loss balancing/gradient conflict and TensorPILS's preconditioned-residual conditioning principle, without copying their PDE-specific equations or replacing the P-CRAFT PINO backbone.

- `DiagonalMomentResidualPreconditioner` estimates per-component scales from the fit split only; validation/test data are never used to fit scales.
- `SpinPINOLoss` can normalize moment and Jacobian residuals by those fixed scales.
- `pcgrad_backward` measures raw task-gradient cosines and projects conflicting gradients among data, moment-physics and Jacobian-supervision terms.
- `conditioning_sweep.py` compares baseline M2b, diagonal preconditioning, and diagonal preconditioning + PCGrad using the same M2b configuration, seeds, data split, optimizer and step budget.
- This is a training-strategy adaptation; TensorPILS's Poisson/Allen-Cahn/Stokes PDE residuals are not imported, and PI-CViT's CViT backbone is not used.

Acceptance: compare held-out raw r/J metrics, gradient-conflict statistics, training time and seed variance. Promote only if it improves held-out errors or stability without worsening physics identities. No Cherchi labels or Newton admission are implied.


## M4 result — loss conditioning not promoted

- M4 workflow 42194697503 completed the three-seed loss-conditioning sweep.
- Baseline M2b: r/J relative L2 0.2320/0.8912; diagonal fit-split preconditioning: 0.3101/0.8963; preconditioning + PCGrad: 0.2898/0.8907.
- The diagonal preconditioner and PCGrad did not beat the baseline combined score. PCGrad increased CPU time from 2.53 s to 4.56 s.
- Gradient diagnostics show the current moment-physics residual gradient is nearly zero (~9.1e-17) because the chosen potential structure already satisfies the tested identities. Thus PCGrad has almost no useful data-vs-physics conflict to resolve.
- Decision: keep baseline loss as default; retain conditioning/PCGrad as optional ablations, not promoted.
- Next M5: borrow W6 M7's logistic realizable-atom moment/Jacobian head into the P-CRAFT PINO trunk. This targets the remaining Jacobian gap while keeping PINO primary.


## M5 — M7 logistic realizable-atom head transplant into PINO (started 2026-11-06)

M3 showed W6 M7's logistic realizable-atom parameterization has substantially better held-out Jacobian accuracy than the current smooth-hinge PINO head. M4 showed that loss preconditioning and PCGrad do not fix the gap on the present analytic dataset. M5 therefore transfers only the M7 moment/Jacobian formula into the P-CRAFT PINO model head:

- P-CRAFT UFNO3d factorized-Fourier U-shaped trunk remains unchanged and primary.
- Keep the support-masked positive quadrature weights predicted by the PINO geometry head.
- Add `moment_parameterization='logistic_atom'` with M7's projective sigmoid atom rule and analytic native-coefficient Jacobian.
- Preserve the smooth convex-hinge head as the baseline/ablation.
- For logistic atoms, use tangent-projected q-space Jacobian symmetry/PSD physics residuals, not the full smooth-Hessian constraint.
- Verify analytic Jacobian by central finite differences, complement identity, radial identity and tangent PSD.
- Run the same-data three-seed tournament against midpoint smooth PINO, Gauss smooth PINO, W6 M7 and W5 DeepONet.

Promotion requires lower held-out J error without unacceptable loss of r accuracy or a false physical-certification claim. The logistic-atom head is not itself a scalar convex potential, and its tangent PSD property does not certify the continuum/CAD Jacobian.


## M5 result — logistic realizable-atom head improves PINO Jacobian

- Same-data tournament run 42195661322 completed the PINO CPU test and M3 tournament jobs successfully.
- The optional logistic-atom head, transplanted from W6 M7 while retaining the P-CRAFT PINO trunk, achieved held-out r relative L2 0.2060 and J relative L2 0.3147 (three-seed mean).
- This improves on the smooth-hinge midpoint PINO (0.2320 / 0.8912) and the W6 M7 baseline (0.4372 / 0.4931) on the restricted analytic P0 task.
- Promote logistic-atom as the leading research head candidate, retain smooth-hinge and Gauss as ablations. The logistic head is not a scalar convex potential; use tangent-projected q-space structure constraints.
- Next: broaden geometry/orientation/event tests and compare inference latency/memory before any Newton or real Spin claim.


## M6 — rotation-covariance and exact cube-group augmentation (started 2026-11-06)

- Added exact transforms for Spin's native ten coefficients, ten raw moments and 10x10 Jacobian under rigid rotations.
- For x'=R x, construct T_R for moments and S_R for native coefficients; transform J as J'=T_R J S_R^{-1}.
- Added voxel rotation with correct XYZ-to-grid_sample coordinate mapping.
- Added the 24 proper signed-permutation rotations of the cube (a grid-preserving SO(3) subgroup) so occupancy masks can be rotated without interpolation/cropping ambiguity.
- Added training-only rotation augmentation and a separate held-out rotated-ellipsoid evaluation. The 30-day scope tests this exact subgroup first; arbitrary SO(3) is not claimed.
- M6 compares logistic PINO with and without cube-rotation augmentation on the same base splits/seeds/steps. The labels are transformed analytically, not re-evaluated through W2/Cherchi.

Acceptance: moment/quadric/Jacobian transform tests pass; augmentation preserves the geometry/data contract; rotated held-out errors improve without degrading unrotated results materially.

## M7 arbitrary-orientation generalization — started 2026-11-06

- M6 cube augmentation evaluated all 24 proper signed-permutation rotations. Augmentation changed held-out r relative L2 from 0.206012 to 0.205555 and J relative L2 from 0.314603 to 0.314324: a negligible improvement.
- Added deterministic Haar-SO(3) rotations using seeded unit quaternions, exact transformations of native quadric coefficients, ten raw moments and native Jacobians, plus trilinear voxel resampling on the fixed cube.
- Added tests for proper rotations, quadric evaluation covariance, moment/J transform shape and deterministic augmentation.
- The new arbitrary-SO(3) experiment must report voxel interpolation error separately; label transforms are exact, but resampled voxel geometry is not.
- M7 cloud CPU CI is pending. No arbitrary CAD or Newton certification is implied.
## M7b — corrected fair arbitrary-SO(3) comparison

- The first M7 experiment is exploratory only: its three conditions did not share the same rotated test distribution, and the rotated metric included original samples.
- M7b now fixes the evaluation protocol: no augmentation, cube augmentation and arbitrary-SO(3) augmentation all evaluate the same held-out geometries under the same deterministic SO(3) rotations.
- Only rotated test samples contribute to the rotated metric.
- Record voxel clipping fraction and soft occupancy mass ratio separately because trilinear resampling is not exact.
- Cloud CPU CI and three-seed comparison are pending. Do not draw conclusions from the first M7 comparison.