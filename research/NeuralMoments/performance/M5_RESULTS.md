# W1 M5 — Non-invasive fresh-native stage-attribution harness

**Branch:** `research/neuralmoments-w1-native-20261019`  
**Frozen ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**Only writable area:** `research/NeuralMoments/performance/`.

## What was actually executed in this milestone

1. Re-ran M4 regression on the genuine H8e 25-point artifact with the archived independent GMP executable: **10/10 passed**, 0 skipped. Then pushed its exact seven source/evidence files (including full raw 25-point timing event log) to W1 in commit `eac5be2fc7402cc7169aa5afd51e5cca6fe26734`.
2. Built `m5_native_call_instrumentation.py`, a diagnostic *dynamic subclass* of the frozen `InProcessCherchiEvaluator`. It recomposes only the existing Python `__call__` AST with a timing context around **each original top-level statement** and propagates the native stage observer into the **same hierarchical ledger**. The child native wall interval is subtracted from its containing Python statement, so parent inclusive time is never double-counted. The tool preserves the original AST statement bodies unchanged. No native bindings, production Python code, or ABI were modified.
3. Implemented fail-closed archived H8c request SHA, exact original source Git-blob pin, native-module import, zero-swap, 24 GiB address-space, one-hour timeout, Cherchi backend, material same-call, exact rational boundary, independent Fraction ten-moment, Jacobian-shape, and full material-archive guards. The runner only emits `baseline-performance.json` after **all actual checks succeed**. A missing native module or source immediately results in `failure.json` instead of a fabricated benchmark.
4. Implemented `m5_attribution_report.py` to independently close the historical 25-point time ledger and refuse cross-machine subtraction from the newly executed M4 arithmetic replay. **11 local tests passed / 0 skipped** for M5 after a corrected missing-archive expectation; `evidence/m5-tests.log` is the final run. The first pre-correction test log produced 10 passed / 1 error because the test expected `ValueError` rather than the actually correct `FileNotFoundError`. The code was corrected and the final test run is green.

### Verified historical constraint

- Original H8e 25-point *failed* run: wall **379.493727883 s**.
- Named original evaluator steps total **77.944304694 s**.
- Residual still unclassified on that original runner **301.549423189 s**, approximately **79.46%**.
- `prepare_arithmetic_boundary` recorded **1.806115796 s**, only **0.4759%** of that original wall. Even removing this measured segment entirely while keeping all else identical would yield at most **1.004782×** overall speedup. This is a conditional Amdahl bound, not an achieved speedup.
- The M4 offline 25-point `Fraction` expense and native GMP expense were measured on a *different* machine and with *different* operations. They **cannot** be assigned to the historical unclassified residual.

### Run in a pinned native environment

Build the frozen project dependencies with the existing strict Cherchi GitHub Actions procedure. Do not oversubscribe W1/W3 native work. Set `PYTHONPATH` to the repository's `python/` plus built native module paths. With genuine H8c artifact `12132634988` downloaded as `/tmp/h8c-reference.zip`:

```bash
python research/NeuralMoments/performance/m5_native_call_instrumentation.py \
  --archive /tmp/h8c-reference.zip --root . --output /tmp/w1-m5-fresh-native-01
```

All hooks run only in this command's process and keep the original source unchanged. A successful execution, including independent geometry auditing, reports one **new H8 single-q Cherchi evaluation**, not a complete Newton convergence or material-seal speedup. For the static evidence-only stage accounting:

```bash
python research/NeuralMoments/performance/m5_attribution_report.py \
  --m4-report research/NeuralMoments/performance/evidence/m4-baseline-performance.json \
  --output /tmp/w1-m5-attribution.json
python -m unittest discover -s research/NeuralMoments/performance -p test_m5.py -v
```

## Remaining gates

- **Fresh Cherchi full-chain sample not run in this environment**: `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments` are not installed here, and the needed matching full CMake/Cherchi stack is absent.
- Full original-vs-optimized production Newton run, geometry/source/Jacobian/success-or-failure/terminal material parity **not established**.
- W0 MomentContractV1 formal production validation and W2 real-teacher independent comparison **not asserted complete**; H8 reconstructed CAD is not author CAD.
- Noodles V7 original same-run timing and frozen status remain missing from this W1 snapshot.
- No author-matched paper speedup claim.

**Next milestone:** run the new profiler once on the pinned native host, identify top actual Python/validation costs from its single-run exclusive ledger, then select the most expensive reversible optimization and run strict old/new full solver equivalence. Do not remove exact geometric auditing without independent proof.
