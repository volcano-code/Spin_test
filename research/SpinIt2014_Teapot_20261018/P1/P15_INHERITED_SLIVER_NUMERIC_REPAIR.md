# W4 P15 | Inherited native Cherchi slivers: exact-face audit and bounded numerical micro-weld

**Science class:** real saved Cherchi Boolean M∪shaft, D−shaft and F=(M∪shaft)−D from W4 P14 historical GitHub Actions [run 39462578208](https://github.com/volcano-code/Spin_test/actions/runs/39462578208), original native artifact `12283931537`. This is **not** a new native exact Cherchi material certificate or Spin-It/Faster optimization.

## Observed result and mechanism

The P14 source rejected all 11 native D variants; no candidate is retrospectively promoted to native PASS. Three of those trials (`rotate_1p5`, `translate_y_008`, `translate_xy_012_m008`) produced actual saved D meshes with no nonmanifold edges, positive volumes, preserved protected-shaft winding and no tiny triangles. Their native saved F meshes were oriented, watertight, positive-volume and had zero non-two-incidence edges, **but retained 28 sliver triangles** whose area was <=1e-14.

P15 independently compared the **oriented exact binary64 coordinate signature** of each of those 28 F slivers against the untouched actual native outer `M∪shaft` output. Every one of the 28 is inherited **byte-equivalent in vertex-coordinate meaning and face orientation** from the preexisting outer surface, not created by subtracting D. The 28 triangles contain exactly 14 disjoint pairs of vertices separated by at most `2.225860458774576e-16` in unapproved reference coordinates, and each pair occurs on precisely two inherited sliver faces.

## Deliberately bounded numerical postprocessing

`p15_inherited_sliver_repair.py` permits a maximum **1e-15 unapproved reference unit** representative-vertex change. It only collapses those 14 disjoint, source-verified pairs and removes the corresponding 28 explicitly known sliver triangles. It refuses novel close pairs, chains, removal of other faces, bad winding, new open edges, new tiny faces, non-volume meshes, SHA mismatches and a false claim of historical P14 native success. The original P13/P14 and real native OBJ files are neither edited nor replaced.

The outputs are **new numerical float64 mesh postprocessing candidates**, not the unmodified native Cherchi implicit rational surfaces. This makes a physically meaningful distinction: the native CSG stage passed numerical topology except for *inherited* tiny triangles; the postprocessing is bounded and auditable, but the *exact* implicit construction is not yet certified.

| Real P14 D hypothesis | Clean F vertices/faces | Inherited F slivers removed | Source-Boundary edge errors | Independent nonincident SAT witnesses | max abs r_outer-r_F-r_D |
|---|---:|---:|---:|---:|---:|
| D rotated 1.5 degrees | 4099 / 8198 | 28 | 0 | 0 | 1.7416623698807143e-15 |
| D translated +Y 0.008 | 4091 / 8182 | 28 | 0 | 0 | 6.036837696399289e-16 |
| D translated (+X 0.012, -Y 0.008) | 4091 / 8182 | 28 | 0 | 0 | 2.42861286636753e-16 |

Parent M∪shaft cleaned mesh: 3779 vertices / 7558 triangles; numeric preflight closed, consistent winding, strictly positive triangle areas, zero non-two-incidence edges and zero witnesses across **9447 nonincident AABB candidate pairs**. All three cleaned F and untouched native D separately passed exhaustive finite-float nonincident triangle SAT; the F bounding material retained **two closed oriented boundary components** (external and internal cavity).

All ten ordinary raw unit-density moments use W0 order `M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY`; cross-terms are NOT doubled. Full partition residual tolerance predeclared `1e-10` (all three << threshold). The postprocessing changes individual F raw-ten moments by at most `4.440892098500626e-16`. Output mesh SHA256 are frozen in `p15-inherited-sliver-study.json`, independent from the source native receipts.

## Executed tests and artifact

The actual downloaded original Actions ZIP was loaded in a local Python 3/NumPy/SciPy/Trimesh environment. `python -m unittest -v test_p15_inherited_sliver_repair` ran **8 tests, 8 passed (5.670s)**, covering original negative P14 identity, literal inherited sliver signatures, bounded cleanups, full independently checked native M/F/D arithmetic and self-contact, forged native receipt SHA rejection, winding-reversal rejection, unauthorized weld distance refusal, and an analytic tetrahedron.

GitHub Actions new **separate audit-only P15 job**, not depending on an upstream green native geometry result, downloads exactly the immutable P14 real native artifact from run `39462578208`, reruns these 8 tests and generates a distinct archive of the postprocessed candidates. It does NOT hide the negative 11-variant P14 output or convert it to a native Cherchi PASS.

## Scientific stop conditions

Always false: `original_CAD_shape_certified`, `exact_Cherchi_implicit_geometry_certified`, `W0_physical_tip_or_FD_approved`, `printable_wall_thickness_certified`, `SpinIt_Faster_optimization_executed`, `MuJoCo_before_after_optimization_run`. This is the **numerical micro-weld feasibility result**, not W0-approved protected shaft geometry, manufacturability, real differentiable derivatives, an actual optimized teapot, or a final before/after physical comparison.

Next independent geometry step: move this postprocessing into a separately reviewed native constrained triangulation / exact rational arrangement stage or prove exact-set equivalence across sliver collapse; obtain a W0 Teapot physical contract and printability constraints before official material optimization.
