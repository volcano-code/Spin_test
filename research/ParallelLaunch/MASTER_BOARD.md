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
| W0 | 数学合同与总控 | [research/neuralmoments-w0-contract-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w0-contract-20261019/research/ParallelLaunch/W0_START_HERE.md) | 无 | MomentContractV1＋质量矩坐标测试 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
| W1 | Cherchi/Faster 性能 | [research/neuralmoments-w1-native-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w1-native-20261019/research/ParallelLaunch/W1_START_HERE.md) | 可独立 profiling；合并需 W0/W2 | 冻结同输入逐段耗时＋原生改造对照 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
| W2 | 精确教师与标签 | [research/neuralmoments-w2-teacher-20261019](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w2-teacher-20261019/research/ParallelLaunch/W2_START_HERE.md) | 正式发布标签需 W0 | 真实 r,J＋SHA＋可微/失败状态 | `BRANCH_AND_CHARTER_CREATED; DEVELOPMENT_NOT_STARTED` |
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
