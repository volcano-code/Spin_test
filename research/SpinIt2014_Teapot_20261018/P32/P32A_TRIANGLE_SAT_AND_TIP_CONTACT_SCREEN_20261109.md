# W4 P32-A — nonincident triangle SAT screen and shaft contact interpretation
Date: 2026-11-09
Repository: volcano-code/Spin_test
Branch: research/neuralmoments-w4-teapot-p1-20261019
Inputs are the immutable P19 OBJ blobs listed in P31-B/P31-C. No source mesh was changed.

## Method
- Triangulate each OBJ face as a fan (the inspected P19 source faces are triangular).
- Build triangle AABBs and sweep candidates along x; reject disjoint y/z intervals.
- For remaining pairs, apply a floating-point triangle separating-axis test using both triangle normals, all 9 edge-cross-edge axes, and in-plane edge-normal axes for coplanar cases.
- For same-mesh self-tests, exclude triangle pairs sharing any indexed vertex (incident pairs are expected to touch).
- Numerical tolerance: 1e-11 times axis norm for projection interval separation; axes below 1e-14 norm are ignored.
- This is a custom floating-point screening implementation, not an exact predicate or a certified robust mesh kernel.

## Candidate and screen results
| Test | AABB candidate pairs | Nonincident pairs passed to SAT | SAT intersections |
|---|---:|---:|---:|
| M self | 60,993 | 10,160 | 0 |
| D self | 3,018 | 439 | 0 |
| S self | 4,324 | 580 | 0 |
| M vs D | 0 | 0 | 0 |
| D vs S | 0 | 0 | 0 |
| M vs S | 6,580 | 6,578 | 2,144 |

M-vs-S SAT intersections were further classified:
- 1,120 pairs involve an M or S triangle entirely on the common top plane z=1.71;
- 1,024 pairs involve both triangles incident geometrically to the common apex [0,0,0];
- 0 other pairs.

Thus the observed M/S contacts are localized to the registered top cap plane and bottom tip apex. No additional SAT intersection away from these two contact loci was found by this screen. This supports interpreting S as a protected internal shaft/reference whose endpoints meet the body's top and tip, rather than as a separately added mass component. It still does not prove exact containment or acceptable contact stress.

## Shaft tip/contact geometry
The S mesh has a single apex vertex at [0,0,0]. Its near-tip profile expands to radius 0.025 reference at z=0.025 reference. Under the provisional 0.025 m/reference mapping:
- first 0.025 reference length = 0.625 mm;
- the 0.025 reference radius = 0.625 mm;
- the idealized contact apex remains a point, not a finite contact pad.

The current P20 `support_points=[]` therefore remains a physical-design gap. The tip's mesh apex is not, by itself, a fully specified support/contact model. W0 must decide whether to retain a point-like tip as an idealized diagnostic, or redesign a finite-radius/flat contact pad and regenerate/freeze the physical geometry. Any change must create new geometry hashes and a new preregistration; do not edit frozen P19/P20 inputs in place.

## Interpretation and gate
- P32-A custom SAT screen: **0 nonincident self-intersection candidates for M, D, S**; no M-D or D-S AABB-overlap candidates.
- M-S contacts: confined by this screen to top plane and bottom apex.
- Exact/robust no-self-intersection and solid containment: **NOT CERTIFIED**.
- Shaft inclusion/no-double-counting: strong sampled and contact-localization evidence, still awaiting W0 robust set proof.
- Finite contact patch/support design: **NOT FROZEN**.
- W0 physical approval: **MISSING**.
- W2 Teapot teacher approval: **MISSING**.
- P30-B Cherchi native calls: **0**.
- Optimization, Newton, training, printability and MuJoCo optimized before/after: **NOT ADMITTED / NOT EXECUTED**.

## Required W0 decisions
1. Re-run this screen with an independent robust kernel (self-intersections, M/D containment, S-in-F containment, coincident top-cap and apex contact handling).
2. Approve or redesign the point apex/contact pad; define the support plane, contact patch, friction/contact parameters and load case.
3. Confirm shaft S is a protected reference already accounted for in F and not separately added to raw mass moments.
4. Freeze physical dimensions, material properties and spin/load envelope before issuing a diagnostic-only W0 receipt.

## Reproducibility
The exact source OBJ blobs remain:
- M: `e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e`
- D: `9820f3d73d15a4cdd0c504a0264f934aefd40df1`
- S: `9fe9f78257c7a90970095f6bb54c5148198a33d1`

The algorithm and tolerances above are fully described so the screen can be independently reproduced. This report is a diagnostic result, not a formal geometric certificate.
