# W4 P28: archived formal-M6 evidence review (2026-11-07)

## Decision and scope

**PASS — byte-bound formal M6 receipt and independent exact-arithmetic archive replay. NOT a scientific release.**

This review used the user-supplied `P27_FORMAL_M6_EVIDENCE.tar.gz` as the immutable input. A standalone Python checker in a separate cloud runtime implemented the documented P21 file, source/Boolean, winding, exact tetrahedral-moment, stage and Jacobian-byte contracts. **It did not execute the repository's original `p21_replay_verify.py` executable**. Do not conflate the matching outcome string with an actual run of that original script. No Cherchi/native extension was imported or run during this review. A separate final run of the original verifier can provide another independent implementation check; it is not represented as already done here.

The review checks consistency of a real formal-M6 *runtime receipt*, preserved operation artifacts, and independently recomputed exact moments. It does not reexecute CGAL native set predicates, independently attest the build's binary origin, prove Jacobian numerical correctness, certify a smooth derivative neighborhood, or authorize W0/W2, Newton, training, optimization, or MuJoCo physical admission.

## Evidence binding

- Uploaded archive SHA-256: `6827a0951ce8201e4bea5585ba4e2b485b4652c830604b06592e5a0146583e89`.
- Run: `formal-m6-20261106T091202Z/formal-m6-run-20261107T050117Z`.
- Outer manifest SHA-256: `3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773`.
- Pre-registered P27 lock SHA-256: `451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4`.
- All 37 manifest file hashes/sizes match. No missing or unexpected regular files in the submitted archive; tar paths are canonical and neither symlinks nor hardlinks.
- W0 commit: `5bab2eb2616df306906a6887a273f68acfa49320`.
- Source snapshot digest: `291aa2dd1f9ca7e471722b8ef76d1e43e2047837067f9acca175f053b7d087cd`.
- Formal wrapper: `W4_P20_M6_RUNTIME_V1`; child worker: `W4_P20_M6_WORKER_V1`; native geometry evidence: `W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1`.
- Formal status: `REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE`.
- Formal code 0, `native_audit_invoked=true`, `native_full_partition_certified=true`, `source_files_unchanged=true`, collection completed with zero errors.
- Archived P21 execution wall time: 101.1352 s; actual child runtime: 100.9141 s. Host physical RAM: 60.434 GiB; effective memory: 24 GiB; swap: zero. Resource policy was accepted both in wrapper and child.

## Same-call source, Boolean and capture

The archived 38 ordered stage events and nested artifact SHA-256 values were replayed:

- Source generation: 1 completed.
- Cherchi Boolean: 2 completed, using frozen `cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0`.
- Derivative: 1 completed.
- Moment integration: 2 completed.
- Intersection-motion / retained-material serialization: 1 each.
- Same-call stage ordering and factory-fresh initial call counts were checked.
- Retained and cavity packets have 356 vertices / 712 triangles and 156 vertices / 312 triangles, respectively.
- Source has 42 vertices / 80 triangles.
- Retained exact vertex tokens, reconstructed winding, physical/target transformations and stored source/geometry hashes match.

## Exact R10 replay and Jacobian bytes

Independently rebuilt the closed oriented surfaces and recomputed all 10 raw signed tetrahedral moments using `fractions.Fraction`. These are exact arithmetic checks on the represented archived geometry, **not** replacement native set proofs.

- Exact `D - R - C = 0` for all ten raw moments.
- Exact `M - F - R - C = 0` for all ten raw moments.
- Archived W2 exact-math R10 reference matches the recomputed retained moments; its independent Cherchi Boolean and smooth-Jacobian proof fields are still **false**.
- Binary64 conversion max absolute error: retained 0, cavity 0, fixed `1.8041124150158794e-16`, combined `1.8041124150158794e-16` (within the recorded P21 comparison tolerance).
- The same-call 10x10 Jacobian is 800 bytes; all 100 IEEE754 binary64 entries match the saved material matrix **byte-for-byte**.
- Jacobian capture SHA-256: `26cf3b5dd53d45a4b80f14319b39d28fa9ef7b8d8be3a915189e90ba077a08a5`.
- This is **identity of a single-point captured matrix**, not correctness, differentiability on an open neighborhood, Newton eligibility, or optimization convergence.
- Three byte-bound native set-predicate receipts (`fixed_plus_design`, `design_cut`, `full_outer`) all report complete exact partitions without positive-volume overlap. Their digest parent-child relationships were verified against the archived original partition digest. Native set predicates were **not reexecuted** in the cloud replay.

## Independent negative controls

Two independent synthetic mutations were applied to temporary copies; the authentic evidence remained untouched:

1. Change one Jacobian artifact byte without updating hashes: rejected at `FILE_HASH_MISMATCH:capture/000006-derivative-001.f64le`.
2. Change that byte while updating capture event SHA, capture manifest SHA, outer file SHA and the *test harness's* external-manifest input: rejected at the deeper `SAME_CALL_100_JACOBIAN_BYTES` contract.

Both negative controls passed (in the sense of correctly rejecting corrupted evidence).

## Reproducibility status

- Standalone P28 checker result: `ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT`.
- Cloud checker source SHA-256: `48a078de655231cb88315a42f4f6d856b8de94f63c0d6502997fb6ab0602989f`.
- Cloud result JSON SHA-256: `2581532e0d0c51f79573693ca1746670cd271a15a33330a670081912b67330b4`.
- Negative-control JSON SHA-256: `717f9af7b731d59d94656615bd0faca278753d5d05465d88014ea8646b656b00`.

The raw archive and the checker/report generated in the cloud session remain user-downloadable conversation artifacts, not public GitHub source files. This GitHub report records provenance and the review decision without uploading user machine paths, heavy native logs, or raw captured geometry to a public repository.

## Next scientific gates

1. Ask W0 to independently adopt the *physical* Teapot material/tip/density case and its constraints. The current original-evidence field remains `BLOCKED_UNKNOWN` and physical parameters are a proposal, not independently approved.
2. Obtain an independent W2 teacher/native Boolean proof, then evaluate derivative neighborhood and branch stability at and around the formal seed. The one-point 10x10 Jacobian has no smooth-neighborhood certificate.
3. Only after those owner and derivative gates: run genuine Newton optimization, three separate objectives (inertia, lowering COM, reducing mass), independent exact material checks for final objects, and matched-initial-condition MuJoCo before/after comparisons.
4. Preserve immutable P27 evidence and the previously registered lock. There is no reason to rerun the expensive formal M6 unless a reviewer identifies a concrete missing receipt or different seed.
