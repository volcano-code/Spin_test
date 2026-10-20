# W1 M13 — Pinned native build/provisioning milestone

**W1 branch:** `research/neuralmoments-w1-native-20261019`  
**Frozen ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**Modified tracked scope:** `research/NeuralMoments/performance/`

## Implemented

`m13_pinned_native_build.py` creates a guarded execution path from the historical H8c artifact to the existing M11 independent scientific gate, without modifying production mathematical code or C++ ABI. It validates the actual W1 Git worktree, frozen evaluator Git blob, H8c ZIP/request/material identities, no swap, available memory and Python/C++ dependencies.

The build path pins Cherchi `7bd6c2697695f555f9a15d7e154e084d841316f0` and CGAL `f7c3c8212b56c0d6dae63787efc99093f4383415`, checks tracked source cleanliness and required headers, and requires explicit `--fetch-pinned-sources` before any network retrieval. Existing nonempty or modified source trees are never overwritten.

The executable can compile `_make_it_stand`, `_cherchi_core_boolean`, and `_cherchi_rational_moments` into isolated `build/w1-m13-*` directories, with at most four compile workers (default two), an isolated generated-Ninja-only workaround for non-PIC static Boost, and no `sudo`/host-library mutations. It verifies real extension files and entrypoints before allowing M11 to serially execute M5 and M9. Each native job has its own 3600-second cap. Only M11 independently admitted receipts can mark five real H8c calls as evaluated, **not** a full Newton result.

## Actually executed this turn

| Tests | Passed |
|---|---:|
| M5–M8 | 51/51 |
| M9–M10 | 34/34 |
| M11–M12 | 24/24 |
| M13 new native build/unsafe-input tests | 21/21 |
| **Total** | **130/130**, 0 failed/skipped |

All tests ran locally in distinct groups with exit code 0. Among the M13 guards are malicious/pre-existing source rejection, absent or wrong pinned revisions, clean tracked-source checks, Boost shared-link-only rewrite, source-hash integrity, build timeout/worker limits, and no successful receipt after an unsuccessful stage.

A real read-only preflight and an explicit `--execute --fetch-pinned-sources --workers 2` attempt ran against authentic GitHub Actions H8c artifact ID `12132634988`. SHA-256 `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7` and zero swap passed. Both attempts exited **2 / BLOCKED**: this container lacks the full W1 Git worktree, frozen production source, pinned external sources, shared Boost/development packages, and has a **4 GiB** cgroup ceiling (conservative build floor: 6 GiB). Local Git access to `github.com` failed DNS. There were **zero** new native Boolean evaluations, **zero** native Jacobian regenerations, and **zero** Newton solves. No false `baseline-performance` or solver speedup has been created.

## Reproduce on a suitable W1 host

Run this only from a complete W1 checkout with the real H8c archive, Python 3.13, pinned pybind11 3.0.1, shared Boost, GMP/MPFR and original H8 native CMake development prerequisites. Coordinate large jobs with W3; swap must be disabled.

```bash
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python research/NeuralMoments/performance/m13_pinned_native_build.py \
  --root "$PWD" --archive /path/to/h8c-reference-39118951636.zip \
  --output /tmp/w1-m13-check-01

python research/NeuralMoments/performance/m13_pinned_native_build.py \
  --root "$PWD" --archive /path/to/h8c-reference-39118951636.zip \
  --output /tmp/w1-m13-real-01 --execute --fetch-pinned-sources --workers 2
```

Successful compilation still requires M11/M12 full material/Jacobian/geometry/time evidence and subsequent W0 math-contract/W2 real-teacher review before any production merge. The historical H8e failed branch-hash result is unchanged. Neither paper-matched speed nor complete Faster/Newton performance has been measured in M13.

**Status: native build-entry source and local safety regression COMPLETE; native computation BLOCKED on this environment.**