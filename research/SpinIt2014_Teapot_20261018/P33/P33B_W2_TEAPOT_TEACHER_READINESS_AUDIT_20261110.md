# W4 P33-B — independent read-only audit of W2 Teapot teacher readiness
Date: 2026-11-10
Repository: volcano-code/Spin_test
W2 source branch inspected: research/neuralmoments-w2-teacher-20261019
W4 write branch: research/neuralmoments-w4-teapot-p1-20261019
Scope: source-contract inspection only. W4 does not modify W2 files and does not issue W2 approval.

## W2 source files actually fetched
1. `research/ParallelLaunch/W2_START_HERE.md`
   - Git blob SHA1: `208e2255cdd02f77bbb3853a72d0e9e020cf38b2`.
   - Confirms W2 exclusive write scope is `research/NeuralMoments/teacher/` and its tests; no public core edits.
   - Requires actual native Cherchi `r_D,J_D`, fixed `r_F) separately identified, full source/module/geometry identity, failure accounting, and no training release from hashes alone.
2. `research/NeuralMoments/teacher/native_cherchi_teacher.py`
   - Git blob SHA1: `d19ef43d3591ff5f8f69886512781d3d19f470d5`.
   - Module docstring explicitly calls it a **pre-W0 fail-closed teacher label adapter** and says no native Cherchi call is implied.
   - Defines ten-moment ordering, native matrix-entry coefficient convention and cross-term conversion (q=Bc).
   - `seal/verify` bind payload, model/module hashes, geometry, density, frame, (r_D,J_D,r_F), topology/derivative statuses, timing, memory and split.
   - Derivative label is rejected unless J exists, derivative contract exists and topology status is VALID.
   - This is a sealed label adapter, not evidence that a Teapot Cherchi call was made.
3. `research/NeuralMoments/teacher/test_native_cherchi_teacher.py`
   - Git blob SHA1: `0f24debe88bf701bd799c8fdd541cf28981a90b6`.
   - Covers an analytic closed-box reference, envelope round-trip, tamper rejection, wrong coefficient/model identity and invalid derivative rejection.
   - Its fixture explicitly uses `native_cherchi=False`; these tests are software-contract smoke, not a native Teapot teacher experiment.
4. `research/NeuralMoments/teacher/independent_reference.py`
   - Git blob SHA1: `25e44a4323fcb8b19ddf1be00e9421dd11dbf77a`.
   - Performs exact rational signed-tetrahedron integration for ten raw moments and per-component budget comparison.
   - Its module docstring explicitly states that closure/orientation does not certify embedding or legal Cherchi material.
   - This can be an independent numerical oracle only after exact rational geometry/Boolean boundaries are legitimately available.

## P33-B assessment
| Requirement | Current evidence | W4 assessment |
|---|---|---|
| Ten-moment order and cross-term convention | Explicit in W2 adapter | Software contract present |
| Label tamper/identity rejection | W2 unit-test source present | Test design present; this audit did not execute W2 tests |
| Analytic exact reference | Closed-box and signed-tetra reference | Reference implementation present |
| Real Teapot Cherchi (r_D) | No Teapot-specific native receipt observed | Missing |
| Real Teapot same-call (J_D) | No Teapot-specific native receipt observed | Missing |
| Teapot feature-branch identity | Must be tied to exact W4 feature branch and W0 receipt | Missing |
| Robust material/Boolean validity | W2 oracle explicitly does not certify embedding/Boolean legality | Requires W0 independent geometry certificate |
| W2 Teapot owner approval | Exact P30 Teapot receipt path not found on W2 branch | Missing |
| Training/optimization admission | W2 adapter is pre-W0 and fail-closed | Correctly not admitted |

## Required W2-owned next deliverable
W2 should, within its exclusive branch, produce a Teapot-specific review package that:
1. Reads the exact frozen W4 M/F/D/S OBJ blobs and P20 request/frame identities without changing them.
2. Waits for and pins the W0 diagnostic-only physical receipt SHA256.
3. Independently binds the exact Teapot source-feature branch and actual Cherchi source/Boolean/integration module identities.
4. On the qualified local runtime, records same-call (r_D,J_D), fixed (r_F) separately, exact reference comparison, topology/branch status, failure reasons, wall-clock and peak RSS. No mock/analytic label may be described as native.
5. Publishes the W2 receipt at `research/NeuralMoments/teacher/P30_TEAPOT_FEATURE_PILOT_AUTHORIZATION.json`, with Newton, training and optimization authority explicitly false.
6. Preserves every failure and refuses any Heart/Noodles receipt as a substitute for Teapot-specific review.

## W4 coordination and gate
- W4's exact decision and physical assumptions are in `P31/P31A_PHYSICAL_CASE_DECISION_20261108.json`.
- P20's `support_points=[]` and point-like shaft tip still require W0's explicit diagnostic-contact decision or a newly frozen finite-pad design.
- W0 authorization path was checked and remains missing.
- W2 Teapot authorization path was checked and remains missing.
- P30B native calls remain 0. No Cherchi sample, Newton, optimization, training, printability or MuJoCo paired run is claimed.

## Limitations
This is a read-only inspection of GitHub source blobs. It does not execute W2's tests, build native modules, evaluate Teapot geometry or call Cherchi. W2 owns its source changes and independent approval.
