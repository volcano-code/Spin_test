# W5 M4 — W0-native physical P0 labels, derivative training, held-out family decisions

**Write scope:** W5 branch `research/neuralmoments-w5-deeponet-20261019`, exclusively under `research/NeuralMoments/models/deeponet/` and independent `tests/python/test_w5_m4_native_p0.py`. No changes to `main`, W0 or W2, nor cherry-picks/merges. Frozen common source: `0bcc187b3005478baa586a6d6f450e73811ca342`.

**Read-only dependencies checked 2026-10-19**: W0 `bfedacd3a1f4e10d30f1258331260380739d243c`, W2 `56212f46b007fa255cc5796224192010aa67513c`. The W2 manifest remains `w2-cherchi-teacher-v1-pre-w0`, `ADAPTER_SMOKE_ONLY`, `native_teacher_runs=0`, `training_samples=0`. W2 deliberately rejects self-attested `MomentContractV1` digests as valid derivative certificates. **Real Cherchi training is blocked** and no W0/W2 code or mock data is incorporated into training.

## Materially new since M3

M1/M2 used a **nonphysical synthetic polynomial density** whose c was not a native cut parameter. M3 added the isolated correct-native sphere-cap oracle but *did not train*. M4 adds actual differentiable-supervision training on **physically retained material mass moments** for THREE closed analytic primitive families, from two independently implemented mathematical routes:

- `native_p0_families.py`: a uniform box, exact ball, or axis-aligned ellipsoid `D` is cut by the *positive* halfspace `beta=c0+c3*z >= 0` with `c=(-h,0,0,1,0,...)/sqrt(1+h²)` and `c3>0`. It returns the ten **ordinary undoubled** raw retained mass moments `r_D` and the **full native ambient** Jacobian `Jc[10,10]` for that smooth continuum point. All formulas are finite polynomial antiderivatives or exact gamma/disk moments (up to float roundoff), not network-generated labels. This experiment has `F=0`; `r_total=r_D`, `J_total=J_D`; no fixed mass double counting.
- The correct W0 `B=diag(1,1,1,1,1,1,1,2,2,2)` maps native symmetric-entry `c` to the monomial polynomial. Under **smooth interior horizontal cuts only**, `Jc B^{-1}` is symmetric, `Jc c=0` and `Jc (dc/dh)` matches the independent finite difference of physical r(h). No symmetry is assumed directly for `Jc`.
- A shape's **10D physical descriptor** contains original (uncut) center, axes, density, mass and two central second-moment invariants. It contains **no** test-family one-hot flags, cut-specific labels, or mesh/Cherchi output. It is distinct from M3's **24D closed-triangle-mesh descriptor**. Thus M4 does *not* show that native CAD shapes are trained or feature-compatible with real teacher records.
- `m4_native_p0_train.py`: trains the existing cached DE-DeepONet and parameter-matched Geometry-MLP, each from the **same per-seed initial parameters** with equal data and minibatch draws for ordinary `MSE(r)` and derivative-enhanced `MSE(r)+0.5*MSE(Jc)`. It tests an **unseen geometric family** (ellipsoid) distinct from the box/sphere training families. It measures r error, W0 per-component physical-normalized r error, full J error, height-directional derivative error, and true post-update objective for a constrained **1D horizontal cut-height** damped Gauss–Newton step. Neither full native 10D optimization nor actual Cherchi speedups are implied.
- A frozen-network ridge affine residual head is tested with *exactly* 0/1/2/4/8 **independent analytic oracle r** support calls, evaluated on different cut-height queries. An adaptation sample is not silently recycled as its own test label. Fewer oracle calls are not guaranteed to improve every seed/model.

## Independent audit and known boundaries

Analytic box mass and moments are checked against separable box integrals; sphere r/J against the existing independent W5 M3 sphere-cap oracle; the axis-aligned ellipsoid retained moments against the **independent affine pushforward** of a sphere-cap integral. A finite difference along native c(h) verifies the full native J's permitted tangent response. Cross terms `YZ`, `XZ`, `XY` carry the factor 2 in native c, **but the r outputs do not**. A `Jc B^{-1}` diagnostic is only meaningful under this smooth-continuum hypothesis; do not apply it to discrete contact, mesh topology events, general nonlinear cut variation or unknown derivatives.

M4's primitive identity SHA-256 is a hash of an exact analytic specification, **not** the byte identity of CAD/OBJ geometry. Its labels are analytic retained *perfect solids*, not the tessellated surface used by M3. The closed-form sphere/box/ellipsoid assumption avoids geometry ambiguity only inside this synthetic physical benchmark; it supplies no Boolean or manufacturing proof. Our held-out family exercise is not the same as held-out real CAD.

## Reproduce the locally executed work

Python 3.13, PyTorch 2.10 CPU, NumPy 2.3, pytest 9.0. No CUDA or native build. From W5 checkout root:

```bash
python -m pytest -q \
  tests/python/test_w5_deeponet_smoke.py \
  tests/python/test_w5_m2_contract_and_gate.py \
  tests/python/test_w5_m3_mesh_and_p0.py \
  tests/python/test_w5_m4_native_p0.py
# Result: 56 passed, 26 subtests passed

python -m research.NeuralMoments.models.deeponet.m4_native_p0_train \
  --seeds 7,19,31 --steps 500 --per-family 20 --repeats 25 \
  --w2-manifest /path/to/read-only/w2/teacher_manifest.json \
  > research/NeuralMoments/models/deeponet/m4_native_p0_seed7_19_31_cpu.json
```

Dataset per seed: 20 box + 20 sphere training geometries; 20 independent ellipsoid test geometries; **three independent native-c cut heights per geometry** (120 train and 60 test examples). `random.Random` and `torch.manual_seed` fixed per seed. Minibatch size 16; Adam learning rate 0.003, 500 steps; no scheduler/early stopping. Derivative weight 0.5; output/native Jacobian learned without any post-hoc imposed Hessian symmetry. Per-arm parameter counts: DeepONet 13,722; Geometry-MLP 13,530 (1.42% difference). All timing is uncompiled, single-thread CPU; GPU elapsed is 0; reported native-teacher queries are 0. Timing medians cover the model path only and are **not** a speed comparison against W2/Cherchi.

## Recorded cross-family heldout results (mean across seeds 7,19,31)

| Model / loss | r MAE | Jc MAE | height directional MAE | 1D step absolute error | mean signed true objective gap |
|---|---:|---:|---:|---:|---:|
| DeepONet / r | 0.050377 | 0.082847 | 0.10985 | 0.029802 | 0.0021835 |
| DeepONet / r+J | 0.048872 | **0.044132** | 0.081026 | 0.029067 | 0.0019382 |
| Geometry-MLP / r | 0.049516 | 0.083930 | 0.11925 | 0.041749 | 0.0065603 |
| Geometry-MLP / r+J | **0.045212** | 0.047251 | 0.088079 | 0.041390 | 0.0043768 |

The mean full Jc MAE drops by 46.7% (DeepONet) / 43.7% (Geometry-MLP) when adding derivative supervision **on this analytic P0 benchmark**, not on native CAD. Step errors change less; successful derivative regression is **not** proof of meaningful solver acceleration or convergence.

Mean 0/1/2/4/8-query adaptation results, latency medians and per-seed raw data are preserved in **`m4_metrics_summary.json`** and **`m4_native_p0_seed7_19_31_cpu.json`**. In these runs, the error curves are sometimes nonmonotonic; this is expected for few-shot underdetermined affine corrections. The signed objective gap may be negative if an approximate decision happens to outperform a damped one-step oracle locally, so no nonnegativity guarantee is claimed.

## Environment, failures, CI, next

The test fixture caught and corrected an M4 performance-report schema migration bug (`parameters` moved under `estimated_complexity`); the final combined regression re-run passed **56/56 tests**. The process's max RSS was about 324 MiB, total CLI wall time ~15.3s in this isolated container. Models trained in serial, CPU only. No CI status should be marked green without a real remote workflow result.

**Next (M5)**: independently authenticated W2 per-CAD `r_D,J_D` labels with valid original/F/D geometric SHA, frame/density transformations, verified smooth neighborhood/tangent category, allowed splits and exact material, plus a frozen geometry encoder over comparable CAD data. Real native training, Cherchi-vs-network cost, full 10D optimizer decision quality, H8 anomaly, Teapot non-watertight input and solver-level speedup remain **unverified**. Never train or certify on the current W2 `ADAPTER_SMOKE_ONLY` manifest.
