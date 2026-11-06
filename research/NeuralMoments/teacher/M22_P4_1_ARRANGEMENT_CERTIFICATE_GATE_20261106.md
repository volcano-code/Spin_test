# W2 M22-P4.1 — exact arrangement certificate gate (framework only)

**Date:** 2026-11-06  
**Parent W2 HEAD:** `d75412b42708c1b07bc159e4c0f0649aaba9c30a`  
**Branch:** `research/neuralmoments-w2-teacher-20261019`

## Delivered

Added:
- `m22_p4_arrangement_certificate.py`
- `test_m22_p4_arrangement_certificate.py`

The verifier uses exact rational arithmetic and fails closed on:
- missing or duplicate input parent IDs;
- missing or duplicate output-face IDs;
- missing arrangement cells;
- zero-area cells or non-rational coordinates;
- per-parent exact area gaps;
- selected cells without output-face references;
- excluded cells carrying output references;
- ambiguous cell classifications;
- incorrect global selected/excluded area totals.

Cloud-side unit tests: **10/10 passed**, 0 failures, 0 skips (0.043 s).

## Critical scope limitation

This is **not** the global Boolean set-equality proof and it does not construct the arrangement. It validates the internal consistency of a supplied arrangement certificate. The producer still has to compute the complete exact triangle-intersection arrangement, prove that its cells cover each parent triangle without overlap/gaps, classify every open cell against both operands, and tile every selected cell with the output faces.

No real Heart arrangement certificate has been generated. No Cherchi call was run. No existing M22-P3 result is upgraded by this framework-only milestone.

## Next implementation

M22-P4.2 must build a deterministic exact rational arrangement producer:
1. For each Design and QuadricSource triangle pair, compute exact coplanar overlap or non-coplanar segment intersection.
2. Split each parent triangle by all incident intersection segments into planar cells.
3. Canonicalize cell polygons and establish exact disjointness plus area conservation.
4. Classify one exact rational witness in each open cell against the other solid.
5. Match output triangles to selected cells and prove exact coverage with no overlap.
6. Emit the certificate consumed by the verifier.

The current cloud environment can develop and test the producer on synthetic and small real subsets. Full production arrangement construction may require local execution because the pairwise arrangement can be substantially larger than the existing surface-intersection audit.

## Scientific status retained

- M22-P3 three-surface exact self-intersection checks remain passed.
- Face provenance, two-scale local side probes, input-face-centroid checks and 4,096 Sobol probes remain finite consistency evidence.
- Global Boolean set equality remains **NOT CERTIFIED**.
- Full M21 same-call serialized material object remains unrecovered.
- `J_D=null`, `split=excluded`, training samples = 0.
