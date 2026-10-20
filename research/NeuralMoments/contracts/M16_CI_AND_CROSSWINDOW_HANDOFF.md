# W0 M16 — GitHub CI activation and source-pinned consumer-interface audit

Research scope: `volcano-code/Spin_test`, W0 branch `research/neuralmoments-w0-contract-20261019`; no edits to main or W1–W6. For this milestone the user explicitly authorized activating CI. The sole narrow exception to the prior W0 directory boundary is **new** `.github/workflows/w0-contract-ci.yml` on the W0 branch; all other new files are W0-owned. Enabling CI is not a scientific release.

## Read-only audited sources

- W0 `MomentContractV1` schema + validator: pinned Git blob byte identities; unit-native-c rule remains `abs(norm(c)-1) <= 1e-12` and `q=Bc` last 3 entries doubled.
- W2 v2 manifest: exact branch-source snapshot with 81 archived historical H8f candidates explicitly excluded, zero new native teacher runs and zero released training entries; no W0 formally approved `J_D`.
- W5 DeepONet loader: read-only exact branch source shows legacy `w2-cherchi-teacher-v1-pre-w0` schema, and a **looser** `1e-9` saved-c norm preflight. This is an interface mismatch, not proof W5 has imported any forbidden real labels. No direct changes to W5.
- W6 P-CRAFT gate: read-only exact branch source contains a hard deny via `TeacherUnavailable` for real native teacher; analytic P0 use is separate, not real Cherchi truth. No direct changes to W6.

Files under `frozen_external_m16/` are explicitly **snapshots** of source bytes, not current branch heads. Git blob SHA-1 is verified before any AST or JSON parsing. Any future upstream change needs a new source review and new snapshot pin, not silent refresh. The compatibility auditor always returns training_admissible=false even when the source-level check succeeds.

## CI activation and tests

`w0-contract-ci.yml` runs only on W0 branch push or approved manual dispatch. It uses the exact committed checkout, Python 3.13, NumPy and pytest, and executes the small W0 analytical/math-contract suite plus M15 and M16 interface tests. It does not compile native Cherchi/CGAL, re-run historical expensive 81-point geometry, certify full solid partition/continuous derivative neighborhood, or run Newton. A green CI is a **Python contract regression only**. The existing `M15_CI_WORKFLOW_TEMPLATE.yml` remains archival only.

Before reporting green, inspect GitHub Actions run conclusion and failed steps; a connector push and a combined-commit-status with no statuses are not a successful CI run. Preserve historical H8f original failed run `39123384402` and W3 no-new-sided-materials facts. W2/5/6 training remains fully blocked until independent native teacher+W0 seal and verified neighborhood, and Heart Newton remains blocked without authentic terminal evidence.

## Required downstream changes (separate window ownership)

1. **W5**: when its window is ready, add an explicitly versioned v2 reader and align strict native coefficient validation to W0 without changing historical raw c or quietly casting v2 to v1. It must independently bind provenance and remain blocked pending real native W0 sealing.
2. **W6**: retain current fail-closed import and only enable real Cherchi data on an independently certified future release; analytic P0 studies can continue.
3. **W2**: keep the 81 H8f archived samples excluded; never convert 64 nonunit raw c to new source evaluations. Formal W0-v2 signed release is future work.
4. **W3**: produce genuinely new, authenticated four-side Cherchi materials on a suitable resource-isolated host before continuity and Newton decisions. Current H8f original CI failure remains an essential fact.
