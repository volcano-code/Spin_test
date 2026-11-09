# M29.3.2.1 — partial-column audit of the completed 72-call finite-difference run

## Observed results from the host log

- 72/72 fresh native function evaluations completed.
- At h=1e-6, 6/9 directions have both sides matching the frozen M9 feature-branch hash.
- At h=1e-5, 3/9 directions have both sides matching the frozen M9 feature-branch hash.
- At h=1e-4 and h=1e-3, 0/9 directions have both sides matching the frozen M9 feature-branch hash.
- Across all 72 samples, operation is Difference, source surface is ELLIPSOID, and cap count is zero.
- 46/72 sample topology hashes differ from the M9 anchor.
- Geometry hashes differ between plus/minus samples even when topology matches; this is expected for a changing geometry and is not itself a branch-change criterion.

## Interpretation

The first six directions at 1e-6 and directions 0, 1, and 4 at 1e-5 contain branch-stable central-difference pairs under the current frozen feature fingerprint. The original M29.3.2 runner discarded partial columns when fewer than all nine directions were valid at a step. The companion offline auditor now preserves and compares those valid columns instead of throwing away useful measurements.

The existing receipts do not include separate hashes for source-face identity and output feature-face identity. Therefore a topology-hash mismatch cannot yet be attributed to source-normal-edge identity, construction-point correspondence, source-face set, or oriented output feature triangles. The fact that operation, surface type and cap count remain constant does not prove that the full discrete feature branch is unchanged.

## Next required action

Run the offline partial-column auditor against the already completed M29.3.2 files. This uses no Cherchi calls. Inspect per-direction derivative errors and cross-step refinement. Based on those results, decide whether a narrowly scoped diagnostic native run is warranted to record the missing fingerprint components.

## Certification status

- Fresh native samples: completed.
- Full 9-column Jacobian FD at all four step sizes: not achieved.
- Partial FD columns: available for offline audit.
- Formal derivative admission: false.
- Newton admission: false.
- Full solver speedup: null.
