# W6 P0 upstream integration adapters

This is the first controlled integration slice for the W6 candidate library.

## What is actually integrated in this slice

1. **NeuralOperator GINO adapter**: pinned upstream GINO is used as a point-cloud geometry encoder. A W6-specific coefficient-conditioned head maps the pooled geometry code and native ten coefficients to the ten raw variable-domain moments. This is an adapter, not transferred CFD weights.
2. **NeuralOperator UQNO adapter**: the upstream UQNO wrapper is used for a positive residual-scale head. A separate split-conformal calibration object produces a finite-sample simultaneous radius only when the calibration sample count supports the requested alpha.
3. **QuadrANN model core**: a side-effect-free extraction of the original MIT model layers is vendored with the original license. The upstream example's import-time training/plotting loop is deliberately excluded. The adapter consumes a point cloud sampled uniformly from the cut domain, a separately supplied domain measure and density, and returns ten raw moments. It does not provide a Jacobian.
4. **Algoim C++ smoke**: CMake fetches the official pinned Algoim commit and compiles an independent unit-sphere ten-moment integration check. Algoim is a comparator/reference, not the authoritative Spin Cherchi teacher.

## What is not claimed

- No pretrained CFD weights are claimed to transfer to Spin.
- No W2 Cherchi teacher labels are consumed; the current W2 manifest has zero admitted training samples.
- UQNO calibration is predictive uncertainty, not physical or derivative certification.
- QuadrANN output is an approximate moment quadrature proposal; domain measure must come from an independent source.
- No P0 adapter returns an admitted J_D. Every path withholds J_D and Newton/training admission.
- Algoim passing its analytic sphere check does not certify the Spin Boolean pipeline or replace Cherchi.
- No end-to-end Spin speedup or GPU/high-resolution result is claimed.

## Reproduction

From repository root:

```bash
python -m pytest -q research/NeuralMoments/models/pcraft_ufno/p0_integration/tests/test_contracts.py
```

Install optional upstream dependencies for the complete CPU smoke:

```bash
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install torch-scatter torch-cluster -f https://data.pyg.org/whl/torch-2.5.1+cpu.html
python -m pip install torch-geometric==2.6.1
python -m pip install "git+https://github.com/neuraloperator/neuraloperator.git@a6648eeeb60fe0837f2d7d021517a945a159a0c8"
python -m pytest -q research/NeuralMoments/models/pcraft_ufno/p0_integration/tests
```

Algoim:

```bash
cmake -S research/NeuralMoments/models/pcraft_ufno/p0_integration/algoim -B /tmp/w6-algoim-build -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/w6-algoim-build --parallel 2
ctest --test-dir /tmp/w6-algoim-build --output-on-failure
```

A dedicated GitHub Actions workflow runs the dependency-backed Python smoke and Algoim C++ smoke on pushes to the W6 branch.

## Latest cloud validation

- GitHub Actions run 42168194446: both jobs passed.
- NeuralOperator + QuadrANN CPU smoke: 8 passed in 2.96 s.
- Pinned Algoim C++ build and unit-sphere ten-moment test: passed; maximum absolute error 7.5044859215722681e-11 at quadrature order 8.
- This is adapter-level validation only. The models remain untrained; no W2 labels, J_D admission, native Newton or end-to-end speedup is claimed.

## Next gate

After CI passes, add matched moment/Jacobian accuracy and cost comparisons on the same synthetic mesh-derived inputs. The QuadrANN model must be trained on the same teacher budget and split as U-FNO/GINO. The UQNO calibration split must be held out. Formal Cherchi supervision remains blocked until W2/W0 admission.
