# W1 M9 — Per-evaluation rational-cache repair and real-native ABBA admission gate

**Date:** 2026-10-19  
**Repository:** `volcano-code/Spin_test`  
**Only writable branch:** `research/neuralmoments-w1-native-20261019`  
**Only modified path:** `research/NeuralMoments/performance/`  
**Frozen source:** `0bcc187b3005478baa586a6d6f450e73811ca342`

## 1. The actual bug fixed

The M8 diagnostic native paired-gate candidate used a class-scoped `lru_cache` for `exact_fraction`. Two calls with the same candidate class reused previous q's exact tokens. Although immutable Fraction value semantics were preserved, this **violated the documented per-evaluation cache boundary** and contaminated comparative cache metrics. Before M9, two consecutive 6-vertex mimic calls had only **2 cumulative misses**, not 2 per call.

In `m8_native_paired_gate.py` M9 now constructs a **fresh `lru_cache(maxsize=65536)` for each candidate invocation**. It instantiates the original, instrumented function **code object** with a private call-local globals mapping via `types.FunctionType`, preserving the same AST and all native `_stage` observers. The cache is always cleared in `finally`, including on exceptions; only hit/miss statistics survive. Original frozen production globals and modules never change, and nonidentity coordinate axes use the original exact Fraction calculation. The two-call mimic now has `[2,2]` misses (four total), `[16,16]` hits, and **zero live cache entries** on return. Full material equality on actual Cherchi can be certified only on a matching native host.

## 2. Stronger real-native ABBA gate, runnable but blocked here

`m9_native_abba_gate.py` implements **A–B–B–A** (`original`, `candidate`, `candidate`, `original`) on an independent evaluator instance for **each** sample at the SAME registered H8c q. It requires:

- SHA-256 exact H8c artifact `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7`, request SHA-256 `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`, frozen Python evaluator Git blob `f9fa539f699df8baf8b8d30729048269a26ecb3c`, original material packet SHA and all three native modules with recorded binary SHA;
- the original H8c independent Fraction/GMP ten-moment certificate, including **proper model-to-target coordinate conversion** (`5.551115123125783e-17` observed on archived H8c vs H8e point 0), and no author-CAD claim;
- *four* fresh pinned Cherchi Boolean calls, each with same-call complete material validation, **native exact rational self-intersection/boundary audit**, *fresh independent Fraction ten-moment integration*, strict fixed/variable/total moment accounting, finite 10×10 Jacobian, serialized material archive and SHA;
- identical full material SHA, q, backend, native/bridge/GMP module hashes, ten-vector, full 10×10 Jacobian, geometry/topology/source identities, and strict boundary flags across all four evaluations;
- independent, **per-evaluation exclusive stage ledgers** (the previous cumulative ledger is not reused as one-call timing), sequential job, swap=0, address-space cap <=24 GiB, timeout <=3600 seconds.

The ABBA reducer reports both evaluation-only and evaluation-plus-same-call-validation ratios. It explicitly leaves **complete Faster/Newton speedup, trial acceptance/rejection, terminal material/3D printability, smooth-stratum and paper-speed qualification as null/false**. A single-q ABBA pass does not imply full solver acceptance, and no material validation is omitted as a speed trick.

**Current host blocker:** no frozen production repository source tree and no `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments` Python extensions. Native attempt **actually exited nonzero**, with `failure.json: M5_PRODUCTION_SOURCE_UNPINNED`; 0 fresh Boolean evaluations. It produced no success baseline. Local Git cannot resolve `github.com`; GitHub connector was used only for reading/pushing the isolated W1 code.

## 3. Execution results

- **68/68 local W1 M5–M9 unit/functional tests passed** (`test_m5 test_m6 test_m7 test_m8 test_m8_native_paired test_m9`, 0 failed/skipped). Included a fresh compiled C++/GMP independent arithmetic test and actual archived H8 point checks. `test_m9` alone: 17/17, including non-unit c, NaN Jacobian, false geometry flags, mismatched binary SHA, changed archived material, missing native, per-call error cleanup and two distinct archived 8,455-vertex inputs.
- Replayed **50/50 real H8e archived post-Boolean exact construction points** (25 original plus 25 optional candidate). Every original resolved record, target rational coordinate and binary64 target bit matched, with **historical 8/24 feature-hash changes and failed H8e CI preserved**. Wall 15.733 vs 12.560 seconds; *single uncontrolled A/B pair, descriptive post-Boolean subpath only*. No new Cherchi source/Boolean, native Jacobian or Newton solve. This ratio must never be represented as M9 production speedup.
- H8c archived ten-moment vector translated to the H8e target frame matched the independently stored original H8e point-0 ten-vector within `5.551115123125783e-17`.
- Prior M8 class-wide cache still produced numerically consistent results, but did not meet cache-lifetime semantics. New scoped cache does; **no production ABI/math code changed**.

Evidence: `evidence/m9-baseline-performance.json`, `m9-before_after.json`, `m9-tests.log`, `m9-archived-replay-50.json`, `m9-native-failure.json` and logs. The preserved historical H8e 25-point workflow failure must **not** be overwritten.

## 4. Native host reproduction

```bash
# In a W1 checkout with complete external Cherchi and original pinned CMake sources,
# compile _make_it_stand, _cherchi_core_boolean and _cherchi_rational_moments
# using the existing frozen H8e workflow procedure, <=4 build jobs.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH="$PWD/python:$PWD/build/heart-cloud-core/python:$PWD/build/heart-cloud-cherchi/python:${PYTHONPATH:-}"
python -m unittest discover -s research/NeuralMoments/performance -p 'test_m9.py' -v
python research/NeuralMoments/performance/m9_native_abba_gate.py \
  --archive /path/to/h8c-reference-39118951636.zip \
  --root "$PWD" --output /tmp/w1-m9-real-native-abba
```

The native runner refuses version drift or missing prerequisites; never use mock reports as if four real Cherchi calls happened. Do not run this alongside W3's other large native jobs. **No changes to `main`, `src/`, `bindings/`, W0 or W2–W6 were made.**

## 5. M10 gate

Execute M9 native ABBA on a suitable pinned >=24 GiB or other sufficient host while **capping RSS/address space at 24 GiB and keeping swap disabled**; independently review actual biggest exclusive stages, then consider a W1-only candidate build. Only after W0 math contract and W2 independent real teacher are admitted should W1 implement a production-side change, followed by whole-solver same-input old/new Newton, accept/reject, material, end-to-end speed and reproducibility tests. Do not conflate any archived 393.44/168.27, 569.56, 379.49 or local offline metrics from different runs.

**Status: M9 source and local evidence complete; native ABBA and full Faster speed gate still BLOCKED.**
