# W1 M10 — native-host admission, module ABI preflight and serial M5/M9 launch

**Branch:** `research/neuralmoments-w1-native-20261019` (only this branch may be updated)  
**Exclusive area:** `research/NeuralMoments/performance/`  
**Frozen common ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**Scope:** execution-environment engineering, **NOT a new Faster/Boolean/Newton speed claim**.

## Implementation actually completed

- `m10_native_host_runner.py` is a runnable CLI that requires the full actual W1 Git checkout at HEAD with verified frozen ancestor. An adjacent source directory with a borrowed name is rejected; so are `main`, detached HEAD, wrong branch and shallow history lacking a verifiable ancestor.
- Pins the original H8c CI artifact (run `39118951636`, artifact `12132634988`, SHA-256 `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7`), embedded H8 request SHA and historical 8455-vertex / 16910-face exact material certificate.
- Pins the original `python/make_it_stand/verification/cherchi_inprocess.py` Git blob SHA-1 `f9fa539f699df8baf8b8d30729048269a26ecb3c` without modifying that file.
- Resolves three *real* `.so` / CPython-extension-suffix modules: `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments`. Python `.py` stubs or wrong/ambiguous paths do not count. An isolated subprocess must **actually import** each and check the essential exact-boundary/Boolean/GMP API and arithmetic identity, using binary paths recorded with SHA-256.
- Enforces zero swap; per-process address-space cap at or below **min(24 GiB, physical RAM, cgroup memory ceiling)**; `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`; one native process at a time; exclusive inter-process W1 native lock; each M5 or M9 job limited to **3600 s**. Cooperation with W3 scheduling is still required; the W1 lock cannot reserve W3.
- Only after *all* preflight requirements pass does it spawn M5's genuine strict single-q Cherchi stage profiler followed **serially** by M9's four fresh Cherchi ABBA calls. It requires the expected original stage schemas and 1+4 real Boolean-call counts; any nonzero exit, missing proof report, unexpected schema, timeout or lock collision yields `failure.json` and **no success report**.
- The hypothetical successful-run receipt would still say `full_solver_speedup=null`, `full_solver_terminal_verified=false` and `paper_speed_qualified=false`: **5 real single-q evaluations would not be a complete Newton solve or W0/W2 admission.**

## What was actually run on this environment

- `M5–M10` full local regression: **85/85 passed**, 0 failed, 0 skipped, 17.013 seconds (source and full log in `evidence/m10-tests.log`). This includes existing real H8 archived material tests and C++/GMP checks, but not a freshly compiled Cherchi Boolean.
- Real CLI preflight run against the genuine H8c archive returned **exit code 2**, `state=BLOCKED`. The authentic ZIP, exact request, physical/cgroup memory inspection and zero-swap tests passed.
- Confirmed four independent blockers: full W1 Git checkout missing, pinned production source missing, all three native compiled modules missing, and therefore native ABI import unavailable. This runner's cgroup memory limit is **4 GiB** (`4294967296` bytes), even though `/proc/meminfo` reports about **5.81 GiB physical RAM**. The 24 GiB research ceiling does **not** mean 24 GiB is available here.
- The blocked execution wrote `preflight.json` and `failure.json`, with zero new Cherchi Boolean/solver invocations and **no** `native_evaluation_summary.json`.
- Tests explicitly reject wrong Git branch/ancestor, changed archive, fake `.py`/invalid `.so`, duplicate binaries, locked parallel jobs, failed native subprocess, success exit without science report, output overwrite, and per-job timeout above 60 minutes.
- No frozen production `src/`, `bindings/`, `python/make_it_stand/`, no other W window, and no `main` changes. No old H8e failed CI, raw CAD, historical source bundle or failed evidence was overwritten.

## Native host reproduction

Use the actual W1 Git checkout, retaining enough history to prove ancestor `0bcc187...`. Follow the repository's **pinned H8e existing GitHub Actions native-build procedure** to build the three modules on a machine with sufficient RAM (do not run parallel with W3). Obtain H8c artifact `12132634988` separately; do not substitute the H8e 25-point archive.

```bash
# Run in W1 checkout only; all commands are read-only with respect to the repo.
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python research/NeuralMoments/performance/m10_native_host_runner.py \
  --root "$PWD" \
  --archive /path/to/h8c-reference-39118951636.zip \
  --output /tmp/w1-m10-real-native-01 \
  --module-dir "$PWD/build/heart-cloud-core/python" \
  --module-dir "$PWD/build/heart-cloud-cherchi/python" \
  --max-seconds 3600

# Run regression, including tests which verify the real immutable archived H8c/h8e:
export W1_M8_H8C_ARCHIVE=/path/to/h8c-reference-39118951636.zip
export W1_M8_H8E_ARCHIVE=/path/to/h8e-25point-39121571756.zip
python -m unittest discover -s research/NeuralMoments/performance -p test_m10.py -v
```

Failing preflight yields `<output>/failure.json` and `<output>/preflight.json` (no native work); only real successful module importing + full M5/M9 audited outputs yield `native_evaluation_summary.json`. A complete production full-solver A/B, true accept/reject history, terminal material and paper-speed comparison remain pending. W0/W2 formal teacher/contract admission is NOT presumed by this milestone. The H8e historical 25-point branch hash drift (8/24) and original failed workflow state remain preserved.
