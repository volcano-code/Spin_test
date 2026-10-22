# W1 V2 M24 — fix full Newton ABBA false-green / unverified Jacobian evidence

**Repository:** `volcano-code/Spin_test`. **Writable branch:** `research/neuralmoments-w1-native-20261019`. **Scope:** `research/NeuralMoments/performance/` only. Frozen ancestor `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Goal and concrete change

M23's full Newton runner existed locally but its core Python source and 20 tests were absent from GitHub. Those source, tests, baseline log and report were **first backfilled** to W1 commit `ce451e30a9bc31cf1c630d10c9aa2e7458ce035f` and their returned Git blob SHA checked. The backfill preserved original M23 negative native evidence.

A separate, **actually reproduced** M23 fail-closed bug was then corrected: `run_four` returned the explicit status `FAILED_NONCONVERGED` when all four synthetic child runs exited normally but had `solver_status != CONVERGED`, yet `main()` returned exit code **0** because it only treated `BLOCKED` or `FAILED` as failure. That could have produced a green workflow with **no converged Newton solver**. The corrected `main()` permits exit 0 only for the explicit `FOUR_NATIVE_RUNS_SAME_SCIENTIFIC_DIGEST_NOT_W0_W2_ADMITTED` diagnostic state, and exit 2 for every other state (including an unknown state). Exit 0 for that one state does **not** confer W0/W2 mathematical admission.

An independent evidence hole was also corrected. The old `audit_saved_newton_events()` verified each saved material file SHA and some moments but did **not** require the complete 10x10 `moment_jacobian` attachment. An adversary could remove the Jacobian, update the same-run journal SHA, and have the old lightweight summary accept it. The patched code requires every saved material to contain **100 finite numeric Jacobian entries** and **two complete finite ten-moment vectors**. It includes the complete Jacobian in the four-run strict material comparison, so a changed J cannot disappear from the equality test. This remains strict equality for diagnosis; W0's formal, independently precommitted tolerance and smooth-neighborhood certificate are NOT assumed.

Finally, the patched journal audit validates the actual production `record-verification.json` contents (not just file existence): `record_integrity_valid==true`, `saved_materials` equals observed map count, a strictly positive number of `accepted_updates`, `rejected_evaluations` equals observed rejected map count, and `core_admission==false`; it requires the terminal event to be `RUN_TERMINATED` with `CONVERGED`. It does not alter the existing original Newton solver, runtime evaluator, native C++ modules, source/Boolean geometry math or W0/W2 contracts.

## Reproduced defect: old vs patched (synthetic-only)

`evidence/m24-before-after-negative-reproducer.json` contains the actually executed original-M23/updated-M23 checks:

| Controlled negative | Old M23 | Patched M23 |
|---|---|---|
| Four child results report `FAILED_NONCONVERGED` to CLI | **Exit 0 (incorrect)** | **Exit 2** |
| Self-consistent SHA with missing 10x10 Jacobian and missing terminal/proof | **Accepted** | **Rejected** `M23_SAVED_FULL_JACOBIAN_MISSING_OR_NONFINITE` |

These are **synthetic receipt tests only**, not actual Cherchi native runs, not evidence of real Newton convergence or solver acceleration.

## Actually executed tests

- Baseline unmodified M23 tests were run from the genuine archived H8e ZIP: **20/20** passing before patch.
- Updated M23 tests cover the original tests plus **12 new positive and adversarial cases**: missing, short, NaN Jacobian; shortened ten-moment vector; invalid original record-integrity flag/count/accepted-updates; missing terminal; CLI nonconverged/unknown state; a complete fake four-child nonconverged parent; allowed successful *diagnostic* state.
- Independently replayed M22 13-test suite against the source-pinned M8 exact coordinate code and modified M23 32-test suite: **45/45 passing** without skips (`evidence/m24-combined-45-tests.log`). All original exact H8e CAD identity and archive SHA tests remain active.
- Re-invoked the **actual, source-authenticated** H8e native preflight with the real original Actions ZIP, SHA-256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`: status `BLOCKED`, CLI exit **2**, blockers are missing full W1 Git checkout, 4 GiB cgroup <6 GiB minimum, and all three native `.so` extensions. Saved exact output is in `evidence/m24-real-native-preflight.json`, `evidence/m24-real-native-failure.json`, `evidence/m24-real-native-attempt.log`. **No new native Boolean, full Newton call, nor end-to-end speed ratio was produced.**

## Scientific boundaries and next indispensable step

W1 M19 hierarchical profiling and M22 true native ABBA remain blocked by unactivated W1-only GitHub Actions workflow; W1 CI owner handoff is Issue #3. Independent W0 Jacobian math approval and W2 real teacher admission remain separate. The historic H8e 8/24 changed feature hashes and failed original Actions conclusions are preserved. All new file changes remain under W1's exclusive performance folder. This milestone closes actual code/CI false-green bugs and publishes runnable full Newton code, **not** the original Faster acceleration research goal.

On a properly pinned native host, first run real M19 profiling, then M22 old/new `M9` single-q ABBA and M11/M14 custody, and only then launch the M23 runner for complete four-process Newton comparisons. Capture real `.so` SHA, all evaluation/terminal records, W0/W2 review, accepted/rejected trajectories and complete wall time; never substitute synthetic fixtures or last-bit Jacobian repeatability for scientific admission.
