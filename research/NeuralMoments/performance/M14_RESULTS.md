# W1 M14 — immutable native-build custody and honest admission scope

**Date:** 2026-10-20  
**Repository / writable branch:** `volcano-code/Spin_test` / `research/neuralmoments-w1-native-20261019`  
**Exclusive write scope:** `research/NeuralMoments/performance/` only.  
**Frozen ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Goal and original W1 gap

W1's original deliverable is **actual full Cherchi/Faster performance improvement** with
same-input, fully admitted 10 moments, 10x10 Jacobian, source/provenance,
accept/reject decisions, terminal partition and Newton end-to-end timing.
M1–M13 established genuine archived H8 analysis and regression tooling but **no
new native Cherchi Boolean or complete Faster solver A/B on this host**.
The archived failed H8e 25-point run retains an **unattributed 301.549423189 s**;
no archived cross-machine run is a legitimate way to assign it.

## Concrete M14 development

- Added `m14_native_build_custody.py`, a **read-only independent release gate**
  for a completed M13 host build + M11 five-call artifact directory. Requires
  a genuine W1 Git checkout descended from the frozen ancestor, no modified
  tracked production source, and no *committed* changes outside W1's performance
  folder (except original `research/ParallelLaunch/W1_START_HERE.md`).
- Rechecks Cherchi revision `7bd6c2697695f555f9a15d7e154e084d841316f0`
  and CGAL `f7c3c8212b56c0d6dae63787efc99093f4383415`, not merely a
  caller-supplied `pinned=True`; requires source trees to remain clean.
- Rehashes M13's **actual build-stage logs**, verifies exact core and Cherchi
  binary build targets, <=4 compile parallelism, all required CMake exact-
  geometry/GMP switches, and the unmodified-host shared Boost Ninja graph.
- Rehashes three newly built CPython native modules from the dedicated build
  directories and compares with M13 build receipt and M10/M11 real-native
  provenance; rejects stale/unrelated system `.so` binaries.
- Rechecks M11's five-call summary, H8c request/ZIP identity, exact complete
  saved-material/Jacobian receipts and independently invokes the strengthened
  M11 verifier. Only an exact real M11 match creates `admission.json`; every
  failure writes only `failure.json` with `full_solver_speedup=null`.
- Backfilled previously local-only `test_m13.py` to W1 so M13's original
  builder tests can be independently reproduced without an external bundle.
- Synthetic unit fixtures are explicitly **not** source/binary science proofs.

## Actual tests and native attempt

Ran four **sequential local groups**, saving full verbatim logs:

| Tests | Passed | Failed | Skipped |
|---|---:|---:|---:|
| M5, M6, M7, M8, M8 native paired | 51 | 0 | 0 |
| M9, M10 | 34 | 0 | 0 |
| M11, M12 | 24 | 0 | 0 |
| M13, M14 | 39 | 0 | 0 |
| **Total** | **148** | **0** | **0** |

`test_m14.py` adds **18 cases** with actual temporary Git repositories and
synthetic build fixtures, deliberately tampering with production commits,
non-W1 branch edits, staged/unstaged files, missing build stages, forged
logged times/binaries, wrong CGAL identity, five-worker builds, wrong H8
checkout, mutated M11 receipts, and output overwrite. All fail closed.

Ran `m14_native_build_custody.py` against **actual, genuine H8c archival ZIP**
SHA-256 `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7`
with the local `/mnt/data/W1_M14_work` folder as proposed W1 root. It exited
**1** because this is *not* a real W1 Git checkout: `M10_FULL_GIT_CHECKOUT_REQUIRED`;
its `failure.json` contains `verified_native_calls=0`, and no `admission.json`
was generated. The host cgroup cap is 4 GiB, zero swap; three native modules
are missing and `git ls-remote https://github.com/...` could not resolve DNS.
**No native CGAL/Cherchi build was attempted or reported successful**, and no
new Boolean, Jacobian, full Newton solve or end-to-end performance result was
obtained in M14. The true-native admission gate was exercised only on the
negative prerequisite path.

The first test assembly mistakenly restored M8's *older* native paired gate
instead of the updated M9 version, yielding 4 failures from missing `.calls`.
We restored the **exact M9 Git blob** `871ff1fc85ac7bd129d2a90c12bc1a912940af94`
from the archived M9 ZIP and reran all four groups; final 148 tests passed.
The intermediate run is not counted as success and did **not** modify GitHub.

## Host reproduction

Build the actual native modules on a prepared W1 host first using the already
committed `m13_pinned_native_build.py` and its frozen Cherchi/CGAL revisions.
Do **not** try this as a substitute for actual separate source, geometric and
Newton validation. Then point the new custody gate to the M13 output:

```bash
python research/NeuralMoments/performance/m14_native_build_custody.py \
  --root "$PWD" \
  --archive /path/to/h8c-reference-39118951636.zip \
  --m13-artifacts /path/to/w1-m13-real-native-output \
  --output /tmp/w1-m14-verified-custody-01
```

The gate is **read-only** to repository/source/binaries; the output folder
must be absent. It requires M13 `native-build-receipt.json`, all four source
build logs, `m11/m11-native-validation-summary.json`, `m11/work/preflight.json`,
M5 and M9 native proof directories and exact saved-material archives.
If absent, fail, don't fabricate a receipt. Build resource limits remain
<=24 GiB process address space, zero swap, <=4 compile workers, <=60 min per
heavy job, and no parallel heavy work with other windows (including W3).

## Still blocked, unchanged mathematical boundaries

- Need **real pinned native build** and actual M5+M9+M11 material runs; current
  4 GiB environment cannot satisfy the build host guard.
- No production Cherchi/Faster optimization has been admitted or installed;
  the isolated GMP validator speedup and post-Boolean provenance speedup do
  **not** prove full solver acceleration.
- Historical H8e original **8/24** changed feature hashes and failed status
  preserved. No smooth-neighborhood derivative or Newton seal claimed.
- W0 mathematical contract and W2 true-teacher production admission remain
  separate; a five-evaluation receipt is not a full Faster end-to-end A/B.
- Noodles V7 393.44s / 168.27s original same-run artifacts still not
  authoritatively restored. Do not combine them with historical 569.56s.
- No GitHub Actions workflow was modified or silently triggered. W1 exclusive
  file scope prevents adding a new `.github/workflows` trigger; remote CI cannot
  be claimed merely from locally passing Python tests.

**M14 conclusion:** one significant **build/source/evidence custody hole is
closed** with 148 real local passing regression cases. Actual W1 scientific
performance goals remain **blocked**, pending suitable native host execution.
