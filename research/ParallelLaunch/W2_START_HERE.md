# W2｜真实 Cherchi 教师与数据契约

**GitHub 仓库：** `volcano-code/Spin_test`  
**唯一写入分支：** `research/neuralmoments-w2-teacher-20261019`  
**冻结源版本：** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**独占文件范围：** research/NeuralMoments/teacher/ 和对应独立 tests/（不改公共 core）  
**依赖：** 对外发布正式标签前等待 W0 MomentContractV1；可以先开发 adapter/mock

## 给新聊天复制的启动指令

> 我负责并行研究窗口 **W2：真实 Cherchi 教师与数据契约**。请先通过 GitHub 连接器读取 `volcano-code/Spin_test` 分支 `research/neuralmoments-w2-teacher-20261019` 中的 `research/ParallelLaunch/W2_START_HERE.md`，把它作为本窗口唯一任务说明。仅修改此分支独占范围，先检查代码和现状，再马上实现可验证的首个里程碑，运行测试，提交到自己的 GitHub 分支并返回 commit SHA、CI/日志、真实成果及尚未完成事项。不要只给规划，不要等待其他窗口即可做的 smoke；没有权限或工具时说明阻碍，绝不冒充推送。

## 具体工作

1. 阅读 `python/make_it_stand/verification/cherchi_inprocess.py`、`faster_material.py`、H8 81 点保存协议和 Noodles V7 现有数值证据。
2. 建立 `native_cherchi_teacher.py`：一次请求返回带完整身份的 `r_D,J_D`、构造拓扑/合法性状态与阶段耗时；固定矩 `r_F` 独立标注，不能 double count。
3. 建 `teacher_manifest.json` / schema：几何、密度、坐标、模型 SHA、native module SHA、q、十矩/导数、适用导数合同、失败原因、exact proof 和数据划分。
4. 在已验证的解析闭合体与合法 Frozen Heart/Noodles 样本上运行 smoke；H8 point60 只能独立标记为 branch-change/unknown，不自动作为平滑导数真值；Teapot 开边界不能作为合法体积教师。

## 当期验收清单

- 标签重读 SHA 和 q 严格一致，丢失/篡改/交叉系数交换必须拒绝。
- 精确十矩与独立 reference 对比；分离物理矩与导数合法性状态。
- 记录真实教师耗时和内存；每条失败也入账；不编造新训练数据。
- 不启动并发大量 Cherchi 作业抢 W1/W3 资源。

## 所有窗口都必须遵守的规则

- 本任务是独立 GitHub **代码开发任务**，不是让对话在后台自行持续执行。每轮必须实际检查文件、编写代码、运行可用的测试并提交证据；未经执行不能声称通过。
- 仓库 `volcano-code/Spin_test`。禁止修改其 `main`、历史 `volcano-code/Spin`、`volcano-code/test/main`、他人 W 分支；不覆盖此前保存的失败 CI、历史报告、原始 CAD。
- 与其他窗口沟通通过 GitHub 的合同版本、提交 SHA 和文件链接；等待依赖时先完成自己的解析/纯代码 smoke，不得捏造依赖已完成。
- 每个里程碑提交新分支，反馈更改文件、通过/未通过的真实测试、误差/性能和下一步；所有优化必须保留完整材料与强真值独立验收。
- 按先前资源协议，大型原生作业串行、24GiB/swap0、每次≤60分钟、编译最多4并发；GPU 训练避免与其他窗口冲突。

