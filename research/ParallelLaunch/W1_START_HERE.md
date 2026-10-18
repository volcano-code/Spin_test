# W1｜Faster/Cherchi 原生性能收尾

**GitHub 仓库：** `volcano-code/Spin_test`  
**唯一写入分支：** `research/neuralmoments-w1-native-20261019`  
**冻结源版本：** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**独占文件范围：** research/NeuralMoments/performance/；共享 src/bindings 候选修改只能在本分支、需独立构建和全量回归  
**依赖：** 独立开展性能采样；合并优化需 W0 合同及 W2 教师比对

## 给新聊天复制的启动指令

> 我负责并行研究窗口 **W1：Faster/Cherchi 原生性能收尾**。请先通过 GitHub 连接器读取 `volcano-code/Spin_test` 分支 `research/neuralmoments-w1-native-20261019` 中的 `research/ParallelLaunch/W1_START_HERE.md`，把它作为本窗口唯一任务说明。仅修改此分支独占范围，先检查代码和现状，再马上实现可验证的首个里程碑，运行测试，提交到自己的 GitHub 分支并返回 commit SHA、CI/日志、真实成果及尚未完成事项。不要只给规划，不要等待其他窗口即可做的 smoke；没有权限或工具时说明阻碍，绝不冒充推送。

## 具体工作

1. 从冻结 Noodles V7、Heart H8 输入提取可重放求值任务；优先核对 `research/Noodles_v7_20261017/V7_STAGE_STATUS.json` 与原生日志计时口径。用户先前提供的 393.44s/168.27s 尚需找到同次原始证据，不得与其他作业的569.56s或199.00s拼接。
2. 分别测量源面、Cherchi Boolean、GMP 原始十矩、构造来源/导数、Python Fraction 转换、JSON 快照、同次验证；要求互斥阶段和端到端计时。
3. 实现不改变数学的最小原生 `PreparedMaterial` / source-ref 持有试验，避免无必要的精确 rational 字符串 roundtrip；若改 `src/` 或 `bindings/`，仅在此分支修改并明确 ABI 边界。
4. 对输入实体、十矩、Jacobian、接受/拒绝、终态材料进行同输入旧/新等价测试；不能通过跳过未证明可省的几何验收来虚增速度。

## 当期验收清单

- `baseline-performance.json` 含输入/二进制 SHA、硬件、内存、样本与分段互斥耗时。
- `before_after.json` 完整记录修改前后，不能只展示局部 microbenchmark。
- 大型原生作业串行、≤24GiB/swap0、单次≤60分钟、编译≤4并发。
- 未完成作者同条件跑分前不宣称达到 paper speed。

## 所有窗口都必须遵守的规则

- 本任务是独立 GitHub **代码开发任务**，不是让对话在后台自行持续执行。每轮必须实际检查文件、编写代码、运行可用的测试并提交证据；未经执行不能声称通过。
- 仓库 `volcano-code/Spin_test`。禁止修改其 `main`、历史 `volcano-code/Spin`、`volcano-code/test/main`、他人 W 分支；不覆盖此前保存的失败 CI、历史报告、原始 CAD。
- 与其他窗口沟通通过 GitHub 的合同版本、提交 SHA 和文件链接；等待依赖时先完成自己的解析/纯代码 smoke，不得捏造依赖已完成。
- 每个里程碑提交新分支，反馈更改文件、通过/未通过的真实测试、误差/性能和下一步；所有优化必须保留完整材料与强真值独立验收。
- 按先前资源协议，大型原生作业串行、24GiB/swap0、每次≤60分钟、编译最多4并发；GPU 训练避免与其他窗口冲突。

