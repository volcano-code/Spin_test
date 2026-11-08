# W6 P18 — Three-seed trained 64³ PINO × DensiCrafter material-design confirmation

Date: 2026-11-08.
Run: https://github.com/volcano-code/Spin_test/actions/runs/42454664233
Commit tested: `5f1fc96b4224e4f7398c68d333eb9a689c18e1fa`.
Status: **SUCCESS; one contract test passed; three full independent seed/geometry designs completed.**

Artifact: `w6-p18-three-seed-trained64-PINO-DensiCrafter`, ID 13607136915.
ZIP SHA-256:
`daab6173ca3c59fc4154f689b04c71b4e5cad8f320382271fbc94d0fc8110b52`.
JSON SHA-256:
`340a674c254e0872ca4075885440f8ded51fd8af594b8cfd2098843007c9c239`.

## Fixed experiment

- P14 trained P-CRAFT SpinPINO checkpoints, native 64³ Fourier grid,
  seeds 271/277/281. All PINO weights frozen; only DensiCrafter
  material-density logits optimized.
- Three independent analytic P0 sphere geometries, one per seed.
- 2-voxel protected shell: surface cells are exactly fixed at rho=1;
  outside geometry remains exactly zero.
- Density starts near 1 to match the PINO training input distribution.
- DensiCrafter original MIT mass, COM and smooth bottom-contact losses.
- Four arms: Densi-only, PINO-only, soft joint, and independent
  hard-feasibility joint.
- 12 Adam updates per arm, lr=.06.
- Independent cell-centered hard-cut ten-moment reference and
  normalized full-material nine-moment ledger.
- Predeclared tolerances: PINO cut-r relative change <=2%,
  independent hard-cut r relative change <=2%, normalized full-material
  nine-moment L2 change <=2%.

## Aggregate three-seed results

| Metric | DensiCrafter only | Feasible joint PINO + DensiCrafter |
|---|---:|---:|
| Mean material mass reduction | 0.9300% | **0.9225%** |
| Mean PINO cut-r relative change | 0.9828% | **0.2330%** |
| Mean independent hard-cut r relative change | 0.8635% | **0.8542%** |
| Mean normalized full-material 9-moment L2 | 0.0003345 | **0.0003315** |
| Protected shell | 3/3 passed | **3/3 passed** |
| Feasibility backtracking accepted | — | **36/36 steps** |
| Feasibility backtracking rejected | — | **0/36 steps** |

Per-seed feasible-joint results:

| Seed | Mass reduction | PINO moment change | Independent hard-cut change | Normalized 9-moment L2 | Accepted/rejected |
|---|---:|---:|---:|---:|---:|
| 271 | 0.8963% | 0.0747% | 0.9522% | 0.0003141 | 12/0 |
| 277 | 0.9107% | 0.0901% | 0.9720% | 0.0003220 | 12/0 |
| 281 | 0.9604% | 0.5342% | 0.6383% | 0.0003583 | 12/0 |

All three distinct geometries satisfy all predeclared 2% limits. The
PINO-only baseline is a zero-update control with zero mass reduction.

## Interpretation

This confirms P17 was not a single-sphere coincidence: DensiCrafter's
density design layer is coupled to three independent, genuinely trained
P-CRAFT PINO checkpoints at native 64³ Fourier resolution. All 36
constrained optimization updates were admitted without backtracking,
and the independent hard-cut check agreed within the fixed 2% screen.

The improvement is nevertheless **modest (~0.92% mass saving)**. The
normalized nine-moment ledger is a shape/inertia proxy, not exact
preservation of absolute inertia after mass reduction. A two-voxel
shell is not a millimeter-certified manufacturing wall. The hard cut
is cell-centered voxel quadrature, not continuous Cherchi integration.
No FEM/FEA stress or printed strength is validated.

## Decision and next

- Accept DensiCrafter as an experimentally integrated design layer
  for trained P-CRAFT PINO at 64³; keep it optional, not yet a default
  production design algorithm.
- Next increase the diversity of real geometries and test CAD meshes;
  enforce physical-unit wall thickness and structural stress/strength.
- Use W0/W2 admitted Cherchi teacher for exact continuous cut moments
  and Jacobian verification.
- After P16 64→128 transfer, repeat the same three-seed design
  experiment at native 128³.
- Only then measure the incremental benefit of QuadrANN/GINO over
  the already trained PINO + DensiCrafter baseline.

No Cherchi, arbitrary quadric derivative certification, Newton
admission, 512³ GPU training or full Spin-it Faster acceleration is
claimed.
