# W6 P17 — DensiCrafter coupled to a trained native 64³ P-CRAFT Spin-PINO

Date: 2026-11-08. Research branch only.
Run: https://github.com/volcano-code/Spin_test/actions/runs/42454394508
Source commit: `dadcf302f0ede856677435cdf1f4c2be4539fbbb`.
Result: **SUCCESS; 2 tests passed, 0 failed; four-arm trained-PINO density design completed.**

Artifact: `w6-p17-trained64-PINO-DensiCrafter`, ID 13606923000.
ZIP SHA-256:
`e6fdb99943353ec31039766f07f556835d4c173cf9c88679b659a83fa21b7a7c`.
JSON SHA-256:
`edbad19cdab4ab5b9a1f008ac83b27bcb7cd144c8cac520241e248a7371b4dae`.

## Actual trained model and design

- Strictly loaded P14 seed-271 trained P-CRAFT SpinPINO at native 64³
  Fourier grid (width 8, modes 4, four U-FNO layers, 512 quadrature atoms).
- All PINO weights frozen; only DensiCrafter density logits optimized.
- Synthetic P0 sphere geometry, 64³ source; 2-voxel protected surface
  shell: 9,955 protected cells, 12,693 interior design cells.
- Initial interior density logit=4 (rho≈0.982) to match P14 density=occupancy
  training distribution.
- 12 Adam updates per design arm, lr=.06.
- Original MIT DensiCrafter mass, COM and smooth ground-contact losses.
- Independent cell-centered hard-cut ten-moment integral and normalized
  full-material nine-moment ledger; fixed tolerances 2% for PINO cut-r,
  independent cut-r and normalized nine-moment shape change.
- This is trained PINO coupling, not random PINO and not merely a code
  import. It remains analytic P0, not W2/Cherchi.

## Measured four-arm result

| Arm | Material mass reduction | PINO cut-r relative change | Independent hard-cut r relative change | Normalized full-material 9-moment L2 | COM shift | Constraint status |
|---|---:|---:|---:|---:|---:|---|
| DensiCrafter only | 0.9069% | 1.0146% | 0.9643% | 0.000318 | 3.53e-5 | within 2% tolerances |
| PINO-only | 0% | 0% | 0% | 0 | 0 | trivial no-op |
| Soft joint | 0.8963% | 0.0747% | 0.9522% | 0.000314 | 3.18e-5 | within 2% tolerances |
| **Feasible joint with independent filter** | **0.8963%** | **0.0747%** | **0.9522%** | **0.000314** | **3.18e-5** | **12/12 accepted, 0 rejected** |

The feasible joint run meets all predeclared limits without backtracking
rejections. Its loss decreases from 0.164142 to 0.163382. The outer shell
remains exactly 1 and outside-solid density remains exactly zero.

## Interpretation

This is the first W6 result demonstrating DensiCrafter's material design
losses connected to an actually trained P-CRAFT PINO model at a native
64³ Fourier grid, with an independent voxel hard-cut ledger. It is a
genuine integration step beyond P13's random/untrained PINO prototype.

The observed mass saving is **modest (~0.90%)**, not a dramatic lightweight
optimization. The PINO moment predictor changes by 0.075%, while the
independent hard-cut moment changes by 0.952%; the independent check is
therefore essential. The two-voxel shell is a voxel-count protection
rule, not a millimeter-certified manufacturable wall thickness.

The hard filter's 12/12 acceptance means this particular run remained
inside the predeclared 2% screening tolerances; it does NOT certify
continuous CAD geometry, exact structural inertia, stress/FEM strength,
printability, Cherchi integration or Newton derivative safety.

## Next

- Repeat across multiple P14 seeds and several independent geometry IDs.
- Add a unit-aware minimum wall constraint once physical CAD bounds are
  supplied; do not equate two voxels with a manufacturing specification.
- Use actual W0/W2 Cherchi-admitted labels for continuous cut-moment and
  Jacobian verification.
- After P16 64→128 transfer evaluation, repeat this design experiment
  using the selected trained 128³ PINO.
- Only then add QuadrANN as an optional quadrature proposal and measure
  its incremental value against this trained-PINO + Densi baseline.
