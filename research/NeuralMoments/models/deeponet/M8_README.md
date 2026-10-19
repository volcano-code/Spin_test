# W5 M8 — Same four-channel voxel input for DeepONet, MLP, P-CRAFT U-FNO and convex potential

**Development branch ONLY:** `research/neuralmoments-w5-deeponet-20261019` of `volcano-code/Spin_test`. **Parent SHA:** `cbc460dbb4ecc3fce8a0d3797f1e0593ca467ee4`. Frozen shared source `0bcc187b3005478baa586a6d6f450e73811ca342`. This milestone adds only W5-owned files `research/NeuralMoments/models/deeponet/m8_*`, this `M8_README.md`, and `tests/python/test_w5_m8_voxel_parity.py`. No merges or writes to W0/W2/W6/main or original `volcano-code/test`.

## Dependency check, 2026-10-19

- **W0 M8** `76c7240bb0f4823440d7b37785ef675a4fdc5a04`: independently reproduced the ten exact numeric moments for **25 archived genuine native H8e evaluations**, with no complete 81-point/smooth-neighborhood/terminal-Newton certification; original upstream native GitHub Actions run **failed**.
- **W2 M8** `bd87b26a926e260a4f3dd4df6b96ca561a49f6eb`: historical 25 H8e archived material observations reverified, **0 new native evaluations, 0 training-admissible samples**, `teacher_manifest.json` blob `fffb0d9286935bedaae3380e4171d7a4a9501442` (v2-pre-W0). The original numeric `r` data are genuinely historical Cherchi, NOT qualified full ambient `J` and NOT multiple held-out CAD families. Their unqualified Jacobians are not used for M8 training. W2's 25-point upstream run remains `failure`; M8 must not rewrite that status.
- **W6 M6** `27d51678cf741233c7a2e6c54c78d9a4667bec00`: has further Gauss potential experiments but, crucially, reported a **negative-mass physicality counterexample** for larger smoothing. M8's matched 5-way comparison deliberately freezes two W6 M5 model sources by Git blob SHA (which remain unmodified); new W6 M6 Gauss variants and other not-yet-trained candidate families are **not** silently called M8 participants.

## What actually changed

1. `m8_voxel_models.py`: new W5 DeepONet/Geometry-MLP variants with a learnable four-channel **depthwise 3D spatial encoder**, position-weighted pooling and the original DeepONet/MLP heads. All receive `[B,4,8,8,8]` voxels, **not** the lossy 9D statistics used in W5/W6 M7. The geometry tensor is encoded **once**, projected into a cached latent, and all subsequent `c` queries use only the appropriate head. Both normalize positive native coefficient rays without identifying the negative ray and use a correctly differentiated `10×10` `Jc` (including the coefficient-normalization derivative). This is a NEW architecture, not reusing trained M4 W5 weights.
2. `m8_analytic_data.py`: independent double-precision analytic continuum mass/J calculation for W0 native `c=(-h_world,0,0,1,0,..)/sqrt(1+h_world²)` and `beta>=0`, using box polynomial antiderivatives or spherical disk integrals with affine ellipsoid transport. The ten raw moments are **undoubled**, but the native last three columns of `Jc` use W0's `B=diag(1,..,1,2,2,2)`. The 4 channels are sampled density, occupancy, **signed implicit-level proxy (NOT exact SDF)**, and boundary-proximity proxy, all determined exclusively by the **uncut** geometry. Analytic continuum teachers are NOT integrals over 8³ voxels and NOT native Cherchi labels.
3. `m8_fair_benchmark.py`: runs the actual two W5 voxel encoders alongside W6's source-pinned `LiteUFNOMoment(bottleneck)`, `LiteUFNOMoment(local_only)` and `ConvexPotentialMoment` 6³ (`hidden=32`, `smoothing=.04`) on the **same 4-channel input bytes**, native coefficients, exact analytic labels and train/validation/test geometry IDs. No external W6 files are committed, copied into production imports, edited or trained in W6. Separate W6 tree is loaded via M7's strict Git blob verifier into a private import namespace.
4. Matched equal *fit label* budget, minibatches and Adam settings, validation-only early stopping; held-out r/J/directional errors, necessary negative-mass symptom, corrected `Jq=Jc·B^-1` asymmetry, a one-dimensional **analytically re-evaluated** candidate step's true loss and acceptance, plus CPU encoding/cold/warm/J timings and cached-query cost curves. The 1D diagnostic is **not** full 10D Spin Newton, KKT, CAD or manufacturing certification.

**Source-pinned external W6 files:**

| W6 read-only model source | Exact Git blob SHA-1 |
|---|---|
| `pcraft_ufno/m4_lite_model.py` | `853ea92054e5895abe06d33092615a0be4b58772` |
| `pcraft_ufno/m5_potential.py` | `b5f976af0b2ef0621fd3f557ea93ae08a48ba99a` |

All five receive the **identical raw four-channel tensor**. This fixes **input access parity**. It does **not** imply matching encoder architecture, effective latent information, compute costs, convergence, hyperparameter optimizations or prior pretrained weights. Model capacity is within 5% including FFT complex parameter weights counted twice; counts are 13,939 (W5 DeepONet), 13,747 (W5 MLP), 13,746 (W6 U-FNO), 14,098 (W6 no-FFT) and 13,448 (W6 convex). Maximum/minimum ratio `1.04833`.

## Freshly executed protocol (not copied from W6 historical report)

```bash
export W5_M8_READONLY_W6_ROOT=/path/to/read-only/W6/exact-source-root
export W5_M7_READONLY_W6_ROOT="$W5_M8_READONLY_W6_ROOT"
PYTHONPATH=. python -m research.NeuralMoments.models.deeponet.m8_fair_benchmark \
  --w6-root "$W5_M8_READONLY_W6_ROOT" \
  --seeds 19,23,29 --steps 100 --per-family 20 --repeats 7 \
  --output research/NeuralMoments/models/deeponet/m8_matched_seed19_23_29_cpu.json

PYTHONPATH=. python -m pytest -q \
  tests/python/test_w5_deeponet_smoke.py \
  tests/python/test_w5_m2_contract_and_gate.py \
  tests/python/test_w5_m3_mesh_and_p0.py \
  tests/python/test_w5_m6_analytic_rollout.py \
  tests/python/test_w5_m6_model_adapter.py \
  tests/python/test_w5_m6_budget_audit.py \
  tests/python/test_w5_m7_cross_framework.py \
  tests/python/test_w5_m8_voxel_parity.py
# 89 passed, 40 subtests passed
```

Each seed has **40 different box/sphere geometries** with 2 native-cut queries = 80 analytic values; **32 training geometries / 64 fit queries**, **8 validation geometries / 16 validation queries**; **20 fully held-out ellipsoids / 40 test queries**. All 5 networks share seed, train/val/test bytes, Adam lr `.003`, identical deterministic 100×8 minibatch schedule, supervised loss `MSE(r)+0.5 MSE(Jc)`; validation checkpoints use `r_MAE+0.25 J_MAE` every 10 steps with patience 5. **Test is never consulted for checkpoint selection.** `m8_matched_seed19_23_29_cpu.json` contains per-seed dataset SHA256s, split counts, steps, losses, timing, decision outcomes, CPU training time and all aggregate sample SDs.

**Fresh held-out analytic P0 results, mean of seeds 19/23/29** (lower is better except acceptance):

| Model | r MAE ↓ | Jc MAE ↓ | independent true 1D step acceptance ↑ | CPU cold moment ms ↓ | CPU cached J ms ↓ |
|---|---:|---:|---:|---:|---:|
| W5 voxel DeepONet | 0.02298 | **0.01328** | 79.2% | 0.355 | 0.870 |
| W5 voxel Geometry-MLP | 0.02576 | 0.02044 | 67.5% | **0.333** | 0.790 |
| W6 P-CRAFT U-FNO | 0.01921 | 0.01624 | 72.5% | 0.833 | 0.806 |
| W6 local-only **without FFT** | **0.01878** | 0.01666 | 74.2% | 0.456 | 0.862 |
| W6 convex potential 6³ | 0.05059 | 0.02367 | **87.5%** | 1.007 | **0.209** |

The decision acceptance percentages come from **independent analytic 1D vertical cut objective checks** with trust radius 0.12, not real W2 native oracle acceptance. They do not mean full 10D optimization convergence. The no-FFT control is NOT an FNO; retaining it is essential for measuring the value of spectral mixing. The convex potential's higher acceptance despite worse `r` MAE highlights that predictive MAE and decisions need separate reporting, not an architecture dominance claim.

### Shape and physicality limitations

- All sampled cuboids/balls/ellipsoids are perfect analytic continuous bodies, not signed exact Boolean source meshes. Low-resolution sampled voxel inputs are imperfect geometric proxies by design. No true real-CAD generalization has been measured.
- A candidate `Jq=Jc·B^-1` might be asymmetric for free heads; for convex head symmetry is a mathematical model property, not a material certificate. Even positive semidefinite symmetric Hessian is not proof of a physical moment cone (W6 M6 provides counterexamples). Nonphysical negative predicted masses occur for some unconstrained arms.
- W6 W5 model weights were **newly initialized and trained in this local isolated M8 study**, not original P-CRAFT pretrained stress/PINO weights. Training uses only analytic P0 labels; **no W2 real-mesh `r_D/J_D` teacher labels** were admitted.
- CPU-only PyTorch, one thread, CUDA/GPU training seconds **zero**, GPU memory unavailable. A network-only latency is NOT a Faster/Cherchi solver speedup; amortization curves are additive performance estimates under fixed single-geometry repeated queries and no CAD IO.
- New W5 wrapper **improves access parity**, but architecture-specific encoders still reduce information in different ways. No full 10D Pareto/terminal solve, 3D printing or CAD geometry correctness is claimed.
- Tests M1–M3 and M6–M8 were rerun on a local mirror, including W5 M5 production source restored with *exact* Git blob `aa59005481f9e313670608932e038c4577c61ac2`. The earlier W5 M4 500-step specialty test was not rerun; no GitHub CI success is assumed without actual workflow evidence.

## Next safe milestone

When W2 publishes independently approved, **full original/F/D identity-bound and derivative-neighborhood-qualified** real Cherchi labels across genuinely distinct CAD families, first verify teacher accuracy and split/missing-derivative categories; then train **all** shortlisted models on a common native data contract. If only `r_D` is verified, moments-only supervised evaluation is possible after legitimate per-record admission but **never** use archived H8e `J_D` as smooth truth without independent proof. Compare true native calls, assembly costs, solver step acceptance and terminal full-F/D physical validity separately. Until then preserve W2's failed historical CI as failed and do not claim speedups.
