# W4 P31-D — provisional SI envelope derived from frozen P19 meshes
Date: 2026-11-09
Repository: volcano-code/Spin_test
Branch: research/neuralmoments-w4-teapot-p1-20261019
Purpose: engineering envelope estimate for the user-selected new Utah-Teapot-inspired spinning-top test article. This is conditional arithmetic, not W0 physical approval.

## Frozen input identities
- M OBJ blob SHA1: `e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e`.
- F OBJ blob SHA1: `180c3ade7c939008b90fa1aaabe82653047b2e6c`.
- D OBJ blob SHA1: `9820f3d73d15a4cdd0c504a0264f934aefd40df1`.
- S OBJ blob SHA1: `9fe9f78257c7a90970095f6bb54c5148198a33d1`.

## Conditional unit conversion
User selected provisional values:
- length: 0.025 m per P19 reference unit;
- density: 1200 kg/m^3.

P19 M bounding box:
- x: [-1.1980, 1.3736], span 2.5716 reference = **64.29 mm**;
- y: [-0.8, 0.8], span 1.6 reference = **40.00 mm**;
- z: [0, 1.71], span 1.71 reference = **42.75 mm**.

The resulting provisional outer bounding dimensions are therefore approximately **64.29 × 40.00 × 42.75 mm**. This is a bounding box, not a CAD envelope with manufacturing clearances or support geometry.

## Signed-volume and mass estimates
The P31-B signed mesh volumes were:
- M = 1.6596798579703191 reference^3;
- D = 0.026406299068153116 reference^3;
- F = M-D = 1.633273558902166 reference^3.

At the provisional density and scale, mass per reference cubic unit is:
`1200 × 0.025^3 = 0.01875 kg/reference^3`.

| Region | Signed volume (reference^3) | Conditional mass |
|---|---:|---:|
| M whole outer body | 1.6596798579703191 | 31.1190 g |
| F retained material M-D | 1.633273558902166 | 30.6239 g |
| D design/cavity region | 0.026406299068153116 | 0.4951 g |

D is about 1.59% of M's signed volume. These are geometric density-based estimates only; no print-process, infill, porosity, material anisotropy or manufacturing allowance has been included.

S reference shaft volume from its oriented mesh is approximately 0.01841220069030338 reference^3, corresponding to 0.3452 g if treated as a separate solid at the same density/scale. **Do not add this 0.3452 g to F** unless W0 determines that S is a separate physical component. P20 currently describes S as protected material already included in F; P31-C supplies sampled evidence that its surface lies in the closure of M\D, but robust containment/fusion remains for W0 to certify.

## Engineering implications
1. A 64.29 mm × 40 mm × 42.75 mm bounding envelope is compatible with a small tabletop test article, but it does not establish stability, safe rotational speed, printable minimum wall or strength.
2. The P20 local carve-wall threshold of 1/32 reference unit converts to **0.78125 mm** under the provisional scale. The source contract explicitly limits this to a local newly-carved-boundary check; it is not a global wall-thickness or strength guarantee.
3. No support/contact geometry is registered in P20 (`support_points=[]`). W0 must define the actual tip and contact patch/support geometry before a physical stability or MuJoCo claim.
4. No safe spin-speed limit can be inferred without material properties, shaft dimensions/attachment, load cases and a structural safety criterion.
5. The report's native coordinate frame is normalized by the P20 bbox-L transform. The proposed 25 mm/reference conversion is an external physical mapping and must not be confused with the internal normalization used for native Cherchi coefficients/Jc.

## Gate
- Conditional dimensional and mass arithmetic: **PASS**.
- Physical scale/density/material approval: **NOT APPROVED**.
- Support/contact/load case: **MISSING**.
- Global wall/strength/printability: **NOT CERTIFIED**.
- W0 physical owner receipt: **MISSING**.
- W2 Teapot teacher receipt: **MISSING**.
- P30-B native Cherchi calls: **0**.
- Optimization, Newton, training and MuJoCo before/after: **NOT ADMITTED / NOT EXECUTED**.

## Next decision needed from W0
W0 should review the conditional dimensions/mass and explicitly approve, revise or reject the physical unit mapping; define tip/support/contact and load cases; and certify the shaft semantics. W0 must not interpret these derived estimates as measured material properties or a validated print.
