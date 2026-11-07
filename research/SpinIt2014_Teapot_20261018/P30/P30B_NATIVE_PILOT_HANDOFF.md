# W4 P30-B — owner-locked real Cherchi tangent pilot (implementation + handoff)

## State, as actually tested on 2026-11-07

**SOFTWARE READY; REAL PILOT BLOCKED UNTIL INDEPENDENT W0/W2 DIAGNOSTIC AUTHORIZATION.**

- This W4 milestone implements `p30b_authority.py`, `p30b_native_sampler.py`, `p30b_run_approved_native_pilot.sh` and pure-Python regression tests.
- W4's GitHub Actions checks **20** negative/recovery tests and cross-window HEAD: the W0/W2 authorization files are **absent**. The current correct readiness result is `BLOCKED_WAITING_INDEPENDENT_W0_W2_APPROVAL`, exit code 3, new Cherchi native calls **0**.
- Existing P27 formal M6 and P28 exact arithmetic archive are immutable baselines; there is no reason to repeat those operations.
- The initial P30 `h=0.002` radian three-direction pilot (12 points) is a **proposal**, not W0-approved.
- This code is a versioned integration of the actual frozen P20 factory, the genuine `InProcessCherchiEvaluator.__call__`/same-call `material(c)` API, and immutable evidence pins. The real 12-point native path has **not** been tested; a software-only CI pass is not a native success claim.

## Owner and teacher handoff

W0 must publish the following *tracked* JSON file in the W0-owned contract folder on its independent research branch:

`research/NeuralMoments/contracts/P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json`

Example **schema only; not a valid W0 approval**:

```json
{
  "schema": "W0_TEAPOT_P30_DIAGNOSTIC_AUTHORIZATION_V1",
  "decision": "APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
  "source_w0_baseline": "5bab2eb2616df306906a6887a273f68acfa49320",
  "p20_request_sha256": "a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9",
  "p27_manifest_sha256": "3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773",
  "p30_plan_sha256": "fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc",
  "native_c_sha256": "57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca",
  "approved_physical_case": true,
  "real_support_tip_and_shaft_reviewed": true,
  "approve_real_native_pilot": true,
  "pilot_directions": [0, 1, 2],
  "maximum_real_native_points": 12,
  "step_radians": 0.002,
  "length_ref": 1.0,
  "density_ref": 1.0,
  "max_normalized_jacobian_error": 1e-8,
  "newton_authorized": false,
  "training_authorized": false
}
```

**Important:** `length_ref=1.0`, `density_ref=1.0` and `max_normalized_jacobian_error=1e-8` in this example are *placeholder proposal values*, **not** authorized physical tolerances. The independent W0 owner must derive and replace them from real physical units, available material and desired objective, or withhold the approval. The example must never be copied verbatim into W0 as a rubber-stamp authorization.

W2 must publish the following *tracked* JSON file in its own teacher folder:

`research/NeuralMoments/teacher/P30_TEAPOT_FEATURE_PILOT_AUTHORIZATION.json`

Required W2 fields: schema `W2_TEAPOT_P30_FEATURE_PILOT_AUTHORIZATION_V1`, decision `APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY`, P27 manifest SHA and P30 plan SHA, native `c` and 800-byte `J_c` SHA, the actual W0 approval **file SHA-256**, `feature_branch_policy=SOURCE_FEATURE_BRANCH_V2`, `base_feature_branch_sha256` matching the **independently reviewed** P27 base topology/feature token, `independent_feature_branch_reviewed=true`, `approve_real_native_pilot=true`. All `native_Jc_numerically_certified`, `smooth_neighborhood_certified`, `Newton_authorized` and `training_authorized` remain **false**.

This requires *actual owner-issued records*. Neither a W4-authored JSON nor a synthetic CI fixture is an acceptable substitute. Current GitHub Issues: [W0 physical #5](https://github.com/volcano-code/Spin_test/issues/5), [W2 Teacher #6](https://github.com/volcano-code/Spin_test/issues/6).

## Local preparation WITHOUT new native calls

Use the previously reviewed private archive and the original P30 package (never substitute a new plan with altered float rounding). Create **two separate, independently updated Git checkouts** for W0/W2 approval documents, not the frozen P27 W0 runtime checkout.

```bash
export P27_BASE="$HOME/Spin_test-W4-P27-20261106T080428Z"
export P27_ROOT="$P27_BASE/runs"

# Original hash-locked files from the private P27 and P30 download packages:
export P30B_PLAN="$P27_BASE/P30_UNEXECUTED_TANGENT_PLAN.json"
export P30B_ARCHIVE="$P27_BASE/P27_FORMAL_M6_EVIDENCE.tar.gz"

# Two NEW, independent review clones (not P27's frozen W0 worktree):
export P30B_W0_REVIEW_ROOT="$P27_BASE/review-w0"
export P30B_W2_REVIEW_ROOT="$P27_BASE/review-w2"

git clone --branch research/neuralmoments-w0-contract-20261019 \
  https://github.com/volcano-code/Spin_test.git "$P30B_W0_REVIEW_ROOT"
git clone --branch research/neuralmoments-w2-teacher-20261019 \
  https://github.com/volcano-code/Spin_test.git "$P30B_W2_REVIEW_ROOT"

# P30B is on an updated W4 checkout; do not change the original P27 lock:
export P30B_W4_ROOT="$P27_BASE/repo-w4-p30b"
git clone --branch research/neuralmoments-w4-teapot-p1-20261019 \
  https://github.com/volcano-code/Spin_test.git "$P30B_W4_ROOT"

# Read-only gate. Until W0 and W2 issue approvals, exit 3 (BLOCKED) is correct.
cd "$P30B_W4_ROOT"
P30="$P30B_W4_ROOT/research/SpinIt2014_Teapot_20261018/P30"
python3 "$P30/p30b_authority.py" --mode preflight \
  --w0-review-root "$P30B_W0_REVIEW_ROOT" \
  --w2-review-root "$P30B_W2_REVIEW_ROOT" \
  --plan "$P30B_PLAN" \
  --p20-request "$P30B_W4_ROOT/research/SpinIt2014_Teapot_20261018/P1/P20_native_request.json" \
  --output "$P27_ROOT/P30B_READINESS_FIRST_REPORT.json"
```

Do not treat the expected blocked exit as a software failure. If the owner receipts are absent, **stop**: no `p30b_native_sampler.py` or Docker pilot should be started.

## Only AFTER independently published W0/W2 approvals

1. Fetch the exact owner/teacher issue-resolved commits into those **separate** review checkouts.
2. Repeat `p30b_authority.py --mode preflight` with a NEW output path. The expected status changes to `DIAGNOSTIC_PILOT_APPROVALS_PRESENT_NOT_EXECUTED` only if all owner and teacher fields, Git blob identities and plan SHA match.
3. Run `p30b_authority.py --mode seal` with a NEW output path inside `P27_ROOT`, for example `P30B_PRERUN_LOCK.json`. It creates an *immutable proposal* that itself grants no new native/scientific admission.
4. **Independently record/review** `sha256sum P30B_PRERUN_LOCK.json`. Do not self-register it within a single script execution. Preserve both the W0/W2 Git refs and P30B lock bytes.
5. When the registered hash is known, configure `P30B_LOCK`, `P30B_EXTERNAL_LOCK_SHA256`, and a NEW `P30B_EXEC_DIR="$P27_ROOT/p30b-pilot-<unique-id>"`, then run `bash "$P30/p30b_run_approved_native_pilot.sh"`. Do not run before independent review.

The wrapper checks 60GiB-class host RAM/swap0, enforces a 24GiB/zero-swap Docker cgroup, loads P27 **existing binaries** (no rebuild), verifies actual P27 source/plan/pins/lock every worker, and runs a bounded maximum 12 samples (one source/Boolean/integration/derivative per fresh evaluator worker). The real 12 samples may require substantial time and must be serialized against all other native W0/W2/W4 jobs.

### How interrupted runs are preserved

Each sample uses `point-NNN/attempt-NNN/` and leaves `BEGIN.json`, `stdout.log`, `stderr.log`, same-call material, receipt and final attempt result when available. An incomplete or failed attempt is never silently marked successful. For an interrupted run, preserve all files and set `P30B_RESUME=1`; a new attempt is appended and valid previous successes are independently checked before being skipped. Do not delete or alter the original attempt files. The overall pilot has a 3600-second parent time limit, and individual workers have a maximum of 900 seconds; those limits are enforced on the batch process.

## Scientific limits / next decision

A 12/12 real **diagnostic** pilot is NOT an independent native set proof for all 12 points, a continuous derivative-neighborhood certificate, a terminal Newton convergence result, a trusted Teacher training dataset, printable physical object approval, or a MuJoCo before/after optimization video. Even a perfectly matching 100-entry Jacobian and W0 numerical tangent test only establish finite-sample arithmetic compatibility. The independent W0/W2 case/feature, derivative-neighborhood and Newton terminal gates remain closed until their separate authentic receipts.
