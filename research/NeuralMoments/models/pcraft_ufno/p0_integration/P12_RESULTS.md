# W6 P12: three-seed trained original-source GINO / material-aware QuadrANN / UQNO

Date: 2026-11-07. W6 branch only; P-CRAFT Spin-PINO remains the sole production backbone.
Verified run: https://github.com/volcano-code/Spin_test/actions/runs/42373752345
Run succeeded: 8 tests passed and 0 failed; three-seed P0 training and UQNO scale calibration completed.
Commit for checkpoint fix: 351c07c3ebbfd7f97f82e66295d14bb78ac49f94.
Artifact: w6-p12-three-seed-trained-original-upstream / w6_p12_three_seed_pino_upstream.json
Raw JSON SHA256: c44fb2200111f9a2e4b18426e823619cf6a211cd1dcd7fd8174152cfee21e527
ZIP SHA256: 95317a2587cb4e6869a528ac9fb2e418f3a73a69224a9f31fcecea0ad9ad639e

## Frozen protocol and scope
Seeds 131,137,139. Each seed: 16 fit geometry IDs, 4 validation IDs, 6 held-out ellipsoid IDs, 2 coefficient queries per geometry.
Shared PINO receives 40 pretrain optimizer steps; P-CRAFT PINO head, original GINO, and source-material-conditioned pinned QuadrANN each then receive exactly 12 additional fit updates and validation-only checkpoint selection.
Trainable parameter counts and FLOPs are unequal. Only analytic continuum restricted vertical-plane P0 r/J labels are used, NEVER W2/Cherchi.

| Arm | r relative L2 | J relative L2 | Trainable params | Cold encode 6 geometry s | Additional training s |
|---|---:|---:|---:|---:|---:|
| Original PINO head | 0.420825 | 0.499192 | 6688 | 0.00981 | 0.07857 |
| P-CRAFT PINO + trained GINO | 0.361681 | 0.454980 | 8603 | 0.31678 | 2.30400 |
| P-CRAFT PINO + material-aware QuadrANN | 0.329522 | 0.422629 | 4066 | 0.01608 | 0.16000 |

Mean r/J relative error improvement for QuadrANN vs PINO: 21.7% / 15.3% on THIS limited 8^3 analytic P0 experiment.

Per seed r/J relative L2:
- 131: PINO 0.394034/0.487248; GINO 0.337892/0.442850; QuadrANN 0.295517/0.405949; QuadrANN validation-selected step 12.
- 137: PINO 0.440143/0.536851; GINO 0.382237/0.505427; QuadrANN 0.350707/0.465083; QuadrANN step 12.
- 139: PINO 0.428298/0.473478; GINO 0.364912/0.416662; QuadrANN 0.342343/0.396854; QuadrANN BEST STEP ZERO.

Important: QuadrANN seed 139 improved over PINO with random initial gate correction; its improvement cannot be attributed to training. GINO cold encoding was about 32x slower than PINO on this CPU microbenchmark. Do not promote either plugin based only on this run.

UQNO residual scale: 24 fit-only updates per seed; groupwise split conformal on four validation geometry IDs per seed, separate from test ellipsoids. alpha=0.25; qhat=0.650568,0.867832,0.679869.
Observed 6/6 held-out geometry-group simultaneous coverage at each seed, BUT exact request fraction is 100% at predeclared maximum radius 0.05. This is an unproven small-sample distribution, not reliable native safety calibration. All native Newton derivatives withheld.

## Decision
- Maintain the original P-CRAFT PINO main path and zero-gated external modules as default.
- QuadrANN is the first candidate for independent confirmatory testing with more updates, new seeds and a fresh rotated holdout, not production promotion.
- A true speedup requires lower total cost including geometry encoding and exact fallback; UQNO's current 100% exact request rate proves no reduction of exact calls.
- Native Cherchi teacher admission, certified CAD J, high-resolution CUDA/fVDB 512^3 training and Heart/Teapot/Noodles end-to-end solver evidence remain absent.
