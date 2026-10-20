# W1 M16 — real historical H8e native forensic and fresh GitHub Actions rerun

**Only writable branch:** `research/neuralmoments-w1-native-20261019`; files only `research/NeuralMoments/performance/`. Original W1 frozen ancestor `0bcc187b3005478baa586a6d6f450e73811ca342`. No changes to main, Heart branch, any other research branch, or production source/ABI.

## Actual native execution initiated

Using the GitHub connector's **rerun failed job** operation, triggered **attempt 2 of the original real H8e 25-point native job** (run `39121571756`, new job ID `118689837052`) on October 20, 2026. GitHub returned `success=true` for the launch; an immediately checked Actions status was **IN PROGRESS**, specifically **Build native core with strict pinned dependencies**. This rerun runs the **original Heart research commit** `fd7459f7bf10344269d3b9b3ada39d3e81edde48` with the pinned Cherchi+GMP implementation, **not** W1's candidate optimization. The original Heart branch was **not modified**. Result of attempt 2 was **not yet available** when this evidence was recorded. No success or performance comparison from attempt 2 is claimed.

Actions URL: https://github.com/volcano-code/Spin_test/actions/runs/39121571756

## New strict same-native-run analysis, actually executed

`m16_native_actions_forensics.py` reopens the real ORIGINAL historical H8e artifact `12134772056` (ZIP SHA256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`), verifies the frozen H8 request SHA, all 25 archived exact same-call material compressed packet SHA-256 digests, exact boundary admission, ten moments and full 10x10 saved Jacobian shape. It independently reconciles each point's complete native wall against *that same point's* eight exclusive recorded evaluator stages; checks their sum against the original report's totals; independently checks the original Actions job 25 timestamped console rows against the archived individual point wall. It refuses every changed scientific-success status and verifies that **eight original source-feature hash changes** are preserved (point indices 17–24).

### Proven exact timing closure — **original archived native host only**

| Metric | Measured from original CI artifact and log |
|---|---:|
| Original H8e native total wall | 379.493727883 seconds |
| Sum of 25 point wall intervals | 379.307753718 seconds |
| Sum of named instrumented native stages | 77.944304694 seconds |
| **Unidentified *inside* the 25 evaluations** | **301.363449024 seconds** |
| Outside-point orchestration in same job | 0.185974165 seconds |
| Median unidentified per point | 12.002300440 seconds |
| Original source-feature hash changes | 8 of 24 perturbations, unchanged |

The unidentified time is **not** assigned to Python Fraction, geometry self-intersection, construction correspondence, or JSON without direct same-run instrumentation. The original live production evaluator `probe_h8_jacobian.py` invokes each independent boundary audit, Fraction verification and material snapshot in the point wall but not in the eight `stage_seconds`; these are candidate components, not individually measured here.

The original 25-point Actions job **FAILED** its feature-neighborhood gate despite completed real Cherchi calls and finite numerical checks; it does not establish a smooth Newton map, formal acceptance, complete Faster solve or speedup. The fresh attempt-2 job cannot be confused with the old archived attempt-1 material or its immutable source and binary identities.

### Actually executed local tests

`PYTHONPATH=research/NeuralMoments/performance python -m unittest discover -s research/NeuralMoments/performance -p 'test_m16.py' -v`

**20/20 pass, 0 fail, 0 skipped**, using the genuine original H8e archive and a verbatim 26-line extraction of the actual original 223-kB GitHub Actions job log. Adversarial tests reject missing/negative stages, false timing closure, missing material digests, modified exact moments, NaN Jacobian, fake binary identities, changed original failure state, missing or duplicate console points, fabricated console durations, and SHA drift. Full test output at `evidence/m16-tests.log`; actual 25-point reconciliation at `evidence/m16-original-same-run.json`.

## Production gate still open

The current local execution host is capped at **4 GiB** cgroup memory, zero swap; GitHub Git remote name resolution is disabled; three production `.so` extensions and a complete frozen W1 checkout are unavailable. The original Actions artifact does not contain compiled extension modules. Although the historical **new** native cloud run was launched, it uses an old Heart commit and cannot certify a W1 candidate A/B. `faster_full_solver_speedup=null` and no new Newton terminal material or W0/W2 admission are claimed. W1's M5/M9/M11/M14 instrumented source can run only on a genuine pinned W1 checkout and complete Cherchi-native environment.

## Reproduce the completed historical evidence audit

```
python research/NeuralMoments/performance/m16_native_actions_forensics.py \
  --archive /path/to/h8e-25point-39121571756.zip \
  --job-log research/NeuralMoments/performance/evidence/m16-original-verified-job-lines.log \
  --output /tmp/w1-m16-h8e-native-original-audit.json
```

The `--job-log` is only the 25 progress and 1 final status lines extracted unchanged from original GitHub Actions job ID `117658066974`; it is not a re-executed native trace. Treat attempt-2 separately. Do not splice original and rerun timing as one call.
