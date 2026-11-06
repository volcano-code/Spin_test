# W6 integration plan — from candidate pool to Spin-specific operator

## 1. Frozen task interface

All candidate encoders and heads must use one common interface:

- Geometry input: immutable source mesh/solid identity, density/material description, optional sparse voxel or surface representation, and source hashes.
- Coefficients: native c order (const, x, y, z, xx, yy, zz, yz, xz, xy); polynomial cross terms carry factor 2.
- Variable-domain output: r_D[10], J_D[10,10], uncertainty, event state, source identity and timing.
- Fixed material output: r_F[10], computed/cached separately.
- Total output: r_total = r_F + r_D; J_total = J_D.
- Invalid, event, unknown or uncertified derivatives must be withheld. The exact native solver remains the fallback.

Never merge historical W2 diagnostics into training data. Current W2 M22 reports one native diagnostic run but zero admitted training samples.

## 2. Original W6 innovation hypotheses

These are proposals to test, not completed contributions.

### A. Geometry-conditioned convex moment potential

Let q = Bc be the monomial coefficient vector and m(x) = [1,x,y,z,x^2,y^2,z^2,yz,xz,xy]. For a variable material region D, define the exact target potential:

Phi(D,q) = integral_D rho(x) max(q^T m(x), 0) dx.

For a smooth regular coefficient neighborhood:
- r_D(q) = grad_q Phi(D,q);
- J_q(q) = Hessian_q Phi(D,q);
- J_q is symmetric positive semidefinite in the ideal exact model;
- convert back to native coordinates using the frozen W0 contract, J_q = J_c B^{-1}.

Train a geometry-conditioned convex potential head (e.g. an input-convex network or positive convex basis) rather than predicting r and J independently. This is a candidate structural innovation: it should reduce inconsistent Jacobians and make derivative tests meaningful. It does not certify CAD provenance, smoothness or topology. R4.2 event classification and W0/W2 admission gates still decide whether J_D may be used.

### B. Event-aware derivative gate

Use R4.2 exact-rational stratum events as the first gate for box domains. Extend the event classifier to general quadrics and real geometry. On zero-stratum events, singularities, unresolved strata or untrusted neighborhoods, set J_D=null, exclude the sample from derivative training and fall back to exact native evaluation.

### C. Geometry-aware adaptive quadrature

Compare:
- Algoim as an independent implicit-geometry quadrature reference;
- QuadrANN as a learned point-cloud quadrature baseline;
- NQR as a paper-level autoregressive adaptive-sampling design until its code license is resolved;
- Cherchi as the authoritative teacher for Spin.

Learned quadrature may propose points/weights, but it must preserve positivity/normalization and be checked against independent exact moments and Jacobians. Never use its own output as the sole label oracle.

### D. Teacher-budget-aware active learning

Use UQNO/ensembles for uncertainty and PhysicsNeMo active-learning strategy patterns for selecting the next expensive teacher queries. Score a candidate query using calibrated uncertainty, distance to R4.2 event boundaries, predicted Newton-step sensitivity and expected reduction in terminal optimization risk. W2 must formally admit labels before this becomes supervised training.

### E. Multi-resolution geometry cache

Compare dense 4-channel voxel D, GINO/GeoTransolver mesh encoding, FIGConvNet/DoMINO point-grid encoding and fVDB sparse SDF/voxel features. Separate cold geometry preprocessing, cached encoding, warm r query and warm J query. The cache key must include geometry bytes, density/material identity, voxelization policy and model version.

### F. Equivariance and optimization-aware training

Test e3nn/EqGINO-inspired rotation equivariance, but separately enforce the correct affine transformation law for raw moments. Use TorchOpt only for differentiable/unrolled optimization ablations; final acceptance remains the native Newton solver with exact fallback.

## 3. Staged execution

### Stage 0 — library and source audit (cloud CPU)
- Keep this registry pinned.
- Verify all license notices and transitive dependencies.
- Create thin adapters; do not vendor entire repositories.
- Resolve the pre-existing M1 density-gradient smoke failure independently.

### Stage 1 — CPU matched baselines (cloud CPU)
- Baselines: current W6 M7 U-FNO, W5 DeepONet snapshot, GINO, Transolver++, QuadrANN, and the exact/non-learned numerical baseline.
- Same source mesh/voxel channels, train/validation/test geometry split, label budget, parameter budget and seed schedule.
- Report ten-moment errors, Jacobian directional errors, physical checks, cold/warm latency and model size.

### Stage 2 — quadrature and event correctness (cloud CPU/native compiler)
- Compile the official pinned Algoim source and run independent plane/quadric/box cases.
- Extend R4.2 from a single axis-aligned box to multiple boxes and general quadrics.
- Include tangencies, repeated roots, face/edge/vertex events, near-degenerate cases and exact-rational adversarial fixtures.
- No J_D admission until finite-difference, analytic and independent native checks agree.

### Stage 3 — geometry encoder comparisons (cloud CPU then local GPU)
- Add GeoTransolver, GINO and Transolver++ adapters.
- Add FIGConvNet/DoMINO only after the mesh-to-point/grid contract is mapped.
- Add GAOT/GAOT-3D, GINOT, PhysGTO and EqGINO only after license permission is resolved.
- Keep one model per family for controlled ablation; do not stack all encoders.

### Stage 4 — sparse high-resolution geometry (local GPU)
- Benchmark fVDB and Kaolin against dense voxel input.
- Test 128^3, 256^3 and 512^3 only after memory budget and source geometry are fixed.
- Report peak VRAM, voxelization time, cache size, query latency and numerical error.

### Stage 5 — uncertainty and active teacher queries (W2-dependent)
- Start with UQNO/ensemble calibration on synthetic numerical references.
- Connect active-learning strategy to actual Cherchi query cost only after W2 has formally admitted teacher cases and W0/W3 certify smooth Jacobian neighborhoods.
- Maintain a strict excluded set for diagnostics and event cases.

### Stage 6 — real Spin acceptance (local native environment)
- Validate Heart, Teapot, Noodles and the agreed multi-target suite.
- Compare full optimization wall time and exact teacher-call count, not only neural forward time.
- Require identical terminal physical constraints and no degradation in failure rate.
- If confidence or certification fails, exact Cherchi fallback must preserve correctness.

## 4. Acceptance dashboard

For every model, report:
- ten raw moment per-component absolute/relative error;
- J_D component and directional derivative error;
- J_q symmetry and PSD diagnostics only where the smooth-continuum assumptions hold;
- false derivative-accept rate (target zero);
- event/unknown recall and false regular classification;
- uncertainty calibration and risk-coverage;
- teacher calls saved and fallback frequency;
- cold preprocessing, warm cache, r, J, and end-to-end time;
- CPU wall time, GPU wall time and peak VRAM;
- held-out geometry family, topology and material generalization.

A neural model is promoted only if it is more useful than the strong exact/numerical baseline at a fixed accuracy and risk budget.