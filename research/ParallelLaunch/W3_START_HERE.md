# W3｜Heart H9 构造分支异常与 Newton 准入

**GitHub 仓库：** `volcano-code/Spin_test`  
**唯一写入分支：** `research/neuralmoments-w3-heart-h9-20261019`  
**冻结源版本：** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**独占文件范围：** research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/ 中新增 H9 source/tests/reports，仅当前分支  
**依赖：** 无；基于冻结 H8f 产物独立分析

## 给新聊天复制的启动指令

> 我负责并行研究窗口 **W3：Heart H9 构造分支异常与 Newton 准入**。请先通过 GitHub 连接器读取 `volcano-code/Spin_test` 分支 `research/neuralmoments-w3-heart-h9-20261019` 中的 `research/ParallelLaunch/W3_START_HERE.md`，把它作为本窗口唯一任务说明。仅修改此分支独占范围，先检查代码和现状，再马上实现可验证的首个里程碑，运行测试，提交到自己的 GitHub 分支并返回 commit SHA、CI/日志、真实成果及尚未完成事项。不要只给规划，不要等待其他窗口即可做的 smoke；没有权限或工具时说明阻碍，绝不冒充推送。

## 具体工作

1. 读取 GitHub Action run 39123384402 的原始 81 点证据及 artifact 12135528290；保留 CI 失败事实，不篡改 run。
2. 精确调查 sample 60，对应 c[7] +3e-6：比较与基点及两侧邻近点的 LPI/TPI 语义身份、有理边界面片及 434 个变动三角索引；区分纯重三角化与实际构造切换。
3. 若只能证明有限点等价，不得宣称连续可微邻域；对最先出现的差异出具有理证据/反例。
4. 只有满足真实求值与接受状态的门槛，才启动 Cherchi/Faster Newton；独立导出并重新积分结果，不用 H8 81 点通过冒充真实 Heart 优化。

## 当期验收清单

- 报告 `H9_BRANCH_DECISION_CN.md`，附重放命令、点位、哈希、分支原因。
- 不允许把通过的 30/30 数值差分等价为 H8f 完整通过。
- 最终 Heart OBJ、收敛残差、物理指标必须真实产生，否则明确无终态。
- 所有重要进展提交本分支及 CI 证据。

## 所有窗口都必须遵守的规则

- 本任务是独立 GitHub **代码开发任务**，不是让对话在后台自行持续执行。每轮必须实际检查文件、编写代码、运行可用的测试并提交证据；未经执行不能声称通过。
- 仓库 `volcano-code/Spin_test`。禁止修改其 `main`、历史 `volcano-code/Spin`、`volcano-code/test/main`、他人 W 分支；不覆盖此前保存的失败 CI、历史报告、原始 CAD。
- 与其他窗口沟通通过 GitHub 的合同版本、提交 SHA 和文件链接；等待依赖时先完成自己的解析/纯代码 smoke，不得捏造依赖已完成。
- 每个里程碑提交新分支，反馈更改文件、通过/未通过的真实测试、误差/性能和下一步；所有优化必须保留完整材料与强真值独立验收。
- 按先前资源协议，大型原生作业串行、24GiB/swap0、每次≤60分钟、编译最多4并发；GPU 训练避免与其他窗口冲突。

