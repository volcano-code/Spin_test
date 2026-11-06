# W2 M22-P4 — Frozen Heart global Boolean set-equivalence audit

**Date:** 2026-11-06  
**Branch:** `research/neuralmoments-w2-teacher-20261019`  
**M21 run:** `heart-pilot9-flex-20261105T083338329274558-3159689`

## Verdict

**PASS — the exact arrangement certificate independently replays and establishes the global regularized Boolean boundary equivalence for the frozen H8f point-000 Design/QuadricSource operands and the M21-matched output boundary:**

`O = D \\ Q`

This is a geometric set-semantics result for this frozen reconstructed model and this exact point. It is not a claim that the missing full M21 same-call serialized material object or native shared libraries have been recovered. It is not a derivative/Jacobian/Newton or training-admission result.

## Evidence identity

| Evidence | SHA-256 |
|---|---|
| H8f original Actions artifact | `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9` |
| M21 raw evidence archive | `259b9f288b629415bafa42e4e09d6503e4f474e0e2253e6cc9eb1cd775a64dfd` |
| Frozen prepared request | `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c` |
| H8f point-000 compressed member | `c372f749bf7b85015e2dcdad4a445aeab4f2f6fbd25d622089ec58d471992973` |
| M21 frozen spec | `4d3cb03ee3a1190142638a99cd90e6aaf0a3e7030b956ef813ebabeb0c6898d0` |
| M21 label | `747101c819d95959020a39ea54eec5af280fd465b786c3f94312bb7447136729` |
| M21 result | `f84b38c326bc4fd79068d5a89f94500bb60306c5a77289a550a278355dd89dc3` |
| M21 matched exact output boundary | `48aae36777ed15e705f1ab919edac07756d3a7444100c060ee5baabd310afe20` |

The M21 request and native coefficient vector match the frozen H8f request and point-000 coefficient vector. The M21 `r_D`, geometry hash, topology hash and exact output-boundary digest match the historical point-000 record. The historical full material SHA and evaluation-map identity do **not** match the M21 same-call descriptor; that provenance gap remains explicitly open.

## Exact operand intersection arrangement

- Design: 26,244 triangles.
- QuadricSource: 320 triangles.
- Total possible triangle pairs: 8,398,080.
- Exact binary64 AABB broad-phase candidates: **7,711**.
- Exact rational narrow-phase results: **6,927 disjoint**, **784 segment intersections**, **0 point-only contacts**, **0 coplanar pairs**.
- The stored 784 exact segments were independently recomputed from the pinned operands and matched exactly.

Every intersection segment is included in both incident parent-face arrangements. Every parent face is subdivided by its exact operand-intersection segments and output-triangle edges. The independent verifier checks the exact planar half-edge cell complex: no crossing/overlap, paired internal edges, complete parent-boundary coverage, and exact parent-face area partition.

## Cell classification and output coverage

An independent C++/GMP exact rational ray classifier replayed **28,528** arrangement-cell witnesses:

- Design parent cells: 27,378.
- QuadricSource parent cells: 1,150.
- Exact ray candidate triangle tests: 734,777.
- Exact ray hits: 24,370.
- Ambiguous rays: 0.
- Membership mismatches: **0**.

The C++ ray sample input was regenerated from the pinned cell ledger; the regenerated ray output is byte-identical to the recorded replay log. Replay result: `ALL_EXACT_MEMBERSHIP_MATCH`.

All **16,910** output triangles have exactly one input-parent assignment and the correct orientation:

- 16,034 Design-parent faces preserve Design orientation.
- 876 QuadricSource-parent faces reverse QuadricSource orientation.
- Unmatched or multiply assigned output faces: 0.

For every arrangement cell, independently classified expected membership equals output membership. Exact area accounting is equal per parent and globally: every selected cell is covered by output faces, excluded cells have no output coverage, every output edge is present in its parent arrangement, and every operand-intersection segment is covered by both incident parent arrangements.

## Independent exact volume identity

The selected boundary cells on Design-inside-QuadricSource and QuadricSource-inside-Design form the boundary of the intersection. Their exact signed-volume integral satisfies:

`V(D ∩ Q) = V(D) − V(O)`

with exact rational equality (not a tolerance comparison).

| Quantity | Binary64 display |
|---|---:|
| `V(Design)` | 1.0998850071299318 |
| `V(QuadricSource)` | 1.3881363252327446 |
| `V(Output)` | 0.4638104336177978 |
| `V(Design ∩ QuadricSource)` | 0.6360745735121340 |
| `V(Design) − V(Output)` | 0.6360745735121340 |

The QuadricSource total volume is larger than Design because it extends outside Design; subtracting the whole QuadricSource volume would be incorrect.

## Independent verifier result

`verify_m22_p4_certificate.py` completed successfully with:

`PASS_EXACT_ARRANGEMENT_CERTIFICATE_REPLAY_GLOBAL_REGULARIZED_BOOLEAN_BOUNDARY_EQUIVALENCE`

It independently rechecked the operand triangle intersections, output parent map and orientations, every arrangement-cell sample against the other operand using the separate C++/GMP ray replay, planar cell-complex partition, output edge/segment coverage, exact area accounting and exact volume identity.

The synthetic P4 test suite plus real frozen-archive binding test passed **7/7**, 0 failures, 0 skips.

## Execution note

A fresh full rerun of the Python producer exceeded the 300-second execution window while processing the Design faces. That incomplete producer rerun is **not** counted as the successful proof. The PASS verdict above comes from the SHA-pinned intersection-segment, arrangement-cell and output-parent certificates, followed by the completed independent verifier replay and byte-identical C++/GMP ray replay. The full producer source and exact evidence package are retained for reproduction.

## Scientific limits retained

- The H8f frozen geometry is a paper-inspired reconstructed CAD, not author-original CAD.
- The M21 same-call serialized material payload and original native shared objects remain unrecovered; historical material/evaluation-map identity differs even though request, coefficient vector, output boundary digest, geometry/topology hashes and physical moments match.
- The original H8f 81-point workflow conclusion remains `failure`; this point-level geometry proof does not rewrite it.
- `J_D=null`; derivative status remains unknown; `split=excluded`; training samples remain 0.
- No new Cherchi call was made in M22-P4.
- W0/W3 continuous-neighborhood and full 10×10 Jacobian admission, Newton acceptance, and Noodles V7 six-packet F/D/A reconstruction remain outstanding.

**Conclusion:** M22-P4 closes the global Boolean set-semantics gap for the frozen Heart point-000 geometry. It does not close W2's dual-model teacher, derivative, Newton, provenance, or training goals.
