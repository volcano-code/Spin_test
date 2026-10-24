# W1 M19 cross-build fix: genuine new-native-build H8e stage profiling without pretending historical binary identity

**Status:** W1-only opt-in profiler recovery; actual fresh Cherchi 25-point execution pending the user's native workstation run. **NO new production performance claim**.

## Observed deterministic blocker

The genuine immutable H8c ZIP `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7` contains `artifacts/h8-cherchi-point/result.json`, declaring historical `_make_it_stand` SHA256 `ad0c4fe3527954c611743dbbccb384cc1521909e8a39d68c3b7554b3a3919d40` and `_cherchi_core_boolean` SHA256 `3cc8bf789168752f8b921c160ca9937cdf0f61c845d3088760811b9e5a4596b7`. Actual M13 locally built, ABI-verified distinct `.so` SHAs are respectively `579128457145c22f6192df8bf7b75603f5cfc5b3c719008d39ef9e3fb40ae0bf` and `d6c2da58e4396c7ad279fb10457dd365783ba6f056983acf1353a73ce63e3351`. The SHA requirement in the *untouched frozen* H8e driver correctly rejects the old certificate in the new host before any Boolean work.

M13 compiled from correct pinned Cherchi `7bd6c2697695f555f9a15d7e154e084d841316f0` and CGAL `f7c3c8212b56c0d6dae63787efc99093f4383415`. Equal source revisions are not equal compiled ELF bytes, which can vary by compiler and machine.

## Code scope and acceptance

- Modification ONLY to W1 `research/NeuralMoments/performance/m19_real_h8e_profiler.py`, plus a new W1 regression file. Frozen `research/Heart_v1_20261017/.../probe_h8_jacobian.py`, production Cherchi Python/C++, main and W0–W6 branches remain unmodified.
- **Default `--baseline-mode strict`** preserves the frozen same-binary certificate check without qualification.
- Opt-in `--baseline-mode fresh-native` explicitly records historical and actual ELF SHA separately, requires three present local module digests and genuine original H8c ZIP, and verifies immutable request/reference/certificate SHA256. It refuses if the binaries actually match the archive (must use strict).
- For this explicitly different-ELF run, the unchanged frozen H8e AST `run` receives `None, None` for the *same-binary H8c certificate arguments only*; this is the original documented no-certificate code path, not removal of a scientific validator. ALL 25 original Cherchi Boolean calls, per-point exact geometry boundary audits, independent Python Fraction ten moments, 10x10 Jacobian, same-call material snapshots, numerical FD checks and feature branch tests remain unchanged.
- The profiler separately compares the actual first saved point against immutable historical H8c **model-to-target 10 moments with the same `1e-10` absolute bound and 8455 vertices/16910 faces**. It rejects any mismatch and writes `fresh-native-cross-build-authority.json` only after that extra check succeeds; the complete M19 stage ledger still writes normally only if the whole native experiment passes M19's existing conditions. Historical exact packet SHA, historical compiled ELF equality and historical Jacobian bitwise equality are explicitly **NOT claimed**.
- Historical H8e feature-branch drift (`8/24`) and W0/W2 independent mathematical admission remain outstanding. A complete 25-point timing can legitimately exit 2 if smooth feature branch fails. Zero full Newton calls and zero proof of Faster end-to-end speedup.

## Verified W1 local code regression

`test_m19` historical snapshot (20 tests) + 7 new `test_m19_cross_build_identity` tests: **27/27 passed** on 2026-10-25. Tests use actual pinned H8c ZIP and actual historical H8e first point, no fabricated production native call; additionally reject forged certificate/request/reference, missing binary provenance, wrong q, ten moments and mesh size. Production C++/pybind modules cannot be built/run in the assistant's capped container. User's local native W1 build remains the authority.

## Run on the user's Ubuntu 22.04 host (W1 root already present)

```bash
conda activate w1-native
export ROOT=/data/xvxinyao1/Spin_test-W1/Spin_test-w1
export EXP=/data/xvxinyao1/Spin_test-W1/experiments
export P="$ROOT/research/NeuralMoments/performance"
export H8C="$EXP/archives/h8c-reference-39118951636.zip"
export H8E="$EXP/archives/h8e-25point-39121571756.zip"
export CORE="$ROOT/build/w1-m13-core/python"
export CHERCHI="$ROOT/build/w1-m13-cherchi/python"
cd "$ROOT"
git pull --ff-only origin research/neuralmoments-w1-native-20261019
W1_M25_H8C_ARCHIVE="$H8C" W1_M25_H8E_ARCHIVE="$H8E" \
  python -m unittest discover -s "$P" -p 'test_m19_cross_build_identity.py' -v
export M19_RUN="$EXP/runs/m19-fresh-native-$(date +%Y%m%d-%H%M%S-%N)"
set -o pipefail
python -u "$P/m19_real_h8e_profiler.py" \
  --root "$ROOT" --archive "$H8C" \
  --module-dir "$CORE" --module-dir "$CHERCHI" \
  --baseline-mode fresh-native --output "$M19_RUN" \
  2>&1 | tee "$EXP/logs/$(basename "$M19_RUN").log"
rc=${PIPESTATUS[0]}; echo "exit=$rc output=$M19_RUN"
ls -lh "$M19_RUN"
```

**DO NOT** reinstall native modules or edit the frozen H8e source. Output directories must be new; failed prior M19 attempts are retained. Verify `actual-frozen-h8e/report.json`, `baseline-performance.json`, `fresh-native-cross-build-authority.json`, `failure.json`, and `partial-stage-ledger.json` as applicable. Upload raw evidence for next research action.
