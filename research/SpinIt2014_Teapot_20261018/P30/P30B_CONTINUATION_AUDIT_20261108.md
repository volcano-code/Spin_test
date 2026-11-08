# W4 continuation audit — 2026-11-08

## Scope
This is W4 (2014 Utah Teapot conforming solid repair and optimization initial state), not W6.
Repository: `volcano-code/Spin_test`
Only write branch: `research/neuralmoments-w4-teapot-p1-20261019`
Task contract: `research/ParallelLaunch/W4_START_HERE.md`

## Verified state
- M22 software/frame integration is documented as PASS in `P30_M22_FRAME_INTEGRATION_REPORT_20261108.md`.
- The M22 report records GitHub Actions run 42472917746: 20/20 sampler unittests and 17/17 frame/transform pytest cases passed, zero skipped.
- That same report explicitly records 0 genuine Teapot tangent samples out of 12, 0 new Cherchi calls in that CI, no 24-GiB native pilot, and scientific admission false.
- P30-B remains fail-closed. Its authority code requires two tracked owner receipts:
  - W0: `research/NeuralMoments/contracts/P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json`
  - W2: `research/NeuralMoments/teacher/P30_TEAPOT_FEATURE_PILOT_AUTHORIZATION.json`
- Direct reads of both paths on their designated owner branches returned NOT_FOUND at this audit. Therefore P30-B correctly remains blocked; do not fabricate W0/W2 receipts in W4.
- The P30-B workflow is software/preflight evidence only. Its synthetic readiness test expects `BLOCKED_WAITING_INDEPENDENT_W0_W2_APPROVAL`, zero native calls and training disabled.
- The latest inspected P30-B workflow edit is commit `f324f532da1b3a62d59e6f6ed7e0f667ac6fdc7b`, which restores explicit 20-test unittest and 17-test pytest checks. The connector's commit-run lookup only exposes PR-triggered runs and returned none for this commit; this audit does not claim that edit has a fresh successful run.

## What is and is not complete
Complete: P20 initial F/D design-domain milestone; M22 native/SI frame software integration; prior MuJoCo diagnostic/software checks recorded in earlier evidence.
Not complete: formal M6 full-material acceptance; independent W0 physical-case approval; independent W2 Teapot feature/teacher approval; P30-B real 12-point Cherchi diagnostic; continuous smooth-neighborhood certification; Newton acceptance; training; physical-strength/printability validation; optimized-before/after MuJoCo comparison.

## Next gated sequence
1. W0 owner must publish the exact Teapot diagnostic authorization on the W0 branch after reviewing authoritative CAD or an explicitly owner-defined design, measured scale, material/fill, support/tip/shaft/contact/load, and D-region strength requirements.
2. W2 owner must independently publish the matching Teapot feature-pilot authorization on the W2 branch, bound to the exact W0 receipt SHA, P27 manifest, P30 plan, native c/Jc and reviewed feature-branch hash.
3. Re-run the W4 owner/teacher preflight and register the independently reviewed P30-B lock. Until then, new Cherchi calls must remain zero.
4. Only after both receipts and lock exist, run the 12-point diagnostic on the qualified local Docker host with 24-GiB cgroup limit and host/cgroup swap zero. Preserve every failed attempt.
5. A successful finite diagnostic is not smoothness/Newton/training admission. Those require separate numerical and scientific reviews.

## Cloud/local boundary
Cloud can continue source inspection, deterministic Python tests, CI wiring, provenance checks and report generation. The genuine native Cherchi pilot is explicitly designed for the qualified local Docker host and cannot be represented by a GitHub-hosted synthetic CI run. MuJoCo before/after physical validation also requires the actual approved physical model and corresponding runtime evidence.

## Safety of claims
This audit is a source/evidence reconciliation only. It does not claim a new native Cherchi run, a formal M6 pass, W0/W2 approval, Newton/training readiness, or successful physical optimization.
