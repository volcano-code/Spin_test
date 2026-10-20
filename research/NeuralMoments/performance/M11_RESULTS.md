# W1 M11 — Native receipt gate (2026-10-20)

Exclusive branch: `research/neuralmoments-w1-native-20261019`
Exclusive path: `research/NeuralMoments/performance/`
Frozen source: `0bcc187b3005478baa586a6d6f450e73811ca342`

## Implementation
- `m11_native_evidence_gate.py`: validates actual M10 native-module preflight and module-byte SHA-256, rereads M5 + four M9 saved material snapshots, checks each report, q, all ten moments, complete 10x10 Jacobian, source/geometry hashes recomputed from exact geometry, native self-intersection audit flag receipts, timing-ledger closure and original/candidate ABBA ratio. Rejects duplicate-key/nonfinite JSON, incomplete or drifted packet evidence.
- `m11_native_host_runner.py`: runs the existing M10 M5-then-M9 serial native pipeline in a quarantined subdirectory, promotes a M11 result only after the independent gate succeeds. No M10-only success is promoted if M11 evidence fails.
- Neither tool alters production `src/`, `bindings/`, `python/make_it_stand/`, `main`, or any other W branch.

## Actually executed (local)
- Full M5–M11 Python/C++ regression: **99/99 tests passed**; no skips or failures. The new M11 synthetic receipt/failure-gate suite passed **14/14**. Tests distinguish deliberately synthetic metadata from actual Cherchi execution.
- Genuine historical H8c Actions artifact 12132634988 (run 39118951636) and its frozen input/certificate SHA verified.
- Actual M11 preflight exit code **2**: `BLOCKED` before any Boolean. Blockers: no full W1 Git worktree; pinned production source missing; `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments` missing. Zero swap and true archive verified. cgroup RAM ceiling **4 GiB**, below the planned 24 GiB research resource ceiling.
- **Zero fresh native Boolean or Newton calls**; no full-solver speedup, green CI or paper-speed claim.

## Run on matching native host
In an actual complete W1 checkout with pinned compiled native modules and H8c archive, respecting swap=0, <=24 GiB, <=4 compiler workers, <=3600s per native job, and W3 job coordination:

```bash
python research/NeuralMoments/performance/m11_native_host_runner.py \
  --root "$PWD" \
  --archive /path/to/h8c-reference-39118951636.zip \
  --output /tmp/w1-m11-native-01 \
  --module-dir "$PWD/build/heart-cloud-core/python" \
  --module-dir "$PWD/build/heart-cloud-cherchi/python" \
  --max-seconds 3600
```

All failed preflights and altered M5/M9 saved proofs fail closed. A five-call successful native receipt is **not** a finished Newton solve or manufactured terminal material. W0 math contract, W2 true teacher, complete optimizer accept/reject history and author-matched speed remain pending. The original H8e 25-point feature-hash failure (8/24) remains unchanged.

Full local M11 test and blocked-preflight logs plus readable sources are retained in the conversation-linked M11 reproducibility ZIP; the GitHub submission here contains the production-independent code and scientific scope summary.
