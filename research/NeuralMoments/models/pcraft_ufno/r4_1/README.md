# W6 R4.1 — regular plane cuts, raw moments and derivative screening

This is an additive research artifact. It does not overwrite the frozen M13 branch content or claim native/Cherchi admission.

## Files
- `W6_R4_1_CODE_TESTS_BENCH.zip`: three implementation modules, two tests and the reproducible benchmark script.
- `REPORT.md`, `SOURCES.json`, `SUMMARY.json`, `benchmark_replay.json`, `tests.log`: review and replay evidence.

The code archive is an incremental patch for the R4 parent review package. Its modules use the existing `spin_pino.r2_material`, `r3_hard_quadric`, `r3_exact_plane`, `r4_reference_gate` and `r1_material_tree` modules. Extract the R4 parent archive first, then overlay the archive paths into that package root.

## Reproduction
```sh
python scripts/verify_r4_1_package.py
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python -m pytest -q tests tests_r0_r1 tests_r2 tests_r3 tests_r4
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python -m scripts.r4_1_benchmark --output /tmp/r4_1_replay.json
```

The package verifier requires the parent R4 manifest. Current cloud replay: 151 passed, 38 skipped, 0 failed. Benchmark replay: 36 fixed-seed cases. The algorithm covers regular plane cuts of disjoint constant-density axis-aligned boxes only; floating-point algebra is not an interval certificate. It is not arbitrary CAD, not a Cherchi teacher, and not admitted to native Newton. The local speed ratios are a plane-only CPU subtask comparison, not end-to-end Spin acceleration.

## Provenance
- W6 parent head at packaging: `870e972cbeca8866c0b729b2ceae44db64cc6893`.
- Code/test/benchmark archive SHA-256: `9d01d8711e6f12e1c0ef059a5229eadfb421837d43da74b4884035dbd12e26b9`.
- Original R4 parent archive remains an independent ChatGPT Library artifact; it is not copied into this Git commit.
