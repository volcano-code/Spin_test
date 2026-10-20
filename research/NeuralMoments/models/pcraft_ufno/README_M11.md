# W6 M11 — source-bound moment-anchor decision calibration (analytic P0 only)

**Repository:** `volcano-code/Spin_test`  
**Only writable branch:** `research/neuralmoments-w6-pcraft-20261019`  
**Only changed subtree:** `research/NeuralMoments/models/pcraft_ufno/`  
**Parent / frozen W6 prior milestone:** `8063babb40dec18740e66261ee112636764b9f33` (M10)  
**Frozen Spin/quadric source:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**External W5 reference:** source-matched 4-channel `W5VoxelDeepONet`; model blobs matched to their GitHub published tree, NOT a write to W5.

## Purpose and scientific honesty

M10 found that incorrect **current moments**, even with relatively accurate native 10×10 Jacobians, can invert the 1D objective gradient and cause bad optimization decisions. M11 studies amortizing **one or two independently purchased analytic moments per geometry** across several novel cuts. It is not an improvement to the M7 material predictor itself, nor proof of a true Cherchi/Faster computational saving.

Only boxes and spheres are used in model fitting/validation. Only previously held-out ellipsoid families appear in the decision study. The independent oracle is the *published* `analytic_cut.vertical_cut_truth`, with W0's native `c=(CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY)`, ordinary ten raw moments, positive signed projective convention and `J=dr/dc_native`.

**W2:** at the start, W2 M15 branch `824d7d566397508d953b04c465442e9a22ee3798` still has **0 admitted training samples, 0 new native teacher calls**. Excluded archived H8f/H8e observations are never ingested. `AnalyticAnchorLedger.obtain_r` accepts only the hard-coded analytic oracle, denies native-like source strings and cannot grant physical/source/derivative certification.

## Implementation

- `m11_anchor_cache.py`: source-bound per-geometry ledger with a **full model state SHA-256** and raw four-channel D bytes SHA-256 plus analytical geometry identity. A single `encode_geometry(D)` occurs when the cache is created. Changed model weights, changed geometry identity or D input are rejected. Repeating the exact same `h` returns the same frozen analytic anchor record **without a second teacher call**.
- `0` anchors: no corrections and no oracle teacher selection cost. `1` anchor at `h=0`: add its frozen exact `r(h0)−r_model(h0)` to the residual used by a Gauss–Newton *step*, not to the released material moment. `2` anchors at `h=−0.3,+0.3`: interpolate their residuals inside the bracket and use the nearest residual outside (no unbounded extrapolation). Each remains anchored to the same model and geometry.
- Only *decision* `r_for_step` is corrected; original M7 nonnegative atomic `r` and **the network's Jc** are unchanged. Before using a corrected 10-vector, apply necessary positive-moment conditions in the fixed coordinate box `[-1,1]^3`. If the correction fails, revert to raw model moment for the diagnostic step. **Passing this gate is not material existence, positive-volume CAD, or W0/W2 certification**, especially for W5's unconstrained raw head.
- `m11_experiment.py`: train 13,448-DOF W6 M7 baseline, 13,448-DOF directional variant, and 13,939-DOF W5 DeepONet; use identical raw four-channel center-cell geometry, fitting/validation family splits, 100-step Adam/batch schedule, validation-only checkpoint selection. The existing frozen M10 training and native 1D regularized/clipped GN protocol are preserved.
- `m11_merge.py`: recompute both target-direction summaries **from the underlying per-case JSON**, reject changed seeds, data digests, model parameters, batch hashes, unpaired target controls, false W2 counts, misreported oracle budgets; report exploratory 2,000-draw **hierarchical seed/geometry** paired bootstrap bounds. Historical positive reports were executed before the `goal_offset` field was added; the CLI's documented `+0.12` default is explicitly annotated, not silently relabeled.

## Actual experimental protocol

Python 3.13.5, PyTorch 2.10.0+cpu, NumPy 2.3.5, `OMP_NUM_THREADS=1`, no GPU. Seeds: **67, 71, 73, 97, 101, 103**. Each seed: 20 unique training boxes + 20 training spheres, two controls each (64 fitting labels / 16 geometry-held-out validation labels); 20 previously unseen ellipsoids, **8 new random target controls each**. Positive and negative tests share the **exact** trained model weights, geometry IDs and 8 target controls, only changing the goal direction between `h+0.12` and `h−0.12`.

**Per model and goal direction:** 120 unique test geometries × 8 controls = **960 decisions**. For K=0/1/2, additional analytical support queries for **selection** are 0/120/240, amortized **0 / 0.125 / 0.25 queries per candidate**. The "oracle-current" counterfactual uses **one additional oracle at every target**, 960 extra and 1.0 per candidate. The analytic truth values used to construct the common *goal*, to measure the initial/after losses, and for diagnostic regret are **validation-only** and excluded from these *selection* query counts; they are not zero-cost in a hypothetical native pipeline. All models use identical oracle policy budgets.

### Six-seed outcome: 1D vertical analytic P0, candidate accepted if true objective strictly decreases

| Model | `h + 0.12` K=0 | K=1 | K=2 | `h - 0.12` K=0 | K=1 | K=2 |
|---|---:|---:|---:|---:|---:|---:|
| W6 M7 base | **79.79%** | **92.60%** | **100.00%** | **99.27%** | **97.92%** | **99.38%** |
| W6 directional | 80.42% | 92.40% | 100.00% | 99.27% | 98.02% | 99.38% |
| W5 voxel DeepONet | 85.42% | 92.71% | 95.21% | 71.15% | 90.52% | 96.25% |

The current-r oracle **counterfactual** accepts 100% of the cases in this restricted one-dimensional setup, but it costs a real *per-target* current-r query. Crucially, one anchor made W6's **reverse-direction** results *worse*, from 99.27% to 97.92% despite consuming extra oracle observations. Do not claim unconditional improvement or an algorithm guaranteed to achieve 100% success on other c, target, CAD or solver states.

The W6 M7 base `h+0.12` paired K=2 improvement over K=0 is **+20.21 percentage points**, with an **exploratory** grouped-bootstrap interval of approximately **+15.4 to +25.0 points**. The reverse-direction K=1 difference is **−1.35 points**, exploratory interval approximately **−2.71 to −0.42 points**. These intervals are not a pre-registered external validation; no universal convergence guarantee is claimed.

**Safety/representation limitation:** on W6 M7, about **18.44%** of one-anchor correction attempts and **14.38%** of two-anchor correction attempts violate tested necessary moment conditions and are **rejected**, falling back to the unmodified model. Thus the bias-adjusted vector is not a realizable material surrogate. Any use of corrected `r_for_step` is exclusively an optimization-decision study; the original M7 raw bounded atomic output and J remain unchanged. This guard does not certify material geometry and the W5 base unconstrained head has separate unproven physicality.

## Reproduction

From a checkout of W6 M11 SHA, where all frozen predecessor source files are available:

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m unittest \
  research.NeuralMoments.models.pcraft_ufno.test_m4 \
  research.NeuralMoments.models.pcraft_ufno.test_m5 \
  research.NeuralMoments.models.pcraft_ufno.test_m6 \
  research.NeuralMoments.models.pcraft_ufno.test_m7 \
  research.NeuralMoments.models.pcraft_ufno.test_m8 \
  research.NeuralMoments.models.pcraft_ufno.test_m9 \
  research.NeuralMoments.models.pcraft_ufno.test_m10 \
  research.NeuralMoments.models.pcraft_ufno.test_m11 \
  research.NeuralMoments.models.pcraft_ufno.test_m11_merge -v

python -m research.NeuralMoments.models.pcraft_ufno.m11_experiment \
  --seeds 67,71,73,97,101,103 --steps 100 --target-controls 8 \
  --goal-offset 0.12 --output /tmp/w6_m11_positive.json
python -m research.NeuralMoments.models.pcraft_ufno.m11_experiment \
  --seeds 67,71,73,97,101,103 --steps 100 --target-controls 8 \
  --goal-offset=-0.12 --output /tmp/w6_m11_negative.json
```

The committed `m11_summary.json` and `m11_per_seed_receipts.json` contain measured numeric evidence, frozen training/dataset SHA-256, model-source state hashes and per-geometry oracle accounting. The standalone ZIP distributed alongside this commit includes the full unabridged per-case positive/negative JSON and its checksums. We deliberately do **not** edit earlier failure logs or commit huge raw experiments as unaudited prose. GitHub Actions is NOT claimed to have run unless independently confirmed.

**Local executed result:** M4–M10 previously committed tests **158/158 passed**, M11 new tests **23/23 passed**, hostile M11 merge tests **8/8 passed**: combined **189/189 passed**. `compileall` on all new Python files passed. Source mirror was restored from milestone artifacts and original predecessor Git blob SHA1s independently matched with the W6 remote tree; it is **not** a full remote GitHub Actions checkout. No GPU, real W2 labels, native Cherchi re-evaluation, full 10D quadric optimization, closed CAD proof, or actual Faster end-to-end speedup measured.

## Next scientific gate

M12: establish a validation-only **value-of-information** policy that chooses whether paying 1/2 native moment queries is worth it, and separately compare a truly physically-realizable atom-weight fit against decision-only bias calibration. Test mixed target directions and unseen surface/topology classes before endorsing either method. Production requires independent W0/W2 source/geometry/F/D/derivative seals and a real Cherchi cost model.
