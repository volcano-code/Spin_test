# W1 M17 — true repeated Cherchi baseline, scientific data repeatability and cloud ABBA handoff

**W1-only write target:** `volcano-code/Spin_test`, `research/neuralmoments-w1-native-20261019`, `research/NeuralMoments/performance/`. Frozen ancestor `0bcc187b3005478baa586a6d6f450e73811ca342`. No writes to main, Heart, W0–W6, or production C++/Python files.

## Real native cloud executions checked — NOT optimized ABBA

- GitHub Actions H8e 25-point job `39121571756`, attempt 1 job `117658066974`, **FAILED** historical feature-hash admission; immutable ZIP ID `12134772056`, SHA-256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`.
- Same historical job **rerun attempt 2**, job `118689837052`, **completed FAILED** at the same explicit feature-hash stability gate on 2026-10-20. New ZIP ID `12275408088`, SHA-256 `b763aabfdcaddb821a8766bf661fb25c184f416aa96cb24609874b15f9bc08e1`.
- Both builds use identical `actual_native_sha256`, `actual_cherchi_sha256`, and `actual_arithmetic_sha256` plus frozen H8 request SHA. These are two unchanged Heart research baseline executions, NOT W1 optimized calls or an ABBA on a single native host.
- Both completed 25/25 genuine native Cherchi evaluations, all original numerical finite-difference tests, and both **failed** smooth-feature admission for the same changed 8/24 point indices 17–24. No Newton, terminal solid, whole Faster solve or training qualification.

### Complete material and Jacobian scientific comparison

`m17_repeated_native_baseline.py` re-opens both genuine artifact ZIPs, checks SHA-256 of *entire archive*, strict original three CAD inputs and frozen H8 request, all three original native binary SHA, all 25 point packet SHA of that individual attempt, exact geometry and construction provenance, all ten raw moment binary64 bits and the complete 10×10 Jacobian in each saved material. It does **not** skip or replace exact geometry provenance and never upgrades the original failed stability verdict.

| Measure | Observed |
|---|---:|
| Matched input and all three native binary SHA identities | Yes |
| Full non-Jacobian material fields exactly equal | **25 / 25** |
| Independent and native ten raw mass-moment components identical | **250 / 250, bitwise** |
| Pointwise geometry, topology and source provenance match | **25 / 25** |
| Pointwise Jacobian JSON SHA bitwise identical | **0 / 25** |
| Number of differing Jacobian entries | **1,096 / 2,500** |
| Maximum absolute Jacobian difference | **1.7763568394002505e-15** |
| Maximum scaled Jacobian difference | **2.1384136821605478e-16** |
| Original failed 8/24 feature hashes | **unchanged** |

The *original* baseline already produces tiny floating-point Jacobian variations between two independent GitHub native runs. All 25 full serialized JSON material SHA differ, because the serialized Jacobian is included; **all other fields of the parsed complete material are exactly equal**. The source H8c `.json.gz` compressed file also varies in gzip bytes while its **uncompressed** exact Cherchi packet content is byte-for-byte identical. **Never use compressed-byte equality alone** to diagnose new geometry drift.

The old M9 gate requires the full serialized material SHA and all 100 Jacobian binary64 bits to match exactly among four calls. This repeated-baseline observation demonstrates that such strict bitwise matching *cannot be assumed even for unchanged original native code across cloud executions*. This is **NOT** permission to loosen production scientific admission: preserve M9 fail-closed behavior until W0 formally defines the independent numerical Jacobian parity tolerance and W2's real teacher is admitted. Separate exact provenance/ten-moment equality from independently bounded Jacobian repeatability in future read-only diagnostic reports.

### Original-native wall, same call/host attribution

| Measure (seconds) | Attempt 1 | Attempt 2 |
|---|---:|---:|
| Original 25-point total wall | 379.493727883 | 371.882780008 |
| Sum of genuine 25 point wall spans | 379.307753718 | 371.710572 |
| Sum of eight named engine stages | 77.944304694 | 74.939924 |
| **Unknown INSIDE point wall** | **301.363449024** | **296.770649** |
| Outside-point orchestration | 0.185974165 | 0.172208 |

The ratio 379.49/371.88 = **1.02046599** describes TWO DIFFERENT RUNS OF THE SAME BASELINE (different cloud runners/times). It is **not** an optimization speedup, not a paired within-job ABBA and does not identify which stage contributes the ~12 seconds/point unattributed work. Independent exact rational boundary auditing, Fraction verification and JSON material handling are plausible but **NOT measured exclusive contributors** within this original job.

Full machine-readable 25-row per-stage/geometry/Jacobian report: `evidence/m17-crossrun-25point.json`; test log `evidence/m17-tests.log`; actual attempts in `evidence/m17-actions-attempts.json`.

## Cloud live W1 old/candidate ABBA — runnable handoff, not activated

`m17-w1-real-native-abba.workflow.template.yml` is an **INACTIVE** workflow template stored strictly in W1's exclusive directory. If a CI owner later authorizes activation on an approved CI workflow ref (without modifying W1's frozen tracked production paths or main), it will:

1. Checkout EXACT W1 branch with full frozen ancestry, build pinned Cherchi `7bd6c269...`, CGAL `f7c3c821...`, 3 genuine native modules, zero swap and bounded memory/concurrency; authenticate the exact original H8c archive.
2. Run existing M13 true compiler, then M5 genuine single q and M9 A–B–B–A original/candidate 4 calls, each with same-call native exact boundary, independent Fraction moments, complete Jacobian, original material and source evidence.
3. Run M11 independent validation and M14 native binary/source custody; upload full before/after material and build proofs **even if a strict admission gate fails**.

The workflow is NOT deployed under `.github/workflows` because that directory is outside W1's ownership. Inserting a new tracked workflow file in W1 itself would also make M14's frozen-production checkout protection fail. This connection does **not** offer an authorized workflow-dispatch mutation tool. CI owner authorization and repository workflow registration are required before it can actually run; no fresh W1 candidate cloud ABBA or new Newton run has occurred in this milestone.

## Reproduce actually executed comparison

```bash
python research/NeuralMoments/performance/m17_repeated_native_baseline.py \
  --attempt-1 /path/to/h8e-25point-39121571756.zip \
  --attempt-2 /path/to/h8e-25point-rerun-attempt2-12275408088.zip \
  --output /tmp/w1-m17-crossrun.json

cd research/NeuralMoments/performance
python -m unittest test_m17 -v
```

The comparison is read-only and requires BOTH original authentic cloud ZIPs; fake artifacts are rejected by whole-ZIP SHA. Optional `orjson` speeds JSON loading of the original 14MB material packets; stdlib `json` remains the fallback. The returned Jacobian noise floor is **observation**, not a universal scalar tolerance. Keep historical failures visible and require W0 formal acceptance and actual same-host W1 ABBA before any paper-speed claim.
