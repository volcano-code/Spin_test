# W4 P32-C — reproducible mesh-screen source and CI wiring
Date: 2026-11-09
Branch: research/neuralmoments-w4-teapot-p1-20261019

## New source assets
- `P32/p32_triangle_screen.py`: standalone deterministic OBJ reader, pinned Git blob SHA1 checks, AABB sweep, floating-point triangle SAT, coplanar in-plane axes and contact-locus classification.
- `P32/test_p32_triangle_screen.py`: four unittest groups covering schema/fail-closed flags, source identities/counts, self-screen totals, cross-mesh screen and top/apex contact localization.
- `.github/workflows/w4-p32-triangle-screen.yml`: Python 3.12 push/dispatch workflow that compiles the script, runs unittest and emits a JSON diagnostic result.

## Source integrity
The script refuses to run if any frozen M/D/S Git blob SHA1 differs from:
- M `e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e`
- D `9820f3d73d15a4cdd0c504a0264f934aefd40df1`
- S `9fe9f78257c7a90970095f6bb54c5148198a33d1`

## Test expectations
- M/D/S nonincident self-pair counts: 10,160 / 439 / 580; expected SAT hits 0 for each.
- M-D and D-S AABB candidates: 0.
- M-S AABB candidates: 6,580; expected SAT hits: 2,144.
- M-S contact localization: 1,120 top-plane pairs, 1,024 common-apex pairs, 0 other pairs.
- Every output explicitly keeps `robust_solid_containment_certified=false`, `scientific_admission=false`, and `printability_certified=false`.

## CI verification state
The workflow file and script/test files were committed to the W4 branch. The GitHub combined commit-status endpoint for workflow commit `3974b59f6fdbac221773a5d56eea63e012db54fa` returned an empty status list at the time this report was prepared. Therefore **no CI PASS is claimed yet**. The workflow should execute on the branch push; its run must be inspected in GitHub Actions before calling this test suite green.

## Critical limitations
This is a reproducible *floating-point diagnostic screen*, not an exact or robust geometric certificate. Its tolerances are fixed in source. It cannot certify embeddedness, exact solid containment, Boolean equality, watertightness under a robust kernel, or contact stress. W0 must independently verify M/F/D/S with a robust kernel and issue the owner receipt. W2's Teapot-specific teacher receipt remains independently required.

## Gate
- Reproducible source and tests committed: **YES**.
- Workflow committed: **YES**.
- Workflow run confirmed: **NO / status not yet reported**.
- W0 Teapot diagnostic receipt: **MISSING**.
- W2 Teapot teacher receipt: **MISSING**.
- P30B native Cherchi calls: **0**.
- Optimization/Newton/training/MuJoCo baseline-vs-optimized: **NOT EXECUTED**.
