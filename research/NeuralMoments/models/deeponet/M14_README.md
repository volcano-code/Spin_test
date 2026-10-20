# W5 M14 — exact oblique-plane clipping of a declared voxel-cell volume

**Branch:** `research/neuralmoments-w5-deeponet-20261019` in `volcano-code/Spin_test`. Parent reviewed: `33363d833d0623627afb2a7d5eff5dde5c46dffc`. **Only W5-owned paths and independent `tests/python/test_w5_m14_*.py` are changed.** W0, W2, W3, W6, `main`, original CAD and historical failed Actions runs remain untouched. Frozen common source: `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Scientific scope: real code, deliberately narrow admissibility

- `m14_oblique_cell_integrals.py` extends M13 from *positive vertical planes* to **arbitrarily oriented signed linear planes** `beta_c(x)=a+b_x*x+b_y*y+b_z*z`; the native quadratic slots must be exactly zero. The original native coefficient order is `(a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy)` and monomial coefficients are `q=Bc`, `B=diag(1,1,1,1,1,1,1,2,2,2)`. The retained side remains `beta>=0`; `c` and `-c` are different. Saved unit c is passed through and never re-normalized.
- A source-bound four-channel cell-centered voxel tensor defines a **piecewise-constant volume density `rho*occupancy` on `[-1,1]^3`**, not a native material. Full and empty cells use polynomial product integrals. A partially intersected cube is clipped by its six face polygons, capped by its exact plane intersection polygon, and tetrahedralized about a convex interior point for ten raw volume moments. Its surface Gram uses an **exact degree-four six-node triangle cubature**, then `Jc=(rho/||b||) ∫_cap m m^T dA · B`. This includes all 100 ambient derivative entries **at a smooth planar base c** even though the evaluator cannot accept a nonplanar quadratic c away from that base. Corrected `Jc B^-1` is symmetric PSD and `Jc c=0` up to floating-point roundoff *only under this cellwise linear-plane/continuous sliding-cut hypothesis*.
- **Fail closed:** native quadratic terms, zero plane normal, nonunit saved c, changed source bytes, modified cached numeric data, bad density/occupancy, and plane/grid-vertex contact cannot be interpreted as a legal 10×10 derivative. A grid-vertex contact returns `r=None,Jc=None`, not fabricated zero or a mislabeled smooth derivative. This deliberately excludes some numerically valid but uncertified interface cases.
- `m14_oblique_analytic.py` independently derives ellipsoid/ball oblique-cap `r[10]` using affine sphere-cap formulas and `Jc[10,10]` using polynomial-exact disk quadrature. A separate **yz-plane Gauss integral for tilted boxes** checks all ten r components and all 100 derivative entries without calling the clipped-cell implementation.
- `m14_error_bounds.py` requires an independent *analytic ellipsoid specification*. Its float64 interval-margined inside/outside test bounds the uncertainty to cells whose source occupancy might differ from the true analytic solid. The total ambiguous cell volume bounds all ten raw moment errors; the plane's ambiguous-cell section area bounds all native J entries. These bounds are **conservative and typically loose**; they rely on the privileged exact source specification and a finite rounding cushion, and are **NOT** a rigorous outward-rounded arbitrary CAD/Boolean proof.

## Actual executed regression and experiments

An isolated local checkout reconstructed from the exact Git blobs of previously pushed W5 milestone files and SHA-verified unmodified W6 M4–M7 source. Read-only W0/W2 historical summary file blobs were restored for existing test contracts, NOT used for native training.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=.:tests/python \
  pytest -q tests/python/test_w5_*.py
# 262 passed; 42 subtests passed; 0 failed; 0 skipped.

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=. \
  python -m research.NeuralMoments.models.deeponet.m14_oblique_benchmark \
    --seeds 79,83,89 --per-family 2 --queries 2 \
    --resolutions 8,16,24 \
    --output research/NeuralMoments/models/deeponet/m14_oblique_seed79_83_89_cpu.json
# exited 0; 12 geometries, 24 independent oblique-plane query identities,
# 72 exact cell-reference evaluations; 36 geometry-cache bindings.
```

### Independent ball/ellipsoid P0 heldout results

All three resolutions start from the **same 12 analytic primitive specifications and 24 native-plane query identities**; changing resolution resamples the declared proxy volume. Same numerical sources and independent closed-form/disk oracle for every comparison.

| Center-cell resolution | Raw `r MAE` ↓ | Native `Jc MAE` ↓ | Mean oblique cell `r+J` CPU wall ↓ | Conservative mean maximum-component `r` bound | Conservative mean maximum-entry `Jc` bound |
|---|---:|---:|---:|---:|---:|
| 8³ | 0.00641061 | 0.00553898 | 25.39 ms | 0.69119 | 1.78512 |
| 16³ | 0.00192737 | 0.00175830 | 89.44 ms | 0.29601 | 0.84343 |
| 24³ | 0.000780224 | 0.000900547 | 193.62 ms | 0.20575 | 0.57774 |

For 72/72 evaluations, the independent analytic-vs-proxy componentwise absolute error stayed below its explicitly source-dependent bound. All corrected `Jq` asymmetries were 0 at float64 precision, worst radial-null `||Jc c||≈1.70e-16`, and minimum symmetric `Jq` eigenvalue ≈ `-1.35e-16` (roundoff). For the exact **uniform tilted box**, all r/J entries match the independent 2D Gauss oracle within `2e-11`, including the doubled native cross coefficients.

**Critical negative cost:** Generic oblique polyhedral cell clipping is MUCH SLOWER than M13's specialized horizontal cached polynomial sums (~sub-millisecond). These 25–194 ms CPU times are *not* a speedup compared with a native Cherchi call, and do not measure network inference or a real Faster iteration. Future stages must amortize the exact reference or use an optimized native kernel. The W6 control present in the JSON is **UNTRAINED M7 maximum Gauss-node capacity with a hard cut**, not a fair trained network score, and supplies no valid smooth J.

## Independent dependencies and blockers

At M14 start: W0 M14 HEAD `83f9709c220e51a5927e053537bdd98ecc20f7c0`, W2 M13 HEAD `69fbabeeeb4cdf9704acbf16dbea2ec806da91f3`, W6 M9 HEAD `42d9a3b10df7d12d97a7db6e076d2306b8f0c6ae`. W2's contemporary manifest has **0 new native teacher runs, 0 admitted training samples, and 81 excluded H8f historical materials**. The historical H8f workflow remains `failure`; point 60's actual symbolic branch change, 64 nonunit archived native c, lack of W0 accepted projective-ray derivative categories and lack of W3 new trusted left/right native material mean no continuous W2 J can be trained yet.

This milestone performed **0 new W2/Cherchi native evaluations, 0 surrogate neural training jobs, 0 GPU hours**, and no native optimizer/printability/Newton certification. Neither the new continuous piecewise-cell reference nor its J is the original CAD. Full ten-coefficient nonplanar quadric clip integration, arbitrary real CAD material/F/D frames, independently sealed smooth neighborhood and native end-to-end speed validation are still future work.

## Next dependency gate

Keep the W5 experimental branch isolated. Await independently released W0/W2 per-sample source/geometry/F/D/density/retained-side seals and a derivative type (ambient smooth or verified tangent) together with true W3 point-60 one-sided native receipts and a separately certified Newton terminal. Only then evaluate real-Cherchi training and full solver speed; never relabel archived H8f data or claim a green CI without actual workflow checks.
