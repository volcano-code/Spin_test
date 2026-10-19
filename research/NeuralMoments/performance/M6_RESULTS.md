# W1 M6 — archived H8 independent exact validation acceleration

**Branch:** `research/neuralmoments-w1-native-20261019` (exclusive directory only)

**Frozen main ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Actual changes

- Added `m6_independent_tetra_gmp.cpp`, a standalone C++17/GMP **tetrahedron-at-origin** exact ten-moment verifier. This is mathematically independent of the existing native production **surface-divergence** code. It has its own canonical decimal rational parser, full triangle nondegeneracy and oriented-edge closure gate, exact positive volume requirement, bounded stream format, and fail-closed errors.
- Added `m6_archived_validation_replay.py` to read only SHA-256-pinned real H8e historical CI artifact `12134772056` (`14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`). All 25 original archived same-call packet SHAs, q, moment/Jacobian shapes, material provenance/Boolean identity and historical boundary-audit flags are checked. It independently re-integrates the ten exact moments in GMP, compares all 250 binary64 outputs with the original independent Python Fraction and production values, verifies original 9 FD stencils against the **archived** analytic Jacobian, and preserves eight feature-hash drifts and the original FAILED CI state.
- `test_m6.py` is a real g++-built executable smoke with 11 negative and positive tests. Three real H8e packets (indices 0, 12, 24) also ran the original Python Fraction tetra formula **fresh** to show all ten GMP exact rational results equal component-by-component (not just tolerance). Remaining 22 points match the original independent Fraction `float64` output from historical CI; M4 separately re-evaluated all 25 with Python Fraction.
- Production `src/`, `bindings/`, `python/make_it_stand/`, and other windows were **not changed**. No packed binary, historical failure log or raw CAD was replaced.

## Actually executed results (one local machine, zero swap)

| Result | Actual measurement |
|---|---:|
| Real archived Cherchi H8e packets | **25/25** |
| Exact independently checked historical ten-moment components | **250/250** |
| Fresh exact Python Fraction vs C++ GMP ten-vectors | **3/3 points, 30/30 components** |
| Original numerical five-point stencils independently checked | **9/9** (max scaled error `2.6019151368622826e-10`) |
| Original feature-hash drift | **8/24, unmodified FAILED** |
| Local C++/Python regressions | **11 passed, 0 skipped** |
| Paired validation-sample GMP speed vs Python Fraction | **median ~7.77x**, individual ratios **7.77x, 7.04x, 8.12x** |
| Optimized archived 25-point replay, including archive unpacking/identity/gate/FD | **43.101666244 s** |

The `43.10 s` is a *fresh archived-material replay wall time*: it is **not** a matched complete old/new solver A/B test. The prior M4 `251.67 s` was a different execution with a different validation workload; quoting `251.67/43.10` as achieved Faster speedup would be incorrect. Paired ~7x numbers compare the independently computed ten-moment verifier subset, not the Boolean/geometry evaluator, Newton or 3D printing.

### Real optimized 25-point timing, mutually exclusive stages

| Stage | Seconds |
|---|---:|
| ZIP read | 0.420 |
| Gzip decode | 4.268 |
| JSON decode | 14.881 |
| Archive identity/provenance | 0.088 |
| Exact material-stream construction | 0.954 |
| Standalone independent native GMP (input+face gate+tetra integration) | 21.105 |
| Parity and finite reporting | 0.789 |
| Total wall including unattributed orchestration | 43.102 |

Source, binary, machine, memory, stage ns, SHA, per-point results, fail-closed test log and strict old/new scope are in `evidence/`.

## Reproduce

```bash
# Operate in a W1 checkout. No production bindings are changed.
g++ -std=c++17 -O2 -Wall -Wextra -pedantic \
  research/NeuralMoments/performance/m6_independent_tetra_gmp.cpp \
  -o /tmp/w1-m6-tetra -lgmpxx -lgmp

# Retrieve actual historical artifact ID 12134772056 from workflow 39121571756.
# The tool will reject any archive with a SHA other than the pinned one.
W1_M6_H8E_ARCHIVE=/path/h8e-25point-39121571756.zip \
 python -m unittest discover -s research/NeuralMoments/performance -p 'test_m6.py' -v

python research/NeuralMoments/performance/m6_archived_validation_replay.py \
 --archive /path/h8e-25point-39121571756.zip \
 --binary /tmp/w1-m6-tetra --points 25 \
 --fraction-points 0,12,24 --output /tmp/w1-m6-paired

python research/NeuralMoments/performance/m6_archived_validation_replay.py \
 --archive /path/h8e-25point-39121571756.zip \
 --binary /tmp/w1-m6-tetra --points 25 \
 --fraction-points '' --output /tmp/w1-m6-native25
```

The same reference math, all packet proofs, backend identities, stage accounting, and archived failure status are preserved. `--fraction-points ''` skips only *new duplicate Python Fraction arithmetic*; every archived point is still independently integrated by native GMP tetrahedron, all ten outputs compared with prior same-call independent Fraction/production values, and full native oriented-boundary gate is run. It does **not** skip certified source geometry, because this is offline archive replay, and new full self-intersection proof is explicitly **not** claimed.

## Remaining mandatory gates

1. Native Cherchi Boolean plus M5 full-call statement accounting **on a matching built repository**; current environment cannot resolve GitHub DNS and lacks all three production `.so` modules. Historical original 25-point `301.549423189 s` still unclassified, cannot deduct values from another host/experiment.
2. Full production old/new 10×10 Jacobian and exact same-call material, original accept/reject, terminal partition, + full Faster solver speedup. No production code has been optimized, so these are not certified.
3. W0 native mathematical contract and W2 true teacher comparison before any production change or publication claim; retain H8 nonauthor reconstructed-CAD scope and original FAILED hash-branch record.
4. Noodles V7 original 393.44/168.27 s same-run evidence unavailable; do not splice unrelated historical timings.
5. Memory ≤24GiB, zero swap, serial native jobs, one job ≤60min and ≤4 compile jobs.

**M6 conclusion:** independent exact **verification** is significantly faster in three paired real archived H8 samples, with full 25 packet numerical/identity checks passed. This is **not** evidence of faster production Cherchi/Newton or paper-matched speed.
