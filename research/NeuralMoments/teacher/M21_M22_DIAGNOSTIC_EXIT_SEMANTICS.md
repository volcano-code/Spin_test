# W2 M21/M22 — diagnostic exit-semantics correction and guarded Heart pilot package

**Date:** 2026-11-05  
**Repository:** `volcano-code/Spin_test`  
**Branch:** `research/neuralmoments-w2-teacher-20261019`  
**Write scope:** `research/NeuralMoments/teacher/` only.

## 1. Root cause found in the M21 diagnostic gate

The original M21 helper `verified_pilot_label()` required both child exit code `0` and `payload.failure_reason is None`. That condition is inconsistent with the actual pre-W0 diagnostic contract:

1. `run_native_smoke.py` calls `evaluate_one(..., split='excluded', exclusion_reason='W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED')`.
2. `cherchi_single_request.evaluate_one()` stores `failure_reason = failure or exclusion_reason`. Therefore a successful physical-moment evaluation intentionally carries the W0 exclusion string.
3. `run_native_smoke.py` returns exit code `2` whenever `failure_reason` is non-null, including this intentional admission exclusion.
4. The old M21 gate consequently rejected the exact successful diagnostic path it was designed to record.

This is a deterministic status-semantics bug found by tracing the actual source call chain, not an observed numerical failure. No historical evidence or shared W0/W1/W3/core source was modified.

## 2. Correction

The revised M21 `verified_pilot_label(exit_code, record, spec)` now treats the expected W0 exclusion as **diagnostic-only success** only when all checks pass:

- sealed envelope has exactly `payload`, `payload_sha256`, and `identity`;
- payload digest and q/geometry/model/native-module identity bindings match;
- native C, polynomial q convention, ten-moment order and schema match the frozen spec;
- `r_D` and `r_F` each contain ten finite values;
- `native_cherchi is true`;
- a same-call attachment exists;
- independent ten-moment comparison says `within_tolerance=true`;
- topology is `OBSERVED_DISCRETE_MAP`, derivative is `UNKNOWN`, `J_D=null`, and split remains `excluded`;
- child exit is exactly `2` and failure reason is exactly `W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED`.

The alternative no-exclusion path requires exit `0` and null failure reason. Arbitrary errors, wrong exit codes, tampering, failed comparison, non-excluded splits or any Jacobian remain rejected. The 24 GiB M16 formal admission gate is untouched. No `J_D` or training sample is released.

## 3. Cloud validation

- Original 9 GiB package SHA: `b6aa86911dec125d4bbd3623ca7d3239d23142447b0c39c06faabb8e488936e4`.
- Revised package SHA: `cdadbcb84ebbe6635a80bb83cca05f5da38ea5dbaba0675fd4346147ed6e4164`.
- Revised package ZIP integrity: passed.
- Revised package SHA256SUMS: every listed member matched.
- Full test suite: **48/48 passed**, 0 failures, 0 skips, 5.930 s.
- This includes the original 38 memory/launcher tests and 10 new status-semantics regression tests.
- New tests explicitly cover the expected W0-exclusion/exit-2 case, ordinary exit-0 case, arbitrary numerical failure, digest tampering, wrong spec identity, failed moment comparison, training split and attempted Jacobian release.

These are software and synthetic sealed-envelope tests only. **No real Cherchi native call was run in this cloud container.**

## 4. Updated package

The revised portable package is named `W2_M21_Flexible_9GiB_Pilot_M22fix.zip`. It includes the corrected driver, launcher, source reference, test suite, checksum manifest and test log. It is available as a conversation artifact; the GitHub branch contains the exact textual patch and regression test, not the binary ZIP itself.

## 5. Current scientific status

- Fresh Heart Cherchi evaluation: still pending local execution.
- Most recent supplied real host snapshot: 11.648 GiB available, swap 0; this meets the revised 9 GiB + 2 GiB prelaunch threshold, but it was measured before the 9 GiB pilot was run.
- A 9 GiB cgroup can still OOM after launch; the snapshot is not a memory reservation.
- Historical H8f workflow failure remains immutable.
- `J_D=null`; training samples remain 0.
- Noodles V7: 94/94 source parts and 940 independent exact source-part moment components are recovered; six exact F/D/A rational packets and fresh native teacher remain blocked.
- W0/W3 smooth-neighborhood/Jacobian certification remains pending.

## 6. Next operation

On the user's W2 Ubuntu host, use the revised package (not the earlier ZIP), verify its SHA256, set the reviewed manifest and ten-component budget paths, then run once with `W2_PILOT_MEMORY_GIB=9`, `W2_PILOT_RESERVE_GIB=2`, and `PYTHONINTMAXSTRDIGITS=100000`. Launch only when live `MemAvailable >= 11 GiB` and swap is zero. Preserve the unique output directory and log. Review `M21_PILOT_RESULT.json`, `M21_PILOT_LABEL.json`, `independent_comparison.within_tolerance`, `failure_reason`, `memory_peak_bytes`, `memory_events`, and all postflight hashes. A corrected diagnostic pass still does not constitute W0/W3 derivative admission or training release.

**Verdict:** M21's software status gate is corrected and tested; the real Heart Cherchi experiment is the next external execution dependency.
