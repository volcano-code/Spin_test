# W1 M3 — Archived-real H8 provenance and GMP roundtrip study (2026-10-19)

**Only writable branch**: `research/neuralmoments-w1-native-20261019`. **Exclusive area**: `research/NeuralMoments/performance/`. Frozen main ancestor: `0bcc187b3005478baa586a6d6f450e73811ca342`. Neither production `src/`/`bindings/`, other windows, nor `main` were changed.

## What was actually executed

Locally built and ran a **standalone** C++17/GMP `real_h8_gmp_probe.cpp` on TWO genuine historical H8 Cherchi **archived** material packets retrieved from GitHub Actions, with balanced AB/BA repeats. Independently verified archival SHA-256, same-q and CAD identities, exact rational ten moments, binary64 moments against archived independent Fraction/native certificates, and target-frame translation. The full locally tested implementation, tests, and all original stage rows are preserved in the downloadable `W1_M3_real_H8_replay_bundle.zip` (not automatically a GitHub checkout file). Local tests: **11 passed / 0 failed / 0 skipped**; see `evidence/m3-tests.log`. No fresh Cherchi Boolean was executed. No full Newton solver run, no fresh exact self-intersection audit or derivative/Jacobian regeneration.

In this branch the separate `m3_h8_archive_audit.py` is a **pure-Python fail-closed archival verifier**, which checks SHA identities, q/geometry, exact source material shape, historical cross-frame moments and preserved H8e CI failure state. Running this verifier cannot promote archived evidence to a newly certified native solve. It is a separately uploaded source file and does not imply CI succeeded.

## Recovered original real materials

| Historical run | Artifact | Source packet SHA-256 | Material | Legacy median | Source-ref median | Isolated ratio |
|---|---|---|---|---:|---:|---:|
| H8c 39118951636 | 12132634988 | `ba47a6d6f9fad2dce2569434bf9340252cceaeaf99c14a82df02b637092b6464` | 8455 V / 16910 F | 351.339 ms | 342.969 ms | **1.0244×** |
| H8e 25-point base 39121571756 | 12134772056 | `9538d11fbc180b7b96e7afe3dc98a6af1a5ddf074a680eb182f63517a48d72e3` | 8455 V / 16910 F | 357.036 ms | 352.322 ms | **1.0134×** |

Each path used four **balanced-order** repetitions per packet; both passed 10/10 exact GMP rational moment equality. The archived independent binary64 results and translated model-to-target moments agreed (max absolute frame error `5.551115123125783e-17`). Raw individual, mutually exclusive nanosecond stages, archived binary identities, RAM/swap, and limitations: `evidence/m3-baseline-performance.json` (published summary, locally exported full record in ZIP). No speedup beyond **isolated exact GMP subpath** is claimed.

**Original H8e 25-point status remains FAILED**: 8/24 source-feature hashes drifted. Archived 25-point wall `379.493727883s`; named cumulative evaluator stages sum `77.944304694s`; `301.549423189s` remains **unattributed**, *not* declared validation or JSON cost without direct instrumentation. Arithmetic boundary preparation accounted for `1.806115796s` cumulatively over 25 points. Do not reinterpret these historical observations as a new complete Faster Newton timing.

## Reproduction

Historical artifact inputs are genuine GitHub Actions ZIPs:

```bash
python research/NeuralMoments/performance/m3_h8_archive_audit.py \
  --h8c /path/to/h8c-reference-39118951636.zip \
  --h8e /path/to/h8e-25point-39121571756.zip \
  --output /tmp/w1-m3-audit.json
```

For the complete native C++ side of the local experiment, use the linked M3 source/evidence bundle; the standalone replay source is not yet merged into production bindings and its original local byte-for-byte file is not the newly published Python audit script. All local experimental timings depend on hardware and are **not** author-matched paper results.

## Open admission gates

1. Integrate a direct exact/source-ref handling experiment into an isolated rebuilt Cherchi+GMP binding, without ABI mutation or bypassing independent exact boundary checks. The observed 1–2% effect does not by itself justify a production change.
2. Complete matched old/new full runs with same inputs, accepted/rejected states, provenance, 10-vector, 10×10 J, same-call exact material, terminal physical partition, and full end-to-end wall.
3. W0 published math contract tests are local, and W2's Cherchi teacher is still mock/incomplete for real teacher admission. Neither is to be assumed passed for production merges.
4. Restore missing Noodles V7 `V7_STAGE_STATUS.json` and original same-run 393.44s / 168.27s source evidence; do not combine unrelated timings.
5. Respect sequential large native work, ≤24 GiB/swap 0, ≤60 minutes per run, compile parallelism ≤4.

**Status:** meaningful new verified real-geometry GMP measurement; **production speed gate remains NOT PASSED**.
