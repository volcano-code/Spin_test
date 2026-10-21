# W1 V2 M20 — Repair blocking H8c artifact hash before native CI

**Scope:** Real deployment defect fix on W1 only. Does **not** close V2 M19 native-cloud hard gate or prove W1 optimizer speedup.

## Found actionable blocker in M19 CI template

`m19-w1-real-h8e-stage-profile.workflow.template.yml` pinned a **wrong** SHA-256 to the authentic GitHub Actions H8c ZIP (artifact `12132634988` / historical run `39118951636`). Its `sha256sum --check` would deterministically fail before `m13_pinned_native_build.py` ever launched. The same wrong string appeared in the W1 M19 runtime status snapshot and in open CI handoff Issue #3.

Expected erroneous value:

`78749e99abd25ab2d2571440991ffa4e907a1565b4e20298f8516e061c`

Recomputed actual ZIP SHA-256, independently consistent with the M5 `ARCHIVE_SHA` constant and GitHub Actions artifact metadata:

`78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7`

The two W1-owned files are corrected, with immutable Git history preserving the old incorrect snapshots. An explicit `evidence/m20-m19-h8c-sha-erratum.json` records both old and new fingerprints, scope, and release denial. The authentic 2.7MB H8c ZIP is tested locally against the corrected SHA. A tampered copy, an incorrect declared hash, missing `sha256sum --check` and duplicate checksum declarations are rejected.

## Scope and next real native task

- **No** production source, `main`, W0–W6, GitHub Actions historical failed jobs, original H8c artifact or trust policy was modified.
- The template remains **INACTIVE** in `research/NeuralMoments/performance/` pending authorized CI owner activation; do not mislabel as running.
- CI owner should update the open Issue #3 handoff with the actual new W1 commit and use this corrected template only.
- After legitimate activation, the next real result must be a W1 same-run complete 25-point hierarchical profile; then select dominant time and implement a true original/candidate Cherchi ABBA, followed by Newton and multi-model comparisons.
- Until then: fresh W1 native 25-point profile = **NO**, optimized real ABBA = **NO**, complete Newton speedup = **null**.
