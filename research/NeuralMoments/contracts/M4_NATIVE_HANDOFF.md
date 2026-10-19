# W0 M4 — authentic Cherchi single-call handoff

The code is W0-only. W2 must supply a TRUSTED local Python factory returning
`(InProcessCherchiEvaluator, SpinArtifactProblem, normalized_native_c)`.
Fake duck-typed objects, JSON flags, recomputed self-attested signatures, or pre-release labels cannot certify real geometry.

## Offline mathematics and negative tests
```bash
python -m pytest -q research/NeuralMoments/contracts/test_native_teacher_replay.py research/NeuralMoments/contracts/test_live_native_teacher_cli.py
```
The synthetic tetrahedron confirms exact rational r and undoubled XY/XZ/YZ; closure, source hash, frame, fixed-addition, J byte identity, malicious modifications and resource admission are tested. This is not a native Cherchi teacher test.

## Live production invocation (24 GiB/swap0 node)
Commit independently PRE-FROZEN SHA256 identities to a local JSON file, with **exactly** six keys: `native_sha256`, `bridge_sha256`, `adapter_sha256`, `c_sha256`, `problem_input_digest`, `context_sha256`. Hashes must be lower-case 64-character hex and externally fixed before evaluation; do not derive them from the just-generated output.

```bash
python -m research.NeuralMoments.contracts.live_native_teacher_cli \
  --factory trusted_fixture_module:prepare_one \
  --pins /path/to/precommitted_native_pins.json \
  --output /path/to/w0_m4_real_native_report.json
```

The trusted factory must build a real immutable problem/request and a genuine `InProcessCherchiEvaluator` from independently authenticated original/F/D geometry. No working native factory is shipped: W2 must provide the actual replayable sample and precommitted pins. The CLI checks Linux RAM >=20 GiB, swap0, single child and 3600 s timeout; insufficient hardware returns exit code 3 and saves a `BLOCKED_INSUFFICIENT_PHYSICAL_RAM` JSON report without even importing the factory. Follow overall large-job ≤4 concurrent compiler process policy.

The live gate invokes the source/Boolean once, obtains the saved exact physical and target rational material via `evaluator.material(c)` without a second Boolean, independently rebuilds an authenticated native region and exact subset, separately prepares fixed F once, reintegrates r_D with Fraction, checks F+D and source geometry SHA, and records stage/wall times and process RSS HWM. Pointwise J is NOT a smooth-neighborhood certificate; output is never training-admissible without separate independent neighborhood, complete partition and terminal solver proof.

**W2 handoff gap:** as of 2026-10-19 its pre-release envelope retains r_D/J_D/hashes but omits material exact rational indexed vertices/faces. To reproduce independently, pair the envelope with the authentic same-call source attachment rather than promoting SHA-only records.
