# W4 P33-A — read-only audit of W0's live native exact-material gate
Date: 2026-11-10
Repository: volcano-code/Spin_test
W0 source branch inspected: research/neuralmoments-w0-contract-20261019
W4 write branch: research/neuralmoments-w4-teapot-p1-20261019
Scope: read-only source-contract inspection; W4 does not modify W0 files and does not issue W0 approval.

## W0 source fetched
Path: `research/NeuralMoments/contracts/native_teacher_replay.py`
Git blob SHA1: `4ddd0250ad4a9803139fdd1948c8d4b4e31abf5f`.

The source's own module contract explicitly distinguishes:
- exact-rational numerical replay and indexed closed-surface checks;
- actual native Cherchi producer invocation;
- independent native exact-region subset verification;
- derivative-neighborhood and training admission.

The live entrypoint `audit_live_native_once(evaluator, problem, c, pins)`:
1. Requires the genuine `InProcessCherchiEvaluator` and `SpinArtifactProblem` types; mocks/duck typing are rejected.
2. Verifies externally frozen native, bridge, adapter, c, problem-input and evaluation-context SHA pins.
3. Prepares the fixed F material contribution independently once.
4. Requires a fresh evaluator with zero prior source/Boolean calls.
5. Makes exactly one Cherchi evaluator call; then replays the immutable same-call material without rebuilding the Boolean.
6. Checks exactly one source and one Boolean call occurred.
7. Reconciles same-call moment material and fixed F accounting.
8. Builds an exact-rational retained-region snapshot and an independent design-region snapshot.
9. Calls native `check_exact_material_subset(retained.exact_region(), design.exact_region())` and requires completed + subset true.
10. Records native stage timings, process RSS high-water mark and source/module/context pins.
11. Explicitly leaves smooth derivative proof and training admission false.

This is a useful existing W0 capability for the Teapot diagnostic gate. It is not by itself a complete Teapot physical approval, and the source does not claim to prove arbitrary self-intersection absence or printable contact strength.

## Teapot-specific extension W0 still needs
The current W0 live replay signature accepts one `SpinArtifactProblem`, one design mesh and the actual Cherchi material. The Teapot B design has additional semantics that must be bound into the W0 owner receipt:
- exact immutable M/F/D/S source blobs and their geometry SHA256 identities;
- the intended (M=F\cup D) and (F=M\setminus D) set relations, with exact native predicates rather than volume additivity alone;
- shaft S as a protected reference: certify whether S is in the closure of F, its top-cap/apex contact loci, and that it is not added as a second mass contribution;
- source M and material F embeddedness/self-intersection validation using the qualified independent robust kernel;
- physical coordinate transform and exact tip identity (P20 frame report currently records a represented-tip residual);
- contact choice: ideal point tip for diagnostic-only study, or a new finite-radius/flat pad with new geometry hashes and a new preregistration;
- material/load assumptions and explicit scope of the 12-point diagnostic-only pilot.

W0 should not infer these from W4's floating-point SAT screen or finite point sampling. Those are useful candidate evidence only.

## Existing evidence that W0 should consume
- W4 P31-B mesh topology and M/F/D boundary correspondence.
- W4 P31-C boundary-aware S containment samples (3,584 points).
- W4 P32-A custom triangle SAT screen (zero nonincident self hits; M/S contact candidates localized to top plane and apex).
- W4 P31-D conditional SI envelope.
- W4 P32-B MuJoCo scenario contract.
All remain diagnostic/conditional, not independent geometric or physical certificates.

## Exact owner authorization remains missing
The required W0 path is:
`research/NeuralMoments/contracts/P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json`
on `research/neuralmoments-w0-contract-20261019`.

The W4 authority validator additionally expects the W0 receipt to bind the frozen W0 baseline, P20 request SHA, P27 manifest SHA, P30 private plan SHA, native c SHA, approved physical case, reviewed tip/shaft, 12-point scope, step and per-case error budgets. It explicitly requires Newton and training authority false.

The exact W0 path was fetched on 2026-11-10 and returned NOT_FOUND. W0 authorization remains missing.

## Required W0 deliverable
W0 should publish its Teapot-specific diagnostic-only receipt after completing the independent robust geometry and physical-case review. It must not grant Newton, optimization, training or printability admission. If the point tip or 25 mm/reference / 1200 kg/m^3 proposals are not physically defensible, W0 should reject them and request a new preregistered geometry rather than silently overriding P20.

## Gate
- W0 live exact-material code exists: **YES**.
- W0 Teapot-specific robust M/F/D/S proof: **NOT YET PROVIDED**.
- W0 Teapot physical owner receipt: **MISSING**.
- W2 Teapot teacher receipt: **MISSING**.
- P30B native Cherchi calls: **0**.
- Optimization, Newton, training, printability and MuJoCo paired validation: **NOT ADMITTED / NOT EXECUTED**.

## Limitations
This report inspects source code only. W4 did not execute W0's native replay, CGAL/Nef, Cherchi or the local Docker runtime, and does not represent this source inspection as a geometry proof.
