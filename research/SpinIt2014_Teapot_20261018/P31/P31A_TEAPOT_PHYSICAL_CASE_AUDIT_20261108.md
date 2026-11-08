# W4 P31-A — Teapot physical-case audit and owner review request
Date: 2026-11-08
Repository: volcano-code/Spin_test
Write branch: research/neuralmoments-w4-teapot-p1-20261019
Scope: W4-owned audit/request only. This file is NOT a W0 or W2 approval.

## Executive decision
**P31-A status: BLOCKED — physical case is not yet sufficiently specified or independently revalidated for W0 physical approval.**
The current P20 artifact is a mathematical/coordinate preregistration, not a validated physical Teapot solid. Do not start P30-B Cherchi native sampling, optimization, training, or physical claims from it.

## Evidence inspected
1. W4 `P20_native_request.json` (blob SHA1 `f3bca7bef1f207cb5b857848c9588543fb7e5a9c`).
   - M/F/D/S counts: M 4035 vertices / 8070 faces; F 4235 / 8470; D 200 / 400; S 258 / 512.
   - Geometry policy: frozen binary64 OBJ, no repair/weld/scaling; Cherchi reference construction; CGAL Nef only as independent owned-set checker.
   - Proposed unit mapping: 0.025 m/reference and 1200 kg/m^3, but `physical_parameters_approved=false`.
   - Spinning-top axis [0,0,1]; `support_points=[]`.
   - Wall requirement 1/32 reference unit applies only to newly carved boundary vs original boundary, explicitly not global printability.
   - W0/W2 admission, physical validation, optimization and MuJoCo before/after flags are false.
2. W4 `P20_EXACT_FRAME_AND_PHYSICS_REPORT.json` (blob SHA1 `16a4b4cdf7c1dc6a2de314f22ebbee95364b9c04`).
   - Status `P20_EXACT_MATHEMATICAL_PHYSICAL_CONTRACT_READY_NOT_NATIVE_ADMISSION`.
   - `native_dispatch_performed=false`; `spin_artifact_problem_constructed_by_this_module=false`.
   - `source_meshes_reintegrated=false`; `P19_geometric_proofs_reexecuted=false`.
   - Target frame is `INPUT_NORMALIZED_TARGET_V1`; the frame report explicitly says native length scale is bbox-L, not the proposed SI 0.025 m scale.
   - The report preserves the tip translation residual and says physical parameters/material are not approved.
   - Exact affine raw-moment replay is algebraic evidence; it does not certify the actual Boolean regions or embedded closed solid.
3. W4 P30-B M22 report states 20/20 sampler unittests + 17/17 frame tests passed, but zero genuine Teapot tangent samples (0/12), zero new Cherchi native calls, and no native 24-GiB pilot.
4. W4 P30-B authority code requires two tracked owner receipts:
   - W0 `research/NeuralMoments/contracts/P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json`
   - W2 `research/NeuralMoments/teacher/P30_TEAPOT_FEATURE_PILOT_AUTHORIZATION.json`
   Direct fetch of both exact paths on their designated branches returned NOT_FOUND in this audit.
5. Public historical context: the University of Utah Teapot history describes the 1975 model as 28 Bézier patches, with no bottom/interior and intersecting handle/spout patches. The 1975 graphics model therefore cannot be treated as a watertight printable physical solid without a separately documented solid reconstruction. Official source: https://graphics.cs.utah.edu/teapot/ and https://graphics.cs.utah.edu/teapot/The_Return_of_the_Utah_Teapot.pdf.

## Physical-case decision
There are two defensible project interpretations. W0 must select and own one before authorization:
- **A — historically faithful physical Melitta teapot reconstruction.** Requires a traceable scan/CAD or measured reference object and a documented solid reconstruction. The historical 1975 patch model is not itself that solid.
- **B — explicitly new, Utah-Teapot-inspired spinning-top test article.** Requires W0 to state that this is a new engineered design, freeze its own geometry and dimensions, and approve material, manufacturing process, support/contact and loading conditions. It must not be described as the original Melitta teapot or as author-authentic CAD.

No silent mixing of A and B. The current 0.025 m/reference and 1200 kg/m^3 values are proposals only, not measured or approved facts.

## Required W0 owner decisions and evidence
W0 must provide a tracked, signed-by-ownership (Git-committed) review receipt covering:
1. Selected interpretation A or B and the exact source geometry SHA256(s).
2. Geometry audit: closed/watertight boundary, orientability, connected components, self-intersections, duplicate/nonmanifold faces/edges, boundary loops, genus where meaningful, and exact F/D/S set-membership predicates.
3. F/D/S definitions and disjointness/containment proof; confirm shaft S is already included in F and never double-counted.
4. Physical coordinate frame, measured/declared dimensions and uncertainty, axis, tip, support/contact points and support geometry. Current support list is empty; no inferred contact points are acceptable.
5. Material identity, density with source/uncertainty, print process, infill, shell/wall settings, anisotropy assumptions and temperature/moisture assumptions if relevant.
6. Load cases and D-region structural requirements: gravity/spin speed/angular acceleration, shaft/contact loads, allowable stress/deflection/safety factor and failure criteria.
7. Whether the 1/32 reference-unit carve-wall rule remains only a local geometric constraint or is supplemented by a global minimum wall/strength requirement.
8. Explicit scope of any diagnostic-only 12-point Cherchi pilot. This receipt must not grant Newton, optimization, training or printability admission.

## Required W2 independent review
W2 must independently inspect the exact same frozen W4 source/material and W0 receipt, and publish its own Teapot-specific receipt bound to:
- W0 receipt SHA256;
- P20 request, P27 manifest, P30 plan, native c/Jc identities;
- exact source feature-branch hash;
- same-call Cherchi source/Boolean/integration/derivative provenance;
- branch changes, undefined derivatives and failure records.
Heart/Noodles receipts are not substitutes for Teapot review.

## W4 next actions after owners respond
1. Re-fetch both owner branches and verify exact receipt paths and blob hashes.
2. Run P30B authority preflight against the actual owner branch HEADs and exact W4 materials.
3. Obtain an independent reviewer-registered P30B lock; W4 must not self-authorize it.
4. Only then run the 12-point diagnostic on the qualified local Docker host (24-GiB cgroup cap, host/cgroup swap zero, ≤60 min). Preserve all attempts.
5. Treat 12 finite points as diagnostic only. Smooth-neighborhood, Newton, training, global structural strength and MuJoCo before/after each need separate evidence and gates.

## Cloud/local boundary
Cloud: repository/source inspection, hashes, report/schema/test authoring, deterministic software tests, owner-receipt consistency checks, CI.
Local qualified host: actual native Cherchi sampling and full material/native geometry checks requiring the pinned binary/modules and 24-GiB/swap-zero Docker envelope; MuJoCo physical comparison after a frozen approved physical model exists.

## Explicit non-claims
This audit does not claim a closed Teapot solid, P20 native execution, Cherchi native tangent samples, W0/W2 approval, M6 certification, optimization, training, physical strength, printability, or MuJoCo optimized before/after validation.
