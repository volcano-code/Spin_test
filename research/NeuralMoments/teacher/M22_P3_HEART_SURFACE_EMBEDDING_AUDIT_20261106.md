# W2 M22-P3 · Heart operand and output embedded-surface audit

**Date:** 2026-11-06  
**Branch:** `research/neuralmoments-w2-teacher-20261019`  
**M21 run:** `heart-pilot9-flex-20261105T083338329274558-3159689`

## Result

**PASS — exact self-intersection checks on all three surfaces:** the Design operand, the Cherchi QuadricSource operand, and the historical point-000 Boolean output. All three have positive exact signed volume and passed the pinned W1 M26 GMP checker. This closes the previous M22-P3 blocker that the Design input embedding had not been independently checked.

**NOT CLAIMED — global Boolean set equality.** The three surfaces being individually embedded does not prove that the output is exactly `Design \\ QuadricSource`. The prior local side probes, parent-face centroid coverage, and 4,096 Sobol points are strong finite checks, but the exact arrangement-cell coverage proof remains pending.

## Source binding

- H8f Actions artifact SHA-256: `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`.
- M21 raw evidence archive SHA-256: `259b9f288b629415bafa42e4e09d6503e4f474e0e2253e6cc9eb1cd775a64dfd`.
- Frozen `prepared-request.json` SHA-256: `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`.
- Historical point-000 member SHA-256: `c372f749bf7b85015e2dcdad4a445aeab4f2f6fbd25d622089ec58d471992973`.
- M21 Spec request object equals the historical prepared request object.
- M26 checker source is pinned to W1 commit `249db334303b31b8b8c2cfcb415b21a7cc2c9464`, SHA-256 `2536f7783ff6552ac930c294879e69b8430fc8e527873859b3ec1187d39c6ea0`; it was rebuilt in the audit container using GMP and Boost.Geometry.
- All binary64 operand coordinates are converted to their exact IEEE-754 rational values before entering the checker; output coordinates are retained as their saved exact rational strings.

## Exact surface results

| Surface | Vertices | Faces | Exact candidate pairs | Non-adjacent pairs | Result |
|---|---:|---:|---:|---:|---|
| Design operand | 13,122 | 26,244 | 218,939 | 60,772 | PASS |
| QuadricSource operand | 162 | 320 | 1,986 | 96 | PASS |
| Boolean output | 8,455 | 16,910 | 161,702 | 49,727 | PASS |

All candidate pairs were checked with exact GMP predicates. No illegal self-intersections were detected. The three signed exact volumes are positive.

## Exact signed-volume accounting

| Surface | Signed volume (binary64 display) |
|---|---:|
| Design | 1.0998850071299318 |
| QuadricSource | 1.3881363252327446 |
| Boolean output | 0.4638104336177978 |
| Design minus output (removed portion) | 0.6360745735121340 |

The full exact rational values are retained in the machine-readable local audit output; the output-volume fraction SHA-256 is `a57a86b3791e89327be5c4e7c08e4a7a97f4f0e4adb4d28b7173d6bec6fa3a53` (4,578 characters). The QuadricSource's total volume is larger than Design's because it extends outside Design; subtracting the whole QuadricSource volume from Design volume would be mathematically incorrect. Volume accounting alone does not certify the intersection volume or set equality.

## Reproduction

Committed source: `m22_p3_audit_heart_operands.py`  
Tests: `test_m22_p3_audit_heart_operands.py`

Run from the W2 teacher directory with the two pinned archives and pinned M26 source available:

```bash
python m22_p3_audit_heart_operands.py \\
  --h8f-zip /path/to/H8f_all81_original_artifact.zip \\
  --m21-tar /path/to/M21_HEART_NATIVE_EVIDENCE_20261105.tar.gz \\
  --m26-source /path/to/m26_exact_intersection.cpp \\
  --output /new/path/M22_P3_HEART_SURFACE_EMBEDDING_AUDIT.json \\
  --timeout 600
```

Cloud/local execution record: 7/7 regression tests passed. The three real surface checks completed in approximately 9.74 s (Design), 0.10 s (QuadricSource), and 9.79 s (output), excluding build time. No Cherchi call was made.

## Remaining blockers

1. Exact global Boolean set equality still needs arrangement-cell coverage or an independent exact Boolean backend comparison.
2. The M21 full same-call serialized material object and original native shared objects remain unrecovered; the historical canonical material digest and evaluation-map identity differ from M21 even though the boundary and ten moments match.
3. The H8f source is reconstructed/paper-inspired, not original author CAD.
4. W0/W3 continuous derivative neighborhood and full 10x10 Jacobian certification remain pending; `J_D=null`.
5. Newton convergence is not accepted; no training data are released.

**Verdict:** M22-P3 now certifies the embedded-surface property of both input operands and the output boundary. It still does not certify the complete Boolean set operation. Keep `split=excluded`, `J_D=null`, and training samples at zero.