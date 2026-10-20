# W0 M13 — archived native-c and W3 Stage11 source-change handoff

**Repository:** `volcano-code/Spin_test`  
**Only writable branch:** `research/neuralmoments-w0-contract-20261019`  
**Frozen H8f source:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**Date:** 2026-10-20

## Critical correction to cross-window expectations

The original H8f literal finite-difference experiment evaluated native *un-normalized* `c` at 64 of its 81 positions; only 17 positions satisfy `abs(||c||₂-1) <= 1e-12`. W2 independently reported this as M11. A W0 V1 *serialized unit-c* `MomentContractV1` record therefore cannot be fabricated for the 64 nonunit historical samples. Their original source geometry, signs, `raw c`, native `Jc`, finite-difference positions and SHA identities stay untouched.

There are **three explicitly different quantities**:

1. `c_raw`: 10 archived native symmetric-matrix entries, byte-bound to the exact original source material. Its 64/81 nonunit status is not an error in the source **literal-offset finite-difference** experiment. A native sample SHA must be computed from this same source, not from a newly constructed unit vector.
2. `u_display = c_raw / ||c_raw||₂`: a *computed signed positive-ray diagnostic*, not an alternative native input, not the original material's `quadric_coefficients`, not byte-identical to original `c` and not a valid replacement for the observed stencil abscissae.
3. `q_poly = B c_raw`, `B=diag(1,1,1,1,1,1,1,2,2,2)`: coefficients of the polynomial monomials. The raw H8f/W2 `q` name in historical records is **native c**, not polynomial q. Negative scaling changes the signed retained halfspace and is not equivalent.

The `positive_ray_exact` diagnostic checks positive proportionality using exact rational interpretations of binary64 values; it does not infer material-set identity from rounded re-normalized arrays. The diagnostic never converts archived `dr/dc` to `dr/du`, never applies the W0 V1 Hessian test to a raw finite-difference Jacobian, and never publishes teacher `J_D`. The original `schema_v1.json` and `validate_contract_v1.py` are intentionally unchanged.

## Reproduce from authentic immutable H8f data

Download unexpired artifact `12135528290` from original GitHub Actions run [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) (`failure`). Verify ZIP SHA256:

`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`

```bash
PYTHONPATH=. python -m research.NeuralMoments.contracts.archived_raw_c_m13 \
  --archive /path/to/authentic-H8f-81.zip \
  --output /new/path/archived_raw_native_coefficients.json
```

The reader binds the original report SHA, request SHA, all 81 source-point JSON coefficients and original 81 compressed same-call material hashes; it refuses falsified positive-convergence flags and outputs 81 raw binary64 coefficient digests and non-publishable ray diagnostics. It performs no new Cherchi Boolean, no new native compilation or Newton solve. The source ZIP is not copied into the W0 commit.

## W3 Stage11 is a *changed* source tree

Read-only W3 Stage11 head observed `8322f381ee23f26ef6be0378bba7d4cececbb60e`; its Stage11 run evidence Git blob `342b5e6968ba029c2af389de8de4a394543f422e` reports **0 newly generated Cherchi calls, 0 verified side packets, 0 accepted Newton steps**. Unlike Stage10, Stage11 writes an `unverified-*` gzip checkpoint before geometry and exact-rational moment audits, then promotes **only after** successful audited source evaluation; its probe and early capture Git blobs are `083ea0075d9df7d71f97e77591a18f5453691665` and `22a62f46a458452186126ae571b50a44212197aa`.

W0 M13's `w3_stage11_delta_m13.py` checks byte-exact, pinned Git blob contents when Stage11 W3 source files are provided, and can independently verify internal SHA/coefficients of an early `unverified-*` packet. **An early capture is never a verified side**. These byte consistency checks are not a cryptographic proof that a specific native runtime produced the capture.

**The W0 M12 Stage10 pre-run source lock is not reusable for Stage11**. W3 must precommit a new clean-tree/binary/source identity before a real native run; an independent collector must separately freeze 13 final promoted W3 report/material files after completion, then W0 M11 may re-integrate the four real sides. No re-sealed producer output can be used to silently authorize the checkpoint.

## Test protocol and scope

```bash
export W0_M13_REAL_ZIP=/path/to/authentic-H8f-81.zip
python -m pytest -q research/NeuralMoments/contracts/test_archived_raw_c_m13.py \
                     research/NeuralMoments/contracts/test_w3_stage11_delta_m13.py
```

M13 new tests: **34/34 PASS**, with actual 81-archive rebind in two tests. The M8–M13 compatible local mirror: **210/210 PASS** with two long original-coefficient real cases deselected, and separately **2/2 PASS** for these two; total **212 unique tests passed in completed invocations**. Earlier first single-invocation job hit its time limit and is NOT a success result. The W3 Stage11 positive-flow tests use explicitly synthetic raw bytes and monkeypatched expected test hashes; **the unmodified real Stage11 source files were only inspected through the GitHub connector, not executed as an actual W3 native job in the W0 local mirror**.

## Release gate (always denied at M13)

- H8f remains a failed CI experiment despite 81 finite points and high numerical agreement; reconstructed H8 CAD is not the original author's CAD.
- 64 nonunit raw-c samples must not be auto-normalized and re-certified as W0 V1.
- W3 has no new verified in-between samples; original point 60 discrete identity still changes.
- Finite local tests, raw moment equality, finite differences and positive-ray diagnostics prove neither continuous smooth parameter strata nor full exact Boolean F/D/cavity partition, Newton/KKT terminal convergence, physics, manufacturing or W5/W6 real-teacher label eligibility.

**Next:** Once W3 publishes real Stage11 qualified four-side outputs under a new *precommitted* clean-tree native identity, run M12 new receipt collection and M11 independent four-material replay. In parallel, introduce a **versioned, reviewed** nonunit *archival* wire schema if needed; never mutate V1 or fabricate V1 labels by normalization.
