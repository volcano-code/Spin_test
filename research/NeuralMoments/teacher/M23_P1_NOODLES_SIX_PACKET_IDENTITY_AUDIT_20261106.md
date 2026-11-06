# W2 M23-P1 — Noodles V7 six-packet cross-branch identity recovery

**Date:** 2026-11-06  
**W2 branch:** `research/neuralmoments-w2-teacher-20261019`  
**Main checkpoint branch:** `main` at `8c949de977ef50be337da7aec6c852566e0da565`  
**Frozen source snapshot:** `Noodles_v7_GitHub_research_source_snapshot.json`  
**Snapshot SHA-256:** `f7cf4c2efbd32b9c19d33359471f0671aa2efae104d3aa912500157052f39980`

## 1. Key discovery

The six Noodles V7 rational packet **identities were not absent from all project records**. They are independently recorded in the frozen V7 checkpoint on `main`, and all six SHA-256/face-count pairs exactly match the six packet identities expected by W2 M20:

| Packet | SHA-256 | Faces |
|---|---|---:|
| design | `48e8d3008bba746823eafd9c3704b52d597595b802066450a921ecc0dcb7f611` | 108,804 |
| envelope | `92f46d68025467961fcc8b2b52353b4a18c2a981a09ad654ad6af3fb128b73fd` | 1,280 |
| fixed | `71f9df91fca12fde4f4f2c80dc26e2d1229e8209e09db46e680d0de7baee264a` | 114,942 |
| fixed-inside-envelope | `a944da4e36e5fe386cee3b28e4acf5800fc3942cde4eb35ba54f5de626f55dc7` | 107,160 |
| fixed-outside-envelope | `8c66f71da99773fbc9a76b4f82fc43c55816df1876b643634ae64768f72ba262` | 35,342 |
| initial | `640877647134a54152a8e1f63c1f356d752e6c66f7913301580c1e85a356d83b` | 36,986 |

The match is three-way: V7 `construction.json`, W2 `M20_HISTORICAL_96_BOOLEAN_DAG.json`, and W2 `M20_REAL_94_INPUT_FDA_PREFLIGHT.json` agree on all six names, hashes and face counts.

The V7 construction record also matches the W2 source-manifest SHA `67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a`, the pinned historical CGAL backend SHA `d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3`, 94 source parts (93 fixed) and 96 reported CGAL operations (92 fixed unions + 4 final CSG operations).

## 2. Three exact oriented-chain receipts also match

The V7 snapshot records three independent exact oriented rational surface-chain relations, each with zero nonzero support planes and zero exact zero-area triangles:

1. `F + D = A`
2. `K + D = E`
3. `K + R = F`

All relation inputs reference the same six packet hashes listed above. This is substantially stronger than merely recovering six digest strings: it preserves exact boundary-chain receipts for the F/D/A and envelope partitions.

However, the V7 chain summary explicitly says it **does not prove native solid validity**. These are oriented boundary-chain equivalence proofs; they do not by themselves establish absence of all invalid solid configurations, independent Boolean set semantics, or a binary64 partition without gaps/overlaps.

## 3. Important remaining limitation: payload bytes are still absent

The uploaded source snapshot is 296,965 bytes and has SHA-256 `f7cf4c2efbd32b9c19d33359471f0671aa2efae104d3aa912500157052f39980`. It contains the V7 source, manifest, construction summary, chain summary, Newton/evidence reports and receipts. It does **not** contain the six `exact_v7c/*-rational.json` packet payloads themselves.

The six packet hashes are therefore cross-authenticated as historical identities, but the packet bytes have not been recovered in this milestone. The main-branch Noodles V7 README also states that the large rational input bodies are not included in the checkpoint. The Actions workflow `Assemble verified Noodles V7 OBJ` run `39015376793` has no downloadable Actions artifact; it only reassembled the final OBJ transfer chunks.

Accordingly, this milestone does **not** change the historical W2 fact that the six raw packet payloads are unavailable. Do not recreate packet JSON from hashes or face counts.

## 4. V7 run context and model scope

The frozen V7 checkpoint is explicitly classified as `PAPER_PHOTO_GUIDED_RECONSTRUCTED_METHOD_VALIDATION_NOT_AUTHOR_CAD`; `author_original=false`. It records a separate real Cherchi/Faster warm-restart convergence on this reconstructed V7 candidate (5 accepted updates, residual (2.8251949346891595\times10^{-14})), but that is not automatically a W2-admitted Noodles teacher sample. It does not release a W2 `J_D`, and it does not replace the missing full rational packet payloads or a formal F/D/A solid-partition admission.

The original historical CGAL construction record reports 96 operations and the exact-chain summary reports three passed relations. The separate V7 optimization checkpoint has its own stated limitations: author CAD unavailable, multi-seed statistics absent, latest full native branch not freshly rebuilt, and formal separate binary64 F/D/A partition not passed.

## 5. M23-P1 code and tests

Added:
- `m23_p1_noodles_six_packet_audit.py` — fail-closed cross-branch identity and chain-receipt auditor.
- `test_m23_p1_noodles_six_packet_audit.py` — tests for all-six identity match, packet SHA mismatch, chain failure, backend mismatch and missing packet names.
- `.github/workflows/w2-m23-p1-noodles-audit.yml` — branch-scoped regression workflow.

The auditor deliberately returns `SIX_PACKET_IDENTITIES_AND_THREE_EXACT_CHAIN_RECEIPTS_CROSS_MATCH_PACKET_BYTES_STILL_MISSING`; it does not promote the six packet payloads to recovered.

## 6. Next step

M23-P2 is now narrower:
1. Search the original V7 experiment storage for the six payload files by the six pinned SHA-256 values.
2. If they cannot be recovered, rerun the pinned 96-operation CGAL construction only on a qualified local host, preserving every intermediate receipt and final packet byte.
3. Independently audit each packet's closed/oriented/embedded solid properties and prove the F/D/A set partition, including binary64 conversion suitability.
4. Only after those gates pass, create a new W2 Noodles Cherchi teacher request and run it under a qualified native protocol.

Cloud work can continue for digest/receipt auditing, source review and small synthetic tests. Recovering or regenerating the six large exact rational payloads and full solid checks should be done from original experiment storage or a qualified local environment. No new CGAL or Cherchi calls were made by M23-P1.

**Verdict:** M23-P1 recovers and cross-validates all six historical packet identities and three exact chain receipts, but not the six packet bytes or formal solid/teacher admission. Keep `J_D=null`, `split=excluded`, and W2 training samples at zero.


## CI verification addendum

The branch-scoped GitHub Actions workflow `.github/workflows/w2-m23-p1-noodles-audit.yml` was run.

- First run `42211036530` exposed a test-fixture bug only: three negative-path tests passed a `Path` object to `json.loads` instead of reading the file text. The two positive-path tests passed.
- The fixture was corrected in commit `05b090ff4f3802f1592654c09d333c35c0906be6`.
- Rerun `42211272055`: **5/5 tests passed**, 0 failures, 0 skips.
- This CI run tests the cross-branch identity auditor against synthetic fixtures. It does not download or rehash the six absent rational packet payloads and does not run CGAL or Cherchi.
