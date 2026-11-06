# P27 pre-run lock review — 2026-11-06

## Decision

**BYTE-INTEGRITY REVIEW: PASS. RESOURCE-POLICY SNAPSHOT: PASS.**
The reviewed lock is accepted for one formal, non-optimized M6 material-partition audit only, subject to a fresh host-resource check immediately before execution.

This review does **not** grant W0 owner/physical approval, W2 teacher/training admission, derivative-neighborhood certification, Newton terminal certification, optimization admission, or physical validation.

## Reviewed artifact

- Review bundle: `P27_LOCK_REVIEW.tar.gz`
- Bundle SHA-256: `4e0d645832674b51af45356b89e75914f49f1385b145e72fd67316403c519238`
- Run directory: `formal-m6-20261106T091202Z`
- Lock schema: `W4_P21_M6_PRERUN_LOCK_V1`
- Lock created: `2026-11-06T09:24:02.811460+00:00`
- **Registered lock SHA-256: `451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4`**
- Lock byte length: 1,053,605
- SHA-256 in sidecar equals recomputed SHA-256 of the exact lock bytes.
- Canonical source-snapshot digest recomputes to `291aa2dd1f9ca7e471722b8ef76d1e43e2047837067f9acca175f053b7d087cd`.

## Identity checks

- W0 commit: `5bab2eb2616df306906a6887a273f68acfa49320`.
- W0 commit tree: `6804666121948ca7395f6ff62669ae2c0cf57231`; matches the lock snapshot.
- The W0 source snapshot contains 1,892 tracked source entries; the authoritative Git tree has the same 1,892 entries under the P21 source-file selection rule.
- All 11 critical W0 source blob pins in P20's launcher were checked against the fixed W0 commit; all match.
- All 77 Python source blobs registered by the P20 request match in both the fixed W0 tree and frozen Core tree.
- The seven critical W4 P20/P21 files (request, P20 launcher/factory, P21 replay/factory/capture/verifier) were independently SHA-256 checked against the current W4 branch and match the lock snapshot.
- The six registered P19 inputs (M, F, D, shaft reference, manifest, canonical report) match the P20 preparation report's input hashes.
- W0, Core, request, launcher, factory, P21 factory and pins identities are internally consistent.

## Native build and pins

Build report status: `BUILT_AND_IMPORT_VERIFIED_NO_GEOMETRY`.

- Build report SHA-256: `fef7da88a29ac0ff55e6e7f828a448e9953d5069b6586e9dc3bed3fa080b469b`.
- Core source: `58fd12c1306c1c01679a19172e2d76eef0cb30542`.
- Cherchi source: `7bd6c2697695f555f9a15d7e154e084d841316f0`.
- GMP: 6.3.0; MPFR: 4.2.1; GCC: 13.3.0; CMake: 3.31.6; Python: 3.12.3.
- Core, libigl, CGAL, Eigen and Cherchi checkout identities remained unchanged before/after the build; tracked files matched their commits.
- `_make_it_stand`: `30409c25260355e63e827486ca058067e2a6bd312ac7d2c809e2f74c7454e413`.
- `_cherchi_core_boolean`: `e6913eea1db74305a37b00b7fbb23237134e76f04da5f1553d0ca903fde11e22`.
- `_cherchi_rational_moments`: `8deaf8b187f12f43ce0f9f955f59c38eeb997c82baf5586e4f05269bf1c87bfa`.
- Native and Boolean hashes match the six-pin record; the rational-moments module hash is recorded in the native arithmetic identity and locked native search-path snapshot.
- The P20 preparation's six observed pins equal the separate pins JSON and the P21 lock.

## Material preparation scope

P20 preparation status: `P20_OWNED_MFD_AND_FRESH_FACTORY_PREPARATION_PASS`.

- Exact represented-set partition `M = F ∪ D`: complete.
- Union equals whole; no positive-volume overlap; both parts are subsets of the whole.
- All ten exact additivity residuals are zero.
- The independent owned-set checker is CGAL Nef/GMP verification of the frozen P19 Cherchi inputs; it is not the geometry-construction backend.
- Cherchi remained the registered geometry backend, but **this P20 preparation did not call Cherchi Source, Boolean, or derivative operations**: fresh evaluator call counts are all zero.
- The fixed-shell moment integration diagnostic ran. It reports a maximum absolute difference of approximately `1.7754528434353378e-16` from the exact affine target-F moments after binary64 normalization/rounding, and explicitly says this diagnostic does not grant W0 moment-gate admission.
- The problem's `original_evidence_admission` remains `BLOCKED_UNKNOWN`; the physical/frame contract is `P20_EXACT_MATHEMATICAL_PHYSICAL_CONTRACT_READY_NOT_NATIVE_ADMISSION`.

The next formal M6 run is therefore the first P27 execution expected to perform the registered same-call Cherchi Source, two Booleans, exact moment comparisons and 10×10 Jacobian capture. The request is explicitly a preregistered **non-optimized one-point material-partition probe**, not a Teapot optimization run.

## Resource checks

At P21 registration:

- Physical memory: 60.434 GiB.
- Effective cgroup memory: 24 GiB.
- Minimum required physical/effective memory: 20 GiB.
- Host and container swap: zero.
- P21 status: `ADMITTED_RESOURCE_POLICY_ONLY`.

During P20 preparation, MemAvailable was approximately 13.71 GiB before and 13.46 GiB after. This is not a failed P21 policy check (the policy checks physical memory, effective cgroup memory and zero swap), but it is an operational caution: close memory-heavy applications and recheck `MemAvailable` immediately before formal execution. The P27 execute path rechecks host and cgroup resource policy.

## Admission boundary

The lock explicitly records:

- `registration_is_read_only = true`
- `factory_imported = false`
- `registration_is_independent_attestation = false`
- `registration_grants_scientific_admission = false`
- `formal_M6_executed = false`
- `native_worker_started = false`

All scientific admission flags remain false. The SHA registration in this review is a durable byte-identity review record, not a cryptographic signature or scientific approval.

## Execution gate

The lock SHA below is approved for the P27 P21 wrapper's external byte-lock check:

`P27_LOCK_SHA256=451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4`

Before running, recheck current `MemAvailable`, `MemTotal`, `SwapTotal`, Docker daemon and the three pinned checkouts. Do not edit the lock, pins, P20/P21 inputs or native modules after this review. A successful M6 geometry receipt still does not grant W0/W2, Newton, training or physical admission.
