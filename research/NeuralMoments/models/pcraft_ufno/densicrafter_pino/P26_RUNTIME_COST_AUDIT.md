# W6 P26.0 — paired runtime cost audit contract

## Code and CI evidence

- Runtime audit: `p26_runtime_cost_audit.py`
- Contract tests: `tests/test_p26_runtime_cost_audit.py`
- CI: [Run 42781121358](https://github.com/volcano-code/Spin_test/actions/runs/42781121358) — PASS.
- The audit contract checks paired timing arithmetic, unique sample IDs, and explicit exact-backend provenance.

## Required measured fields

Each JSONL row must contain:

- `sample_id`: unique query identifier.
- `pino_ms`: measured primary PINO inference wall time.
- `uqno_ms`: measured uncertainty-head and gate wall time.
- `fallback_used`: whether exact fallback ran for this query.
- `exact_ms`: measured exact callback time when fallback was used.
- `exact_reference_ms`: measured exact-only reference time for the same query, even when the hybrid gate accepted PINO.
- `exact_backend`: `cherchi` or `voxel_hardcut`.
- `exact_provenance`: build/commit/manifest identifier for the exact backend.

The exact-only baseline is paired by query. Hybrid latency is `pino_ms + uqno_ms + exact_ms` when fallback runs, otherwise `pino_ms + uqno_ms`. Speedup is mean paired exact-reference latency divided by mean hybrid latency.

## Important evidence boundary

The current CI uses synthetic timing rows only to verify accounting logic. It does **not** claim any measured Spin acceleration. A Cherchi claim is permitted only when the input ledger carries actual Cherchi backend provenance and measured timings. Voxel hard-cut measurements must remain labelled separately.

## Next integration requirement

W1/W2 must supply a same-query timing ledger from the actual PINO inference, UQNO gate and exact reference backend. Until that ledger exists, P26 remains a validated measurement harness, not a speedup result or production approval.
