# W2 M23-P2 — Noodles V7 rebuild readiness gate

**Date:** 2026-11-09  
**Branch:** `research/neuralmoments-w2-teacher-20261019`

## Why this milestone

The user's local scan found two rational JSON files from a different Balanced Noodles experiment; neither matched the frozen V7 SHA. The six V7 packet bytes therefore remain unrecovered. The frozen V7 checkpoint does preserve the 94-part manifest, 96-op build script, exact backend identity, and three historical chain receipts.

A source inspection exposed an additional reproducibility blocker: the frozen `build_exact_v7.py` imports `common.py`, but `common.py` is not present anywhere in the GitHub V7 source tree. The chain verifier also imports `exact_planar_patches.py` from an external `/mnt/data/Noodles_v6_C4_work/code` path, which is not part of the GitHub checkpoint. Thus the historical build scripts are not self-contained in the repository snapshot.

## Delivered

Added:
- `m23_p2_noodles_rebuild_readiness.py`
- `test_m23_p2_noodles_rebuild_readiness.py`
- `.github/workflows/w2-m23-p2-noodles-readiness.yml`

The readiness tool is read-only and never launches CGAL or Cherchi. It checks:
1. exact V7 source manifest SHA and schema;
2. all 94 model OBJ and SI OBJ files against manifest hashes;
3. 93 fixed parts;
4. presence of `common.py`, `build_exact_v7.py`, `prove_v7_chain.py`;
5. presence of external `exact_planar_patches.py`;
6. historical backend existence and exact SHA, plus shared-library resolution;
7. successful 94-part source audit;
8. at least 24 GiB free disk space;
9. the existence and SHA of any already-created six rational outputs, without trusting filenames alone.

It fails closed and writes a JSON readiness report. It does not change the six historical identities or relabel a new build as historical recovery.

## CI result

GitHub Actions run `42568573797`: **4/4 readiness tests passed**, 0 failures, 0 skips. The job completed successfully on 2026-11-09.

[CI run](https://github.com/volcano-code/Spin_test/actions/runs/42568573797)

## Current actual blocker

No local readiness run has been performed yet because the latest user instruction was to continue cloud development rather than run disk scans. The prior local report still says 0/6 historical SHA matches and no backend candidate. In addition, the GitHub checkpoint omits `common.py` and the external chain dependency. This is a concrete source packaging gap to resolve before the 96-operation builder can be safely launched.

## Next work

1. Recover `common.py` and the pinned `exact_planar_patches.py` implementation from the original V7/C4 local project or Git history; verify their hashes and API against the frozen build script.
2. Add those dependencies to the W2 branch with provenance and tests, without editing main or other workspaces.
3. Run the readiness audit locally after the user has adequate disk headroom and the exact backend/source audit are available.
4. If ready, execute the 96-op builder as a new separately identified build, with one node per durable receipt, resume-safe cache validation, and output SHA verification.
5. Run solid embedding and F/D/A global partition proofs. Only then request a fresh W2 Noodles Cherchi teacher.

No new CGAL or Cherchi call was made. Keep `J_D=null`, `split=excluded`, and training samples at zero.
