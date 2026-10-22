# W1 V2 M23 — full Faster/Newton A–B–B–A executor, authentic Heart CAD input

**Only writable branch:** `research/neuralmoments-w1-native-20261019`.  
**Only modified directory:** `research/NeuralMoments/performance/`.  
**Frozen ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`.  
**Milestone scientific status:** **BLOCKED**; genuine same-host Newton ABBA has **not** been run.

## Why this was necessary

M22 provided an isolated candidate with bytecode-identical production `solve_cherchi_inprocess_and_seal_faster()`, but only mocked Newton events and replayed original rational vertices. The frozen H8c prepared-request does not itself constitute the **immutable SpinArtifactProblem** required for true full-solver execution, and using its literal q as a new initialization would violate the registered request-seed-only solver protocol. This milestone implements an explicit, separate, real-CAD locked-input route rather than mislabeling a single-point replay as a Newton benchmark.

## Actual genuine input recovered and tested

From H8e Actions run `39121571756`, artifact SHA256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`, the tool independently opens the archived `H8_CAD_AUDIT.json`, `H8_INDEPENDENT_AUDIT.json`, true CAD OBJ files and frozen prepared request (SHA256 `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`). Verified *original and design CAD* arrays reproduce the original registered H8 request **bit-for-bit** at the same 25 mm scale and identical original faces. No CAD vertex is silently regenerated or repaired.

| Genuine reconstructed H8 CAD | Vertices | Triangles |
|---|---:|---:|
| Original initial top | 15,646 | 31,288 |
| Fixed shell F | 28,768 | 57,532 |
| Design region D | 13,122 | 26,244 |
| Shaft | 1,580 | 3,156 |

The new full-solver **problem normalization may be different** from the original single-point H8c request, because `SpinArtifactProblem` sets its normalization from the actual outer mesh. This is a **separately registered reconstructed Heart problem**, not a claim to reproduce the old H8c single-q coefficients or to use the author's original CAD. The actual native `SpinArtifactProblem` constructor, when available, must independently verify `O = F + D`; archived CAD's analytic construction statement is **not** a native represented-solid certificate.

The tool uses physical units `mm`, `g`, density `0.001187 g/mm³` (1187 kg/m³), original shaft-based target `z = −2.874999612569809 mm`, recorded conservative initial wall clearance and exact unchanged frozen evaluator/Newton configuration.

## Actual code and failure behavior

`m23_real_newton_abba.py`:

1. Enforces archived ZIP/request/CAD SHA256, correct W1 branch/ancestor, original frozen production-source Git blob, pinned M8/M22 implementation, memory >=6 GiB, zero swap, three genuine **unique** native `.so`s and invariant module hashes during all runs.
2. Starts **four independent serial processes** in order `original, candidate, candidate, original`; each heavy solver is hard-capped at <=3600 seconds and <=24 GiB. Actual problem F/D/original partition, native geometry and solver are invoked in the child, never mocked. Same production solver function for original/M22 and same `SpinSolverConfig`.
3. Preserves authentic stage records and material checkpoints; rehashes every `MAP_SAVED` material and rechecks the Newton event sequence, terminal complement, complete journal and independent record-verification evidence. Any difference or missing verification **fails closed**. No relaxed W0 Jacobian tolerance is introduced.
4. Reports a **diagnostic** full-solver wall ratio *only* if all 4 real solver processes converge and produce completely matching scientific/terminal evidence. It **never** changes the frozen historical H8e 8/24 feature drift result; W0/W2 release remains false until their separate approval.

## Tests actually run

- Original M22 suite: **13/13** passed.
- New M23 suite: **20/20** passed using actual H8e source ZIP for CAD identity, checksums, authentic face/coordinate registration, units, memory and negative native preflight, plus adversarial simulated journal/identity proof corruption. **33/33 distinct tests passed**.
- First M23 combined run failed one negative fixture regex because it asserted `NONCOMPLETE` rather than the actual `INCOMPLETE_OR_NONCONVERGED` error. Fixed the fixture and reran all 33 cleanly; the first failed run is preserved locally and not counted as a pass.
- Actual M23 CLI invoked against the real archived ZIP and this host. It exited **2 / BLOCKED_BEFORE_NATIVE** for missing full W1 Git checkout, local 4 GiB memory cap and all three production extensions; produced real `preflight.json` and `failure.json` with `solver_calls=0`, `full_solver_speedup=null`. This is **not a new Boolean or Newton execution**.
- Source, test, output and SHA256 details are in `evidence/m23-*` and the accompanying downloadable archive. Remote GitHub Actions were not triggered by this milestone.

## Run on a *real native host*, after M13/M19 and separate CI-owner authorization

```bash
export W1_P=research/NeuralMoments/performance
python "$W1_P/m23_real_newton_abba.py" \
  --root "$PWD" \
  --archive /path/to/h8e-25point-39121571756.zip \
  --module-dir "$PWD/build/w1-m13-core/python" \
  --module-dir "$PWD/build/w1-m13-cherchi/python" \
  --output /tmp/w1-m23-full-newton-01 \
  --max-seconds 3600
```

Inputs and mode are source pinned. The runner only writes a success-style diagnostic if original/candidate runs actually complete *four* times and all saved scientific records match. Read every `failure.json` and never promote a failed/partial run to an optimization success. The original M19 profiler must still run to attribute ~12s/point, and M22 **real Cherchi four-call ABBA** is still a separate earlier gate. The W1 CI owner Issue #3 remains open.

**M23 verdict:** Real original/F/D/D CAD input is recovered and checked, the genuine Newton A–B–B–A host executor is implemented and tested, but **0 fresh full Newton native calls and no supported complete-solver speed ratio**. This is infrastructure to unblock an actual native benchmark, not a completed V2 research goal.
