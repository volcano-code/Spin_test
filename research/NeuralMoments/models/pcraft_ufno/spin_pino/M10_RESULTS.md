# W6 M10 — source-resolution sparse detail reaches the primary P-CRAFT Spin-PINO

Date: 2026-11-07. Protected window: `research/neuralmoments-w6-pcraft-20261019`.
Primary source commit:
https://github.com/volcano-code/Spin_test/commit/8c4f8f2feb6ecd5327ff1f4b27390af45b6fd52f
Actual independent CPU CI:
https://github.com/volcano-code/Spin_test/actions/runs/42349300725
CI status: **SUCCESS, 22 tests passed, 0 failed** (1.02 seconds).
Official GitHub Actions artifact: `w6-m10-sparse-detail-evidence`,
file `w6_m10_sparse_detail.json`.
Downloaded artifact ZIP SHA-256:
`688afd58aaaf7bd934382ca82ae839e28d354cad792719353742b64120c41a58`.

## New source and contract
- `m10_sparse_detail.py`: `SparseMultiscaleDetail` and
  `SparseDetailSpinPINO`. Fixed-coefficient-agnostic material descriptors
  are gathered using sparse grouped voxel bins and local first/second-order
  *subcell* offsets. Levels 16/32/64 on a 512^3 input are supported without
  allocating a full dense source grid.
- Original P-CRAFT factorized FNO/U-FNO geometry encoder and original
  physics-aware ten-moment and Jacobian heads remain authoritative *within
  the neural model*. The new branch is an optional bounded positive
  multiplicative correction of its support-masked quadrature atoms.
- New `detail_gate` initializes to zero. Existing PINO numerical
  outputs are bit-exact at that setting. With an explicitly nonzero gate,
  fine-scale original source voxel positions are available to the model.
- Tensor tests check exact initialization equivalence; same coarse
  material with differing subcell detail; positivity; r(c)+r(-c) algebra;
  Jacobian projective radial property; model parameter gradients; 512
  coordinate-domain source; invalid source/duplicate rejection.

## Actual CI measurement (CPU 1 thread; random untrained PINO)
| Check | Observed |
|---|---:|
| Combined M10 + M9b + M9 regression | 22 passed, 0 failed |
| Two distinct 32^3 source datasets map to identical coarse 8^3 input | true |
| Zero-gated PINO vs original r/J max absolute difference | 0.0 |
| Nonzero-gated r max abs difference for that fine-detail pair | 4.136189818382263e-5 |
| Nonzero-gated J max abs difference | 8.777901530265808e-5 |
| 32^3 pair two forward evaluations | 5.171398 ms |
| Source coordinate domain | 512^3 |
| Input sparse active samples | 4096 |
| Sparse feature scales | [16,32,64] |
| 512^3 *coordinate-domain* reduced PINO forward | 4.981872 ms |
| Discrete material mass conservation relative error | 0.0 |
| Fine-to-coarse ten-moment relative drift | 0.0023333211340887975 |
| Entire dense 512^3 spectral computation | false |
| Native fVDB or PhysicsNeMo FIGConvNet source integrated | false |
| Trained model, held-out accuracy gain, or Cherchi-certified derivative | false |

The change in r/J for the carefully constructed pair proves
**representational sensitivity**, NOT lower error; the nonzero gate was
manually activated on random weights. This experiment does not establish
a well-trained high-resolution neural operator. Neither 512^3 full
occupancy nor GPU memory/throughput was stress tested. This M10 bridge
still reduces the base PINO geometry to a small dense grid; only the
separate detail features preserve source-scale information.

## Admission decision / recommended next milestone
M10 is admitted only as an *optional experimental feature interface*:
its physical-structure unit tests and same-coarse different-fine
sensitivity contract passed. Do NOT promote it as a production default.

Next M10b:
1. Train using **identical, geometry-disjoint** data/teachers and
   compare against unchanged PINO, PINO+source moments alone, and
   PINO+sparse local multi-scale features; include 3 seeds and budgets.
2. Test same-coarse but different fine geometry on held-out shapes/cuts;
   report r and J errors, calibration, cold/warm costs and coverage.
3. Verify 16/32/64/128 scale with memory logs and source hashes. For
   512^3 use the existing local GPU with an independent fVDB-compatible
   environment, official source/notice pins and sparse occupancy stress
   tests, before making performance claims.
4. Only use formally W0/W2-admitted Cherchi teacher and safe Newton
   derivative records; analytic P0 remains separately labeled.
5. Preserve P-CRAFT PINO as the sole main network. FIGConv/GINO and
   other advanced projects remain optional feature or fair baseline
   candidates until demonstrated marginal value.

Cloud can do the M10b CPU analytical small-scale training and artifact
audits now. Official fVDB CUDA and full local native Heart/Teapot/
Noodles 512^3 experiments require user's actual compatible local host.
