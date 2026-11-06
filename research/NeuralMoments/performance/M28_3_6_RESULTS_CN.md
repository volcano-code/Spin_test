# W1 M28.3.6 — global parent-face inventory, output topology and seam audit

Date: 2026-11-06  
Repository: \`volcano-code/Spin_test\`  
Branch: \`research/neuralmoments-w1-native-20261019\`  
Base revision: \`e545d364bf76a0b8859840ea199f5a59165ec574\`  
Frozen input archive SHA-256: \`0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976\`

## Results actually executed

M28.3.6 reused all M28.3.5 cut-parent receipts and the per-parent uncut-face classification receipts. The original evidence ZIP manifest (33 entries) was rehashed before replay. Each output triangle was independently located on exactly one input parent triangle using exact plane hashing, an outward-rounded spatial broad phase, and exact rational containment.

Across evaluations 4, 116 and 117:

- **80,564 input parent faces** accounted for: 1,555 cut parents plus 79,009 uncut parents.
- All **33,176 saved output triangles** map to exactly one Design or Source parent face; zero unmapped, ambiguous, or dual-owned output triangles.
- All 1,555 cut-parent receipts have exact missing/extra/overlap area = 0 and agree with actual saved-output triangle area.
- All 79,009 uncut parent faces have exact expected-vs-actual area equality.
- Exact total surface area from all input-parent patches equals the exact area of each saved Boolean output.
- All output meshes have one connected component, Euler characteristic 2, no index-edge or geometric-edge incidence defects, no edge-orientation conflicts, no vertex-link defects, and no duplicate exact-coordinate vertices.
- Every one of **49,764 output edges** was seam-audited. Same-operand parent seams lie on the exact shared input edge; cross-operand seams lie on both exact parent triangles. No invalid seam was found.

## Per evaluation

| Eval | Operation | Input parents | Cut | Uncut | Output faces | Components | Euler | Invalid seams |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4 | Intersection | 26,812 | 417 | 26,395 | 10,312 | 1 | 2 | 0 |
| 116 | Difference | 26,876 | 568 | 26,308 | 11,432 | 1 | 2 | 0 |
| 117 | Difference | 26,876 | 570 | 26,306 | 11,432 | 1 | 2 | 0 |

## Empty evaluation 123

The saved Boolean packet remains strictly empty: vertices, exact vertices, faces and construction records are all empty. This stage did not re-prove solid containment or rerun the input-input exact intersection test; it records the frozen empty observation only.

## Scientific limits

This establishes global parent-face inventory coverage and topology/seam consistency **for the three saved nonempty Boolean outputs**, conditional on the frozen M28.3.5 cut-parent index and exact side-classification receipts. It is not yet an unconditional proof that no cut parent was omitted by the earlier conservative candidate-discovery filter, nor does it independently prove the 3D Boolean material domain.

\`global_boolean_completeness_certified=false\`; \`production_admitted=false\`. No new Cherchi Boolean, production-native ten moments, 10×10 Jacobian, smooth-neighborhood certificate, Newton convergence, W0/W2 admission, or full A/B/B/A speed test was performed. \`full_solver_speedup=null\`.

## Tests

M28.3.6 topology regression tests: **5/5 passed**.

## Local/cloud assessment

All M28.3.6 work used frozen saved evidence and ran in the cloud. No local operation is required for the next offline audit step. Production Cherchi moments/Jacobian, real Newton convergence and final A/B/B/A remain dependent on the pinned native environment.
