# W6 M4 — Compact U-FNO encoder ablations, validation-only early stopping, three seeds

**Only writable branch:** `research/neuralmoments-w6-pcraft-20261019` in `volcano-code/Spin_test`. Base M3 commit: `0aedc2263d7f327bd72746d3002122c100d33bee`. Only new files under `research/NeuralMoments/models/pcraft_ufno/`; no W0/W2/W5/main edits.

## Implemented

- `m4_lite_model.py`: independently implemented geometry-cached ten-moment surrogate. Three parameter-matched variants: `lite_dual` (axiswise FFT at 4³ and 2³), `lite_bottleneck` (2³ FFT only), `lite_local_only` (no FFT). No full voxel displacement/stress decode. `encode_geometry(D)->z_D[B,24]`, `moment(z,c)->r_D[B,10]`, `jacobian(z,c)->J_D[B,10,10]` remain separately callable and differentiable for repeated c. Positive projective scale invariance is enforced through c normalization; sign inversion is not identified. No FEM PINO loss, field decoder or unapproved teacher labels.
- `m4_experiment.py`: reproducible same-analytic-data benchmark of three new variants and W5 source-pinned DeepONet and Geometry-MLP snapshots **already committed by M3**. Three seeds: 19,23,29. Per seed, source dataset **matches prior M3 SHA-256 exactly**, 40 boxes/spheres × two native plane cuts = 80 labeled examples. Eight whole geometries (16 queries) are set aside for validation, leaving 32 geometries (64 queries) for optimizer fitting; independent unseen ellipsoid family test contains 20 geometries (40 queries). **Held-out test is never used for early stopping.** Validation determines one checkpoint per model, using `r_MAE+0.25*J_MAE` every 10 steps, patience 5, max 100 steps, batch size 8, Adam lr 0.003. The same per-seed training minibatch schedule and derivative loss `MSE(r)+0.5*MSE(J)` is used for all architectures.
- `m4_moment_only_cpu.json`: independent same-seed/geometry/early-stop control for all three W6 variants without J training loss. W5 counterparts are not rerun in the moment-only arm in M4.
- `test_m4.py`: executable unit/integration regression for data SHA, family/geometry validation isolation, FFT modes/gradients, caching, finite-difference J, projective radial null, source-derived capacity parity, early stopping and 5-way CPU end-to-end.

## Actually executed local CPU evidence

```
PYTHONPATH=<repo_root> python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m4 -v
PYTHONPATH=<repo_root> python -m research.NeuralMoments.models.pcraft_ufno.m4_experiment \
  --seeds 19,23,29 --steps 100 --per-family 20 --repetitions 7 \
  --output research/NeuralMoments/models/pcraft_ufno/m4_three_seed_cpu.json
PYTHONPATH=<repo_root> python -m research.NeuralMoments.models.pcraft_ufno.m4_experiment \
  --seeds 19,23,29 --steps 100 --per-family 20 --repetitions 5 \
  --models lite_dual,lite_bottleneck,lite_local_only --moment-only \
  --output research/NeuralMoments/models/pcraft_ufno/m4_moment_only_cpu.json
```

- **14/14 tests passed** (2.074 seconds, exit 0); both full CPU jobs exited 0; no GPU was used. Python 3.13.5, PyTorch 2.10.0+cpu, single PyTorch/BLAS thread. Local testing reconstructed M2 `analytic_cut.py` in a separate sandbox: the regenerated **training dataset SHA-256 matches all three frozen M3 train SHA strings**. GitHub's existing, unmodified `analytic_cut.py` remains the production/reference location; its bytes were not changed for M4.
- Original W5 model blobs rechecked on the current W5 branch: DeepONet `7aa363769c0baf9f843d50e268164e761b566977`, Geometry-MLP `85db98ec60926a653270020f05294a7347221dcb` and interface `9d776e5c324140899f03296ee96dbfad602f8836`. The M3 local geometry MLP snapshot has ONLY an import-path compatibility fix; otherwise identical weights/architecture. **All five models are within 5% trainable real DOFs** (13,482–14,122). W5 consumes a lossy label-blind 9D summary of the same voxel tensor, versus full 4-channel voxels for W6: this is NOT representation-equivalent and is NOT a production model ranking.

### Results: held-out analytic ellipsoids, derivative-enhanced training

| architecture | real parameters | r MAE mean ± SD (3 seeds) ↓ | J MAE mean ± SD ↓ | CPU cold median across seeds ↓ | selected step 19/23/29 |
|---|---:|---:|---:|---:|---|
| lite_dual | 14,122 | 0.02769 ± 0.00616 | 0.01826 | 1.576 ms | 100/100/100 |
| lite_bottleneck | 13,746 | 0.03097 ± 0.01388 | 0.01731 | 2.053 ms | 100/100/100 |
| lite_local_only | 14,098 | 0.03082 ± 0.01262 | 0.01819 | 0.809 ms | 100/100/80 |
| W5 DeepONet | 13,674 | **0.02662 ± 0.00362** | **0.01697** | 0.576 ms | 100/100/90 |
| W5 Geometry-MLP | 13,482 | 0.02908 ± 0.01060 | 0.01981 | **0.339 ms** | 100/80/80 |

**Interpretation:** a more compact spectral architecture and longer training improved results over 12-step architectural smoke, but did **not** beat the matched-budget W5 DeepONet on held-out r/J MAE. The local-only architecture cuts cold encoder overhead but is **not** an FNO if its FFT blocks are absent. The 2³-only spectral variant is not necessarily faster than the 4³+2³ variant because parameter/head and small-FFT overhead can dominate at 8³; do not infer GPU throughput from single-thread CPU timing.

### Derivative supervision ablation

On the same three seeds and splits, W6-only `J` MAE with the derivative loss vs moment-only is: `lite_dual: 0.01826 vs 0.02443`, `lite_bottleneck: 0.01731 vs 0.02305`, `lite_local_only: 0.01819 vs 0.02469`. Corresponding raw moment MAEs are `0.02769 vs 0.02838`, `0.03097 vs 0.03057`, and `0.03082 vs 0.03073`: J improvement does **not** guarantee better r. Predicted `Jc B^-1` full-batch maximum asymmetry remains large (e.g. 0.456 for `lite_dual`); despite exact teacher Jq symmetry this neural map is **NOT** physically integrable by construction. Do not advertise it as a valid Hessian/solver derivative.

## Failed or blocked validation

1. W2 latest observed `teacher_manifest.json` still reports `ADAPTER_SMOKE_ONLY`, `native_teacher_runs=0`, `training_samples=0`. **No verified native Cherchi material labels, no real geometry proof, no production solver result.** The M2 fail-closed teacher gate remains in force.
2. CPU-only low-resolution (8³), three seeds and up to 100 steps. GPU peak VRAM and GPU training time are **not measured**, and native Faster/Cherchi performance speedup **cannot be claimed**.
3. W5 uses a lossy 9D summary while W6 sees 4-channel voxels; there is no formal input representation equivalence. These results are not a definitive operator-vs-MLP scientific comparison.
4. Several configurations select the 100-step budget endpoint, indicating that training convergence is **not demonstrated**. Error and latency need further multi-scale/multi-seed validation.
5. Existing `M3` one-dimensional test had clipped/trust-region-saturated steps. M4 does not make claims of improved Spin optimization decisions; full optimization with native teacher and independent acceptance remains future work.
6. Local M4 tests used byte-matching data generation rather than a native/Cherchi solver or a freshly fetched Git checkout; no GitHub CI result is implied by local 14/14 success.

## Next milestone

Given the persistent `Jq` asymmetry and derivative structural mismatch, consider a conservative W0-aligned architecture with a scalar generating potential in monomial coordinates `q=Bc`, so moment structure and symmetrized Jacobian can be audited when the smooth ambient hypothesis is satisfied. This requires careful sign/retained-halfspace/tangent contracts and cannot be applied indiscriminately to discrete or invalid W2 gradients. When sealed W2 native material is released, run strict provenance and geometry-family-split independent evaluation and compare true optimizer decisions on full material.
