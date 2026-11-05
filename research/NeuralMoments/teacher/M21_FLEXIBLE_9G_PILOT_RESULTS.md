# W2 M21 — guarded 9 GiB Frozen Heart diagnostic pilot (2026-11-05)

**Repository:** `volcano-code/Spin_test`  
**Branch:** `research/neuralmoments-w2-teacher-20261019`  
**Scope:** `research/NeuralMoments/teacher/` only  
**Prior branch head:** `b52cb2af0260041900fc03560b5dc182cb088750` (W2 M20)

## What this milestone actually delivers

The 10 GiB + 2 GiB reserve pilot repeatedly stopped before native launch when the host had 9.900 or 11.648 GiB available (12 GiB startup threshold). A separate guarded 9 GiB profile was prepared with:

- `MemoryHigh=7 GiB`, `MemoryMax=9 GiB`, `MemorySwapMax=0`;
- 2 GiB host reserve, so the startup threshold is 11 GiB;
- `PYTHONINTMAXSTRDIGITS=100000` applied to preparation, scope worker and native child process;
- original module/source/archive/budget SHA checks, same-call material checks and independent ten-moment comparison retained;
- numerical tolerances unchanged; original native exit codes and training exclusion remain unchanged;
- no J_D release, no training admission, no formal M16 24 GiB admission.

The portable source/test package `W2_M21_Flexible_9GiB_Pilot.zip` is preserved as a separate conversation Library artifact (22,442 bytes; SHA-256 below). This GitHub commit publishes the audit report; it does not claim that the ZIP itself is already committed to the repository.

## Verification actually run for this package

- ZIP SHA-256: `b6aa86911dec125d4bbd3623ca7d3239d23142447b0c39c06faabb8e488936e4`.
- The package's own SHA256SUMS entries were checked against the extracted files.
- Re-ran the included Python test suite in the cloud execution container: **38/38 passed**, 0 failed, 0 skipped.
- Tests use a labelled M16 stand-in and fake systemd/cgroup interfaces. They validate policy arithmetic, launcher wiring, integer-conversion inheritance, failure preservation, unchanged numerical budgets and training isolation.
- These are software tests only: **no real Cherchi native evaluation was run in this cloud test**.

## Current native experiment status — not completed

The latest supplied 10 GiB local run reported `MemAvailable=11.6478577 GiB`, `Swap=0`, and required 12 GiB. It exited in preparation with `PILOT_REJECTED / HOST_MEMORY_NOT_QUALIFIED`; `PREPARATION_STOPPED_NO_NATIVE_LAUNCH`; no `M21_PILOT_RESULT.json`; no `M21_PILOT_LABEL.json`. This is a resource-gate rejection, not a Cherchi numerical failure.

The 9 GiB package's 11 GiB startup gate would have passed that earlier 11.648 GiB snapshot, but the user has not yet supplied a run of this 9 GiB version. A later live memory reading is required. Passing the snapshot does not reserve memory; the 9 GiB cgroup can still OOM if exact rational work exceeds its limit.

## Scientific status

- Historical W2 M20 Noodles recovery: 94 source components and 188 model/SI SHA identities revalidated; exact 96-operation CSG DAG reconstructed.
- Historical six exact rational F/D/A output packets remain unavailable; no new 96 native CSG operations and no fresh Cherchi teacher calls.
- Historical H8f 81-point and H8e 25-point physical moments remain offline re-verification of failed historical workflows, not new native teacher runs; derivatives are not certified.
- Current `J_D=null`, native teacher runs = 0, training samples = 0.
- W0/W3 independent smooth-neighborhood/Jacobian admission remains pending.

## Next action

Run this 9 GiB pilot once on the user's pinned Ubuntu W2 host only if the current `MemAvailable >= 11 GiB` and swap remains zero. Preserve the complete log and output directory. Inspect `M21_PILOT_RESULT.json`, `M21_PILOT_LABEL.json`, `independent_comparison.within_tolerance`, `failure_reason`, `memory_peak_bytes`, `memory_events` and postflight hashes. Do not interpret exit code 2 as numeric failure without reading the nested label, and do not convert a diagnostic pass into teacher/training admission.

**M21 verdict:** the guarded 9 GiB pilot software and tests are ready; a fresh real Heart Cherchi numerical result is still pending local execution.


## M21/M22 follow-up — corrected diagnostic exit semantics (2026-11-05)

A source-chain audit found that the original M21 diagnostic predicate could never accept the intended pre-W0 numeric-success path: `run_native_smoke.py` passes the explicit exclusion reason `W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED` into `evaluate_one`; that reason is stored as `payload.failure_reason`, and the child returns exit 2. The old M21 helper required exit 0 and a null failure reason. This was a status-semantics bug, not evidence of a numerical failure.

Corrected portable package: `W2_M21_Flexible_9GiB_Pilot_M22fix.zip`, SHA-256 `cdadbcb84ebbe6635a80bb83cca05f5da38ea5dbaba0675fd4346147ed6e4164`. The corrected gate accepts only the exact expected W0 exclusion with child exit 2 after validating the sealed payload digest, q/model/module identities, native Cherchi flag, same-call attachment, independent ten-moment tolerance, ten-vector shapes, `J_D=null`, and `split=excluded`. Arbitrary failures and attempted training/Jacobian promotion remain rejected.

Cloud software validation: **48/48 tests passed**, 0 failures, 0 skips, including 10 new status-semantics regressions. No real Cherchi native evaluation was run in cloud. The patch, regression test and detailed explanation are committed in `M21_DIAGNOSTIC_EXIT_SEMANTICS.patch`, `test_m21_diagnostic_label_semantics.py` and `M21_M22_DIAGNOSTIC_EXIT_SEMANTICS.md`.

This follow-up supersedes the earlier 9 GiB ZIP for the next local run. Fresh Heart Cherchi evaluation remains pending; `J_D=null`, training samples 0, and M16's 24 GiB formal admission remains unchanged.
