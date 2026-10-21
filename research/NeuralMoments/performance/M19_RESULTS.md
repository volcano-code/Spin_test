# W1 V2 M19 — instrument frozen 25-point H8e **outer native-evaluation pipeline**

**Branch exclusively writable:** `research/neuralmoments-w1-native-20261019`  
**Only changed path:** `research/NeuralMoments/performance/`  
**Frozen source ancestor:** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**Outcome:** profiler/source/test implementation **completed**; new full Cherchi cloud experiment **not yet performed**. Consequently the V2 M19 real-native admission milestone is **INCOMPLETE**.

## Concrete technical change

The original H8e 25-point driver `research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/probe_h8_jacobian.py` did NOT instrument the expensive independent exact rational triangle audit and Fraction ten-moment verification, same-call material validation and gzip JSON record stages separately. Its original eight engine stage timers covered about 20% of complete point wall. The remaining ~12 seconds/point **cannot be assigned by inference**.

New `m19_real_h8e_profiler.py` authenticates the **exact original production H8e driver Git blob** `0c219e34869c454db655e62f23d18e59ba4db494` and original `InProcessCherchiEvaluator` blob `f9fa539f699df8baf8b8d30729048269a26ecb3c`. It recompiles only the original `run` function AST with six **nested timing contexts** around the original, unchanged statement objects:

1. `EVALUATE_INPROCESS_CHERCHI` (nested original Python statements and engine's exact native stages)
2. `SAME_CALL_MATERIAL_ATTACHMENT`
3. `EXACT_NATIVE_MATERIAL_GEOMETRY_AUDIT`
4. `INDEPENDENT_FRACTION_MATERIAL_TEN_MOMENTS`
5. `WRITE_COMPLETE_SAME_CALL_MATERIAL`
6. `WRITE_EVIDENCE`

This is neither an approximate surrogate nor a replacement of Cherchi. An isolated subclass wraps the original frozen `__call__` AST using the existing W1 M5 statement profiler and **temporarily** enables its existing native stage observer, restoring the original observer on return/exception. One point owns six phases, and native/Python nested spans contribute mutually exclusive elapsed ns; all original geometric/derivative/material checks remain inside their original AST statements. The code refuses any change to frozen source hashes or the declared original phase layout. It refuses incomplete/duplicated point ledgers. No physical source/moment/Jacobian/Boolean math or production ABI was edited.

## Actually executed on the current host

- Real H8c ZIP `78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7` passed authentication; swap=0.
- Native preflight exited **2**, writing only `preflight.json` and `failure.json`. The machine has a **4 GiB cgroup memory limit**, no complete W1 Git checkout / frozen H8e source, and no `_make_it_stand`, `_cherchi_core_boolean`, `_cherchi_rational_moments` production extensions. **Zero new production Boolean calls**. No fresh native baseline or candidate speedup was fabricated.
- **20/20 new local M19 unit/negative tests passed**, including AST structure/source pin, fake evaluator old/new *exact output and error* parity, nested native-stage instrumentation and observer cleanup, disjoint wall closure, fake stage/duplicate point rejection, and real H8c negative preflight. A first synthetic exclusivity test had only one rather than all six required phases, produced one expected test error, was repaired and completely rerun green; that intermediate attempt is not counted.
- **65/65 combined M5/M9/M10/M19 regression passed**, after restoring the original already-committed M4 historical baseline evidence file that the first transient local test mirror did not contain. Original M5 tests initially had five `FileNotFoundError`s from the missing fixture; no W1 GitHub source was modified, and the final 65-test replay passed.
- New W1-owned `m19-w1-real-h8e-stage-profile.workflow.template.yml` defines the real pinned Ubuntu 24.04 core/Boolean/GMP build, authenticated H8c artifact input, `m13 --build-only`, then exact H8e profiling and unconditional upload of complete or failed receipts. This is **INACTIVE** because activating `.github/workflows/` is outside W1's sole authorized file scope. It is not a dispatched or green CI run.

## Real historical original-only anchors (NOT from this new profiler)

Frozen Heart 25-point Actions run `39121571756` attempts 1 and 2:

| Original-only observed quantity | Attempt 1 | Attempt 2 |
|---|---:|---:|
| Actual original native Cherchi points | 25 | 25 |
| Total wall seconds | 379.493727883 | 371.882780008 |
| Named engine stages seconds | 77.944304694 | 74.939924 |
| Unknown INSIDE original point walls seconds | 301.363449024 | 296.770649 |
| 24 perturbations with changed feature branch | 8 | 8 |
| Full Newton solve / accepted terminal | No | No |

The original 8/24 feature-hash drift and failed workflow conclusions MUST be preserved. The new M19 CLI will produce a complete diagnostic stage receipt if all 25 numerical evaluations finish, but will still exit nonzero when its true original feature-branch test fails. Neither the two baseline walls nor any recent isolated GMP subpath timings constitute W1 production speedup.

## To execute on authorized CI/native host

1. A CI owner needs to register a workflow in a separately authorized `.github/workflows/` location, using the W1-owned inactive template. The GitHub connector in this environment can reread/rerun an already registered historical workflow but does not provide an authorized new `workflow_dispatch` action; rerunning original Heart Actions does **not** run W1's candidate.
2. Use the actual W1 branch checkout with full frozen ancestry; real Cherchi `7bd6c2697695f555f9a15d7e154e084d841316f0` and CGAL `f7c3c8212b56c0d6dae63787efc99093f4383415`, correct Python 3.13 and native modules; swap=0, >=6 GiB actual memory and <=24 GiB upper bound; <=4 build jobs, serial large jobs, <=60 minutes per heavy native task, coordinate with W3.
3. Run `m13_pinned_native_build.py --execute --fetch-pinned-sources --build-only --workers 2`, then:

```bash
python research/NeuralMoments/performance/m19_real_h8e_profiler.py \
  --root "$PWD" \
  --archive /path/to/h8c-reference-39118951636.zip \
  --module-dir "$PWD/build/w1-m13-core/python" \
  --module-dir "$PWD/build/w1-m13-cherchi/python" \
  --output /tmp/w1-m19-real-h8e
```

4. Keep `baseline-performance.json`, `actual-frozen-h8e/` original 25 point materials and `failure.json` if feature branch still drifts. A genuinely finished but formally unqualified profile must not be reported as a green scientific solve. Review largest **same-run disjoint** evaluation and audit phases and then implement a production optimizer candidate with a measured same-host ABBA. W0 must approve the comparison protocol; W2 real independent teacher remains a separate gate.

**M19 V2 real-native hard gate:** NOT PASSED. Code and local tests ready; cloud CI activation and genuine W1 native profiling pending. **Full Newton and model-validated production speedup: NONE.**
