# W6 — P-CRAFT-inspired U-FNO-Moment, milestone 1 (untrained smoke)

**Scope:** only `research/NeuralMoments/models/pcraft_ufno/` in `volcano-code/Spin_test`, branch `research/neuralmoments-w6-pcraft-20261019`. Source pin: `volcano-code/test@24eda3e9b3f87ba16251a9025761986d6cfe3079`, `structural/models/pino.py` (`SpectralConv3d_Factorized`, `UFNO3d`, `UFNODualBranch3d`). **No source repository or other W branch was modified.**

## Implementation

- Reimplements *factorized* 1D FFT convolution (frequency mode clipping per axis) and a U-shaped 3D encoder (downsample, spectral bottleneck, upsample + skip, multilevel global pooling). Only one fixed `[B, latent_dim]` vector `z_D` is produced for each geometry; no 64³/256³ 9-channel field decoder.
- Accepts pre-canonicalized `[B,4,X,Y,Z]` or dictionary channels `density`, `occupancy`, `sdf` (negative inside), `internal_boundary` (aliases `signed_distance`, `inner_boundary`). Missing channels are **imputed**, not sensed; `sdf` uses `tanh(sdf/sdf_scale)` with an explicit scale. Coordinates `[-1,1]` form three additional internal channels.
- `model.encode_geometry(D)` -> `z_D`; `model.cache_geometry(D)` -> detached cache; `model.moment(z_D,c)` -> `[B,10]`; `model.jacobian(z_D,c)` -> `[B,10,10]` with `torch.func.jacrev`/`vmap`. `c` is normalized by its positive Euclidean norm inside the head, so **positive** scalar multiples are invariant and `J(c)c≈0`; negative sign is not identified.
- Moment and coefficient slots provisionally follow pinned Spin_test sources (`src/spin/QuadricCoefficients.cpp`, `python/make_it_stand/verification/faster_material.py`): `(constant/mass,x,y,z,xx,yy,zz,yz,xz,xy)`. The physical quadric cross terms are **twice** `c[7:10]` in evaluation; the raw `dr/dc` is *not* assumed symmetric. Any legal ten-moment structural penalty **must await W0**: there is no PINO equilibrium/constitutive/Von-Mises loss here.
- `ResidualAdapter` supports 0, 1 or 2 **actual** teacher `(c,r)` query pairs per *cached* geometry. One support adds a bias; two interpolate a projective normalized coefficient-space secant residual. These are explicit low-query baselines, **not guaranteed** to improve accuracy or preserve physical integrability. Never fit on held-out test teachers and claim zero-shot generalization.

## Local, reproducible smoke (CPU, no teacher GPU or native build)

From the repository root:

```sh
python -m unittest research.NeuralMoments.models.pcraft_ufno.test_smoke -v
python -m research.NeuralMoments.models.pcraft_ufno.benchmark --device cpu --grid-size 8 --repetitions 5
```

Dependencies: Python >=3.10, PyTorch >=2.1. Tests include independent exact unit-cube slab moments and derivatives, translated ellipsoid/sphere formulas, four-channel normalization, frequency mode clipping, projective radial null, finite-difference vs `jacrev` Jacobian, encoder backpropagation, cached re-use, and 0/1/2-support residual correction. **Untrained randomly initialized network outputs are not compared to teacher truth as quality metrics.**

## Fair comparison protocol (for the W5 handoff)

| Control | Requirement |
|---|---|
| Data | W0-signed ten-moment contract + W2 source teacher, explicit status and non-trainable held-out geometry families |
| Split | Same geometry family partition and random seed; no identical CAD identities or transformations leak across folds |
| Budget | Equal labeled geometries, equal teacher calls, 0/1/2-query adaptation, same sample/query weights |
| Model | Report complex parameters as **two real DOFs**; match active trainable parameters within stated tolerance; distinguish standalone geometry MLP/DeepONet vs shared-encoder head ablations |
| Timing | Same device/dtype/batch/grid and warm-up, separate encode, cached `r`, cached 10×10 `J`, first/cold response, peak allocated CUDA memory; synchronize GPU around timers |
| Error | Raw and normalized 10 moments, true native `J`/directional derivatives, independent optimization decision error; never infer speedup or accuracy from random smoke |
| Scientific limits | Fixed-material moments computed once, no fabricated FEM labels, independent full material/strong-truth acceptance, W0 projective sign/coordinate/scale rules |

**Pending:** W0 published/frozen `MomentContractV1`, W2 sealed Cherchi teacher, W5 implementions and comparable budget, 3D complex geometry dataset, training and independent validation. No `volcano-code/test` 12GB weights were available or loaded; this is *not* reproduction of previous FEM training. Do not report fabricated SOTA, GPU latency, or qualified optimization speedup.
