# W4 P14 — Cherchi-only shaft/cavity nonmanifold junction experiment

**Scope:** Exclusive W4 P1 files plus the single W4-specific GitHub Actions workflow already authorized. The immutable original P0/P1, P9/P11 native materials, historical failures, W0/W2 and main branches are untouched.

## Real failure that motivates the experiment

Authentic original GitHub Actions run [39446111126](https://github.com/volcano-code/Spin_test/actions/runs/39446111126), Cherchi reference native commit \`7bd6c2697695f555f9a15d7e154e084d841316f0\`, artifact \`12276067191\`:

- Input reference D sphere: 162 vertices / 320 triangles, SHA256 \`2fee98a34bf26cc536eb424f1013520c87abed05a9af2e439f934e7e5acba5cd\`.
- Protected shaft: 258 vertices / 512 triangles, SHA256 \`65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0\`.
- Cherchi \`M ∪ shaft\`: 3,793 vertices / 7,586 triangles, **watertight**, but **28 very small triangles** (area ≤1e-14) remain; SHA256 \`f3ac662e0d3c175b30a2cbcc6f1efd04785ad9d599d5ca666d7ea44b39718db5\`.
- Cherchi \`D − shaft\`: **native exit 0 does not imply legal material**. Its saved OBJ is 324 vertices / 806 triangles, 162 triple-incidence edges, 8 tiny triangles, 4 indexed components, \`is_volume=false\`; SHA256 \`855d7819f7ccbbb2cb05ccf9c18ab7ac6a1e6eca1456dd231967c3f9a48e30c0\`.
- Independent geometric localization across all abnormal edge midpoints: shaft radial distance **0.059708–0.060000** reconstructed source units, z range **0.4795–0.86044**. This strongly implicates the D/shaft intersection curve, not the Teapot body exterior. It is **not yet a proof** of the exact degeneracy mechanism.

## What P14 actually tests

The new \`p14_cherchi_junction_grid.py\` sources its inputs **only** from the frozen actual P13 GitHub artifact and fails on any SHA mismatch. It does not rely on a fresh P9 rerun, which has been unstable across runners.

It creates 11 input D hypotheses from exact copies of the archived closed sphere:

| Experiment family | Explicit hypotheses |
|---|---|
| Negative control | original D, unchanged |
| Mesh azimuth | D rotated 1.5° and 7.0° about its centroid |
| Center translation | x +0.002, x +0.008, y +0.008, xy (+0.012, −0.008), x +0.020 |
| Combined case | x +0.012 and azimuth +7.0° |
| Radius-only perturbation | scale factors 0.99 and 1.01 |

All lengths are **reconstructed model units, not approved metres or millimetres**; a hard max translation 0.03 and radius bounds [0.98,1.02] apply. Original D, fixed shaft and authenticated Cherchi whole-body union are never changed.

For each case:

1. Save a uniquely hashed D input and calculate the geometric clearance to the immutable outer boundary.
2. Execute **real Cherchi native \`D_variant − shaft\`**, record argv identity, exit code, stdout/stderr and output hash.
3. Independently check exact indexed edge incidence, near-zero triangle areas, winding, \`is_volume\`, components and conservative nonincident triangle SAT.
4. If the result passes, prove the candidate excludes the spindle core and retains off-axis removable volume.
5. Execute **real Cherchi native \`F_eff=(M∪shaft)−D_eff\`** and independently check the saved retained boundary.
6. Check that the shaft core is fixed/retained, and the 10 ordinary W0-style unit-density raw moments obey \`r_outer−r_F−r_D=0\` within predeclared absolute \`5e−7\`.

Any failure is recorded by variant in \`p14-junction-native-study.json\`. A native process return code 0 is never a geometry pass. A complete series with no valid outcome deliberately exits nonzero, leaving negative evidence in the always-uploaded GitHub artifact. **There is no CGAL fallback.** Even when two native Booleans pass, candidate status is \`NOT_W0_APPROVED\` and no Faster optimization/training, real CAD equivalence, physical shaft approval or printability is granted.

## Actual local-first checks and next cloud execution

P14 independent source-geometry regressions ran **10/10 PASS** on the real frozen P13 byte archive, using Python 3 / NumPy / Trimesh. They include 162-edge failure-locus reproduction, frozen SHA identity, original D/shaft/outer closedness, 11 bounded source-preserving variants, rotation/scale-volume invariance, adversarial tamper and false native exit=0, plus exact analytic tetrahedral W0-order raw-ten moments. These checks do not execute the native Cherchi solver.

The authorized W4 workflow now has an \`if: always()\` P14 step following the historical P13 negative native result; it downloads the immutable artifact from Run 39446111126 and reuses the already-compiled Cherchi 2022 binary on GitHub's Ubuntu runner. No extra parallel high-memory builds are added. The study's new native status **must be read from the new workflow run**, never inferred from the local 10 tests.

## Scientific next decision

- If any **numerically legal** whole F/D candidate passes: freeze the actual source/output hashes and request independent exact material certification and W0 physical contact/shaft/designed-domain authorization. Any altered D is **an explicit source deviation**, not reproduction of original CAD.
- If every case fails: isolate native intersection classification/triangulation of the shaft-crossing loops at the actual 162 triple edges; inspect Cherchi arrangement labels and exact implicit-point classes on the original input. Do not silently swap in CGAL or invent an inertia tensor.

## P14 first cloud replay: authenticated indexing difference, not geometric drift

[GitHub Actions Run 39459463702](https://github.com/volcano-code/Spin_test/actions/runs/39459463702) completed with failure **before executing P14's 11 native variants**: the cross-run download step reported \`Bad credentials\`. Therefore the P14 local archive tests were skipped on that runner, and no new material result may be claimed. P12 and actual MuJoCo regression jobs passed; native P13 again generated the familiar invalid \`D − shaft\` output.

However the same run emitted the full fresh P13 native output in its *own* artifact. Comparing the actual previous run 39446111126 and new run 39459463702 showed:

| Mesh | historical raw SHA | new raw SHA | sorted **exact binary64** vertex coordinates | oriented per-triangle coordinates |
|---|---|---|---|---|
| \`M∪shaft\` | \`f3ac662e0d3c175b30a2cbcc6f1efd04785ad9d599d5ca666d7ea44b39718db5\` | \`5fdebdc2514b02f0bf7acabc67355a77eab3657c58cdadfe4d85f501942225da\` | **IDENTICAL** | **IDENTICAL** |
| \`D−shaft\` (invalid) | \`855d7819f7ccbbb2cb05ccf9c18ab7ac6a1e6eca1456dd231967c3f9a48e30c0\` | \`faa48b1bf03573dcf9b0ce772ef89ac66d5ce45ebb1d889335d238d88e0bfbd8\` | **IDENTICAL** | **IDENTICAL** |

The difference is output vertex indexing / face serialization order. **It must not be characterized as random geometric drift.** The new P14 gate uses two complementary identities:

1. Strict original bytewise SHA for the D and shaft inputs, and for *each current native output versus its same-call native receipt*, with pinned native source commit and original M input.
2. SHA256 of a canonical multiset of exact binary64 vertex-coordinate tuples and *oriented* face-coordinate triples, normalized only for vertex/face reordering and cyclic triangle corner shifts — never winding reversal.

The historical canonical geometry SHA256 are:

- Outer \`def3bd6f93214d5fce36c7b58547e6afb730fc454fd0b9e001a9087ef005bd20\`
- Invalid D/shaft subtraction \`9760dff5a6ab6e37a7ec3eac21e7523ab123cfb9d270e285b7c96071279597f3\`

They match **both** independently downloaded native outputs exactly. A new adversarial unit test checks that arbitrary vertex reindexing / triangle ordering preserves canonical identity, whereas changing an oriented face does not.

The P14 workflow now consumes the **fresh P13 same-run outputs** after their native CLI and independent provenance checks, so it does not need cross-run artifact read permissions. On *any* geometry mismatch it still fails closed and never supplies a bogus authorized F/D or optimized Teapot.
