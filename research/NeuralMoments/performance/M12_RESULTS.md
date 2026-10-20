# W1 M12 — Native ABBA performance receipt integrity and reproduction

**Exclusive branch:** `research/neuralmoments-w1-native-20261019`  
**Frozen source ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**Permitted files:** only `research/NeuralMoments/performance/`  
**Result scope:** M11 evidence gate and regression improvements; **NO fresh Cherchi Boolean or Faster/Newton run**.

## M12 fixed an actually reproduced gate flaw

The previous M11 gate independently checked that each stage ledger closed, and independently recomputed the ABBA ratios. But it **did not bind** the reported per-call `complete_validation_ns` (used in the speed ratio) to that same call's `stage_ledger.wall_ns`. As a result, a consistent edit to both candidate point JSON records and the summary could claim a faster *validation-inclusive* A/B ratio without changing any recorded wall-clock source observations.

A real locally executed **synthetic-only** negative reproduction against the original published M11 blob `d19bbe16c851c4996fbda29cea6e1fc78f5abad8` changed both candidate `complete_validation_ns` values from 200 to 120 while their stage ledger wall remained 200 (arbitrary synthetic nanoseconds), updated the four point reports, and recomputed the M9 ratio. **Old M11 accepted a fabricated 1.6667x validation-inclusive speed ratio.** The corrected gate rejects the identical synthetic report with `M11_M9_COMPLETE_WALL_LEDGER_MISMATCH`. Evidence: `evidence/m12-before-after-negative-reproducer.json`. This is **not** a real native performance result.

The corrected `m11_native_evidence_gate.py` now additionally requires:

1. M9's four measured `complete_validation_ns` values match their own `stage_ledger.wall_ns` exactly; individual evaluation-only time covers all native/Python evaluation spans, and the residual validation time covers every independent audit span.
2. M5's `sample_and_validation_wall_ns` is nonzero, bounded by its containing observer window, and covers all measured evaluation plus audit spans.
3. Each sample has exactly one `native:boolean` stage and exactly one of each mandatory same-call material, native rational-boundary, independent Fraction ten-moment, and full material-snapshot audit stages. Renaming/skipping/duplicating one is rejected.
4. Original M5/M9 material hashes, source identities, full 10x10 Jacobians, module SHA, full independent rational and native exact geometry flags remain mandatory. No shortcut to obtain a speedup and no changes to production math/ABI.

`test_m11.py` (14 tests), previously only in the local archive and *not* committed on W1, has now been included with a faithful synthetic ledger fixture. `test_m12.py` contributes **10 new** negative/positive contract checks, including self-consistent timestamp and ratio forgery and omission of exact geometry/Fraction audits. Synthetic receipts are explicitly labeled as such and are not proof of actual Cherchi execution.

## Actual tests and environment

All unit/archived-material regression suites were **run in three independent groups** with captured exit status 0:

| Group | Actual count | Result |
|---|---:|---|
| M5, M6, M7, M8, M8 native paired | 51 | 51 passed |
| M9, M10 | 34 | 34 passed |
| M11, M12 | 24 | 24 passed |
| **Total distinct tests** | **109** | **109 passed; 0 failed/skipped** |

Each log is preserved under `evidence/m12-tests-*.log`. The first monolithic run was **not** counted as a pass because the execution tool timed out; the group runs then completed and returned normal exit status. `evidence/m12-before-after-negative-reproducer.json` demonstrates the old gate's real logic error and the corrected behavior.

`m11_native_host_runner.py` was invoked with authentic archived H8c source (ZIP SHA-256 `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7`). Real preflight returned **exit code 2** with 4 blockers: missing full W1 Git checkout, missing pinned production source, missing `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments`, and therefore no native ABI import. The ZIP and frozen H8c request SHA and swap=0 all passed. This container cgroup ceiling is **4 GiB**, not the 24 GiB maximum budget. `github.com` DNS is unavailable to the local checkout/build tools. No new native Boolean, Jacobian regeneration, material self-intersection execution or Newton solve occurred. Failure and preflight logs are preserved, not converted to a success receipt.

## Reproduce

From the real W1 branch checkout with the historical H8c ZIP available:

```bash
export W1_M8_H8C_ARCHIVE=/path/to/h8c-reference-39118951636.zip
export W1_M8_H8E_ARCHIVE=/path/to/h8e-25point-39121571756.zip
export W1_M6_H8E_ARCHIVE="$W1_M8_H8E_ARCHIVE"
export W1_M7_H8E_ARCHIVE="$W1_M8_H8E_ARCHIVE"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
cd research/NeuralMoments/performance
python -m unittest test_m11 test_m12 -v
```

On a **full pinned native build** after checking 24 GiB/zero-swap/serial/<=60min job limits and coordinating with W3, run the **same** existing M11 pipeline (M12 only tightens the downstream gate):

```bash
python research/NeuralMoments/performance/m11_native_host_runner.py \
  --root "$PWD" \
  --archive /path/to/h8c-reference-39118951636.zip \
  --output /tmp/w1-m12-native-01 \
  --module-dir "$PWD/build/heart-cloud-core/python" \
  --module-dir "$PWD/build/heart-cloud-cherchi/python" \
  --max-seconds 3600
```

Only if the genuine 1+4 native evaluations, same-call material, full Jacobian, exact geometry, independent Fraction, and the now strengthened timing cross-check all pass should M11 produce an admitted single-q receipt. **Full Faster/Newton solver speedup, terminal physical material and paper speed remain unknown**. W0 mathematical contract and W2 true-teacher production admission remain separate requirements; original Heart H8e 8/24 source-feature drift and failed historical CI have not been changed.
