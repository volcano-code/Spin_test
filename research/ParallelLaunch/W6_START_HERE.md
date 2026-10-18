# W6｜P-CRAFT U-FNO-Moment 竞争框架

**GitHub 仓库：** `volcano-code/Spin_test`  
**唯一写入分支：** `research/neuralmoments-w6-pcraft-20261019`  
**冻结源版本：** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**独占文件范围：** research/NeuralMoments/models/pcraft_ufno/ 和独立 tests（绝不直接改 volcano-code/test/main）  
**依赖：** 网络 smoke 可用解析数据；正式教师与训练需 W0、W2 发布冻结合同

## 给新聊天复制的启动指令

> 我负责并行研究窗口 **W6：P-CRAFT U-FNO-Moment 竞争框架**。请先通过 GitHub 连接器读取 `volcano-code/Spin_test` 分支 `research/neuralmoments-w6-pcraft-20261019` 中的 `research/ParallelLaunch/W6_START_HERE.md`，把它作为本窗口唯一任务说明。仅修改此分支独占范围，先检查代码和现状，再马上实现可验证的首个里程碑，运行测试，提交到自己的 GitHub 分支并返回 commit SHA、CI/日志、真实成果及尚未完成事项。不要只给规划，不要等待其他窗口即可做的 smoke；没有权限或工具时说明阻碍，绝不冒充推送。

## 具体工作

1. 固定来源 `volcano-code/test` commit `24eda3e9b3f87ba16251a9025761986d6cfe3079`；阅读 `structural/models/pino.py` 中 `SpectralConv3d_Factorized`、`UFNO3d` 和 `UFNODualBranch3d`。
2. 创建全新的 U-FNO 几何编码器，将密度/占据/SDF/内部边界统一转为固定长度 `z_D`，缓存几何特征；参数 head 输入 c 输出 r[10]，自动微分输出 Jacobian。不要先解码 64³/256³ 9 通道应力场。
3. 现有 PINO 平衡方程/本构/Von Mises 损失与质量矩无关，必须移除或替换为 W0 定义的合法十矩结构；旧 FEM 权重不自动视为已预训练到质量矩任务。
4. 设计与 W5 相同的教师预算、几何划分、参数量级和计时协议，优先 smoke 和 0–2 查询适配，后续再决定训练扩容。

## 当期验收清单

- 原始 repo/test 约12GB权重不在仓库、只有源码/元数据归档，不能声称训练已重现。
- `geometry encoding`只做一次，重复变化 c 保证可微且输出格式与 W5 对齐。
- 记录编码/推断/Jacobian 显存与时延，以及与轻量 MLP/DeepONet 的公平对照。

## 所有窗口都必须遵守的规则

- 本任务是独立 GitHub **代码开发任务**，不是让对话在后台自行持续执行。每轮必须实际检查文件、编写代码、运行可用的测试并提交证据；未经执行不能声称通过。
- 仓库 `volcano-code/Spin_test`。禁止修改其 `main`、历史 `volcano-code/Spin`、`volcano-code/test/main`、他人 W 分支；不覆盖此前保存的失败 CI、历史报告、原始 CAD。
- 与其他窗口沟通通过 GitHub 的合同版本、提交 SHA 和文件链接；等待依赖时先完成自己的解析/纯代码 smoke，不得捏造依赖已完成。
- 每个里程碑提交新分支，反馈更改文件、通过/未通过的真实测试、误差/性能和下一步；所有优化必须保留完整材料与强真值独立验收。
- 按先前资源协议，大型原生作业串行、24GiB/swap0、每次≤60分钟、编译最多4并发；GPU 训练避免与其他窗口冲突。

