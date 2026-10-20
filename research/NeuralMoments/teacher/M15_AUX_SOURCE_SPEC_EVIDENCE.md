# W2 M15 supplemental frozen Heart source-to-request materialization

This file records the additional W2-only M15 source conversion work that was
submitted in parallel with the main `M15_EVIDENCE.md` dual-case campaign.
**The dual-case campaign remains the primary M15 evidence**. No existing M15
report, original H8f result, main branch or other W branch was overwritten.

## Executed source/model audit

- Historic actual GitHub Actions H8f artifact 12135528290, ZIP SHA256
  `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`,
  original workflow conclusion **failure**.
- Re-read the original `initial_top.obj`, 15,646 vertices and 31,288
  ordered triangles, source SHA256
  `fbada64691e30b458bc5b5375f8d4ad351cb0b383d800512bb659077b29532f6`.
- Verified exact binary64 `v_mm / 25 == request.outer_vertices` (zero
  vertex mismatch), and exact face-index/order match; every directed triangle
  edge has one oppositely directed pair. This is not native Boolean certification.
- From the real frozen request generated a derived normalized OBJ and a
  `w2-one-cherchi-request-v3` spec with the original native c and original
  native module SHA. Local derived OBJ SHA256:
  `59ca43758f62bf2cbb700a08e6e1e7ac4a5e6b43f5a06efc5e637b950f68448f`.
  This is the *local supplemental generator's* output SHA, not the separate
  main M15 campaign's normalized OBJ SHA.
- Attempted to import the true `make_it_stand.verification.cherchi_inprocess`
  module in the current execution environment. Result:
  `ModuleNotFoundError: No module named 'make_it_stand'`, recorded as
  `FAILED_PREFLIGHT`; **zero** new native evaluations, zero training admission.
- The GitHub W2 frozen Noodles V7 finite-sample summary reports 81 historical
  finite points and maximum FD error `5.536038294451373e-11`, but explicitly
  has `neighborhood_certification=false` and `case_admission=false`.
  The necessary original frozen source request/material files were not present
  at their cited GitHub paths, so the independent gate returns
  `BLOCKED_MISSING_FROZEN_DATA`. The later *optimized output* cannot
  substitute for original fixed/design input.

## Added W2 files and local checks

- `m15_real_heart_spec.py`: simple SHA-pinned, source-derived Heart v3 spec
  generator. Run via `python research/NeuralMoments/teacher/m15_real_heart_spec.py
  --archive REAL_H8F.zip --output NEW_DIR` (a fresh directory only).
- `m15_noodles_readiness.py`: conservative frozen Noodles source gate.
- `test_m15_real_native_launch.py`: real archived Heart input and drift checks
  plus Noodles readiness negative cases.
- `M15_REAL_NATIVE_ADMISSION_EVIDENCE.json`: observed local source,
  preflight and case-admission state.

A separate local development implementation was actually run:
`python -m unittest -v test_m15_real_native_launch.py test_noodles_gate.py`,
**12/12 passed** in 1.888 seconds, no skip/fail. It uses the genuine H8f ZIP.
The local scripts and newly committed supplemental script are **not byte-identical**;
do not treat these local checks as CI for the exact GitHub files. In particular,
the main W2 campaign has its own independent tests and evidence as described in
`M15_EVIDENCE.md`.

Current sandbox lacks compiled Cherchi and the agreed 24 GiB effective memory
profile. The main dual-case campaign therefore correctly reports a blocked
native execution rather than claiming a fabricated success. Formal Jacobian
teacher labels remain **zero**.
