# W2 M23-P2.2 — recover and pin exact planar-chain dependency

**Date:** 2026-11-09  
**Branch:** `research/neuralmoments-w2-teacher-20261019`

## Recovered source

The exact planar helper was found in the existing `volcano-code/Spin` main checkpoint, not reconstructed:

- Original: `experiments/faster_core_repair_20261012/exact_planar_patches.py`
- Original Git blob SHA-1: `7d6b1f8f20c1834e441fd622bb71e0339d77feb5`
- Original regression test blob SHA-1: `22a104a6a1ce7d64b4be5b606af7fb38eb14cd38`
- Vendored W2 source: `research/NeuralMoments/teacher/v7_exact_planar_patches.py`
- Vendored W2 test: `research/NeuralMoments/teacher/test_v7_exact_planar_patches.py`

The source is byte-for-byte the upstream file at fetch time. Its scope is exact coplanar oriented boundary-chain signatures and coplanar patch grouping. Its own documentation explicitly says it is not a mesh/solid admission test.

## CI

The W2 readiness workflow was extended to run both:
- the 4 Noodles rebuild-readiness tests;
- the 4 recovered exact planar patch regression tests.

First run `42574232458` failed because the vendored upstream test imported `exact_planar_patches` under its old module name. The test import was corrected to `v7_exact_planar_patches`.

Second run `42574289921`: **8/8 tests passed**, 0 failures, 0 skips.

[Successful CI](https://github.com/volcano-code/Spin_test/actions/runs/42574289921)

## Remaining source gap

The actual V7 CSG builder dependency `common.py` is still not recovered. The frozen `build_exact_v7.py` imports `ExactBuilder`, `obj_packet`, `packet_arrays`, `write_json`, `load_json`, and `export_obj`. The GitHub source trees inspected (Spin_test main, W0-W6, upstream branch, and Spin main) do not contain that module.

The exact planar-chain helper is now available within W2, so the external `exact_planar_patches.py` import can be removed from the historical chain verifier. This does not make the 96-operation builder runnable: `common.py`, the exact builder API, original CGAL executable and local source audit are still prerequisites.

## Execution

- No CGAL or Cherchi calls were made.
- No six-packet bytes were regenerated.
- No local disk scan was started.
- Local 96-op build readiness remains false until the exact source and resource gates pass.
- `J_D=null`, `split=excluded`, training samples = 0.

## Next

M23-P2.3: recover the original `common.py` from the user's local /data experiment history. Do not recreate it from guesswork. Verify its symbols, serializer format, exact backend invocation, cache receipts, and timeout/resume behavior against the original build receipts; then add synthetic tests before any full local build.
