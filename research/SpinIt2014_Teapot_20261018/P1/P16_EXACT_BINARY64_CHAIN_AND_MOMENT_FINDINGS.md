# W4 P16 — Exact binary64 chain/moment audit of real Cherchi P14/P15

**Outcome:** Exact signed raw-ten-moment additivity of saved IEEE-754 triangle meshes is demonstrated. **Strict original-vs-micro-weld solid equality is disproved by a nonzero exact signed volume delta.** No original Cherchi implicit rational certificate, W0 authorization, printability, training clearance, Faster optimization, or optimized MuJoCo conclusion is implied.

## Authenticated artifacts, immutable

- Real native Cherchi P14 GitHub Actions [run 39462578208](https://github.com/volcano-code/Spin_test/actions/runs/39462578208); original native archive `12283931537`; P14 report SHA256 `11485d0659ca9933205179de1c968f42e7c27dfaf0ca77a8c28c96125b60ad72`. Historical 11-variant result remains **negative**; none of the native material candidates may be called accepted.
- Actual independent float64 P15 GitHub Actions [run 39555122736](https://github.com/volcano-code/Spin_test/actions/runs/39555122736); verified postprocessing artifact `12324993228`; P15 report SHA256 `0e2d48e40efe5110512b3929a3b90718e1b65b5382a11494e5d6bba473193a56`. P15 commit `ac03b316d2e49cee585d762cf80d11633d03c2a1`.
- Fixed original Cherchi upstream revision: `7bd6c2697695f555f9a15d7e154e084d841316f0`; no CGAL or other geometry solver is run by P16. Both archived source hashes and the original `F` native same-call receipts are enforced.

## New P16 exact arithmetic finding

Unlike P15's approximate moment tolerance, `p16_exact_binary64_chain.py` independently parses each **saved OBJ vertex** to a binary64 value, converts that exact binary value to Python `Fraction`, and integrates all oriented faces using the **exact** tetrahedral formulas for W0 ordinary undoubled moment order:

`M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY`.

It computes the exact signed outer source minus postprocessed outer:

`ΔV = 3727329694084957988057560810167920790317082511 / 842498333348457493583344221469363458551160763204392890034487820288`

which equals approximately **+4.424138952620733e-21 original reconstructed model-volume units**. This rational value is **nonzero**. The outer native and its float64 micro-weld therefore cannot be claimed strictly volume-identical as serialized binary64 solids, even though the change is tiny and P15 floating-point volume appears unchanged. This is an exact *counterexample* to overclaiming the numerical weld as a mathematically identical solid.

**Cancellation discovery:** across each of the three native P14 Cherchi cases, the exact signed triangle 2-chain change caused by micro-welding the exterior is **identical** to the signed 2-chain change caused by micro-welding retained material F. Only 14 disjoint near-coincident vertex pairs and 28 documented inherited sliver triangles were touched. The change chain has **90 noncancelled oriented triangle terms**. As a result, the exact signed tetrahedral *ten-component* deltas of original-outer minus cleaned-outer and native-F minus cleaned-F match **exactly**, component by component — not with a numerical tolerance.

Moreover, for the **saved binary64 triangular surfaces only**:

| Real P14 D variant | `r(M_native)-r(F_native)-r(D_native)` | `r(M_weld)-r(F_weld)-r(D_native)` | formal oriented triangular chain residual terms |
|---|---|---|---:|
| D rotated 1.5 degrees | ten components **exactly zero** | ten components **exactly zero** | 1,280 |
| D translated Y +0.008 reconstructed units | ten components **exactly zero** | ten components **exactly zero** | 1,248 |
| D translated X +0.012/Y −0.008 reconstructed units | ten components **exactly zero** | ten components **exactly zero** | 1,248 |

These **nonzero formal chain residuals** are carried unchanged by micro-welding. They do **not** in isolation prove inconsistent continuous solid regions, because differently triangulated coplanar boundaries can yield different oriented triangle multisets. They do establish that a triangle-by-triangle boundary-chain identity has NOT been demonstrated. A robust exact common refinement/native rational point classification is necessary for a true exact Boolean set/chain certificate.

Critically, `Fraction.from_float` is exact for the *already serialized binary64 coordinates*, **not** necessarily for the native Cherchi implicit exact rational intersection vertices. Exact moment cancellation proves one family of boundary-integral identities, **not** full region equality or a physical F/D design admission.

## Actual tests and cloud replay

The local real-archive suite `python -m unittest -v test_p16_exact_binary64_chain` ran **11/11 PASS** (24.132 s) using source archives from original GitHub Actions. It includes an exact analytic tetrahedron, ordinary undoubled cross moments, non-decimal IEEE-754 sanity, cyclic orientation vs reverse, invalid OBJ rejection, full real exact P14/P15 replay, exact nonzero rational witness, all-three identical change chains, all-ten exact cancellation, immutable file identities and tamper rejection.

The independent GitHub Actions P16 job requires both specific historical GitHub artifact runs, checks their frozen reports and face-source hashes, executes the same 11 tests and the exact-Fraction replay, then uploads the P16 JSON report. **Its run outcome is separate from the existing P13/P14 failing native job.** Until that specific CI job finishes, do not claim a GitHub Actions P16 PASS.

## Next scientific milestone

P17 should extract the native Cherchi **implicit exact rational point** identities and arrangement classifications of the 14 near-coincident pairs, then construct an exact common boundary refinement or a native constrained retriangulation/Boolean preserving geometric set identities. Its acceptance must demonstrate genuine exact F/D Boolean equality, authorized spindle/wall constraints and W0 Teapot case parameters **before** any Faster three-objective optimization or an actual optimized-before/after MuJoCo video.

Scientific flags P16 always keeps false: `full_set_equality_original_vs_microweld`, `native_implicit_point_exact_identity_certified`, `W0_physical_tip_or_FD_approved`, `W2_teacher_training_allowed`, `Faster_optimization_executed`, `MuJoCo_real_optimized_before_after_executed`.
