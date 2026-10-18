# W4 P1 — Utah Teapot topology candidate (not a legal solid)

## Source and scope

- **Only** `research/neuralmoments-w4-teapot-p1-20261019` is written.
- Original OBJ is unchanged: `input/teapot-public-original.obj` (public Newell teapot, **not** author-exact Spin-It CAD).
- Upstream revision: `8a4f8642acaf43f9cd7b67858a1502e1055ef202`; upstream blob: `c839837bfc09f5d5bac4aa757fcbd9f16ddd7ec1`; SHA-256: `1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4`.
- P0 workflow #39126326305 had PASS for **input audit only**.

## Executable P1 smoke

Install `numpy>=2,<3` and `trimesh>=4,<5`.

```bash
cd research/SpinIt2014_Teapot_20261018
python -m unittest discover -v -s P1 -p 'test_*.py'
python P1/p1_geometry.py --input input/teapot-public-original.obj --output P1/reproduced
python P1/p1_geometry.py --input input/teapot-public-original.obj --output P1/reproduced-gated --require-certified  # EXPECTED FAILURE
```

The independent reload test asserts watertight indexed mesh and consistent winding; the program checks boundaries, bow-tie fans, signed tetrahedral moments and conservative triangle SAT contacts. It pins original bytes and rejects tampering.

## Checked result (local actual run, four tests PASS)

- Original 3,644 vertices / 6,320 faces; 3,241 exact unique positions; six loops of 40, 40, 20, 20, 20, 20 (160 open edges). One bow-tie contact at (-2, 0.9, 0).
- Connect the two coplanar 40-ring rims with 80 triangles; add 80 fan triangles to the four open ends; duplicate one pinched vertex **without displacement**.
- Diagnostic candidate: **3,246 vertices / 6,480 triangles**, zero indexed open/non-manifold edges, zero winding contradictions, zero residual bow-tie vertices, three connected closed components.
- Source open-surface pseudovolume 25.770106073456354; repaired candidate signed pseudovolume 26.014930914032348 (+0.24482484057599407, +0.9500%). **This is not a physically meaningful volume preservation guarantee:** open surface and intersecting components cannot certify material mass.
- Conservative contact scan produces at least 12 triangle-pair witnesses; point contact remains. No exact intersection/Boolean union certificate. **REPAIR BLOCKED: no legal solid and no valid F/D.**

## Scientific contract

The original mesh uses **Y-up**, unscaled dimensions and unknown physical units. Candidate proper rotation to Z-up: (x,y,z) -> (x,-z,y). This is only a coordinate proposal; **spin axis, tip, fixed shell/shaft F and removable material D are unset** pending W0. Do not equate flat base with tip. All mass moment values in `p1-diagnostic-moments.csv` are computed for *unit test density, original Y-up and an invalid candidate*; they are **not authoritative physical mass or inertia**.

Figure 9 ablations (inertia-only, center-lowering-only, mass-reduction-only) are registered but NOT RUN. Required next steps: exact/robust union and independent self-intersection-free solid check; W0 axis/tip/scaling/F-D contract; independent saved-material reread and moments; W2 real Cherchi teacher; only then run the three ablations and certify source CAD correspondence separately.

Generated files under `P1/` are fresh additions. All legacy P0, earlier CI failures and main stay untouched.
