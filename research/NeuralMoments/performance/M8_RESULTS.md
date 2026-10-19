# W1 M8 — exact post-Boolean Python provenance and frame replay (2026-10-19)

**Only write target:** `volcano-code/Spin_test` branch `research/neuralmoments-w1-native-20261019` in `research/NeuralMoments/performance/`. **Frozen base:** `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Source audit and isolated implementation

The frozen `python/make_it_stand/verification/cherchi_inprocess.py` Git blob `f9fa539f699df8baf8b8d30729048269a26ecb3c` was inspected through the GitHub connector, especially `exact_fraction`, `_target_view` and the construction correspondence loop in `__call__`. `m8_exact_construction_trial.py` reproduces their original semantics, then tries two mathematical no-ops in an isolated archived-data experiment:

1. A per-evaluation **bounded 65,536-token exact Fraction memoizer**; no approximate rational identity, no cache shared between different q evaluations.
2. For an **exactly identity** target-axis matrix only, return the already computed exact `(model_x,model_y,model_z)` vector without multiplying by identity and summing zero terms. Every other coordinate frame uses the original nine Fraction multiplication/sum operations.

Old and candidate BOTH compute all 8,455 original normalized rational vertices, all 8,455 resolved Cherchi construction records, the same exact target rational coordinate strings, and identical binary64 target coordinates. Each packet must match the original SHA and saved provenance, source q, original 10×10 Jacobian shape, frozen backend identity and historical exact boundary audit result. Nothing is skipped in the scientific parity check. This **does not rerun** Cherchi, independently certify self-intersection, recompute Jacobian or show a complete Faster solution.

An **optional source-file SHA gate** verifies the pinned production file on the real native host. This sandbox does not have the full pinned production checkout, so `source_on_disk_verified=false` is recorded; byte-for-byte correspondence is instead checked against the *archived evaluator's original complete material outputs*. This distinction is not silently waived.

## Measured real H8e ABBA replay

Source: real H8e 25-point archive, Actions `39121571756`, artifact `12134772056`, ZIP SHA-256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`. This **original historical CI remains FAILED**, with 8/24 branch hashes changed; the archive and its evidence are not modified.

Each variant processed all 25 samples twice, sequentially (order **A-B-B-A**) on the **same** Linux/Python 3.13.5 zero-swap sandbox:

| Archived Python-stage replay | Original semantics | Cached + identity fast-path |
|---|---:|---:|
| First 25-point wall | 16.076 s | 12.237 s |
| Second 25-point wall | 19.743 s | 13.033 s |
| **Median 25-point wall** | **17.910 s** | **12.635 s** |
| Original/optimized median ratio | — | **1.4175×** |
| Mean parse exact vertices stage | 2.346 s | 0.692 s |
| Mean exact target-coordinate stage | 4.526 s | 2.171 s |
| Mean provenance resolution stage | 3.173 s | 2.297 s |

**100/100 recorded point evaluations** matched all original source correspondence records and normalized exact target coordinates. There were no production `.so` evaluations. This ratio measures only **archived post-Boolean Python calculation and its matching checks**, not full source/Boolean/Newton, independent Fraction/GMP verification, material sealing, or paper speed. Two runs per arm are descriptive; no statistical significance or cross-host speedup is claimed. Do not subtract this experiment's seconds from historical `301.549423189 s` unknown wall.

## Real-native two-call gate prepared, but correctly blocked on this host

Added `m8_native_paired_gate.py`: when run on an **actual full pinned Cherchi-native checkout**, it clones the **unchanged original production `__call__` AST** into two separately instrumented diagnostic classes. Only the candidate's private function-global `exact_fraction` and `_target_view` are modified. Both calls use the **identical frozen request, q and module binaries** and must independently pass:

- full original same-call material validation and backend identity;
- native **exact rational boundary self-intersection** audit, no bypass;
- fresh independent Python Fraction ten-moment integration;
- full serialized material SHA, material faces/vertices, source/geometry/topology identities, 10-vector and **entire 10×10 Jacobian** literal parity.

Any deviation refuses the speed report. One pair is still not a **full Newton solve**, acceptance/rejection trace, final terminal partition, or W0/W2 admission. This runner has not executed real Cherchi here: all three `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments` modules and the full production checkout are absent. Actual invocation failed as expected with `M5_PRODUCTION_SOURCE_UNPINNED`, producing only `m8-native-host-failure.json`, **never a success baseline**.

## Actual regressions

**51 passed, 0 failed, 0 skipped** from `test_m5.py`, `test_m6.py`, `test_m7.py`, `test_m8.py`, `test_m8_native_paired.py` with real archived inputs and GMP compilation for the M6 tests. The first combined run failed because this worktree had restored an outdated `m6_archived_validation_replay.py` from the M6 ZIP; it was replaced by the **unaltered M7-version file** already committed upstream, then the final suite passed (see `evidence/m8-51tests.log`). This replacement was **local test-worktree recovery**, not a new source edit proposed for commit. M8 also checks malformed rationals, drifted provenance, changed binary64 targets, unpinned source, resource/run guards and callback non-mutation.

## Reproduce

```bash
# The genuine H8e ZIP from Actions artifact 12134772056 is required.
export W1_M8_H8E_ARCHIVE=/path/to/h8e-25point-39121571756.zip
export W1_M6_H8E_ARCHIVE="$W1_M8_H8E_ARCHIVE"
export W1_M7_H8E_ARCHIVE="$W1_M8_H8E_ARCHIVE"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -m unittest discover -s research/NeuralMoments/performance -p 'test_m8*.py' -v
python research/NeuralMoments/performance/m8_exact_construction_trial.py \
  --archive "$W1_M8_H8E_ARCHIVE" --points 25 --output /tmp/w1-m8-abba

# Only on the pinned real native host with all three native extensions and PYTHONPATH:
python research/NeuralMoments/performance/m8_native_paired_gate.py \
  --archive /path/to/h8c-reference-39118951636.zip \
  --root . --output /tmp/w1-m8-native-old-new
```

All raw 100-point stage rows, source SHA-256, native availability failure, test logs and no-paper-speed constraints are under `evidence/`. The full old/new **solver** `before_after` field remains null. Large native jobs must remain sequential, swap=0, memory <=24 GiB, single job <=60 min and compiler parallelism <=4.

**Next indispensable gate:** run M5 and M8 native paired gate on a full pinned native build; only then choose a production optimization, validate W0/W2, and verify entire Newton/acceptance/terminal behavior. **No production `src/`, `bindings/`, `python/make_it_stand/`, `main` or any other W branch was changed by M8.**
