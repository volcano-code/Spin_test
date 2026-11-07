# W4 P29 — W0/W2 scientific admission read-only handoff

**Status:** `P29_BLOCKED_OWNER_PHYSICAL_AND_TEACHER_DERIVATIVE_NEWTON`

## Work performed

This milestone did actual branch-scoped work, rather than just a plan:

- Added `p29_scientific_admission_gate.py`, a strict read-only pinned-source checker.
- Added `test_p29_scientific_admission_gate.py`, 15 regressions including real checkouts of current W0 and W2 fixed SHA versions and adversarial fake admission flags.
- Added `.github/workflows/w4-p29-scientific-admission.yml` to run standard-library-only tests and save a machine-readable `P29_SCIENTIFIC_GATE.json` CI artifact.
- Fixed an initial Python test syntax error; the failed run is preserved. Final successful run: https://github.com/volcano-code/Spin_test/actions/runs/42353652554
- CI: 15/15 tests passed, 0 skipped. Audit's deliberate exit 3 (BLOCKED) is verified by the workflow. No native calls, training or optimization occurred.
- Submitted formal W0/W2 handoff issues: [W0 Owner/physical #5](https://github.com/volcano-code/Spin_test/issues/5), [W2 Teacher/neighborhood #6](https://github.com/volcano-code/Spin_test/issues/6).

## Frozen evidence reviewed

| Source | Fixed identity |
|---|---|
| W4 P27 single-point formal M6 run | `formal-m6-run-20261107T050117Z` |
| P27 formal manifest SHA-256 | `3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773` |
| P27 independent pre-run lock SHA-256 | `451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4` |
| W4 P28 original evidence status | `ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT` |
| W0 contract commit | `5bab2eb2616df306906a6887a273f68acfa49320` |
| W2 Teacher commit | `64f7c491fff8efca6f8dc1d4f12871c677a0ec02` |
| W2 manifest Git blob | `05968ded975532422d52327011768833f087afec` |
| P20 Teapot request SHA-256 | `a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9` |

W4 P28 independently replayed exact archived moments, source/Boolean attachments, and same-call 100 Jacobian bytes. It did **not** run the original `p21_replay_verify.py` executable, reexecute native set predicates or verify Jacobian numerical correctness over an open neighborhood.

## W0 physical review — MUST remain blocked

Current W4 P20 Teapot is a **frozen nonoptimized single-point material-partition probe**:
- nominal reference-to-SI length `0.025 m/unit`;
- density `1200 kg/m³`;
- provisional axis `+Z`, tip `(0,0,0)`, `support_points=[]`;
- fixed shaft already counted in F (not counted again);
- `minimum_outer_wall_reference=1/32` is a limited probe, **not** whole-object printability/structural certification;
- original author CAD, physical validation and W0 Owner adoption all explicitly false.

The older P12 physical *diagnostic* used a different reference scale / density (15 cm and 1240 kg/m³) and a 0.25 kg demonstration video; these must not be merged with the P20 P27 physical case. Independent physical dimensions, actual contact tip/shaft, valid printable F/D, and full mass/COM/inertia objective limits must be formally approved or replaced by W0 before optimization claims.

## W2 Teacher/neighborhood review — MUST remain blocked

The latest reviewed W2 manifest has `native_teacher_runs=1` for a **Heart** diagnostic, `training_samples=0`, empty train/val/test, and the latest Heart `J_D=null`, `split=excluded`. W2's later independent exact Heart point-000 Boolean/arrangement review is genuine progress for that **Heart** case but does not create a matching Teapot Teacher label or a smooth-neighborhood certificate.

The Teapot one-point 10×10 `J_c` byte identity, raw10 arithmetic and three native set-predicate receipts do not prove open-neighborhood derivative continuity, independent numerical Jacobian correctness, Newton terminal or training admissibility.

## Explicit next work

1. **Cloud, W4-owned:** preserve this P29 baseline and add the original `p21_replay_verify.py` execution against a pinned copy of P27 evidence for another independent software crosscheck (current P28 is the standalone reimplementation).
2. **Cloud, W0 owner:** review exact Teapot physical case, shaft/real contact tip, density/scale, feasible printability and constraints; issue an explicit W0 decision tied to request and formal M6 SHA. Do not flip approval via a W4 field.
3. **Cloud, W2 teacher:** independently review same Teapot material/source/Boolean/physical moments and 10x10 Jacobian provenance. Heart and Noodles labels cannot be substituted.
4. **Qualified native host, only when newly necessary:** collect new ±h, ±h/2 tangent and neighboring feature-branch packets at the *same* Teapot c, with independent W0/W2/W3 review. This may use the existing 20+ GiB/swap0 local host, not an extra cloud server.
5. **After independent releases:** run Newton terminal and three separate Teapot objectives, certify final material and export matched-initial-condition before/after MuJoCo comparisons.

The known P27 M6 run **must not be repeated** merely to satisfy these checklists; it is a valid frozen base geometry receipt. No production training/optimization authorization is implied by this document, code or CI pass.

## Boundaries

- This is W4-owned code and documentation only, on W4's separate research branch.
- No main, W0 branch, W2 branch, original CAD, or P27 pre-run lock was modified.
- `scientific_admission=false`, `training_admissible=false`, `Newton_accepted=false` until separately reviewed owner and teacher receipts.
