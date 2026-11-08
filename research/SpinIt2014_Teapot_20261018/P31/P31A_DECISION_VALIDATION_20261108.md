# W4 P31-A decision validation — 2026-11-08

## Frozen user decision
- Case: B — new Utah-Teapot-inspired spinning-top test article.
- Historical attribution: explicitly not original Melitta/author-authentic CAD.
- Provisional unit mapping: 0.025 m/reference.
- Provisional density: 1200 kg/m^3.
- Both physical parameters remain unvalidated and unapproved.

## Immutable source binding
- P20 request blob: `f3bca7bef1f207cb5b857848c9588543fb7e5a9c`.
- P20 frame report blob: `16a4b4cdf7c1dc6a2de314f22ebbee95364b9c04`.
- P20 frame identity: `699a2137d6eebde69792e0e52fd624d642cec70f0ead3b6a54fbd7673c25b3a7`.

The original P20 request and frame report were not overwritten. The new P31 decision is a separate overlay so historical preregistration remains reproducible.

## Deterministic decision-record validation
The committed JSON was fetched back from the W4 branch and parsed. All 11 checks passed:
1. schema identity;
2. selected case B;
3. no historical-CAD attribution;
4. length scale exactly 0.025 m/reference;
5. density exactly 1200 kg/m^3;
6. provisional/unapproved status;
7. native pilot remains disabled;
8. native call count remains zero;
9. training remains disabled;
10. W0 authorization path exact;
11. W2 authorization path exact.

This is a structural/semantic validation of the decision overlay only. It is not a geometry or physics validation.

## Coordination
GitHub issue #8 opened for the independent W0 and W2 owner reviews:
https://github.com/volcano-code/Spin_test/issues/8

W0 receipt path remains absent on W0 branch; W2 receipt path remains absent on W2 branch at this audit. Therefore P30-B remains BLOCKED and no Cherchi native evaluation was started.

## Next gate
- W0: approve/reject the new physical test article and provide geometry, material, support/contact, loading and F/D/S evidence.
- W2: independently approve/reject the same feature branch and teacher provenance, bound to the W0 receipt.
- W4: verify both receipts and independently registered lock before local native pilot.
