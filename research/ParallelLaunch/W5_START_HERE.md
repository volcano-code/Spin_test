# W5｜DE-DeepONet-Moment＋轻量 Geometry-MLP 基线

**GitHub 仓库：** `volcano-code/Spin_test`  
**唯一写入分支：** `research/neuralmoments-w5-deeponet-20261019`  
**冻结源版本：** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**独占文件范围：** research/NeuralMoments/models/deeponet/、research/NeuralMoments/models/geometry_mlp/ 和独立 tests  
**依赖：** 网络 smoke 可用解析数据；正式教师与训练需 W0、W2 发布冻结合同

## 给新聊天复制的启动指令

> 我负责并行研究窗口 **W5：DE-DeepONet-Moment＋轻量 Geometry-MLP 基线**。请先通过 GitHub 连接器读取 `volcano-code/Spin_test` 分支 `research/neuralmoments-w5-deeponet-20261019` 中的 `research/ParallelLaunch/W5_START_HERE.md`，把它作为本窗口唯一任务说明。仅修改此分支独占范围，先检查代码和现状，再马上实现可验证的首个里程碑，运行测试，提交到自己的 GitHub 分支并返回 commit SHA、CI/日志、真实成果及尚未完成事项。不要只给规划，不要等待其他窗口即可做的 smoke；没有权限或工具时说明阻碍，绝不冒充推送。

## 具体工作

1. 基于十维 `c` 与几何输入建立 `encode_geometry(D)->z_D`、`moment(z_D,c)->r[10]`、`jacrev(...)->J[10,10]`，每个 D 编码一次，重复 c 只付轻量 head 成本。
2. 实现几何编码+参数主干 DeepONet 式模型，同时实现容量可比较的轻量 Geometry-MLP；记录参数量、算力、冷/热几何编码与一次 10×10 Jacobian 耗时。
3. 用解析立方体/球/椭球构造适用的真值集 smoke；真实复杂几何标签一律通过 W2 引入，不可用网络自生成伪真值。
4. 导数增强训练与不增强对照、0/1/2/4/8 查询适配初始接口；不先训练大型网络，不声称原 NeurIPS 网络代码已在本项目完整复现。

## 当期验收清单

- 同随机种子、固定数据来源、按几何家族划分训练测试；所有变换由 W0 合同验证。
- 预测 r、真实 J/方向导数与优化决策误差分别报告。
- 禁止没有数据的加速宣称；训练超参数与 GPU 时间计费。

## 所有窗口都必须遵守的规则

- 本任务是独立 GitHub **代码开发任务**，不是让对话在后台自行持续执行。每轮必须实际检查文件、编写代码、运行可用的测试并提交证据；未经执行不能声称通过。
- 仓库 `volcano-code/Spin_test`。禁止修改其 `main`、历史 `volcano-code/Spin`、`volcano-code/test/main`、他人 W 分支；不覆盖此前保存的失败 CI、历史报告、原始 CAD。
- 与其他窗口沟通通过 GitHub 的合同版本、提交 SHA 和文件链接；等待依赖时先完成自己的解析/纯代码 smoke，不得捏造依赖已完成。
- 每个里程碑提交新分支，反馈更改文件、通过/未通过的真实测试、误差/性能和下一步；所有优化必须保留完整材料与强真值独立验收。
- 按先前资源协议，大型原生作业串行、24GiB/swap0、每次≤60分钟、编译最多4并发；GPU 训练避免与其他窗口冲突。

