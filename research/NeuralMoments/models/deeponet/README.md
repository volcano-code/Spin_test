# W5 M1 — analytic DE-DeepONet + Geometry-MLP smoke

**Scope:** `volcano-code/Spin_test`, branch `research/neuralmoments-w5-deeponet-20261019`, based on freeze `0bcc187b3005478baa586a6d6f450e73811ca342`.
The W5 start contract is `research/ParallelLaunch/W5_START_HERE.md`.
No files outside W5's two model directories and the standalone W5 test are changed.

## Provenance and **hard limits**

This is an **independently labeled analytic architecture smoke test**, not a trained Spin solver, not a Cherchi Boolean/intersection truth set, and not the original NeurIPS DeepONet implementation. The W0 contract mapping real ten-dimensional `c` and geometry `D` into production `(r,J)` has **not** been imported or validated in this milestone. Do **not** use this result to claim reconstruction accuracy, real-geometry transfer, 3D-printability or speed relative to Faster/Cherchi/CGAL. W2 must supply frozen independent real teacher records; W0 must supply the frozen transformation and output-order contract before formal training. Nothing here generates pseudo-ground-truth from a network.

For the isolated smoke only, `D=[one_hot(box,sphere,ellipsoid), center_xyz, semiaxes_xyz]` describes an axis-aligned solid (9 scalars). `c` consists of 10 coefficients for a *synthetic polynomial density* on the **fixed** solid:

\[
\phi(x)=[1,x,y,z,x^2,y^2,z^2,xy,xz,yz]^T,\quad
\rho_c(x)=1+\phi(x)^T c,\quad
r(D,c)=\int_D \phi(x)\rho_c(x)\,dx,\quad
J(D,c)=\int_D \phi(x)\phi(x)^T\,dx.
\]

`analytic.py` independently computes all required moments up to order 4: centered boxes use uniform-factorized moments and balls/axis-aligned ellipsoids use exact solid-ellipsoid second/fourth moments, with binomial shifts for arbitrary centers. No mesh sampling or network outputs are used as labels. This synthetic `c` is **not** the physical design/cut parameter of Spin; the Jacobian happens to be constant in `c` for this particular smoke.

## Architecture and interfaces

- `DeepONetMoment.encode_geometry(D) -> z_D` precomputes both the `[10,rank]` geometry branch and its output bias **once**. `moment(z_D,c) -> r[10]` runs only the small parameter trunk/dot; repeated queries may be `[Q,10]`. `jacobian(z_D,c)` uses `torch.func.jacrev` and returns `[10,10]` (or `[Q,10,10]`). An explicit test instruments the branch to prove that repeated queries do **not** execute it again.
- `GeometryMLPMoment` uses the same geometry encoder widths and a size-matched `[z_D,c]` MLP head with exactly the same public API; the model families have **13,674** and **13,482** trainable parameters, respectively (about 1.4% difference).
- `adapt.fit_residual_adapter(model,z_D,support_c,support_r)` keeps network weights frozen and fits a ridge-regularized affine residual correction from **0/1/2/4/8 independent teacher queries**. The adapter exposes `predict(c)` and `jacobian(c)`; zero queries preserve the base model exactly. Few-shot fits are not guaranteed to improve on every task.
- `model.complexity()` counts **linear-layer MACs**, with geometry work charged once and parameter-query work charged per query. Two FLOPs per MAC is only an *approximation*; activation, memory and autograd work are excluded. These counts are **not real GPU throughput**.

## Repeat the actually executed work

Python >=3.10, PyTorch >=2.0, pytest. No CMake, CAD, GPU, downloaded weights or external solver required. From repository root:

```bash
python -m pytest -q tests/python/test_w5_deeponet_smoke.py
python -m research.NeuralMoments.models.deeponet.smoke \
  --seed 19 --steps 12 --repeats 15 --per-family 20 \
  > research/NeuralMoments/models/deeponet/smoke_seed19_cpu.json
```

The 12 training steps are a deliberately small CPU **functional check**, **not** convergence or a publication-quality comparison. Train geometries are **boxes and spheres only** (20 of each, 2 controls/geometry = 80 cases); held-out test geometries are **ellipsoids only** (20, 2 controls/geometry = 40 cases). Seeds and label formulas are fixed. Each model is initialized identically for its residual-only versus derivative-enhanced arm; both arms use the same minibatch draws, Adam lr=0.003, batch size 8. Enhanced loss = MSE(r) + 0.5 MSE(J); residual-only loss = MSE(r). All labels come from the analytic teacher. Train times account for the fit loop, not label generation/evaluation. GPU hours = **0**. Repeating CPU timings will yield different values due to system noise; no conclusions should be drawn from sub-millisecond ratios.

The smoke reports: r MAE and relative L2; J MAE and relative L2; directional-derivative MAE; regularized, norm-capped synthetic Gauss-Newton step L2 error and the **signed** true-objective gap compared with the analytic-J reference step; 0/1/2/4/8-query adaptation MAEs; train CPU seconds; cold geometry+head time, warm cached head time and a cached full `10x10` jacrev time. Step metrics are **synthetic decision diagnostics**, not claims about actual Spin optimization.

## Executed evidence

The tracked file `smoke_seed19_cpu.json` contains the complete machine-readable results from the exact command above, on **Python 3.13 / CPU / single PyTorch thread**, including platform and PyTorch versions. `test_log.txt` contains the separately executed standalone regression result. Errors shown in the JSON are real short-smoke errors, not target error tolerances and not held-out real-mesh validation.

### Next milestone (blocked on external contracts for **formal** data)

1. Integrate the immutable W0 definition of geometric transforms, `c`, ten output moments and Jacobian ordering; add cross-checks for units, topology strata and direction derivatives.
2. Consume frozen W2 independent real Cherchi teacher records without neural-label substitution; require provenance/checksums, topology-split train/test families and train/test leakage audit.
3. Run multi-seed, fixed-budget derivative-enhanced vs residual-only training, true optimization-decision and trust-region evaluation, 0/1/2/4/8 oracle-query budget curves, GPU time/memory and cold/warm performance **against** the real expensive evaluator. The current 12-step CPU demonstration is insufficient for such claims.
