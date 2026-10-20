# W1 M18 — Real native Jacobian repeatability diagnostics, without math admission

**W1 sole writable branch:** `research/neuralmoments-w1-native-20261019`  
**W1 exclusive path:** `research/NeuralMoments/performance/`  
**Frozen ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**M17 source proof:** exact Git blob `077ac148eb35d2aebd14ea36c6bc1cd209156156` (`evidence/m17-crossrun-25point.json`).

## What was actually executed

1. Opened both genuine 25-point original Cherchi H8e GitHub Actions ZIPs (run `39121571756` attempts 1 & 2, artifacts `12134772056`, `12275408088`). Each ZIP's whole-file SHA256 is pinned: `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38` and `b763aabfdcaddb821a8766bf661fb25c184f416aa96cb24609874b15f9bc08e1`. The prior M17 report was pinned by its exact Git blob **before** its recorded 25-point source/material evidence was reused. The M18 per-point diagnostics independently rechecked each saved gzip packet against M17's original SHA256 for that specific point.
2. Independently decoded the 50 full real material packets in six serialized slices: indices `0..4`, `5..9`, `10..14`, `15..17`, `18..20`, `21..24`. Checked **all 21 original material fields** on each matched pair: full non-Jacobian state, exact rational coordinates, construction provenance, Boolean/source identity, ten raw moments, fixed+variable/total identity and original saved geometry hash. The sole excluded comparison field is the **entire** `moment_jacobian`; its 100 native binary64 entries per point are instead compared position-by-position, including signed zero, exact ULP distance and scaled/absolute differences. A different exact source/material or even a changed one-bit ten-moment value is rejected.
3. Independent `m18_merge_slices.py` refused duplicate/missing sample IDs, unauthenticated M17 report content, missing original failures, self-reported release, changed J values, invalid 10x10 coordinates and unclosed counts. The whole material field equality is supported by the pinned *M17* same-call archive verification and the current independently recomputed semantic digests; the diagnostic merger alone is **not** an independent native execution attestation.
4. Created `m18_native_shadow_cli.py` for a **future** genuine M9 4-call failed ABBA: it reads the four material gzip snapshots and saved point receipts, requires existing M9 failure with four completed calls, validates original source/geometry/moments, exact boundary flags, independent Fraction audit stages, timing closure, snapshot SHA and per-call Jacobian binding. It reports actual Jacobian drift separately but is ALWAYS `W1_production_speedup_admitted=false`, `W0_smooth_Jacobian_acceptance=false`. No new Cherchi Boolean is run by this CLI.
5. Added an **inactive** `m17-w1-real-native-abba.workflow.template.yml` step to run the above read-only shadow analysis *after* an M9 failure; any original native/build failure stays a failure. This file remains in W1's exclusive `performance/` scope and is NOT an active GitHub Actions workflow.

## Measured two-original-run data, NOT optimized A/B

| Metric | Audited observation |
|---|---:|
| Archived native material pairs | **25/25** |
| Exact 10-component raw moments, unchanged binary64 | **250/250** |
| Non-Jacobian full material identity | **25/25** |
| Jacobian values compared | **2,500** |
| Jacobian last-bit differences | **1,096** |
| Maximum absolute J difference | **`1.7763568394002505e-15`** |
| Maximum scaled J difference | **`2.1384136821605478e-16`** |
| Signed-zero/ULP description | recorded, **not** adopted as any universal numeric tolerance |
| Original source/Boolean/GMP modules | same frozen SHA256 in both historical runs |
| Original native 25-point wall | **379.493727883 s** |
| Repeated native 25-point wall | **371.882780008 s** |
| Original H8e feature hash drift and failed CI | **8/24**, preserved in both |

The largest differing-column counts are native `c[9]=178`, `c[2]=177`, `c[7]=175`; this is a *description* of historical output instability, not a derivative structural law. The two walls are original-vs-original and differ due to run conditions; their ratio is not W1 speedup. The historical ~301 seconds of per-run unmatched time remain unresolved until M5 is actually run on a native host.

## Executed tests and failures

- M18 synthetic checks include changed exact ten-vector, source, geometry boundary flag, missing Fraction verification, missing native binary SHA, bogus wall clock, altered saved material, absent M9 original failure, partial four-call ABBA, duplicate JSON keys and false W0 release.
- M9+M17+M18 **63/63 passing local unit/archival tests**. No remote CI claim. Test log: `evidence/m18-final-all-tests.log`.
- First complete M17 duplicate audit, then a second unsliced M18 audit, exceeded the local tool window and **were not counted** as passes. A subsequent six-slice run completed all 25 points. The first M18 combine attempted to include a metadata-correction JSON in a too-broad shell glob; that and the original `all_25` metadata naming issue were corrected, with original failed snapshots and a SHA manifest preserved. Final six-slice merge passed. Initial synthetic native-backend name failed one test, was corrected to exact frozen Cherchi ID, and 63 tests were rerun green. Do not interpret those initial failures as native solver failures.

## Reproduce from W1 checkout

The unchanged M17 evidence file is `research/NeuralMoments/performance/evidence/m17-crossrun-25point.json`; it is SHA-pinned in M18. Set your own real artifact ZIP paths; here both are named as in earlier M17.

```bash
cd research/NeuralMoments/performance
for segment in '0 5 00-04' '5 10 05-09' '10 15 10-14' \
               '15 18 15-17' '18 21 18-20' '21 25 21-24'; do
  set -- $segment
  python m18_jacobian_repeatability.py \
     --attempt-1 /path/h8e-25point-39121571756.zip \
     --attempt-2 /path/h8e-25point-rerun-attempt2-12275408088.zip \
     --m17-report evidence/m17-crossrun-25point.json \
     --start "$1" --end "$2" --output "/tmp/m18-slice-$3.json"
done
python m18_merge_slices.py --m17-report evidence/m17-crossrun-25point.json \
     --slices /tmp/m18-slice-[0-9][0-9]-[0-9][0-9].json \
     --output /tmp/m18-complete.json
python -m unittest test_m9 test_m17 test_m18 -v
```

After a **real** failed M9 ABBA (and only if all four saved point JSON/gzip files and a failure record exist):

```bash
python m18_native_shadow_cli.py \
 --m9-output /path/to/m11/work/m9 \
 --output /tmp/m18-shadow-diagnostic.json
```

The shadow result cannot authorize material/derivative/production acceptance on its own. W0 must explicitly choose and precommit a scale-aware Jacobian comparison protocol, independently assess signed derivative neighborhoods and exact same-call material, and W2 native teacher admissibility must be separately proved. Until then the original M9 hard gate remains unchanged. We did **not** modify `main`, other W branches, native `src/`, `bindings/`, or the active `.github/workflows/` directory.

**M18 verdict:** Real original-native repeatability is now reproducible with full scientific invariants and robust postfailure diagnostics. **New W1 optimized native ABBA = 0; new full Faster/Newton solves = 0; production solver speedup = NULL.**
