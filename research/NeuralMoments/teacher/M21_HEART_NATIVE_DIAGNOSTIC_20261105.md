# W2 M21 — fresh Frozen Heart Cherchi numeric diagnostic result

**Date:** 2026-11-05  
**Repository:** `volcano-code/Spin_test`  
**Branch:** `research/neuralmoments-w2-teacher-20261019`  
**Run:** `heart-pilot9-flex-20261105T083338329274558-3159689`  
**Output directory on user host:** `/home/lin/w2-native-runs/heart-pilot9-flex-20261105T083338329274558-3159689`  
**Source of this report:** complete terminal output pasted by the user in the conversation. The run directory and raw JSON/log archive have not yet been uploaded for byte-level independent reinspection.

## 1. Execution and identity

- Corrected portable package SHA-256: `cdadbcb84ebbe6635a80bb83cca05f5da38ea5dbaba0675fd4346147ed6e4164` (matches the package checksum printed by the user's host).
- Frozen pilot spec SHA-256: `4d3cb03ee3a1190142638a99cd90e6aaf0a3e7030b956ef813ebabeb0c6898d0`.
- 9 GiB scope: `MemoryHigh=7 GiB`, `MemoryMax=9 GiB`, `MemorySwapMax=0`, host reserve 2 GiB, startup minimum 11 GiB.
- Host memory at prepare: 12.640 GiB available; second check 12.455 GiB; scope checks 12.534 and 12.490 GiB; swap 0.
- Native child exit code: **2**, because the frozen pre-W0 label deliberately carries `W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED`.
- Corrected outer pilot result: `PILOT_EXACT_TEN_MOMENTS_PASSED_DIAGNOSTIC_ONLY`; scope wrapper exit 0.
- Outer pilot wall time: 8.551563279 s; evaluator `w2_total_wall_seconds`: 4.380925502 s; independent reference: 1.865346236 s.
- `native_cherchi=true`; same-call material attachment present; source record unchanged; source/module postflight verified; postflight errors empty; timeout false.
- Reported cgroup memory peak: 657,793,024 bytes; `memory.events`: low/high/max/oom/oom_kill/oom_group_kill all zero.

## 2. Independent ten-moment comparison

The returned native `r_D` was compared against the independent reference under ten predeclared component absolute tolerances, each `1e-10`.

- `within_tolerance=true`
- all ten absolute errors: `0.0`
- maximum absolute error: `0.0`
- maximum normalized error: `0.0`

The reported vectors (order `m,x,y,z,xx,yy,zz,yz,xz,xy`) are:

```text
r_D = [
  0.4638104336177978,
  0.11380891271472827,
  0.000006229942231641098,
  0.49788671788739586,
  0.21579049823370836,
  0.013230611439409913,
  0.6273299733762362,
  0.000005767197693487517,
  0.10364849363769381,
  0.0000014185021973641493
]

r_F = [
  0.9354681998066362,
  0.20113280107708736,
  -0.0000025469023249884537,
  1.072217996696976,
  0.3222200512260602,
  0.061039627315812146,
  1.4818426821504391,
  -0.00000807031639062049,
  0.22090390707923943,
  -0.000003480336696153265
]
```

The evaluator stage timings reported (seconds): source 0.002303572; physical source boundary 0.031041180; prepare arithmetic boundary 0.034171960; Boolean 0.573648728; integration 0.161586852; derivative 0.237700993; intersection motion 0.237789063; material attachment serialization 0.050336808; independent reference 1.865346236. The derivative stage timing is **not** a derivative certification.

## 3. What is established

This is the first fresh W2 Heart run in the current campaign for which the supplied output reports:

1. actual Cherchi native execution (`native_cherchi=true`);
2. a same-call material attachment;
3. successful source/module postflight identity checks;
4. independent ten-component physical-moment comparison within the predeclared budget, with all reported binary64 absolute differences equal to zero;
5. no timeout or cgroup OOM event under the guarded 9 GiB diagnostic profile.

This is a substantial M21 milestone: **the Frozen Heart physical-moment diagnostic passed**.

## 4. What is explicitly NOT established

The label remains:

- `topology_status=OBSERVED_DISCRETE_MAP`;
- `derivative_status=UNKNOWN`;
- `J_D=null`;
- `failure_reason=W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED`;
- `split=excluded`;
- `training_admitted=false`;
- `formal_M16_24GiB_admitted=false`.

Therefore this result does **not** certify a smooth derivative neighborhood, a valid (10\times10) Jacobian, full material-solid embedding/Boolean semantics, Newton convergence, or training eligibility. The native child's exit code 2 is the intentional W0/solid-proof exclusion; the outer pilot correctly classifies the numeric ten-moment diagnostic as passed, not as a fully admitted teacher.

The cgroup peak is recorded as reported by the run. Do not extrapolate this single case's memory peak into a general resource guarantee for larger Noodles CSG jobs.

## 5. Evidence still requested

For byte-level independent audit, upload an archive containing the complete run directory and both logs:
- `/home/lin/w2-native-runs/heart-pilot9-flex-20261105T083338329274558-3159689/`
- `/home/lin/w2-native-runs/m21-flex-20261105T083338329274558-3159689.log`
- `/home/lin/w2-native-runs/m21-m22fix-20261105T083338Z-2114359.log`

Include `M21_PILOT_RESULT.json`, `M21_PILOT_LABEL.json`, frozen spec, native stdout/stderr, and postflight identity details. The present report is a faithful transcription of the user-supplied console output, not a claim that those local files have already been inspected.

## 6. Next W2 milestone

M22 should now perform the full byte-level audit of this run's label/report/spec, confirm all module/model/request hashes from the archived artifacts, and seal the Heart numeric diagnostic in the teacher manifest while keeping it excluded. In parallel, continue Noodles V7 six-packet exact F/D/A recovery and Boolean set-semantics proof. W0/W3 must independently certify derivative neighborhoods before any `J_D` or training split is released.

**Verdict:** M21 fresh Heart native physical-moment diagnostic = **PASS** on the supplied run output; formal derivative/material admission = **NOT PASSED**; training samples added = **0**.
