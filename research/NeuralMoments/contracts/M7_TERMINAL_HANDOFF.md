# W0 M7 — frozen Newton terminal / M6 partition / original KKT review

**Scope:** `research/NeuralMoments/contracts/` and `research/ParallelLaunch/` only. Native source baseline `0bcc187b3005478baa586a6d6f450e73811ca342`. Never edit another research window or historical failed evidence.

## Two distinct phases of identity

**Before running native:** independently freeze the model/geometry, original and F/D identities, native binary, Cherchi Boolean library, source adapters, objective settings, native c request and source build SHA256. M4–M6's precommitted `six` identity pins remain separate from subsequent journal bytes.

**After the production writer has exited and fsynced, before W0 review:** an independent collector must SHA256-freeze every required output record and **every** `MAP_SAVED` `evaluation-%06d.json` referenced in `events.jsonl`; do not derive/rewrite these hashes inside the review itself. Store `pins.json` outside mutable solver output. The pin JSON has exactly `schema`, `files`, `expected_c_sha256` (canonical native vector digest), `expected_problem_digest` (frozen problem digest). Schema is `W0_M7_PINNED_TERMINAL_ARCHIVE_V1`.

Required `files` keys: `configuration.json`, `events.jsonl`, `native-result.json`, `result.json`, `complete.json`, `terminal-material-reference.json`, `terminal-complement.json`, `terminal-complement-reference.json`, `record-verification.json`, plus all referenced `evaluation-%06d.json` files. Never overwrite original evidence. Omitting a prior non-terminal material, adding an unreferenced file, or rewriting the log with a rebased local digest must fail.

## Run the locally executable W0 regressions

```bash
python -m pytest -q research/NeuralMoments/contracts/test_*.py
```

The isolated M4–M7 local mirror measured **222/222 pass (0.55 s)**, with 142 earlier M4–M6 tests and 80 M7 tests, including a realistic two-evaluation positive case and missing/unreferenced/mutated `MAP_SAVED` negative cases. This does not run the actual Cherchi process, M1–M3 full checkout, or prove an open smooth derivative neighborhood.

## Review one actual externally pinned completed production run

The **production** `solve_cherchi_inprocess_and_seal_faster` must have already completed on the authorized 24 GiB/swap0 native host using serial scheduling (≤60 min native job; ≤4 compile jobs). The M7 reader never starts Newton or a new Boolean. For a numerical archived record-only check:

```bash
PYTHONPATH=python python -m research.NeuralMoments.contracts.live_terminal_m7_cli \
  --archive /path/to/immutable-completed-run \
  --pins /path/to/external-terminal-pins.json \
  --output /new/path/m7_numeric_record_review.json
```

To require the authentic installed production record verifier and its precommitted source SHA256, add:

```text
--require-production-record --production-verifier-sha256 <64hex-production-cherchi_run_evidence.py>
```

For an independently frozen M6 report that binds the SAME geometry/c/source and validates original=F+D, D=retained+cavity, original=F+retained+cavity, add `--partition /immutable/M6.json --partition-sha256 <externally-pinned-sha256>`. The M6 SHA should be frozen after that separate run and before M7 review; SHA agreement alone does not prove genuine native execution.

For **original Spin2014 rotational equations only**, add `--require-original-kkt --original-physics-sha256 <precommitted-faster_material.py-sha256> --objective-contract-sha256 <precommitted-spin2014_objective_contract.py-sha256>`. This invokes installed, hash-matched production source to recompute independent original KKT with the last three doubled dual coefficients, **not** a saved residual. If objective or production modules are unavailable, exit code 3 with `BLOCKED_PRODUCTION_VERIFIER_UNAVAILABLE`. Do not pass flags for original-physics proof on unsupported static/other objectives.

The CLI writes a **new** JSON path with exclusive creation. It refuses replacing a report, failed CI, native journal, CAD or prior proof.

## Scientific meaning and remaining dependencies

The numerical reviewer independently reintegrates the terminal retained rational boundary's ten density-weighted moments, verifies fixed+variable accounting, c and source identity, the final accepted Newton event, per-file SHA, source-opposite terminal complement and native Jc → solver-coordinate Jacobian chain. The M6 binder checks **matching committed evidence identities** but has no authority to certify that a geometric kernel ran. The optional production verifier checks record integrity, not physical truth.

**All M7 output fields `training_admissible`, `newton_terminal_independently_certified`, `smooth_derivative_neighborhood_certified` and `full_native_geometry_certified` remain false** even on a numerically consistent archive. Only separately authenticated actual native solver execution, independent physical/Boolean full-material seal, genuine derivative-neighborhood proof and terminal original-equation verification can trigger a later release review. H8 point60 branch-change and open Teapot remain excluded.
