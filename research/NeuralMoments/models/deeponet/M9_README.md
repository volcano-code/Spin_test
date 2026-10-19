# W5 M9 — Physical-moment gate and Gauss P-CRAFT under four-channel parity

**Repository:** `volcano-code/Spin_test`; **sole write ref:** `research/neuralmoments-w5-deeponet-20261019`. Parent: `84847874d11598c1a6e20406940a6654bd996943`. Only new files under W5's `research/NeuralMoments/models/deeponet/` and `tests/python/test_w5_m9_gauss_physicality.py`. No W0/W2/W6/main changes or any original failed CI mutation.

## What changed (REAL code, not just proposal)

1. `m9_readonly_w6.py` imports W6 M6 **original** `m6_gauss_potential.py` and `m6_moment_guard.py` from a caller-provided W6 read-only checkout after Git blob SHA-1 checks, while M7's loader validates original `m4_lite_model.py` and `m5_potential.py`. W6 M6 source HEAD `27d51678cf741233c7a2e6c54c78d9a4667bec00`, required new blobs `85d0ead6ee0dec9fc3212750e849310230d7878a`, `9a9f0ae8cd1066c7e401529541387052faf264af`. Source is not committed to W5.
2. `m9_physical_benchmark.py` trains seven candidates on the **exact same** W5 M8 four-channel analytic voxel data: W5 DeepONet, W5 Geometry-MLP, W6 U-FNO, W6 no-FFT local ablation, W6 midpoint convex 6³, W6 Gauss 6³ epsilon .04 and Gauss 6³ epsilon .25. Same train/validation/test geometry IDs, native c, r, full analytic Jc, batch schedule and step cap across models. Learned encoder representations are architectural choices, not identical heads. All seven have 13,448–14,098 real parameters, ratio 1.0483.
3. `m9_physical_benchmark.physically_guarded_decisions()` enforces **necessary**, not sufficient, nonnegative material moments for known support `[-1,1]^3` at both original and proposed c; if either fails, it does not advance geometry. Even if it passes, independent analytic continuum truth must show a strict decrease in the one-dimensional target residual before acceptance. This is a safe *research-only* gate, not native Faster/Spin Newton proof.
4. `m9_archive_gate.py` reads original W2 M8 **manifest bytes** from a read-only W2 mirror with Git blob `b1a126d94eb5bfb0fc57ff59cd5250ce0a3b3171`. W2 HEAD `bd87b26a926e260a4f3dd4df6b96ca561a49f6eb`: 25 **historical** Cherchi H8e material packets were independently offline recomputed by W0/W2 (not by W5); original workflow `39121571756` remains **failure**, 8 raw topology-hash drifts, **zero** certified smooth J labels, zero admitted training samples and zero **new** native evaluations. The archived 25 ZIP contents are **not** read in this W5 step. A hash match only authenticates the published manifest metadata, NOT its CAD geometry or native derivative correctness.
5. `m9_merge_reports.py` combines individually executed seed files into a full report, checking identical protocols and unique seed IDs and recomputing aggregate means/SD from raw per-seed results. All per-seed training, decisions, latency and sample identities remain present. No merging with W6 historic metrics. Tests reject tampered external W6 source and W2 manifest, count all sample rejections, check Gauss/midpoint correspondence, check Jq symmetry/PSD **only under the analytic smooth continuum hypothesis**, observe negative empty-cut mass counterexamples and guard behavior.

## What was actually executed

Local CPython 3.13.5, PyTorch 2.10+cpu, NumPy 2.3.5, pytest 9.0.2; one CPU thread, no CUDA. Seven separate models × seeds `[19,23,29]`, 100 Adam steps max, batch 8, lr .003, loss MSE(r)+.5 MSE(Jc), validation-only checkpoint at 10-step intervals, patience 5. 20 independent box + 20 sphere training-family geometries per seed, 20 held-out ellipsoids per seed, 2 distinct native c queries per geometry, separate 4+4 validation geometry IDs, **no inter-split geometry-ID or family leakage**. Training was executed in three **separate seed processes** with identical instructions; the merge script recomputes statistics from exact run files (SHA256 recorded).

```bash
export PYTHONPATH=. 
export W5_M9_READONLY_W6_ROOT=/path/to/read-only-W6-checkout
export W5_M9_READONLY_W2_MANIFEST=/path/to/read-only-W2/teacher_manifest.json
python -m pytest -q tests/python/test_w5_*  # use actual filenames or glob
for seed in 19 23 29; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m research.NeuralMoments.models.deeponet.m9_physical_benchmark \
    --w6-root "$W5_M9_READONLY_W6_ROOT" \
    --w2-manifest "$W5_M9_READONLY_W2_MANIFEST" \
    --seeds "$seed" --steps 100 --per-family 20 --repeats 5 \
    --output "research/NeuralMoments/models/deeponet/m9_seed${seed}.json"
done
python -m research.NeuralMoments.models.deeponet.m9_merge_reports \
    research/NeuralMoments/models/deeponet/m9_seed19.json \
    research/NeuralMoments/models/deeponet/m9_seed23.json \
    research/NeuralMoments/models/deeponet/m9_seed29.json \
    --output research/NeuralMoments/models/deeponet/m9_seed19_23_29_full.json
```

### New seven-framework four-channel analytic P0 result (mean across 3 fresh training seeds)

| Model | r MAE ↓ | Jc MAE ↓ | necessary moment pass ↑ | objective-rechecked candidate accepted *after physical screening* ↑ |
|---|---:|---:|---:|---:|
| W5 voxel DeepONet | 0.02298 | **0.01328** | 34.2% | 34.2% |
| W5 voxel Geometry-MLP | 0.02576 | 0.02044 | 44.2% | 40.8% |
| W6 U-FNO | 0.01921 | 0.01624 | 46.7% | 42.5% |
| W6 local-only (no FFT) | **0.01878** | 0.01666 | 48.3% | 45.0% |
| W6 convex midpoint 6³ / epsilon .04 | 0.05059 | 0.02367 | **99.2%** | **81.7%** |
| W6 Gauss 6³ / epsilon .04 | 0.05216 | 0.03160 | 98.3% | 64.2% |
| W6 Gauss 6³ / epsilon .25 | 0.04973 | 0.03805 | 43.3% | 35.8% |

The P0 held-out acceptance numbers in M8 were without the physical-moment veto. Example: Gauss epsilon .25 had 99.2% **ungated** one-step analytical objective decrease, but only 35.8% accepted **after mandatory necessary-moment screening** (a revealing adverse result). The learned smooth convex-potential Jq is symmetric/PSD by construction in smooth continuum at nonzero c, yet smoothed masses at all-negative constant cuts can be **negative**. The Gauss epsilon .25 model averaged about `-0.01928` mass for a geometrically empty region. No nonnegative material or exact CAD mass realization is implied by Hessian structure alone.

### Repeated geometry queries: *actually measured*, not estimated additive costs

For **8 sequential (r and Jc) queries** with one geometry encoding, mean across three seed-run medians: W5 DeepONet ~10.58 ms, W5 Geometry-MLP ~9.49 ms, W6 U-FNO ~10.46 ms, W6 no-FFT local ~8.83 ms, W6 midpoint convex ~4.01 ms, W6 Gauss .04 ~4.08 ms and Gauss .25 ~4.30 ms. This is CPU cost for the tiny models and includes encoding once, **not** real Cherchi cost or Faster solver wall time; timings are sensitive to host/CPU and the trust check itself is not included in these path microbenchmarks. Report also measures query counts 1/2/4/8/16 with and without recoding geometry. Measured results are stored in the full JSON.

## Limitations / explicit failures

- These new labels are analytically integrated **ideal** box/sphere/ellipsoid cuts, whereas the model input is their **8³ sampled voxel approximation**. Training labels are not W2 real CAD. W2's 25 genuine archived r records were not used for training; zero admissible J labels; original native workflow remains FAILURE. No 81-point full stencil or neighborhood cert, no real Newton terminal convergence.
- GAUSS smoothing .25 is **exploratory**, pre-chosen after W6 M6 past held-out tuning. The new M9 seeds 19/23/29 are also reused from M8, so M9 is a controlled extension, NOT fresh hyperparameter-blind confirmation of better generalization.
- Physical cone checks are necessary only for **known** support; passing cannot certify true CAD geometry, positivity of every point density, proper Boolean F/D, correct derivatives, manufacturing or printability. An analytic-only 1D height decision may not generalize to native full 10D numerical optimization.
- CPU inference/gradient timing is no proof of speedup versus Cherchi. No GPU hours/VRAM measured, no C++ or native Cherchi evaluation, no actual new H8/Faster runs. Historical W0/W2 25-point audit is read-only metadata here.
- All existing historical failures and evidence are preserved; zero cross-window modifications. No GitHub Actions CI status is claimed until remotely verified.

## Next (M10)

When W2 publishes new independent native same-call `r_D,J_D` with original/F/D geometry hashes, valid smooth-neighborhood/tangent mode, density/frame and frozen splits, audit each per-label SHA and retain safety-gated decisions. Separately examine models with physically admissible quadrature moments (hard clipped known-empty/full sign gates, moment-cone projection only with derivative contract, or alternative integrable positive-measure potential) and full solve-level amortization. Do not overfit the existing analytic ellipsoid family.
