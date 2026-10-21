# W2-M16 — Real frozen Heart Cherchi launch gate and Noodles V7 original-source recovery (2026-10-21)

**Repository**: `volcano-code/Spin_test`. **Only write branch**: `research/neuralmoments-w2-teacher-20261019`. **Only write scope**: `research/NeuralMoments/teacher/`. Frozen H8f source SHA: `0bcc187b3005478baa586a6d6f450e73811ca342`.

## What actually ran (not a fabricated Cherchi evaluation)

Used the original GitHub Actions H8f 81-point ZIP (artifact `12135528290`; SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`; original workflow 39123384402 **failure**) as the source of the frozen request and source OBJ files. Independently checked:

- Native request JSON SHA256 `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`.
- Original, fixed and design OBJ SHA against the archived source manifest; respective face counts 31,288, 57,532 and 26,244. All three are closed oriented triangle surfaces by necessary directed-edge pairing. There is **no new exact native self-intersection certificate**.
- Millimeter original OBJ coordinates divided by 25 match the normalized native request's ordered `outer` and `design` binary64 vertices and triangle indices **byte for byte**.
- Independently recomputed signed tetrahedral moments for original, fixed and design. `max|original - fixed - design| = 2.220446049250313e-16`; the source frozen *input* tolerance is 1e-9. An **independent ten-component Cherchi Boolean moment budget is a separate required input**. Reusing 1e-9 from F/D input partition as an automatic Boolean oracle is prohibited.
- Rebuilt a byte-checked view OBJ at `/mnt/data/w2_m16/heart_attempt_final/frozen_normalized_outer.obj` and stored the 6.3 MB frozen raw request in an **uncommitted local run directory**, not a new original CAD file.

The actual CLI was launched:

```bash
python research/NeuralMoments/teacher/m16_native_acceptance.py \
  --heart-archive /mnt/data/h8f_81_real.zip \
  --output-dir /mnt/data/w2_m16/heart_attempt_final \
  --execute-native
```

**Exit 2**, `BLOCKED_BEFORE_NATIVE_CALL`. Local JSON SHA256: `74ddb283a7e1a96bbb049bf48709a885387c63dc4536790f253a25ed0c38d937`. Recovered measured limits: cgroup total `4294967296` B, currently used `820150272` B, effective available `3474817024` B, native minimum `25769803776` B, host swap `0` B. The local Python 3.13 environment has no `make_it_stand`, `_cherchi_core_boolean`, or `_cherchi_rational_moments` packages. Complete Git W2 checkout, **three externally SHA-pinned compiled binaries** and **ten separately predeclared reference budgets** are also absent. A missing precondition is recorded rather than bypassed.

**No new compiled Cherchi Boolean or teacher call was started, no fresh `r_D`/Jacobian attachment or stage-time/RSS from native evaluation exists, and no training label was issued.** This milestone is a real source/resource/identity preflight, not a completed W2 native teacher.

## New native acceptance harness

`m16_native_acceptance.py`:

1. Reopens the true frozen H8f artifact with independent source, OBJ ordering and exact byte identity checks; writes normalized view with immutable digest.
2. Pins five relevant shared W2 Python source blobs and requires a clean, complete W2 Git checkout.
3. Requires an operator-reviewed `w2-m16-externally-frozen-ELF-extensions-v1` manifest with exact paths and externally frozen SHA256 for `make_it_stand._make_it_stand`, `_cherchi_core_boolean` and `_cherchi_rational_moments`. It verifies ELF header/hash **and actual Python import hash**. Binary hash presence does **not** certify build provenance on its own.
4. Checks actual cgroup available memory, 24 GiB cap, host swap=0 and serial launch; caps address space and kills the spawned process group on timeout (max 3590 seconds).
5. Requires independently chosen **ten positive per-component Cherchi moment tolerances**, distinct from F/D partition tolerance, before launching `run_native_smoke.py` once with `NATIVE_GMP_SURFACE_V1` arithmetic. Re-reads source and binary hashes after success.
6. For a success, requires same-call attachment and independent ten-moment comparison, but always retains `J_D=null` and `split=excluded` pending W0/W3. Every ordinary missing prerequisite is a saved failure; repeated output directories are rejected to avoid overwriting evidence.

**Important:** subprocess launch and success validation are not exercised by a *compiled* native job here. Run it on a qualified real research host before claiming completion.

### Exact tests / code identity

`W2_H8F_ARCHIVE=/mnt/data/h8f_81_real.zip python -m unittest discover -s /mnt/data/w2_m16 -p test_m16_native_acceptance.py -v` ran **30/30 PASS**, zero skips/failures, in **3.793s**. Test coverage includes genuine Heart assets and F/D moments, original coefficients, normalized view bytes, real blocked CLI report, SHA identity/tamper, nonclosed/relative-face/NaN rejection, resource limits, fake ELF/hash and source checkout failure. SHA256 of local log: `be833f949af6ee061f5c7f98662367b87e612bf973a22dd6f80517fc4df27f71`.

Both GitHub source blobs were verified **byte-identical** to the locally run source: harness Git blob `078855ba5f8fd5f49d06d92c56cb2f387441b55a`, test Git blob `118a86e5077db14170bcf306b9b8374493687865`. This is **local Python unit testing**, not GitHub Actions CI.

## Noodles V7: new recovery leads, NOT restored frozen teacher

A read-only search of `Spin_test/main`, committed independently of W2, located `research/Noodles_v7_20261017/frozen-parts-v7c/manifest.json` (Git blob `f476a8c3e87bd30ef186b24442f641c2602c32ec`): 94 component entries, 93 fixed components, one outer envelope; every component has expected OBJ SHA. The `source/build_exact_v7.py` generator (blob `0c02cd8f4e7554ab6f3cbde497877253ce5bddec`) defines an exact CSG construction. The historical `frozen-inputs/author-rational/construction.json` (blob `1e824c72d5ee13cc484bbf60a0be9b79be86d787`) reports 96 CGAL Boolean operations and six hashed rational output types.

**Blocking facts:** the 94 part OBJ bytes and six large exact rational CSG output files are **not present in the checked main source tree**. The original solver request evidence stores digests but not full outer/design/F arrays, and the historical status explicitly reports `formal_separate_F_D_A_binary64_partition_passed=false`. Consequently M16 **does not claim Noodles inputs recovered**. The historical optimized final OBJ remains an *output*, never substituted as original F/D teacher input.

A compact immutable ledger of source blob identities, historical output SHAs and missing prerequisites is at `M16_NOODLES_V7_SOURCE_RECOVERY_LEDGER.json`.

## Reproduction on the >=24 GiB/swap0 W2 research host

Place a full W2 checkout on that host and build/import all three genuinely compiled native extensions. Use a separately reviewed manifest with 3 module entries:

```json
{
  "schema": "w2-m16-externally-frozen-ELF-extensions-v1",
  "extensions": {
    "make_it_stand._make_it_stand": {"path": "/real/path/_make_it_stand.so", "sha256": "<actual independently approved SHA256>"},
    "_cherchi_core_boolean": {"path": "/real/path/_cherchi_core_boolean.so", "sha256": "<actual independently approved SHA256>"},
    "_cherchi_rational_moments": {"path": "/real/path/_cherchi_rational_moments.so", "sha256": "<actual independently approved SHA256>"}
  }
}
```

These placeholders are **instructions only, not valid pinned hashes**. Prepare an **independently declared ten-value absolute error budget JSON**, appropriate to the H8f target-coordinate-frame physical moments. Then run:

```bash
python research/NeuralMoments/teacher/m16_native_acceptance.py \
  --heart-archive /path/to/original-h8f-81.zip \
  --checkout /path/to/full/Spin_test-w2 \
  --native-manifest /path/to/approved-native-module-manifest.json \
  --reference-budgets-json /path/to/declared_10_moment_budgets.json \
  --output-dir /fresh/exclusive/w2-m16-real-run \
  --execute-native
```

If the native result succeeds, the scientific next step is to independently check module/source build ancestry and genuine continuous derivative neighborhoods with W0/W3 before any `J_D` is published. If a resource/module/case gate fails, retain its evidence and **do not silently fall back to mock/CGAL**.

## Acceptance

- Original goal: robust Cherchi teacher adapter and numeric physical moment contract: strong historical evidence and frozen-input validation.
- Remaining W2 native goals: **one fresh Heart Cherchi call, one Noodles V7 call on authenticated frozen source/F/D, real staged timing/RSS and independent acceptance**.
- W0 v2/projective signoff and W3 continuous one-sided derivative signoff: pending; Jacobian training labels **0**.
