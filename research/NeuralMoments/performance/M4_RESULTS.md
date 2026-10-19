# W1 M4: archived H8e full 25-point exact arithmetic replay and stage attribution

**Frozen branch:** `research/neuralmoments-w1-native-20261019`. **Only wrote** `research/NeuralMoments/performance/`.
The original 25-point Cherchi job [39121571756](https://github.com/volcano-code/Spin_test/actions/runs/39121571756) and its **failure** (8 original feature-hash drifts) are preserved unmodified. This is a newly executed **archived material replay**, **not** a new native Cherchi Boolean, self-intersection audit, derivative construction, or Faster Newton solve.

## Input and reproducibility

- Download original artifact ID **12134772056** (`heart-h8e-25point-real-jacobian-proof-or-failure`). ZIP SHA256: `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`.
- Frozen request SHA256: `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`.
- Each of the 25 snapshots contains a 8455-vertex / 16910-face exact rational material from historical Cherchi. Every point's archived SHA was rechecked.
- Compile existing independently tested `real_h8_gmp_probe.cpp` (M3 code, production ABI unchanged) serially:

```bash
g++ -std=c++17 -O2 -Wall -Wextra -pedantic research/NeuralMoments/performance/real_h8_gmp_probe.cpp -o /tmp/w1-h8-gmp -lgmpxx -lgmp
python research/NeuralMoments/performance/m4_25point_attribution.py \
  --archive /path/to/h8e-25point-39121571756.zip \
  --binary /tmp/w1-h8-gmp --out /tmp/w1-m4-out --points 25 --repeats 1
W1_H8E_ARCHIVE=/path/to/h8e-25point-39121571756.zip \
W1_M4_NATIVE_BIN=/tmp/w1-h8-gmp \
python -m unittest discover -s research/NeuralMoments/performance -p 'test_m4.py' -v
```

A checked-out repository is sufficient: `m4_25point_attribution.py` has no hidden M3-bundle source import. Native work stays serial, swap=0, no >24 GiB resource budget, per job <=60min, compilation at 1 worker. Output directory must be fresh. The full source and per-point evidence are also in the separate M4 ZIP package.

## Actual measurements (local Python 3.13.5, Linux x86_64, single runner)

- **25/25 full archived packets** validated: each same-q, topology hash, geometry identity, SHA-256, original closed-material certification flag, native backend, 10-vector and archived 10x10 Jacobian shape.
- Independently re-evaluated **250/250 ordinary raw mass moment values** with Fraction tetrahedron integration and a separately compiled C++/GMP surface integral. Exact old/prepared GMP ten moments and independent Fraction values match the archived points in binary64 for every component.
- 9/9 independent five-point finite-difference checks using the **freshly computed Fraction 25-point values** agree with the original base-point analytic 10x10 Jacobian at scaled error <= `2.602e-10`. Analytic Jacobian is **archived, not regenerated**; finite probes cannot certify a smooth neighborhood. 8/24 original feature hashes still differ, so original native job remains failed.
- New offline archived-material pipeline wall **251.671440849s**, and mutually exclusive new steps **251.527664084s**; new unexplained wall **0.143776765s**. Components (seconds):

| Measured offline replay component | Seconds |
|---|---:|
| Independent Python Fraction exact tetrahedron ten-moment evaluation | 174.992 |
| Standalone native GMP subprocess (material stream, 1 legacy + 1 source-ref route / point) | 50.102 |
| JSON decode | 16.392 |
| Gzip decode | 4.844 |
| Fraction token parsing | 3.937 |
| ZIP entry read | 0.603 |
| Remaining hash, identity, parity, journal stages | 0.659 |

- Historical H8e 25-point original wall `379.493727883s`, existing named evaluator stages `77.944304694s`, unattributed `301.549423189s`. These are from **a different CI host**, different work and timing instrumentation: DO NOT subtract the fresh 174.992s from historical 301.549s or report a solver speedup.
- Machine in this replay had ~5.8GiB total RAM, 0 swap; measured Python process peak RSS ~248MiB. Original native C++ GMP source and built executable SHA logged in `baseline-performance.json`.
- Local `test_m4.py`: **10 passed, 0 failed, 0 skipped** with real source artifacts supplied. An earlier porting smoke passed 1/1 real point using the self-contained code after replacing the previous M3 helper import; all 25 data were tested by the same arithmetic implementation before that import-only refactor.

## W1 admission conclusions

**Passed:** archived packet identity, independent arithmetic equality, replayed FD numerical consistency, explicit non-overlap clock, negative archive tests. **Not passed:** fresh Cherchi Boolean run, current native boundary/self-intersection proof, production ABI modification, full baseline-vs-optimized solver, same-call acceptance/rejection, accepted terminal exact material, W0/W2 full approval, author-matched paper speed.

The next optimization target should be the full production evaluation/validation/snapshot sequence, not just removing GMP token roundtrips; M3 observed isolated gains were small. A genuine original-environment instrumentation run is still necessary before attributing the historical 301.55 seconds.
