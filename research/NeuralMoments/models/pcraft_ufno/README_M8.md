# W6 M8 — nonnegative-atomic 0/1/2-query adaptation (analytic P0 only)

**Repository:** `volcano-code/Spin_test`. **Exclusive write branch:** `research/neuralmoments-w6-pcraft-20261019`. **Only new files:** `research/NeuralMoments/models/pcraft_ufno/m8_*`, `test_m8.py`, and this document. **Read-only predecessor:** M7 commit `9d1758ea1ef527577b835f2b6bcfc5f0439d933d`; frozen source `0bcc187b3005478baa586a6d6f450e73811ca342`.

## The hypothesis and exact scope

M7 guarantees that every prediction is the ten undoubled moments of a **sampled, bounded, nonnegative atomic measure**. An ordinary additive ten-output residual head can break mass positivity, covariance inequalities, and the M7 tangent derivative structure. M8 therefore fits **geometry-conditioned atom weights** without altering the trained M7 neural network:

- Given a single frozen geometry input `D=[rho,occupancy,SDF,inner_boundary]`, compute the M7 geometry encoding **once**: `z=encode_geometry(D)`.
- Independently sample the SAME supplied `D` at the known M7 Gauss nodes, defining capacity `cap_k = volume_weight_k * sampled_density_k * sampled_occupancy_k`. Require `0 <= z_k <= cap_k` (up to input float32 roundoff); reject inconsistencies.
- For K in `{0,1,2}`, take K **independent analytic P0** `(c,r)` support queries. With K=0, `z'=z` without fitting. With K>0, solve a small regularized least-squares correction in nodal weight space, clip to `[0,cap]`, and accept backtracking steps only when the observed **support** normalized squared error decreases. This does **not** guarantee independent test-error improvement.
- Reuse the adapted cached `z'` at arbitrarily many novel `c` without rerunning the geometry encoder. `r(c)=sum_k z'_k sigmoid(((Bc)·m_k)/(temperature ||c||)) m_k` with native `B=diag(1x7,2x3)` and undoubled monomial `m=(1,x,y,z,xx,yy,zz,yz,xz,xy)`. The exact model Jacobian is computed by `m7_realizable.RealizableUFNOMoment.jacobian(z',c)`.

Every output remains an atomic nonnegative material moment on the **sampled** grid, with its fixed `D` capacity and `positive-c` projective invariance. The *model* native `10x9` tangent derivative and projected q Gram still satisfy their mathematical consistency tests. **Ambient `Jc B^-1` is not generally symmetric for normalized-temperature M7, and no real Cherchi derivative is certified.** A legitimate fixed F must still be added separately exactly once using the already-published W0 accounting contract. A hard all-empty/all-full classifier returns strict zero/its cached atomic full amount, not a proof of the exact CAD full material mass.

### Explicit real-teacher admission barrier

W0 observed branch `d0a1b136b61b7c809311278c6c5051b62469d29a`; W2 observed branch `33a2ce05e005227bf69f260efa992b7553e91112`. At audit, W2 was `M10_READONLY_81_ARCHIVE_GATE_PASSED_DERIVATIVE_TRAINING_BLOCKED`, **0 admitted training samples**, and **81 excluded historical H8f point candidates**. This code always raises `NativeTeacherNotReady` for any `source` other than `ANALYTIC_P0`, including forged `NATIVE_VERIFIED`; it **does not grant native training admission**. The `source='ANALYTIC_P0'` string is a local test convention, not an authenticated provenance certificate: a caller must not relabel native/archived records to bypass the exclusion. Production ingestion will require external independent W0/W2 material, geometry, source, and smooth derivative-neighborhood seals. W2 archive records, H8 point60, open Teapot and unqualified Newton outcomes were never used as labels.

## Reproduction and executed local evidence

Python 3.13.5, PyTorch 2.10.0+cpu, NumPy 2.3.5, single CPU thread, deterministic algorithms; CUDA **not available**. Commands from repository root:

```bash
python -m unittest \
 research.NeuralMoments.models.pcraft_ufno.test_m4 \
 research.NeuralMoments.models.pcraft_ufno.test_m5 \
 research.NeuralMoments.models.pcraft_ufno.test_m6 \
 research.NeuralMoments.models.pcraft_ufno.test_m7 \
 research.NeuralMoments.models.pcraft_ufno.test_m8 -v

python -m research.NeuralMoments.models.pcraft_ufno.m8_experiment \
 --seeds 19,23,29 --steps 400 --per-family 20 \
 --ridge .0001 --iterations 5 --output /tmp/m8_three_seed_cpu.json
python -m research.NeuralMoments.models.pcraft_ufno.m8_experiment \
 --seeds 31,37,41 --steps 400 --per-family 20 \
 --ridge .0001 --iterations 5 --output /tmp/m8_confirmatory_cpu.json
python -m research.NeuralMoments.models.pcraft_ufno.m8_box_smoke \
 --output /tmp/m8_box_analytic_cpu.json
```

**112/112 local unit tests passed**, 25 M8 + 87 unmodified M4–M7, Python compileall passes. Logs: `m8_all_tests_cpu.log`. Original prior W6 working modules were recovered into a local mirror from archived copies, with `analytic_cut.py`, `m4_lite_model.py`, `m5_potential.py`, `m6_gauss_potential.py`, `m7_realizable.py` and related original files Git-blob validated against the actual predecessor tree. Not a remote GitHub CI result or production build.

Frozen same M3 full P0 training tensor SHA256 for seeds 19/23/29:

- seed 19: `7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087`
- seed 23: `d36d707cbf7ecdd0089f66fea3f8784a200830f09a2e0b5a60790ce6028562e7`
- seed 29: `25eece482d68d864064bfcc7785226785afc41307f56978f2f027ba4ac838394`

40 train geometries (20 boxes + 20 spheres, two controls each = 80 labels); 8 **whole** geometries (16 labels) are reserved for validation/early stopping, leaving 64 fitting labels. Each seed uses 20 previously unseen ellipsoids. For **each** such geometry, two separate analytic supports and eight *different* analytic evaluation controls are generated from disjoint fixed RNG streams; none of the eight target `r/J` values enters the adapter fit. Model: M7 temperature 0.12, 13,448 real trainable parameters (all frozen at adaptation), Adam lr 0.003, validation `r_MAE+0.25J_MAE` every 10 steps, patience 5, max 400 steps. Support queries count 0/1/2 per geometry; no real native/Cherchi calls.

## Six-seed results: meaningful negative finding, not an accuracy win

Means over 19/23/29 and independently evaluated 31/37/41 (6 seeds); each model sees the SAME held-out analytic controls for its 0/1/2 support arms:

| Analytic ellipsoid holdout metric | K=0 | K=1 | K=2 |
|---|---:|---:|---:|
| `r_MAE` ↓ | 0.02560754 | **0.02559759** | 0.02559764 |
| `J_MAE` ↓ | 0.01005395 | 0.01005339 | **0.01005337** |
| material-moment necessary conditions pass | **100%** | **100%** | **100%** |
| mean per-seed geometries with at least one support mass over sampled capacity (out of 20) | n/a | 8.17 | 13.00 |

**Improvement on these complex held-out ellipsoids is negligible; K=2 is not even strictly better than K=1 for unseen `r`.** Analytic continuum volume is often **larger** than the capacity inferred from the coarse 8^3 occupancy samples, so the physical bounds prevent arbitrary correction. M8 does not relax this constraint or silently claim to fit an infeasible oracle exactly. All results are in `m8_three_seed_cpu.json.gz`, `m8_confirmatory_cpu.json.gz`, and six-seed `m8_summary.json`.

To check that the solver actually works on a representable case, a **separate, deliberately untrained** whole `[-1,1]^3` analytic box (where capacity is sufficient) uses supports at `h=-0.4,0.22` and five independent target cuts. Its MAEs are `K=0: 0.46741074`, `K=1: 0.03278410`, `K=2: 0.05113632`. All remain bounded atomic moments; **K=2 can generalize worse than K=1.** This illustration is not a trained accuracy benchmark and is kept separate in `m8_box_analytic_cpu.json`.

## Risks and following gate

1. A locally supplied `D` and `z` may be mismatched while both satisfy capacity; the adapter checks shape/range, not CAD identity. It must only be called with a *same-call frozen geometry cache*, as tested. Native application requires stronger cryptographic input/cached-weight binding.
2. `ANALYTIC_P0` is never a signed teacher proof. The M7 model's `safe_predict` returns `admitted_for_real_optimizer=False`; the adapter forwards this safeguard. Quantized atomic measures are not exact volumetric solid geometry, CAD topology, fabrication/wall proof or W0 smooth native derivative truth.
3. No uniform percentage accuracy guarantee, no speedup vs native Faster or Cherchi, no GPU/VRAM evidence, no solved Newton terminal and no large CAD training. Support observations may be outside discretized capacity; improvement on supports does not establish improvement on held-out controls.
4. Next: improve sampling-capacity fidelity (anti-aliasing, conservative occupancy integration, resolution study) **without inventing material**, then obtain W2 independently accepted native per-geometry records, signed geometry identities and legal derivative categories before a real solver A/B trial.
