# W4 P10–P11 | Independent Cherchi material seal and first genuine subtraction experiment

**Scope:** `volcano-code/Spin_test`, W4 research branch exclusively. No source P0/P1 modification, no cherry-picks/merge to main. Only W4 P1 files and the separately authorized W4 Actions workflow.

## Real input identity

- P0 public Utah Teapot original SHA256: `1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4`.
- P1 topologically repaired source SHA256: `3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47`.
- P9 native Cherchi source: pinned `gcherchi/InteractiveAndRobustMeshBooleans` commit `7bd6c2697695f555f9a15d7e154e084d841316f0`.
- The selected *intentionally modified handle* model comes from genuine GitHub Actions [39362437035](https://github.com/volcano-code/Spin_test/actions/runs/39362437035), artifact `12237748683`, file `cherchi-body-spout-handle-03.obj`. SHA256: `154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4`.
- Original-X-direction handle shift `+0.005` in **unscaled, physically undefined OBJ units**; 0.06094% of original model diagonal. It is not exact original CAD, nor a Spin-It-optimized material.

## P10: executable independent material baselining

`p10_cherchi_material_baseline.py` independently loads the *saved native Cherchi output*, pins input/native provenance, checks oriented edge incidence, bow-tie vertices, one connected surface, no nonincident triangle SAT witnesses, triangle area, positive volume, saved Y-up reread, and Z-up proper rotation of full inertia.

It then parses **all 3,331 saved decimal coordinates as Python Fractions**, integrates 6,662 faces by *exact rational signed tetrahedral formulas*, and checks the full `M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY` vector against the original P9 independent report. The local real-P9 run completed with maximum absolute discrepancy `9.947598300641403e-14`; unit-density volume `25.84789083533902`. It writes `p10-numeric-source-seal.json` and two Y-up/proposed-Z-up OBJ files.

**Proof boundary:** exact *decimal OBJ* moments are not an exact reconstruction of Cherchi's internal rational implicit-point geometry. This is `NUMERIC_CLOSED_DECIMAL_EXACT_MOMENTS_ONLY`, not an exact native material certificate, printability, or original author CAD equivalence.

## P11: experimental Cherchi-native partition feasibility

`p11_cherchi_partition_feasibility.py` proposes an enclosed test-only sphere `D_test` centered in original Y-up coordinates at `(0,1.3,0)`, radius `0.5` **source units**. Independent solid-angle winding (about 1.0) and minimum triangle-distance (about 1.29998) show a conservative sphere clearance `0.79998` source units to P9's saved outer surface. This is a mathematical geometry probe, **not** an authorized printable cavity or physical shell thickness.

The workflow uses the *same fixed Cherchi reference native executable* to run `F_trial = M - D_test` as genuine `subtraction`. It rejects nonzero native exit, missing F, open/degenerate/inconsistent F or D, nonincident float-contact evidence, and independent physical raw ten-moment mismatch. The necessary partition identity is `r(M)=r(F_trial)+r(D_test)` in the same original frame and unit density with the predeclared **5e-7 absolute** tolerance. All three saved OBJ identities are retained in GitHub Actions artifacts.

**Scientific limits:** even if this experiment passes, `material_partition_approved=false`, `W0_fixed_F_removable_D_authorized=false`, `SpinIt_optimization_performed=false`, and the current center/radius are not actual shaft/tip or shell. W0 must independently specify Teapot physical units, contact axis/tip, wall/shell and actual carveable D. W2's genuine archived Heart labels do not authorize Teapot derivatives.

## Local execution and CI

Python 3.13 / NumPy 2.x / Trimesh 4.x; actual P9 full artifact from GitHub. Local `python -m unittest -v test_p10_p11_material` executed **7/7 pass** (1.726 seconds). It covers real P9 seal, analytic exact tetrahedron, nonmanifold/boundary adversarial cases, hash tamper, enclosed D, analytic test sphere ten moments, and no-native abort.

The W4 user-authorized `.github/workflows/w4-teapot-mujoco.yml` invokes these same assertions after P9, then runs the **real native Cherchi subtraction**. P11 success/failure is only determined by that cloud run, not by local geometry smoke. Historical GitHub success/failure logs are preserved. On failure the `if: always()` artifact upload retains failure receipt, F (if any), and input D.
