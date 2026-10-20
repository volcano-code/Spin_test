# W4 P10/P11 — actual executed Cherchi material partition milestone (2026-10-20)

**Real Actions:** [Run 39403411538](https://github.com/volcano-code/Spin_test/actions/runs/39403411538), **conclusion SUCCESS**, source commit `192c9b4d28e3a3be073df2111098e018130e723e`. Full archived native material artifact: ID `12255852225`, name `W4-P7-real-Cherchi-reference-geometry-or-failure-not-optimized`, ZIP SHA-256 `fa7fb9939ae3be2bc245ea3736a15a79962ab9796c22463d9274db5a8c768983`.

The old historical [P9 native Cherchi run 39362437035](https://github.com/volcano-code/Spin_test/actions/runs/39362437035) was authentic and successful. Its P9 Y-up OBJ SHA256 `154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4` and manifest SHA256 `14eea8e8bdb58b91d5602d5fa8079743ad0be4dbc5b4c69c444f2e7a8a0ced9c` were re-authenticated through GitHub Actions artifact retrieval. A *new run* of P9 on 39402670170 failed a numerical topology gate for the precursor union; this negative reproducibility evidence is **not overwritten or represented as success**.

## P10 — independent material source validation

Actual run 39403411538 executed all 7 P10/P11 preflight tests (0 failures). The saved native P9 material was independently reread and checked as a **closed single indexed surface** with 3,331 vertices, 6,662 triangles, volume `25.84789083533902` in **unscaled unknown units**. Exact Python `Fraction` integration of the *saved OBJ decimal coordinates* recomputed 10 standard raw unit-density moments, maximum floating projection difference `9.947598300641403e-14` versus P9 saved production values. Re-read coordinate-frame conversion Y-up to proposed Z-up preserved full inertia. This is NOT a certificate of original implicit Cherchi exact-point geometry.

P10 report SHA256 `8068a2690030b97e0a929fe7b49c766a47cb12c7c4b94086b04385b62ce07800`; proposed Z-up saved OBJ SHA256 `23fd0611a311d08a2e20a948db47c42cbdcabe4389dfe2ede66d8a49a6dc20f3`.

## P11 — **actual new Cherchi native subtraction**, not a mock

One experimental interior candidate `D_trial` is a 162-vertex, 320-triangle sphere, center `(0,1.3,0)` and radius `0.5` in *source Y-up coordinates*. The independent numerical solid-angle inside test was 1.0 and center-to-boundary minimum distance was `1.2999794784256715`, leaving sphere-to-outer-surface clearance `0.7999794784256715` unknown units.

Original fixed-version Cherchi CLI executed `subtraction` `F_trial=M-D_trial` and **returned zero** after `0.032957524999972065` seconds. The saved F and D were independently reread after downloading the actual Actions artifact; both are watertight, oriented and positive-volume. F has **two boundary components** because it encloses a separate inner cavity surface. This is compatible with one connected physical remaining material region, not a disconnected material-solid claim.

| Saved OBJ | SHA256 | vertices | faces | signed unit volume |
|---|---|---:|---:|---:|
| M source (actual P9 Cherchi) | `154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4` | 3331 | 6662 | 25.84789083533902 |
| F trial (new Cherchi subtraction) | `22593c5ab3b5f6ee786f2d17ce15f3beae16fcb09589dce2314d1615b3f115ba` | 3493 | 6982 | 25.342010248532205 |
| D test sphere | `4cc61b54939fe9c9acdfe9e956af24f2a411d6016acd83fd32d46722749a99b9` | 162 | 320 | 0.5058805868068139 |

True native **10-moment residual** `max_abs(r_M - r_F - r_D) = 4.873879078104437e-14`, against predeclared absolute tolerance `5e-7`. The D test accounts for 1.9571% of M unit-density volume; it is not an achieved topology optimization.

Full P11 independent audit JSON SHA256 `798ee3092487a4797a427e9a36dad11791f21835b897235c25f4b6518aee404f`. Native production F and D remain in the named GitHub Actions artifact; the commit contains source and externally anchored evidence, not fabricated file blobs.

## Scientific admission and next handoff

`material_partition_approved=false`, `W0_fixed_F_removable_D_authorized=false`, `W2_Teapot_teacher_admitted=false`, `original_author_CAD_exact=false`, `printability_wall_thickness_verified=false`, `SpinIt_optimization_performed=false`. Under no circumstances should P10/P11 be described as the completed paper Fig. 9 optimization.

**Next required work:** W0 Teapot-specific metric scale/density and physically correct tip/axis, shell and shaft; candidate carveable region construction with collision/wall-thickness guarantee and appropriate manufacturing constraints; independently verify exact native Boolean material/identity where available; only then execute real Cherchi/Faster geometry-dependent moment optimization and send *two distinct saved materials* to MuJoCo for same-condition A/B. Also independently investigate why fresh P9 native reconstruction is unstable across cloud runs; frozen archive avoids falsely assuming repeatability but does not resolve it.
