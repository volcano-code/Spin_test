# R4.1 verification report — 2026-11-05

## Verification
- Original R4 parent manifest and the R4.1 incremental manifest verified: parent intact; 16 incremental files verified.
- Full portable suite rerun in the cloud: **151 passed, 38 skipped, 0 failed** (6.05 s).
- Reproducible benchmark rerun with seed 24041: 36 random cases across box/split/shell families.
- Maximum complement/scale/Jacobian structural residual: **6.661338147750939e-16**.
- Minimum symmetrized Gram eigenvalue: **-2.4632080739768097e-16**, consistent with floating-point roundoff in these fixtures.

## Paired CPU subtask comparison
| Case | New median | R3 hard tiles32 median | Ratio | R3 r relative error | R3 J relative error |
|---|---:|---:|---:|---:|---:|
| oblique corner | 1.230 ms | 63.987 ms | 52.0x | 9.15e-7 | 2.78e-3 |
| oblique cut B | 0.990 ms | 99.259 ms | 100.3x | 2.94e-7 | 5.57e-5 |
| oblique cut C | 1.163 ms | 143.089 ms | 123.0x | 8.36e-8 | 2.42e-4 |

These are plane-only CPU timings against an approximate R3 comparator. The methods are not equal-error; these numbers are not whole-pipeline or native Spin speedups.

## Limits and blockers
- Domain: disjoint, constant-density, axis-aligned box pieces; regular plane cuts only.
- Near box-vertex events the derivative is withheld.
- Floating-point results have no formal interval error certificate.
- Official Algoim source/build and independent pairing are not complete.
- W0/W2 formally admitted Cherchi labels remain zero; no native Cherchi call or native Newton acceptance.
- No GPU/fVDB/256^3/512^3 or real Heart/Teapot/Noodles optimization was performed.

## Next work
R4.2 should first handle curved quadric event classification with fail-closed derivative withholding and independent numerical comparison. R5 should implement static material/geometry cache separation and measure amortized warm/cold costs. Both can begin in CPU cloud; native/GPU/Cherchi acceptance requires the user's local environment and formally admitted teacher data.
