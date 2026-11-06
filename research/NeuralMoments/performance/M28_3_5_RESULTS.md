# W1 M28.3.5 — batch exact cut-parent coverage audit

Date: 2026-11-06  
Branch: `research/neuralmoments-w1-native-20261019`  
Input archive SHA-256: `0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976`

## Results actually executed

- Exact cut-face discovery replayed from frozen physical design/source inputs.
- Cut parent counts: eval 4 = 416 design + 1 source; eval 116 = 560 design + 8 source; eval 117 = 562 design + 8 source.
- Restartable cut-cell coverage batches completed for all three evaluations.
- **1,555 unique cut-parent receipts** produced and SHA-256 verified.
- Every receipt has exact missing area = 0, extra area = 0, overlap area = 0; exact expected-kept area equals actual saved-output coverage.
- Total saved output triangles accounted on cut parents: **3,908**.
- Re-running a completed batch reports zero newly completed receipts.

| Eval | Operation | Parent faces | Output triangles | Arrangement cells | Result |
|---|---|---:|---:|---:|---|
| 4 | Intersection | 417 | 1,039 | 2,700 | 417/417 pass |
| 116 | Difference | 568 | 1,432 | 2,984 | 568/568 pass |
| 117 | Difference | 570 | 1,437 | 2,994 | 570/570 pass |

## Important limitations

This is a **cut-parent-face area coverage audit**, not yet a proof of global Boolean boundary completeness. It does not certify all uncut input faces, all isolated components, 3D boundary adjacency/orientation across parent-face seams, or additional closed output components not mapped to an input parent. Membership uses the saved exact solid classifier, not a fresh native Cherchi run.

No new Boolean or Newton call was made. Production native ten-moment equality, full 10x10 Jacobian, smooth-neighborhood certification, Newton convergence, W0/W2 admission and full A/B/B/A performance remain unverified. `production_admitted=false`; `full_solver_speedup=null`.

## Next

M28.3.6: audit uncut parent faces and global output-to-input coverage, verify seam adjacency and connected components, then compare the full output face inventory to all theoretically retained input patches.

All M28.3.5 code and saved-evidence audits ran in the cloud. No local operation is needed for M28.3.6. Production Cherchi moments/Jacobian, full Newton and final performance remain local/pinned-native tasks.
