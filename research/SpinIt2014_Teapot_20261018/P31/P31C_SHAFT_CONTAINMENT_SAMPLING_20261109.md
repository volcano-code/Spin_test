# W4 P31-C — protected shaft S containment sampling against M/D
Date: 2026-11-09
Repository: volcano-code/Spin_test
Read-only inputs: W4 P19 OBJ files on `research/neuralmoments-w4-teapot-p1-20261019`.
This is a follow-up to P31-B and refines its preliminary ray-parity result.

## Exact inputs
- M `P1/P19_material_case/material/M_native.obj`, Git blob SHA1 `e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e`.
- D `P1/P19_material_case/material/D_native.obj`, Git blob SHA1 `9820f3d73d15a4cdd0c504a0264f934aefd40df1`.
- S `P1/P19_material_case/source/shaft-reference.obj`, Git blob SHA1 `9fe9f78257c7a90970095f6bb54c5148198a33d1`.

## Why this follow-up was needed
P31-B reported 33/258 S vertices and 32/512 S face centroids as "outside" under a three-ray parity classifier against M. A nearest-triangle distance probe then found every one of those points lies on M's boundary to floating-point precision (maximum observed distance (1.39\times10^{-17}) reference units), all at z=1.71. These are boundary classifications, not evidence that S protrudes beyond M. The parity-only outside label was therefore too strong and is superseded here.

## Expanded deterministic sample test
For each of S's 512 triangular faces, test:
- its three vertices;
- its three edge midpoints;
- its face centroid.

Total: 3,584 sample points. Each point was classified against M and D using three non-axis-aligned ray directions, with a nearest-triangle boundary fallback at squared distance < (10^{-24}).

| Solid | Inside | Boundary | Outside | Ambiguous |
|---|---:|---:|---:|---:|
| M | 3,232 | 352 | 0 | 0 |
| D | 0 | 0 | 3,584 | 0 |

No sampled point was outside M or inside/on D. Thus the tested S surface samples lie in the closure of the M\D material region. The 352 M-boundary samples include the shaft's z=1.71 cap/edge samples.

## Interpretation
This is **strong sampled evidence** that S is a protected shaft reference lying in the retained material region F=M\D, with boundary contact at the upper end. It supports the P20 accounting rule that S must not be added as an extra independent material contribution if the owner confirms this is the intended protected-shaft semantics.

It is not yet a formal set-containment proof: finite point sampling does not exclude a narrow triangle excursion between samples, and this ray/nearest-triangle implementation is not an exact robust Boolean predicate. It also does not establish that S is physically fused/connected to the printed body or that contact stresses are acceptable.

## Required W0 closure
W0 should now review the corrected evidence and either:
1. certify S as a protected geometric reference wholly contained in the closure of F, with its top boundary coincident with M; or
2. reject that interpretation and require a revised shaft/material construction.

W0's independent exact/robust test should include triangle-triangle intersection and solid containment, including treatment of coincident top-cap faces. S must not be double-counted in mass moments.

## Gate status
- P31-C sampled S-in-M and S-outside-D check: **PASS, sampled only**.
- Exact/robust S-in-F set containment: **NOT CERTIFIED**.
- F/D boundary correspondence from P31-B: unchanged.
- M/F/D/S self-intersection: **NOT CERTIFIED**.
- W0 physical approval: **NOT ISSUED**.
- W2 Teapot teacher approval: **NOT ISSUED**.
- P30-B native Cherchi calls: **0**.
- Optimization, training, printability and MuJoCo before/after: **NOT ADMITTED / NOT EXECUTED**.

## Reproducibility
The input source blobs are identified above. The audit was run over the fetched OBJ triangle coordinates with deterministic parsing and three fixed ray directions. The boundary fallback threshold is explicitly numerical, not an exact predicate. No source mesh was modified, and no native Cherchi, CGAL Nef or other robust solid kernel was executed.
