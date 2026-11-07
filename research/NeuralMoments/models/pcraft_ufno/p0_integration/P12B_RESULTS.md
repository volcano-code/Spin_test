# W6 P12b: new-seed, geometry-grouped exact-cube rotation confirmation

Date: 2026-11-07; branch: research/neuralmoments-w6-pcraft-20261019.
**Decision: experiment reproducibly supports trained upstream enhancements on restricted P0, but neither is production-promoted.**

## Authoritative measured evidence
Corrected source commit: aa89718bde31703472b6ba45f8f4139bb87006f8.
Confirmatory GitHub Actions: https://github.com/volcano-code/Spin_test/actions/runs/42374352029
CI completed SUCCESS, 6 tests passed, 0 failed.
Source artifact: w6-p12b-rotated-new-seeds / w6_p12b_new_seed_cube.json.
Actual JSON SHA-256: 8073a283d381081236b14872bc65aae818562747603b50bca6fe03936baf5952.
Download ZIP SHA-256: 2f4b21b7c787b3eb6adee205f94d578cfd801b8cc9d4b93aed9305ad2541acbc.

## Frozen experiment
- New seeds: 211,223,227. No tuning of training parameters against this confirmation.
- 80 pretrained P-CRAFT PINO updates for each seed, common initialization reused across conditions; then 36 identical fit observation/update steps for PINO-head, source-pinned GINO and material-aware original QuadrANN.
- Fit: 22 box/sphere geometry IDs; validation: 6 disjoint box/sphere IDs; test: 8 completely held-out ellipsoid geometry IDs. Two coefficient queries per geometry.
- Every held-out geometry gets exactly ONE deterministic signed-permutation cube rotation, shared across its coefficient queries. Its native c, analytic continuum r and J are transformed exactly. No arbitrary SO(3) voxel interpolation in this confirmation.
- Test geometry IDs and transformed test SHA-256 recorded per seed. Test data NEVER select checkpoints; validation score is r_MAE + 0.25 J_MAE.
- The original PINO U-FNO / F-FNO physics-aware head remains primary. GINO and QuadrANN are optional, trainable positive quadrature reweighting components. GINO and QuadrANN allocated trainable parameters/FLOPs differ from PINO, so this is label/update-budget matched but not capacity matched.
- Exact labels are ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI for restricted vertical-plane analytic solids. Test labels under cube rotation are analytic coordinate transforms, not general CAD or real Cherchi supervision.

| Condition | Mean test r relative L2 | Mean test J relative L2 | Trainable parameters | Mean cold encode for 8 geometries | Mean 36-step train time | Selected steps |
|---|---:|---:|---:|---:|---:|---|
| P-CRAFT PINO head | 0.435962 | 0.496816 | 6688 | 0.02157 s | 0.36666 s | 36,36,4 |
| PINO + original GINO | **0.320526** | 0.403233 | 8603 | 0.51543 s | 9.32120 s | 36,36,28 |
| PINO + original QuadrANN conditioned on material | 0.328701 | **0.400509** | 4066 | 0.03280 s | 0.53504 s | 36,36,16 |

Relative to PINO, mean test error reduction on this distribution:
- GINO: r -26.5%, J -18.8%; cold geometry encoding 23.9x PINO.
- QuadrANN: r -24.6%, J -19.4%; cold geometry encoding 1.52x PINO.
These are CPU research-benchmark costs, not native Cherchi/Spin end-to-end speedups.

## Learning attribution: initial random adapter vs validation-selected trained checkpoint

| Seed / adapter | Initial r -> selected r | Initial J -> selected J |
|---|---|---|
| 211 GINO | 0.373286 -> 0.287304 | 0.490225 -> 0.422566 |
| 211 QuadrANN | 0.303410 -> 0.271745 | 0.414918 -> 0.389470 |
| 223 GINO | 0.425391 -> 0.337082 | 0.464938 -> 0.377484 |
| 223 QuadrANN | 0.349900 -> 0.329838 | 0.389257 -> 0.370874 |
| 227 GINO | 0.489955 -> 0.337191 | 0.541392 -> 0.409650 |
| 227 QuadrANN | 0.398764 -> 0.384520 | 0.454916 -> 0.441182 |

Every new seed has training-specific held-out r/J improvements for BOTH upstream adapters over its own untrained/random state. This repairs the initial P12 ambiguity where one QuadrANN seed had selected training step zero.

## UQNO groupwise calibration, true fallback limitation
- Source-pinned UQNO scale head: 48 fit-only training updates per seed.
- Six validation calibration geometry IDs per seed, grouped across two coefficient queries per geometry; alpha=0.25.
- qhat 1.285744 / 1.165212 / 1.557436 respectively.
- Exact request fraction at predeclared maximum simultaneous radius=0.05 is 100% in all seeds. Therefore UQNO currently cannot save native exact calls.
- Held-out empirical simultaneous 10-component geometry-group coverage was 8/8 per seed (24/24 across seeds). This is small-sample empirical coverage, NOT a proof of calibrated real-world reliability or exchangeability.
- No predicted Jacobian is admitted to native Newton. UQNO can request exact calculation but does not execute Cherchi.

## Promotion decision and work remaining
1. Keep **P-CRAFT Spin-PINO** the only default neural backbone; optional GINO and QuadrANN remain off by default.
2. QuadrANN is the first follow-up adapter due to favorable r/J and 1.52x cold encoding cost; GINO is a strong but significantly more expensive alternative. Both require capacity-matched and newly held-out cut/shape tests before any production selection.
3. The trained adapters learned on 8^3 analytic P0 data only. A stronger experiment must use genuinely novel non-vertical cuts / quadric coefficients and formal Cherchi when W0/W2 admit labeled source/derivative receipts. Do not repeatedly tune against held-out ellipsoid labels.
4. UQNO needs practical risk/coverage at a useful exact fallback rate. Current 100% exact-request setting yields no acceleration.
5. Local official fVDB CUDA integration, 64/128/256/512 sparse occupancy/VRAM sweeps, native CAD moment/Jacobian numerical certificates, and end-to-end Heart/Teapot/Noodles Spin-it Faster optimization remain unverified.
6. Current cloud can still implement new mathematical cut-aware proposals, P0 CPU tests and proper training ablations. The user's local GPU/native Cherchi environment is required for high-res end-to-end performance certification.

### Upstream source provenance
Exact pin/notice source: p0_integration/UPSTREAM_PINS.json; QuadrANN MIT original model core in p0_integration/third_party/quadrann_core.py; NeuralOperator GINO/UQNO from pinned upstream package. The PINO source origin remains volcano-code/test internal and needs ownership review before public redistribution.
