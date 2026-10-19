# W0 M6 — exact full F/D/retained/cavity partition audit

Only W0 branch `research/neuralmoments-w0-contract-20261019` owns this work.
Frozen production baseline: `0bcc187b3005478baa586a6d6f450e73811ca342`.

## What the new native pathway actually checks

1. Reuse M4 → M5 authentic one-call Cherchi computation, with the externally **precommitted** six identity pins. It reconstructs a valid saved retained material in the original physical geometry using native exact material-region checks, and verifies W0/W2 ten raw moments.
2. Read `evaluator.material(c)` from that same saved source. Call the actual `InProcessCherchiEvaluator.complement_of_saved_source(evaluator, saved)` once. This performs **one additional opposite-side Cherchi Boolean**, but does **not** generate another source quadric or run Newton. Check that the source hash, source vertices/faces and sign/complement operation remain bound to the original accepted source.
3. Recover exact *physical* cavity vertices by inverting the **actual binary64-to-exact-rational** frame matrix, not by transposing an approximately orthonormal matrix. Verify an exact roundtrip before creating an independently authenticated native `MeshSnapshot`.
4. Use the production `check_exact_material_partition` on actual owned native exact material regions for three ordered tests:
    - `original = [all fixed regions F_i, design D]`;
    - `design D = [retained, cavity]`;
    - `original = [all fixed regions F_i, retained, cavity]`.
   Require `completed`, `complete_partition`, `union_equals_whole`, `no_positive_volume_overlap`, every `part_subset_whole`, no missing/excess content and zero positive-overlap pairs. Retain the complete native predicate facts and partition identity digest.
5. Independently integrate exact physical input/retained/cavity surfaces in the same target frame. Confirm **all ten** `r_retained + r_cavity = r_design` as rational equalities, and separately compare density-weighted fixed F moment sums against the frozen source input. Record same-call counts, stage durations and process-lifetime RSS HWM (not peak for the call).

## Run current, native-free tests

```bash
python -m pytest -q research/NeuralMoments/contracts/test_*.py
```

The local M4/M5/M6 mirror produced `142 passed in 0.27s` on 2026-10-19. This includes synthetic native-shaped test doubles, not an actual `_cherchi_core_boolean` execution. The previous M1–M3 suites were **not** rerun in this local mirror. Do not add up historical counts as one full checkout test.

## Execute one real native partition on an authorized host

A trusted **local** Python factory `trusted_native_fixture:prepare_one` must return `(genuine InProcessCherchiEvaluator, immutable SpinArtifactProblem, normalized native c)` for an independently admitted closed F/D geometry. Provide M4's externally precommitted six SHA256 pins (native binary, Cherchi bridge, adapter source, native c vector digest, locked problem digest, evaluation context digest) in `/path/to/precommitted_pins.json`.

```bash
PYTHONPATH=python python -m research.NeuralMoments.contracts.live_native_m6_cli \
  --factory trusted_native_fixture:prepare_one \
  --pins /path/to/precommitted_pins.json \
  --output /new/path/w0_m6_partition_evidence.json
```

The command has a **20 GiB minimum RAM preflight** for the agreed nominal 24 GiB/swap0 machine, swap must equal zero, and parent/child wall-time limit is 3600 seconds. It shares the W0 M5 intra-window file lock, but **does not coordinate with W1/W2/W3**. Externally serialize all large Cherchi tasks; compile ≤4 concurrent jobs. It always creates evidence files **exclusively**: existing paths, including failed reports, are never overwritten.

The current analysis container has ~5.81 GiB RAM and no installed `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments`. Actual preflight exits `3` with `BLOCKED_INSUFFICIENT_PHYSICAL_RAM` and never imports the test factory. This is **not** a failed real material geometry attempt.

## Scientific nonclaims and next gate

Even a genuine M6 full native exact partition success is limited to the **represented polyhedral material and mass moments**. It does not prove a smooth open derivative neighborhood; M5 samples at four finite points are only a diagnostic. It does not prove that a Newton solve converged or that the saved endpoint has passed the final independent physics/material seal or printability. `training_admissible=false` is mandatory for every M6 output. The subsequent terminal/derivative acceptance must consume an independently verified converged native run and a separate smooth-neighborhood certificate before W5/W6 may receive real training truth. H8 point60 remains branch-change/unknown, and the open Teapot remains invalid until independently repaired and certified.
