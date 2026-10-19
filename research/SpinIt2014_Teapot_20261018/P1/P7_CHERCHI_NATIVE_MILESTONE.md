# W4 P7 — real Cherchi 2022 reference union for public Utah Teapot

## Scientific intent

P2 is a CGAL diagnostic. P7 exercises **original Cherchi source** from `gcherchi/InteractiveAndRobustMeshBooleans` at frozen SHA `7bd6c2697695f555f9a15d7e154e084d841316f0`. This repository's original `main.cpp` explicitly supports `union` on multiple meshes. W4's existing Python pybind Boolean adapter did not expose union, so this experiment compiles the upstream original **CLI** rather than modifying shared code or falling back to CGAL.

This is a geometry *starting solid reconstruction* experiment only: no Spin-It/Spin-It Faster optimization, fixed F / removable D, author-exact Teapot CAD, proof of exact rational exported boundary, W0-approved tip/axis/scale or W2 certified teacher are claimed. An upstream Cherchi CLI OBJ contains floating point coordinates and requires independent topology and moment audits.

## Input and output contracts

Original OBJ: P0 SHA256 `1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4`. P1 topology-only OBJ SHA256 `3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47`. Source P1 is split without alteration into three independently closed input components (face counts 4,800, 840, 840).

Only the fixed Cherchi `main.cpp` blob `3f65d2a0f83b10629f99ed5dcd2781409cdca4b5` may be compiled, with no substitution. The original CLI takes `union input-body.obj input-handle.obj input-spout.obj out.obj` and computes a variadic Cherchi union in one real native call. The runner saves binary SHA256, source SHA, process stdout/stderr, generated OBJ, independent float SAT, oriented/watertight volume, and ten raw unit-density moments from two distinct integrations.

On native failure or malformed geometry, P7 commits no green marker: persisted `p7-cherchi-native-receipt.json` retains `FAILED_NATIVE_OR_GEOMETRY_GATE` and source diagnostics. A PASS at this level certifies only **numerical geometry preflight**; an exact mesh oracle still requires original rational constructions or native exact set equality.

## Actual tests and CI

Local Python 3.13.5 / NumPy 2.3.5 / Trimesh 4.11.1:

```bash
python -m unittest -v test_p7_cherchi_reference
# 6 tests PASS, 0 failures, ~0.3 s
```

Tests cover frozen Teapot components, SHA tamper rejection, missing native hard failure without fallback, wrong executable identity rejection, positive tetrahedral moment crosscheck, open-mesh rejection and timeout bounds. Native Cherchi compilation is **not** possible in the isolated local container because the pinned upstream source and compiled extension are absent; the GitHub Actions job added to the previously user-authorized `.github/workflows/w4-teapot-mujoco.yml` does the actual pinned clone/build/native solve and uploads logs/results on success *or* failure.

The native job is serial after the MuJoCo diagnostic job, limited to two build threads and 45 minutes, with a 240-second Boolean timeout. No changes to main or other windows.

## Future gates

1. Independently compare Cherchi generated solid to frozen CGAL diagnostic as **verification only**, without hiding topology failures; reconstruct exact representation where feasible.
2. Request W0 Teapot-specific physical case dimensions, spin axis/tip, density, F/D identities. W0 M9 and W2 M8 real H8 archives do not by themselves authorize Teapot optimizations.
3. Use actual Cherchi subtraction to produce sealed carved volume and fixed material, verify saved `r_F+r_D`, print constraints and legitimate derivatives, then use the already running MuJoCo cloud workflow to compare *actually different* material geometries with identical dynamics conditions.
