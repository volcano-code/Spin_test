# W4 P33-D — P30B local launch-chain consistency audit
Date: 2026-11-10
Branch: research/neuralmoments-w4-teapot-p1-20261019
Scope: static source audit and CI test authoring only. No host runtime, Docker, owner receipts, lock registration or Cherchi calls were executed.

## Source files inspected
- `P30/p30b_run_approved_native_pilot.sh` blob `6b23ba1988e27503b40fa192dc5bb04d7ccb6be8`.
- `P30/p30b_authority.py` blob `c9d7d69ff8ef0bf998043d5ae73021f1e8e9c767`.
- `P30/p30b_native_sampler.py` blob `d9bb932b3de1606086f1d3dd2002c8652d5217e1`.
- `P30/p30_neighborhood_preflight.py` blob `e64fd8386ff244fb46e566c627d45604a05ee741`.
- W4 scenario contract `P32/P32B_MUJOCO_SCENARIO_CONTRACT_20261109.json` blob `17d7f572ff9699dd7dc94ddd8d92ec0a6a7de9bd`.

## Important path-identity clarification
The wrapper uses `P27_RUN_REL=formal-m6-20261106T091202Z` for the host's prepared run directory containing `P21_PRERUN_LOCK.json`, `P20_NATIVE_SIX_PINS.json` and native-build modules.

The archive verifier uses `RUN=formal-m6-run-20261107T050117Z` as the internal root path *inside* the immutable P27 tar archive. These are different namespaces (host run directory vs archive member root), not by themselves a mismatch. The wrapper's PYTHONPATH and sampler's `p27_run_dir` both point to the host run directory; `verify_archive` and reconstructed tangent plan use the archive's own internal root.

## Cross-file checks encoded in P33-D
The new static checker validates:
1. Wrapper plan SHA equals `P30_PRIVATE_PLAN_SHA`.
2. Wrapper archive SHA equals `ARCHIVE_SHA`.
3. Wrapper core HEAD pin equals sampler `CORE_SHA`.
4. External lock SHA is checked against the separately registered reviewer value.
5. Exact W0/W2 receipt paths from authority code are required by the host wrapper.
6. Docker memory is 24 GiB with total memory+swap also 24 GiB; child requires host swap zero and cgroup swap.max zero.
7. Native modules are resolved from the host P27 prepared run directory and their three binary SHA pins are checked by the sampler.
8. P27 lock and six native/input pins are revalidated inside the sampler.
9. The archive is rehashed, its manifest/files/native M6 evidence are verified, and the 36-probe plan is reconstructed from the archived c/J evidence.
10. 12-point maximum, 15-minute per-point CPU limit, 60-minute total limit, and closed Newton/training/optimization/MuJoCo gates are retained.

## Added assets
- `P33/p33d_static_chain_audit.py`: source-only cross-file consistency checker.
- `P33/test_p33d_static_chain_audit.py`: unittest coverage for the host/archive path distinction, pinned 12-point/resource envelope and fail-closed scientific flags.
- Extended `.github/workflows/w4-p32-triangle-screen.yml` to compile/run P33-D tests and emit the static audit JSON alongside P32 geometry screen evidence.

## CI and runtime truth
The source and tests are committed, but GitHub combined status queries for recent workflow commits have returned empty status lists. Therefore this report does **not** claim the new workflow or P33-D tests passed. Inspect the actual Actions run before treating CI as green.

This static checker does not read local P27 files, measure host RAM/swap, inspect Docker, verify native binary bytes, inspect current owner branch HEADs, create/register the external lock, or invoke Cherchi. Those remain runtime checks in the local wrapper and child process.

## Current blockers
- W0 Teapot receipt: missing.
- W2 Teapot teacher receipt: missing.
- Independent robust M/F/D/S certificate and frozen contact/material/load contract: missing.
- External P30B reviewer lock: not registered.
- New Cherchi calls: 0.
- Newton/training/optimization/printability/MuJoCo before-after: not admitted/not executed.

## Next gate
1. Wait for independently committed W0 and W2 Teapot-specific diagnostic receipts.
2. Verify current owner branch HEADs and all receipt identities against P20/P27/P30 pins.
3. Obtain a separately registered external P30B lock SHA.
4. On the qualified local host, run the wrapper's host preflight (24 GiB cgroup, host/cgroup swap zero, pinned image and module SHA).
5. Only then run the diagnostic-only 12-point Cherchi pilot; preserve all attempts and failures.
