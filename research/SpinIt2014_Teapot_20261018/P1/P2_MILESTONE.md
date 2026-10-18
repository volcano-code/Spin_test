# W4 P2 — actual CGAL union, independent material geometry and moments

**Status:** finite-precision tessellated repair `GEOMETRY_PREFLIGHT_PASS`; Teapot is **not yet optimization-ready**. The original input, P1 candidate and other windows remain untouched.

## Input identities and dependency

- P0 public Newell Teapot OBJ SHA256 `1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4`, Git blob `c839837bfc09f5d5bac4aa757fcbd9f16ddd7ec1`; P0 audit workflow #39126326305. Not the Spin-It 2014 author's exact Teapot CAD.
- P1 topology-only OBJ SHA256 `3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47`; P1 had 3 closed but intersecting components.
- P2 code rejects a changed P0/P1 SHA256 and never edits their input files.
- Native environment tested: Python 3.13.5, NumPy 2.3.5, Trimesh 4.11.1, OpenSCAD 2021.01 CGAL/Nef. Binary STL triangulation and SHA256 may differ with other compiler/OpenSCAD versions; review numerical evidence, do not accept a SHA mismatch silently.

## Reproduce from a clean checkout

Run from repository root:

```bash
python -m pip install 'numpy>=2,<3' 'trimesh>=4,<5'
# Install OpenSCAD with a CGAL-enabled binary separately: `openscad --version`
P1=research/SpinIt2014_Teapot_20261018/P1
python "$P1/p2_cgal_union.py" \
    --source research/SpinIt2014_Teapot_20261018/input/teapot-public-original.obj \
    --candidate "$P1/teapot-topology-candidate-p1.obj" \
    --output "$P1/p2-output"
python -m unittest discover -v -s "$P1" -p 'test_p2_*.py'
```

Outputs after running the script (generated, not all stored as Git blobs): `p2-native-cgal-union.stl`, `p2-teapot-cgal-union-y-up.obj`, `p2-teapot-cgal-union-z-up.obj`, `p2-cgal-union-audit.json`. The audited report is committed under `P1/p2-output/`, alongside this README and the native/test receipts. **Remote GitHub source contains the deterministic generator and audit, not the large regenerated OBJ/STL meshes.** To obtain the full mesh, run the command or use the separately shared current-turn output archive.

Revalidate a saved local result without rerunning CGAL (emits a different receipt and never overwrites the native one):

```bash
python "$P1/p2_cgal_union.py" --source research/SpinIt2014_Teapot_20261018/input/teapot-public-original.obj --candidate "$P1/teapot-topology-candidate-p1.obj" --output "$P1/p2-output" --verify-existing
```

To enforce the **optimization** gate, add `--require-optimization-ready`; it MUST fail closed with `OPTIMIZATION_BLOCKED` until the W0/W2/F-D prerequisites are genuinely satisfied.

## Actual P2 result

- CGAL Nef `Simple: yes`, `Volumes: 2` (ambient exterior + one filled interior); native union ~1.7s, returned exit code 0.
- Numerically reloaded mesh: **3328 vertices, 6656 triangles**, one connected component, genus 1 (`Euler=0`), closed/winding consistent, positive volume, `is_volume=True`; no degenerate faces or nonmanifold edges.
- Independent float64 nonincident triangle SAT after sweep and AABB: **7236 tested pairs, 0 witnesses**. SAT excludes faces sharing vertices, and it is a conservative finite-precision preflight, not an exact arithmetic self-intersection theorem. CGAL `Simple: yes` is a separate native check.
- Unit-density raw-frame volume `25.848771634269497`, COM `(0.02086632040336674, 1.2518337519824232, -3.2999918355563985e-06)`; union overlap correction versus P1 sum: `-0.16615927976285505` (`-0.638707365%`). P1 original/open-surface pseudovolume is not a physical volume or mass conservation reference.
- Ten **raw** density-1 moments follow the W0 ordering `M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY`; cross-products are not doubled. Independent tetrahedral and Trimesh mass-properties moment oracles agree to `6.40e-14` maximum absolute error. Proper Y-up to proposed Z-up rotation preserves transformed mass moments to `7.11e-15`.
- Output SHA-256: Y-up OBJ `8aab36275b137296bc5f1f61ac71fe164d677f7a49829a4aa6b7b2da2e3beba5`; Z-up OBJ `d3289193185192ebca4d63fc813bd77d96810051089c672e887accdf3205b331`; native STL `53d962b0b6bb468cd0988ea92a20832bfe8834aa6a065eee544f5fdc4b23de67`.

## Acceptance boundary

`numerical_mesh_geometry_gate=PASS` **does not imply** paper-matched shape, strict exact-rational exported tessellation, required printability thickness, or physical optimization correctness. W0's mathematical interface exists, but no W0-approved **Teapot-specific** scale, spin tip/axis, density or fixed-shell/shaft (`F`) and carveable-domain (`D`) declaration has been issued. W2 teacher manifest is adapter-smoke-only and has zero authenticated live Cherchi samples. The three Fig. 9 studies (inertia-only, lower-COM-only, mass reduction) remain **NOT RUN**. Do not invent final F/D or submit misleading moment targets.

Next work: obtain an explicit case design frame and dimensioned physical contract from W0; construct independent F and D solids via certified Boolean partition, reject overlap and preserve complete shell/thickness, then reread and verify `r_total=r_F+r_D`, and only then admit W2 real Cherchi/native learning and optimization.
