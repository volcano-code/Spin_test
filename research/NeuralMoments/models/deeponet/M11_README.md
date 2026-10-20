# W5 M11 — cone-valued, *piecewise* integrable homogeneous moment surrogate

**Only GitHub writable ref:** `volcano-code/Spin_test`, branch `research/neuralmoments-w5-deeponet-20261019`; parent `b753ceee68163f40fb939cb4f0ec53afcfdfcb87`. Changes only under `research/NeuralMoments/models/deeponet/` and independent `tests/python/test_w5_m11_*.py`. No main, W0, W2, W6, original failed native CI or real CAD changes. Frozen native source `0bcc187b3005478baa586a6d6f450e73811ca342`.

## New real code

1. `m11_cone_integrable.py`: W5's proposed `ConeIntegrableMoment` wraps the **unaltered, Git blob-pinned** W6 M6 `GaussPotentialMoment` geometry-weight encoder (same 13,448 trainable real parameters as W6 Gauss/M10 positive quadrature). Computes raw ten moments and closed-form **native** 10×10 Jacobian with a cached geometry representation. All network training still uses 4-channel 8³ voxels. Tensor math supports end-to-end gradient training of both r and J without a CAD Boolean call.
2. `m11_experiment.py`: actual new CPU training/replay for DeepONet, M10 positive quadrature epsilon .12, W6 convex Gauss epsilon .04, and two new M11 blends lambda=.25/.75, each from the same source-pinned 4-channel voxel arrays, W0-native c and analytic independent r/J, validation split and minibatch schedule. All are within 3.65% parameter range. Geometry families: box/sphere train, independent ellipsoid test. Entire geometry IDs, not c-query rows, are held out for validation. No previously seen M10 seed is reused in M11: **new seeds 41,43,47**. Exactly 100 Adam-step cap, batch 8, lr=.003, loss `MSE(r)+.5*MSE(Jc)`, validation-only best checkpoint and patience five.
3. `m11_merge.py`: verifies source protocol, parameter counts, unique seeds, unique train/test dataset hashes, required ellipsoid holdout, W2 admission=0 and no new native runs; recomputes mean and sample SD from original per-seed records. Archives source SHA256 for all raw runs. The three full per-seed JSONs and aggregated full JSON are committed; historical W6/M10 metrics are not secretly substituted.
4. `test_w5_m11_cone_integrable.py`, `test_w5_m11_experiment.py`, `test_w5_m11_merge.py`: independent autograd gradient/Hessian checks, PSD, radial and positive scale invariance, negative/empty sign, necessary raw-moment inequalities, nondifferentiable node boundaries, Gauss source pin, gradient backprop, family and budget parity, historical teacher exclusion and adversarial report corruption.

## Why this can have BOTH a moment cone and an integrable Jacobian, with restrictions

Let W0 native coefficients `c=(a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy)` map to polynomial q via `q=Bc`, `Bdiag=(1×7,2×3)`. For W6 positive Gauss weights w_k and undoubled physical monomials m_k(x), define t_k=`max(q·m_k,0)`, W=`sum(w_k)`, S=`sum(w_k t_k²)`. The new *scalar* potential is

```
Phi(q) = (1-lambda) sum_k w_k t_k + lambda sqrt(W*S)
0 < lambda <= 1
```

On OPEN fixed-nodal-sign strata with S>0 and no zero-margin nodes, its gradient in q is

```
r_D = dPhi/dq = sum_k alpha_k m_k
alpha_k = (1-lambda) w_k 1[a_k>0] + lambda sqrt(W) w_k t_k/sqrt(S) >= 0
Jc = Hq * B
Hq = lambda sqrt(W) [ (sum_{active} w_k m_k m_k^T)/sqrt(S)
                      - (u u^T)/S^(3/2) ],  u = sum_k w_k t_k m_k.
```

`Phi` is convex (a positive combination of convex hinge functions and the nondecreasing weighted Euclidean norm of their positive parts) and positively degree-one homogeneous. Consequently **on these strata only**, `Jq=Jc B^-1` is symmetric positive-semidefinite (float-roundoff allowed), `Jc c=0`, and `r(tc)=r(c)` for t>0. Each r is the ten raw moments of a nonnegative **discrete** measure at the W6 Gauss nodes, so necessary known-bounding-box moment conditions hold. Strict all-negative cuts return zero mass and zero J. **Do not negate c as a projective identification.**

### Important adverse findings, NOT a physical certificate

- The network's moment is **not the exact continuum mass moment** of D. Its soft-ratio weights are generally different from physical voxel density or Boolean material. Even when beta>0 at ALL nodes, the lambda>0 term may reweight the full region: then the true physical full mass r should be constant (J=0), but this surrogate can predict nonzero J. An adversarial test keeps this negative result visible.
- The potential is **not globally C2**. As a node crosses beta=0, the hinge part changes; the Hessian may jump or be undefined, and at S=0 the norm can be nondifferentiable. `derivative_regime()` exposes `NODE_SIGN_BOUNDARY_UNDEFINED`, and `jacobian()` rejects those queries. A fixed-node stratum is NOT a W0/W2 certified Cherchi construction stratum or a neighborhood theorem for real CAD.
- The 6³ fixed Gauss discretization and missing exact CAD material labels still bias the result. Passing discrete-moment cone constraints, Jq PSD/symmetry, a finite analytic check or a one-step analytic objective test is **neither** a guarantee of true solid geometry nor native derivative correctness. Real F/D, manufacturing, full 10D Newton/KKT, and true Faster speedup remain unverified.

## Actual NEW CPU measurements (seeds 41,43,47, single-thread, 100 steps max)

All models use exactly the same four-channel density voxel arrays, analytic c, r/J and geometry-heldout splits. 40 independent train-family geometries (20 boxes+20 spheres), with 2 queries each, split into 32 train / 8 validation identities; independent test = 20 ellipsoids, 40 queries. GPU training time 0. The one-dimensional candidate acceptance is from an **independent analytic P0 objective** after necessary moment-cone screening; no native Cherchi/real CAD post-step evaluation.

| Model | r MAE ↓ | Jc MAE ↓ | necessary support pass ↑ | safe analytic candidate ↑ | Jq maximum asymmetry mean ↓ | cached J CPU ms ↓ |
|---|---:|---:|---:|---:|---:|---:|
| W5 voxel DeepONet | **0.03185** | **0.01577** | 39.2% | 29.2% | 0.418 | 0.859 |
| M10 positive discrete eps .12 | 0.03456 | 0.02061 | **100%** | 84.2% | 0.0613 | 0.352 |
| W6 convex Gauss eps .04 | 0.05085 | 0.02454 | 90.8% | 52.5% | ~0 | **0.206** |
| **M11 cone integrable lambda .25** | 0.04688 | 0.02258 | **100%** | 82.5% | **0** | 0.410 |
| **M11 cone integrable lambda .75** | 0.05810 | 0.03786 | **100%** | **88.3%** | **0** | 0.381 |

For M11 lambda=.25/.75, observed minimum eigenvalue of Jq across test points is about -6.7e-8 / -1.9e-7 (float32 roundoff); an independent float64 gradient/Hessian check agreed to <=5e-12 on smooth nondegenerate nodes. Cold encoder plus r takes ~0.865 / 0.973ms for M11 vs ~0.389ms for DeepONet. Actual one-encode + eight serial (r,J) query CPU means: DeepONet ~8.533ms, M10 positive .12 ~5.520ms, W6 Gauss ~3.509ms, M11 lambda .25 ~5.162ms and lambda .75 ~5.219ms. Query tests execute the actual path; they do NOT include native Boolean or a solver. Times depend on CPU, tiny shapes and Python overhead.

**Negative result:** M11's joint structural guarantee is real for its *discrete scalar potential on smooth fixed-node strata*, but both variants are less accurate than the simple DeepONet and the earlier positive-discrete model in the new three-seed P0 experiment. Lambda=.25 improves predicted r/J vs lambda=.75, while lambda=.75 has somewhat higher guarded 1D candidate acceptance. This is NOT a production framework win or a claim of acceleration against Cherchi.

## Upstream status reviewed 2026-10-20

- W6 read-only HEAD `27d51678cf741233c7a2e6c54c78d9a4667bec00`. The W6 M4/M5/M6 production source files used by the local runner were checked byte-identical to the connector-fetched Git blobs, including `m6_gauss_potential.py` `85d0ead6ee0dec9fc3212750e849310230d7878a`; no W6 branch changed.
- W0 HEAD `64fa50ca171bc8e964edc5ded5e0b967cbbdb0a8`, M10 evidence rechecks the actual H8f point59/60 native source-edge sign bracket; neither a new between-endpoint true Cherchi call nor a continuous derivative seal. Original H8f [failed CI run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) remains failure, point60 a branch-change anomaly.
- W2 HEAD `36eb96a0abac1e1b6620264ac79b83f3345bbcb4`, latest `teacher_manifest.json` Git blob `38bb837a6552bacec2bf3935a5db9299deb08203`: **81 historically verified native moment candidates ALL EXCLUDED**, zero training labels and no signed neighborhood proof. W5 read this latest manifest through GitHub, and locally adversarially tests the matching fail-closed *metadata interpretation*. An isolated previous W2 M8 manifest copy is retained only for older M10 regression. Neither W2 nor W0 raw archive is included in training.

## Exact reproducibility

```bash
# W5 branch checkout root; set read-only W6 root with M4/M5/M6 source Git hashes.
export W5_M11_READONLY_W6_ROOT=/path/to/readonly/w6
# Other W5 historical tests need their own W5_M7/8/9/10_* pinned inputs.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m pytest -q tests/python/test_w5_*.py
# Result from assembled, Git-blob-matched local source: 159 passed, 42 subtests passed.

for seed in 41 43 47; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m research.NeuralMoments.models.deeponet.m11_experiment \
    --w6-root "$W5_M11_READONLY_W6_ROOT" --seed "$seed" \
    --steps 100 --per-family 20 --repeats 3 \
    --output "research/NeuralMoments/models/deeponet/m11_seed${seed}.json"
done
python -m research.NeuralMoments.models.deeponet.m11_merge \
  research/NeuralMoments/models/deeponet/m11_seed41.json \
  research/NeuralMoments/models/deeponet/m11_seed43.json \
  research/NeuralMoments/models/deeponet/m11_seed47.json \
  --output research/NeuralMoments/models/deeponet/m11_seed41_43_47_full.json
```

Raw per-seed source/file SHA256 and all selected checkpoint steps, training seconds, geometry split hashes, individual held-out errors, guard rejections, cold/warm measured cost and full-precision aggregates are retained in JSON; no historical result is relabelled as newly run. This work uses no CUDA, no native Cherchi, no source geometry changes, and no GPU or native 24GiB job overlap.

## Next: M12

Confront the observed full-retention bias before claiming physical integrability: design a continuous positive-density potential that returns exact full/empty moments and zero derivative on strictly certified sign regions *without introducing an unverified discontinuity at the region transition*, or explicitly make a derivative-mode-dependent native bypass. Investigate node/voxel cell integration and structural regularization; add new independent primitive families, 3D full 10D decision auditing, and W2 native r-only evaluation only after independent geometry and file authentication. Do not train native Jacobians from the excluded H8f 81 points.
