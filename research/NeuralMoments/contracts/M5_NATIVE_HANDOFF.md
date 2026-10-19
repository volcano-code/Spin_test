# W0 M5 — verified W2 mathematical oracle / Cherchi runtime handoff

## Source identities

- Frozen Spin/Cherchi baseline: `0bcc187b3005478baa586a6d6f450e73811ca342`.
- W0 own branch: `research/neuralmoments-w0-contract-20261019`.
- W2 observed branch: `research/neuralmoments-w2-teacher-20261019` at `c2628ea75a8680910557855896e7317f92567756`.
- Read-only copied W2 `independent_reference.py` Git Blob SHA1 `d734398292e1fdaf839db3413c537de2474df3e1`, SHA256 `3238fb14d4cbf85d7754551689fa40cbb08653bf3a9bf631faf16138f9c6bea9`. W2 has updated binary64-density semantics; snapshots from earlier W2 revisions are **not** silently interchangeable.

## Run mathematical checks

```bash
python -m pytest -q research/NeuralMoments/contracts/test_*.py
```

`cross_oracle_gate.py` compares W0 and W2 independently implemented rational surface integrators over the SAME exact indexed mesh and density, asserting exact equality across M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY. The F/D sum is an accounting identity, not a proof that F and D are disjoint. The pinched-shared-vertex witness is rejected by W0; the self-intersecting/overlapping closed-components witness remains numeric-only.

`tangent_neighborhood.py` requires a **frozen base feature-branch fingerprint** as well as the four ±h, ±h/2 geodesic samples per direction and the native c-coordinate Jc matrix. A stable sample fingerprint does not prove a continuous open smooth neighborhood, and all outcomes have `training_admissible=false`. No universal prediction error threshold exists; choose case-specific normalized-error budgets before obtaining measurements.

## Invoke one real native evaluator (not possible in this container)

Use a trusted, source-bound Python factory returning `(InProcessCherchiEvaluator, SpinArtifactProblem, c_native)` and a PRECOMMITTED external pins JSON with exactly these keys: `native_sha256`, `bridge_sha256`, `adapter_sha256`, `c_sha256`, `problem_input_digest`, `context_sha256`. Read M4_NATIVE_HANDOFF.md for source fingerprint details. Do not construct pins after seeing evaluator output.

```bash
PYTHONPATH=python python -m research.NeuralMoments.contracts.live_native_m5_cli \
  --factory trusted_native_fixture:prepare_one \
  --pins /path/to/precommitted_sha_pins.json \
  --output /path/to/w0_m5_live_report.json
```

The CLI requires sufficient physical RAM for the 24 GiB/swap0 charter host (preflight threshold >=20 GiB, swap exactly 0), only one W0-M5 CLI at a time, and a hard 3600s wall timeout. Compilation concurrency must be capped at 4; manually coordinate native jobs with W1/W2/W3 because their tools do not share W0's lock. If resources or native imports fail, the report contains a failure state; it does not report success.

The production path delegates to the authentic M4 `audit_live_native_once`, then reads `evaluator.material(c)` from that SAME native invocation. It checks pinned W2 exact r10 on the retained rational boundary without running another Cherchi Boolean; both component-level and independent original F/D validation remain required. This mathematical parity and a pointwise J are **not** certification of exact full material partition, smooth derivative-neighborhood, printability or converged Newton terminal.

On the current container, actual preflight returned exit `3` and status `BLOCKED_INSUFFICIENT_PHYSICAL_RAM` at `5.808525085449219 GiB` / swap0. W2 manifest presently has `native_teacher_runs=0`, `training_samples=0`.

Training promotion requires a separate proof chain: complete exact Boolean F/D/cavity partition, independent sealed full-material r, real derivative neighborhood excluding H8 point60 branch changes, solver terminal and model/source/checkpoint hashes. Open Teapot boundaries cannot be used as truth.
