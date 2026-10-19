# Spin_test Neural Moment parallel R&D — master coordination board

**Established:** 2026-10-19. **This board records prepared branches, not running ChatGPT chat sessions or completed experiments.**

## Source identity

- Full source, current Heart baseline: `0bcc187b3005478baa586a6d6f450e73811ca342` (`research/heart-p0-p3-20261017`).
- Teapot P0 baseline: `24f89ed21c251a8678aceb997e4ca30e4ba24125` (`research/spin-it-teapot-20261018`).
- P-CRAFT source: `volcano-code/test` at `24eda3e9b3f87ba16251a9025761986d6cfe3079`.
- Preserve `volcano-code/Spin`, `Spin_test/main`, historical CI failures and materials.

## Windows and startup instructions

| Window | Role | Branch / exact instructions | Dependencies | Earliest evidence target | State |
|---|---|---|---|---|---|
| W0 | 数学合同与总控 | [research/neuralmoments-w0-contract-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w0-contract-20261019/research/ParallelLaunch/W0_START_HERE.md) | 无 | MomentContractV1＋质量矩坐标测试 | `M4_LIVE_REPLAY_GATE_COMMITTED; 43_PURE_TESTS_PASS; REAL_NATIVE_RESOURCE_BLOCKED; W2_TRUTH_DENIED` |
| W1 | Cherchi/Faster 性能 | [research/neuralmoments-w1-native-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w1-native-20261019/research/ParallelLaunch/W1_START_HERE.md) | 可独立 profiling；合并需 W0/W2 | 冻结同输入逐段耗时＋原生改造对照 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
| W2 | 精确教师与标签 | [research/neuralmoments-w2-teacher-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w2-teacher-20261019/research/ParallelLaunch/W2_START_HERE.md) | 正式发布标签需 W0 | 真实 r,J＋SHA＋可微/失败状态 | `W2_ADAPTER_MOCKS_PRESENT; MANIFEST_0_NATIVE_RUNS_0_TRAINING; TRUTH_BLOCKED` |
| W3 | Heart H9 | [research/neuralmoments-w3-heart-h9-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w3-heart-h9-20261019/research/ParallelLaunch/W3_START_HERE.md) | 无 | 81 点 point60 构造变化诊断 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
| W4 | Teapot P1 | [research/neuralmoments-w4-teapot-p1-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w4-teapot-p1-20261019/research/ParallelLaunch/W4_START_HERE.md) | 已完成 P0；体积/求解需 W0/W2 | 合法茶壶输入、F/D 与初态 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
| W5 | DeepONet＋MLP | [research/neuralmoments-w5-deeponet-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w5-deeponet-20261019/research/ParallelLaunch/W5_START_HERE.md) | 解析 smoke 立即；真实训练需 W0/W2 | r,J 模型＋导数监督/成本报告 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
| W6 | P-CRAFT UFNO | [research/neuralmoments-w6-pcraft-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w6-pcraft-20261019/research/ParallelLaunch/W6_START_HERE.md) | 解析 smoke 立即；真实训练需 W0/W2 | U-FNO 几何编码缓存＋r,J head | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |

## Merge/review gates

1. W0 publishes `MomentContractV1`, including native coefficient order and cross-term factor-two mapping. No published teacher/NN experiment can silently change it.
2. W2 publishes immutable real Cherchi/GMP `r,J` labels with native/source identity and explicit validity categories. Training may use analytic smoke data before this.
3. W5/W6 benchmark on equal verified frozen labels and geometry-family splits, report geometry encoding separately from hot parameter-head inference and Jacobian.
4. W1 shares same-call baselines, never merges validation-skipping shortcuts, and reports end-to-end wall time and raw geometry/moment invariance.
5. W3 retains H8f failure at 1/80 branch-feature classification; no converged Heart model before real Newton terminal proof.
6. W4 retains public teapot original input. 19 indexed components and 160 geometric open edges require independently validated repair.
7. W0 alone coordinates integration/cherry-pick via reviewed commits. No other window edits this board; work progresses only when a connected new chat or agent actually executes tools.

## Resource and evidence policy

- Full native jobs serialized in same environment: 24GiB RAM, swap0, 60min/job, compile ≤4 jobs; coordinate GPU usage.
- Every milestone: commit SHA, changed files, tests/CI, measured results, failure ledger, model and data identities.
- Network prediction/physical constraints are not a geometry validity certificate. Final material and raw residual require true Cherchi/Faster audit.



## W0 milestone 1 record (2026-10-19)

- W0 math contract and reference implementation pushed exclusively to `research/neuralmoments-w0-contract-20261019` under `research/NeuralMoments/contracts/`.
- Native c order `a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy`; ordinary r order `M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY`; map `q=B*c` with last three B diagonal entries equal to 2.
- Local analytic tests: 15 passed from independent, more extensive W0 working implementation. GitHub CI and run of exact committed files are not claimed; frozen Cherchi production geometry not run.
- W1–W6 completion and CI statuses not independently verified; preserve previous statuses until per-window evidence is reviewed.
- Required integration gates: independent exact material seals, true geometry and derivative identity, and terminal Newton validation, none replaced by P0 analytic smoke.


## W0 milestone 2 record (2026-10-19)

- Implementation `6eb8d16ccec11ef3de283f239facd6a9bc183a04`: strict source/shape/math consistency validator, W2 pre-release identity adapter, and adversarial tests; original native `moment_coordinates.py` mixed-boolean coercion fixed.
- Local test command `python research/NeuralMoments/contracts/run_contract_smoke.py` passes 57/57 (0.13 seconds); all published source files were checked byte-for-byte by Git blob SHA before pushing, runner blob verified separately. See [W0 M2 evidence](W0_M2_EVIDENCE_20261019.md).
- Actual Cherchi/Eigen runtime, exact Boolean material certification, derivative smooth-neighborhood proof, end-to-end Newton terminal and GitHub Actions result are **NOT VERIFIED**, so teacher and network training admission remain blocked.
- The current W2 manifest (read-only observation) reports adapter-smoke only and zero native teacher/training samples. Other W rows are unchanged pending independent audit.


## W0 milestone 3 source-linked native / exact P0 observation (2026-10-19)

- The unchanged frozen production `src/spin/QuadricCoefficients.cpp` and header are Git-blob verified as `ae831afe9191f67fb2659f112d1b85a8e2b61581` and `d315960a8d9616197df656a3c74b74b2da037798`, compiled together with W0 native probe and a linker stub **only** for unrelated slicer SHA hashing.
- 125 actual native-Eigen points passed (value, gradient, homogeneous matrix, pullback; worst absolute error `6.66e-16`). Signed exact-rational 24-face fixed shell F plus 12-face inner D was independently integrated against separable analytic box mass-moments and transformed meshes, with **exact zero** algebraic difference. New M3 tests: `9 passed in 11.85s`.
- Source/test files committed under W0-only scope; see [W0 M3 evidence](W0_M3_EVIDENCE_20261019.md) and `research/NeuralMoments/contracts/contract_smoke_m3.json`.
- Machine has only 5.8GiB RAM, no swap, and neither `_make_it_stand` nor `_cherchi_core_boolean` present. **Real Cherchi material, independent exact Boolean seal, teacher r/J, Newton terminal and training admission NOT VERIFIED.** GitHub CI is not assumed green.
- The following W1–W6 branch SHAs and commit subjects were **read-only observed**, not independently benchmarked or certified. The earlier state cells remain unchanged to avoid treating commit messages as tested evidence:
  - W1: `01a1d480ec4044ff678bc648051234bcb7e85aeb` — research(w1): M2 exact GMP PreparedMaterial parity and H8 replay profiler
  - W2: `14b1d2d5da4e258d125e664b5665ef84f7ebbb4e` — W2: add mock smoke for one-call Cherchi adapter and failure accounting
  - W3: `0f5229bb10cac098011f42ab9c996eec485ac034` — Heart H9 W3: certify archived edge-event sign bracket, add guarded native microprobe and tests
  - W4: `8fc1dd33e6cabb29a54849dce271ec63660b6af4` — W4 P2: reproducible CGAL teapot solid union with independent self-contact and moment gates
  - W5: `7054cf6624eeb85f8ba06093090127bdb8016dc4` — W5 M2: gate W0/W2 teacher provenance and audit multi-seed analytic baselines
  - W6: `694e5764e656de0c769f59d2838dc53eddde0b63` — W6 M2: W0-native analytic cut oracle, derivative smoke, W2 fail-closed gate and CPU evidence


## W0 M4 native replay gate and read-only branch heads (2026-10-19)

- Implemented real-source Cherchi single-call replay, independently exact rational mass moments, frozen 6-way input/native/source SHA pins, resource-guarded native worker and 43 adversarial pytest cases. See [M4 evidence](W0_M4_EVIDENCE_20261019.md).
- Local M4 tests 43/43 passed; on the actual 5.8085-GiB/swap0 host the native admission command returned exit 3, `BLOCKED_INSUFFICIENT_PHYSICAL_RAM`; no real Cherchi teacher evaluation, exact Nef replay, derivative-neighborhood certificate or training labels were produced.
- W2 manifest remains `ADAPTER_SMOKE_ONLY`, `native_teacher_runs=0`, `training_samples=0`. Its pre-W0 label envelope omits exact rational material vertices/faces, so a genuine live `evaluator.material(c)` attachment is required for W0 numeric replay.
- Read-only branch HEAD snapshots (commit presence **not** proof of runtime correctness):
  - W0: `0c3ad0a8f6a6f8088ecb617c980d979fafe68383`
  - W1: `bbee1eb3044bf41bb5328f0348e97334d8faf0a5`
  - W2: `56212f46b007fa255cc5796224192010aa67513c`
  - W3: `fc08c229ecf966f9a4453414dbb54095d22cc118`
  - W4: `dcae39d2113aeed91c26d7bacceba3e252306d27`
  - W5: `c535cbde306a6ec4447e4d60583fbbe997ac26f5`
  - W6: `b5d3985ec4a10c74316bda6579767b58c13b4eaa`
- Earlier W1–W6 status columns are retained pending formal per-window test evidence review. Native jobs must remain serialized (24 GiB/swap0; compile ≤4; ≤60min/job).
