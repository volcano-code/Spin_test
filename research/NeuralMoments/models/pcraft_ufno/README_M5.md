# W6 M5 — Convex scalar-potential U-FNO moment head

**Repository:** `volcano-code/Spin_test`, W6-only branch `research/neuralmoments-w6-pcraft-20261019`. No changes to `main`, W0/W2/W5 or `volcano-code/test/main`. M4 parent before this milestone: `b5d3985ec4a10c74316bda6579767b58c13b4eaa`. This is an **analytic P0 experiment**, not a real Cherchi teacher run, production Faster implementation or manufacturing certificate.

## Motivation and exact mathematical property

M4's free 10-output head had held-out maximum asymmetry of `Jc B^-1` around 0.35–0.40. For smooth **full-ambient continuum** retained-halfspace derivatives, the W0 contract defines native coefficients `c=(a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy)`; ordinary raw moments are `r=(M,Lx,Ly,Lz,Qxx,Qyy,Qzz,Qyz,Qxz,Qxy)`. Its monomial coefficients satisfy `q=Bc`, `B=diag(1,1,1,1,1,1,1,2,2,2)`. Checking raw native `Jc` for symmetry would be a mathematical mistake.

`m5_potential.py` keeps the M4 **spectral bottleneck U-FNO** geometry encoder but drops its previous unconstrained 10-output head. It learns `w_k(z_D)>=0` once for fixed nodes `m_k=(1,x,y,z,x²,y²,z²,yz,xz,xy)` on an N³ quadrature grid, N in {4,6,8}. With `eps>0` and `q=Bc`, define:

```text
Phi(z_D,q) = Σ_k (w_k(z_D)/2) * [q·m_k + sqrt((q·m_k)^2 + eps^2 ||q||^2)]
r_D(z_D,c) = ∂Phi / ∂q
Jc(z_D,c)  = (∂²Phi / ∂q²) B
```

Every summand is convex and positively degree-one homogeneous in `q` for `q!=0`. Hence, in exact arithmetic, `Jq=Jc B^-1` is **symmetric positive-semidefinite**, `Jc*c=0`, `r_D(tc)=r_D(c)` for `t>0`, and the sign of `c` is **not** identified with its negative. The code calculates the first and second derivatives by closed-form tensor expressions; tests independently cross-check them against `torch.autograd.functional.hessian` and finite differences. The effective `encode_geometry(D)` computes the quadrature weights **once**, with cached heads producing ten moments and Jacobians for changes in `c`.

**Crucial boundary:** the smoothed hinge is an approximation to positive-part integration, so despite structural Hessian integrability, the predicted `r_D` is **not necessarily realizable as exact moments of a valid solid**. PSD/symmetry are *necessary-looking* smooth boundary properties but do not prove C++/Cherchi geometry, topology, valid F/D, manufacturing strength, or certified numerical accuracy. The Hessian property must **not** be applied to W2 tangent-only, discrete/contact, topology-changing or undefined derivatives without a separate hypothesis check.

## Dependencies and W2 gate

- W0 observed HEAD `bfedacd3a1f4e10d30f1258331260380739d243c`, native contract and B mapping used read-only.
- W2 observed HEAD `56212f46b007fa255cc5796224192010aa67513c`, `teacher_manifest.json` remains `ADAPTER_SMOKE_ONLY`, `native_teacher_runs:0`, `training_samples:0`. W6's earlier `teacher_gate.py` is still fail-closed. No native labels were used.
- W5 observed HEAD `0c67cd0e922a063d59ba17818976a8d157b85597`; the unchanged W5 model source is read from the W6 M3 snapshot with only a documented import-path shim. **W5 sees the same underlying voxels via a 9D lossy summary while W6 sees 4 raw channels plus label-independent 9D statistics**. The model capacity, oracle labels, seeds and budget are matched, but **full representation parity is not met**.

## Executed CPU protocol

```bash
python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m4 -v
python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m5 -v
python -m research.NeuralMoments.models.pcraft_ufno.m5_experiment \
    --seeds 19,23,29 --steps 100 --per-family 20 --repeats 7 --output m5_three_seed_cpu.json
python -m research.NeuralMoments.models.pcraft_ufno.m5_experiment \
    --seeds 19,23,29 --steps 400 --per-family 20 --repeats 7 --output m5_long_400step_cpu.json
python -m research.NeuralMoments.models.pcraft_ufno.m5_experiment \
    --seeds 19,23,29 --steps 400 --per-family 20 --repeats 7 \
    --names lite_potential_6,lite_bottleneck --moment-only --output m5_value_only_400step_cpu.json
```

The `--output` path can be any writable path, including the W6 project directory. Each seed has **40 distinct train-family geometries** (20 boxes+20 spheres), 80 synthetic analytic cut queries; validation holds out 8 *entire* training-family geometry IDs (16 queries); independent held-out testing uses 20 ellipsoids (40 queries). Identical seeds 19/23/29 and identical full-dataset SHA-256s match the archived M3 and M4 inputs. Batch 8, Adam lr=0.003, derivative objective `MSE(r)+0.5 MSE(J)`; validation selection `r_mae + 0.25 J_mae`, checked every 10 steps with patience 5. Maximum 100 (M4 parity) or 400 (exploratory longer run). All network models range from **13,448 to 13,840** real trainable parameters, including complex Fourier weights counted double. No GPU computation was used.

**Local executable tests:** 17/17 M5 tests passed, 14/14 prior M4 tests passed, `compileall` passed. The M5 tests independently verify positive homogeneous potential, autograd gradient and Hessian equality, finite-difference J across all 10 columns, PSD up to numerical precision, non-symmetric native `Jc` but symmetric `Jc B^-1`, sign distinction, caching once, valid nonnegative quadrature weights, training gradients, fixed F addition, and W2 fail-closed rejection. See `m5_test_local.log`, `m5_previous_m4_regression.log`.

### Held-out ellipsoid mean across three seeds (100-step maximum)

| Model | Real parameters | raw r MAE ↓ | native J MAE ↓ | max asymmetry of `Jc B^-1` ↓ |
|---|---:|---:|---:|---:|
| M5 potential 4³ | 13,528 | 0.07117 | 0.03993 | ~9e-9 |
| M5 potential 6³ | 13,448 | 0.06793 | 0.02838 | ~1.5e-8 |
| M5 potential 8³ | 13,840 | 0.05321 | 0.03631 | ~1.9e-8 |
| M4 free U-FNO bottleneck | 13,746 | 0.03097 | 0.01731 | 0.4023 |
| W5 DeepONet | 13,674 | **0.02662** | **0.01697** | 0.1091 |
| W5 Geometry-MLP | 13,482 | 0.02908 | 0.01981 | 0.06293 |

**Negative result:** at 100 steps, the scalar-potential variants have **substantially worse prediction accuracy** despite a nearly perfect symmetry diagnostic. Structural validity is not a substitute for strong teacher supervision or a sufficiently flexible quadrature model.

### Held-out ellipsoid mean across three seeds (400-step maximum)

| Model | raw r MAE ↓ | native J MAE ↓ | max asymmetry ↓ | CPU cached J median* ↓ |
|---|---:|---:|---:|---:|
| M5 potential 4³ | 0.03337 | 0.02779 | ~2.4e-9 | 0.149 ms |
| M5 potential 6³ | 0.02267 | 0.01810 | ~1.6e-9 | 0.226 ms |
| M5 potential 8³ | 0.02064 | 0.02462 | ~1.0e-8 | 0.366 ms |
| M4 free U-FNO bottleneck | 0.01989 | 0.01680 | 0.348 | 1.288 ms |
| W5 DeepONet | **0.01562** | **0.01530** | 0.0979 | 1.111 ms |
| W5 Geometry-MLP | 0.02463 | 0.02087 | 0.0727 | 0.787 ms |

*CPU timings: 7 repetitions × three seeds, median of seed-wise median, PyTorch CPU, one thread, no GPU. Cached J deliberately excludes geometry encoding. For the 6³ potential, **CPU cached J is faster**, because it uses an explicit analytical derivative, but full cold inference is slower than the small W5 geometry descriptor models. **This is not a comparison against native Faster/Cherchi runtime** and is not a full solve acceleration claim. Peak CUDA VRAM was not measured. Small variations in sub-millisecond runtimes are hardware-dependent.

The potential 6³ chose validation steps `[400,310,330]`, versus free U-FNO `[190,240,110]` and DeepONet `[200,150,230]`; some potential seeds remain training-limited. Mean float32 minimum eigenvalue of corrected potential Jq was approximately `-1e-7` (roundoff), whereas in double-precision unit tests the Hessian is PSD within `1e-9`. The free head displayed substantive negative eigenvalues.

### 400-step value-only ablation (no Jacobian labels in training)

| Model | raw r MAE ↓ | native J MAE ↓ | max asymmetry ↓ |
|---|---:|---:|---:|
| Potential 6³ value-only | 0.03571 | 0.03814 | ~1.7e-8 |
| Potential 6³ derivative-enhanced | 0.02267 | 0.01810 | ~1.6e-9 |
| Free U-FNO value-only | **0.01792** | 0.02032 | 0.4141 |
| Free U-FNO derivative-enhanced | 0.01989 | **0.01680** | 0.348 |

The integrability/PSD architecture persists without any Jacobian labels, but derivative supervision is still required for competitive accuracy under this limited budget.

## Evidence and next work

- `m5_summary.json` gives machine-readable aggregates, source/hashes and all limitations.
- Full per-seed training histories, error metrics, timings and selected validation steps are archived as `m5_three_seed_cpu.json.gz`, `m5_long_400step_cpu.json.gz`, `m5_value_only_400step_cpu.json.gz`. Decompress with `gzip -dk <file>.json.gz`. The standalone ZIP also contains raw JSON.
- Full remote W6 checkout CI has **not** been executed. The local M4 model+experiment match the committed Git blob SHAs; local `analytic_cut.py` is an equivalent shorter reconstruction whose three full-seed dataset hashes match M3/M4 exactly, but its bytes differ from GitHub. The **exact remote file set still needs independent checkout CI**.
- No trusted real-mesh r/J, true heavy-native Boolean optimization, H9/Heart, Teapot, higher-resolution 64³/256³, GPU time/VRAM, or independent manufacturing approval were performed. Do not fabricate those results.

Next milestone: integrate W0's semantic validator and a new W2 fully sealed native teacher format when published. Then compare learned positive-volume quadrature, finer/adaptive quadrature and integrable-potential alternatives under strict geometry-family holds, validation-only hyperparameter selection, error bars and **true objective/step acceptance**. Retain free W6 and W5 baselines rather than claim the potential is already superior.
