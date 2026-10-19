# W1 M2 — exact-GMP source-reference experiment and H8 same-call profiler

Branch: `research/neuralmoments-w1-native-20261019`. Exclusive paths: `research/NeuralMoments/performance/`. Frozen base: `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Native microbenchmark (genuine C++/GMP executable, not Cherchi)

```bash
cd research/NeuralMoments/performance
c++ -O2 -std=c++17 -Wall -Wextra -pedantic prepared_material_probe.cpp -o /tmp/w1-prepared-material-probe -lgmpxx -lgmp
/tmp/w1-prepared-material-probe --self-test
/tmp/w1-prepared-material-probe 32 5
python -m unittest discover -s . -p test_m2.py -v
```

Both variants use the **same new, canonical, exact GMP coordinates** for each test case; the legacy variant serializes to rational tokens and parses them back; the prepared variant holds an immutable `shared_ptr<const Geometry>` and consumes the exact coordinates directly. Both run the same exact orientable boundary/degeneracy gate and the same ten-moment divergence integrator, checked for exact equality over distinct inputs. A control rejects noncanonical GMP rationals, bad orientation, out-of-range faces, null source refs. This is an isolated arithmetic experiment; it does **not** run actual Cherchi Boolean, independently verify physical geometry/self-intersection, compute Jacobian, or change production ABI. Therefore isolated microbenchmark times are never paper speed or even full Faster evaluation speed.

## Real Heart H8 single-q replay (run only on pinned native host)

Requires the frozen prepared request with SHA-256 `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`, the existing H8 Python scripts, and matching compiled `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments` plus a populated `PYTHONPATH` for `python/` and the extension directories.

```bash
# Execute once at a time; compile at most 4 workers, run with zero swap and <=24 GiB.
export PYTHONPATH="$PWD/python:$PWD/build/heart-cloud-core/python:$PWD/build/heart-cloud-cherchi/python"
timeout 3600s python research/NeuralMoments/performance/h8_native_replay.py \
  --root . --request /path/to/verified/prepared-request.json --output /tmp/w1-h8-single-q-001
```

The runner preserves all production stages (source, original exact-source audit, Cherchi Boolean, construction motion, rational preparation, derivative and GMP integration, same-call material serialization), then performs fresh native exact rational boundary validation and independent Fraction ten-moment verification on the **same** material. It records an exclusive nonoverlapping ledger plus setup time and a strict sample end-to-end time including independent acceptance and snapshot. It fails closed into `failure.json`; only a complete validated sample emits `baseline-performance.json`. The separate `before_after.json` remains unqualified (null speedup) until both full old/new runs, same-input material/moment/Jacobian/acceptance/terminal parity, W0 math contract and W2 real teacher comparison exist.

## Limitations / next acceptance

- Noodles V7 `research/Noodles_v7_20261017/V7_STAGE_STATUS.json` was absent on frozen W1 branch at audit. Never substitute historical 569.56 s or 199.00 s for purported 393.44/168.27 s without identical source hashes and same-run raw events.
- The H8 request is generated as a CI artifact and is **not** checked in under the location searched; do not hand-fabricate a request from H8 narrative reports.
- Do not modify `src/` / `bindings/` or claim an accelerated complete solver until the native ABI experiment is rebuilt/regressed and the W0/W2 dependencies are satisfied.
- This probe's self-checks cover exact arithmetic and limited mesh edge topology; they do **not** certify independent self-intersection, author CAD, material legality, Hessian/Newton acceptance, full terminal closure or manufacturing.
