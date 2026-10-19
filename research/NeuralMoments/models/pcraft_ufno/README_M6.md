# W6 M6 — Gauss positive quadrature, teacher gates and physicality counterexample

**Date:** 2026-10-19. **Repository:** `volcano-code/Spin_test`, **only writing branch:** `research/neuralmoments-w6-pcraft-20261019`. **Exclusive file scope:** `research/NeuralMoments/models/pcraft_ufno/`. Previous W6 M5 parent: `8bc72fe0c2d88bf2cd4de1922242a4745c141891`. No modifications to `main`, W0/W1/W2/W3/W4/W5 or `volcano-code/test`.

## Exact upstream read-only pins

- W0: `f30d2ece1d14051b29b30d85655928a3bf412567`; `validate_contract_v1.py` blob `fe5f71e7cb2b6c6ad45f48c49ab4042f797a113e`; `moment_coordinates.py` blob `7f844fadc02b8f02c8560b5180e29bac78332ab4`.
- W2: `c2628ea75a8680910557855896e7317f92567756`; `teacher_manifest.json` still records `native_teacher_runs=0` and `training_samples=0`, with a pending W0 dependency. Its `q` is **native matrix-entry c**, not W0 monomial `q=Bc`. **No actual Cherchi labels were used or admitted.**
- W6 frozen source: `0bcc187b3005478baa586a6d6f450e73811ca342`; native c order `(const,x,y,z,xx,yy,zz,yz,xz,xy)` and ten ordinary raw moments `(M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY)`. `B=diag(1×7,2×3)`, signed retained side `beta>=0`, positive projective equivalence only.

## Real code changes

1. `m6_gauss_potential.py` — preserves M5's 13,448-real-DOF factorized spectral trunk and nonnegative convex-potential weight head, replacing fixed uniform midpoint nodes with 6×6×6 tensor-product Gauss–Legendre nodes and positive weights that sum to 8. The 25% *label-blind* coarse occupancy-prior ablation still caches geometry once and uses analytic r/J only. `rule='midpoint',prior_fraction=0` reproduces the M5 network exactly at the same seed, including r/J values.
2. `m6_experiment.py` — same frozen W6 M3 data generator, split by geometry identities with *no* train/validation/test identity leakage, equal training steps, 80 analytic labels per seed (64 training and 16 validation queries), 40 held-out ellipsoid labels, Adam LR .003, `MSE(r)+.5*MSE(J)`, validation score `r_mae+.25*J_mae`, early stopping every ten steps with patience five. It reports r/J/directional errors, continuous-cut Jq asymmetry, P0 zero-reference quadratic objective *gradient* mismatch (no fake clipped Newton step), cold/warm CPU timing, and an independent necessary-material-moment diagnostic.
3. `m6_teacher_handoff.py` — fail-closed W2 manifest gate, even for self-asserted positive sample counts. Only when an **unchanged, importable, pinned** W0 validator and its coordinate dependency become available does the compatibility inspector invoke the actual W0 `validate_record`. Even a valid W0 record remains **candidate only** until separately certified native F/D/retained boundaries, proof and derivative-neighborhood checks. This code never promotes W2 to training.
4. `m6_moment_guard.py` — additional **necessary**, not sufficient, nonnegative-material inequalities on raw moments for a caller-grounded bounding box: `M>=0`, first-moment box bounds, covariance matrix `M Q - L L^T` PSD, and diagonal upper second-moment constraints. Rejects unsafe tuples for optimization. Passing does **not** grant geometry/material truth.
5. `m6_safe_inference.py` — exact rational interval bounds on the *binary* native-c polynomial for a caller-grounded geometry box. Strict `CERTIFIED_EMPTY` returns `(r,J)=(0,0)`; strict `CERTIFIED_FULL` returns **discrete positive-quadrature** `r=sum_k w_k m_k` and `J=0`; `UNDECIDED` returns the smoothed surrogate only when its necessary moment constraints pass, otherwise throws `PhysicalAdmissibilityFailure` if `reject_invalid=True`. Proof is **only of the polynomial sign within a supplied box**, not that CAD D is inside the box nor that the approximated full moment equals real volume.
6. `test_m6.py` — 31 new math/gradient/physicality/smoke tests, including 1,000 sampled spatial points for interval inclusion and negative-mass counterexample. Re-ran 14 M4 tests, 17 M5 tests; **62/62 total green**.

## Exact commands and executed environment

Local Python 3.13.5 / PyTorch 2.10.0+cpu / NumPy 2.3.5; CPU single thread; no CAD runtime, CUDA, model weights or FEM checkpoint.

```bash
PYTHONPATH=. python -m unittest \
    research.NeuralMoments.models.pcraft_ufno.test_m4 \
    research.NeuralMoments.models.pcraft_ufno.test_m5 \
    research.NeuralMoments.models.pcraft_ufno.test_m6 -v
# Total: Ran 62 tests, OK; recorded in m6_test_local.log.

PYTHONPATH=. python -m research.NeuralMoments.models.pcraft_ufno.m6_experiment \
    --seeds 19,23,29 --steps 400 --names lite_m6_midpoint,lite_m6_gauss,lite_m6_gauss_prior25 \
    --output m6_exploratory_400_cpu.json

PYTHONPATH=. python -m research.NeuralMoments.models.pcraft_ufno.m6_experiment \
    --seeds 19,23,29 --steps 400 --names lite_m6_midpoint,lite_m6_gauss \
    --smoothing 0.12 --output m6_bandwidth_012_cpu.json
PYTHONPATH=. python -m research.NeuralMoments.models.pcraft_ufno.m6_experiment \
    --seeds 19,23,29 --steps 400 --names lite_m6_midpoint,lite_m6_gauss \
    --smoothing 0.25 --output m6_bandwidth_025_cpu.json

# Exploratory comparison was followed by a separate-seed confirmation.
PYTHONPATH=. python -m research.NeuralMoments.models.pcraft_ufno.m6_experiment \
    --seeds 31,37,41 --steps 400 \
    --names lite_m6_confirm_baseline,lite_m6_confirm_gauss25 \
    --output m6_confirmatory_400_cpu.json
```

When re-executing from GitHub, use the target W6 branch checkout and adjust output paths, not any other window. All experiment commands reported exit 0; the result files contain the *full* seed/split/label digests and timing traces. Current working environment had no direct GitHub DNS for cloning, so tests were run on a local mirror. The M4/M5 critical source blobs were separately checked against GitHub `fetch_file` in this session; the analytic source in this mirror is a prior mathematically equivalent reproduction with identical frozen M3 **dataset SHA256 for seeds 19,23,29**, not a byte-for-byte claim about the GitHub analytic_cut.py. No GitHub Actions CI passed status is asserted.

## Results — exploratory, seeds 19,23,29 (means, 400 steps)

| quadrature / smoothing | r MAE↓ | J MAE↓ | directional MAE↓ |
|---|---:|---:|---:|
| midpoint / .04 = frozen M5 control | 0.02267 | 0.01810 | 0.01717 |
| Gauss / .04 | 0.03541 | 0.02523 | 0.02249 |
| Gauss+25% occupancy / .04 | 0.03000 | 0.02477 | 0.02535 |
| midpoint / .12 | 0.02329 | 0.01765 | 0.02541 |
| Gauss / .12 | 0.02458 | 0.02089 | 0.02677 |
| midpoint / .25 | 0.02472 | 0.01986 | 0.04073 |
| Gauss / .25 | **0.02099** | **0.01798** | 0.03503 |

The epsilon .25 candidate was *selected after exploratory held-out observation*, so this sweep cannot itself certify generalization.

## Separate seed confirmation — seeds 31,37,41 (means, 400 steps)

Pre-specified after the sweep: M5 midpoint epsilon .04 versus M6 Gauss epsilon .25; same 13,448 trainable real DOF, same geometry sampling, 80 train/validation plus 40 held-out analytic labels and matching training/early-stopping rule.

| metric | midpoint .04 | Gauss .25 |
|---|---:|---:|
| raw r MAE↓ | 0.04108 | **0.02383** |
| raw J MAE↓ | 0.03291 | **0.01961** |
| directional derivative MAE↓ | **0.03383** | 0.03954 |
| analytic quadratic objective gradient MAE↓ | 0.10521 | **0.02569** |
| **fraction satisfying necessary moment conditions↑** | **86.67%** | **35.00%** |
| mean predicted mass for truly empty c=(-1,0,...,0) | −0.001022 | **−0.013547** (worse) |

**Do not deploy the Gauss .25 head without physicality rejection.** A lower r/J error does not make an invalid negative-mass moment physically acceptable. The larger smoothing moves away from the exact retained volume's discontinuous Heaviside representation. Early-stop variance is material; three analytic seeds are not a real CAD generalization benchmark.

## Critical M5/M6 theoretical counterexample

The smoothed convex potential is `sum_k w_k (a_k + sqrt(a_k² + epsilon² ||q||²))/2` with `a_k=q⋅m_k` and `w_k>=0`. It **is** convex and positively one-homogeneous; `Jq = Jc B^-1` is symmetric PSD in smooth nonzero-q regions. But for `c=(-1,0,...,0)`, all points have beta=-1, so the true retained solid is EMPTY. Yet with six-point Gauss quadrature and half of each positive integration weight, the smoothed `r[0]` is **−0.00159936053**, which violates the mass nonnegativity condition. Therefore **Jq symmetry/PSD is not sufficient to establish the moment cone, independent volume truth or solver applicability.** Exact hard Heaviside quadrature returns zero here but does not supply a useful smooth ambient J away from the cut; there is no free physicality guarantee.

M6's rational interval shortcut repairs this strictly negative-polynomial case without claiming anything about ambiguous boundary-crossing cuts. It also bypasses the smoothed overfull case for strictly positive polynomials by using the cache's discrete positive weights. The output is still only *approximate quadrature* unless independently authenticated for real source geometry.

## Unresolved / next actions

- W2's real Cherchi labels still **zero**. W0 symbolic compatibility is not proof of native F/D partition, derivative branch stability, or sealed Newton outcome. The W0 runtime pin is not installed in this isolated W6 checkout, so positive-path official W0 validator integration was **not exercised**; only missing/tamper fail-closed paths were actually tested.
- The larger-bandwidth Gauss model has a serious physicality-acceptance regression. Build a genuinely moment-cone-valued integrable (or derivative-mode-dependent) potential, not merely a PSD Hessian. Test clipping/contacts separately; don't fabricate ambient 10×10 J for W2 tangent/undefined runs.
- Test real geometries only once W2 publishes authenticated labels with frozen identity and source hashes; compare actual native evaluation/Jacobian/solver terminal errors separately from CPU model timing. Preserve serial native 24GiB/swap0 host constraints and GPU training resource policy.
- No SOTA, complete Spin-it faster runtime speedup, GPU VRAM, real Newton success or 3D printable material guarantee is asserted.
