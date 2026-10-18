# W4｜2014 Utah Teapot 保形实体修复与优化初态

**GitHub 仓库：** `volcano-code/Spin_test`  
**唯一写入分支：** `research/neuralmoments-w4-teapot-p1-20261019`  
**冻结源版本：** `24f89ed21c251a8678aceb997e4ca30e4ba24125`  
**独占文件范围：** research/SpinIt2014_Teapot_20261018/ 下 P1 文件（不覆盖原 OBJ）  
**依赖：** 原始 teapot P0 已通过；正式目标与矩需要 W0 合同

## 给新聊天复制的启动指令

> 我负责并行研究窗口 **W4：2014 Utah Teapot 保形实体修复与优化初态**。请先通过 GitHub 连接器读取 `volcano-code/Spin_test` 分支 `research/neuralmoments-w4-teapot-p1-20261019` 中的 `research/ParallelLaunch/W4_START_HERE.md`，把它作为本窗口唯一任务说明。仅修改此分支独占范围，先检查代码和现状，再马上实现可验证的首个里程碑，运行测试，提交到自己的 GitHub 分支并返回 commit SHA、CI/日志、真实成果及尚未完成事项。不要只给规划，不要等待其他窗口即可做的 smoke；没有权限或工具时说明阻碍，绝不冒充推送。

## 具体工作

1. 从已审计公共 `input/teapot-public-original.obj` 原件出发（3644点/6320面/19原索引连通分量/160条开边）；审计 run 39126326305。
2. 不改源文件，仅创建可追踪的修复实体新文件，记录边界孔洞、面方向、连通性、体积等价/偏差及几何修复策略；公开 Teapot 不等于 Spin-It 作者原始 CAD。
3. 建立明确尺度与坐标变换、目标轴、轴尖、固定杆/外壳 F、可删区域 D，输出新初始 OBJ、F/D OBJ 与物理矩初态表。
4. 优化方案先登记原 Spin-It Teapot 图9对应的惯量、降低质心、减质量三个消融；只有合法实体并通过 W0/W2 真实教师才能运行。

## 当期验收清单

- 源 OBJ 的 upstream SHA 原样保存、修复体闭合/无自交/一致朝向的独立结果。
- F 与 D 不重叠；保存后材料重读/独立矩、尺度和轴尖审核。
- 绝不能把目前 P0 Input Audit PASS 写成 Teapot 已优化。

## 所有窗口都必须遵守的规则

- 本任务是独立 GitHub **代码开发任务**，不是让对话在后台自行持续执行。每轮必须实际检查文件、编写代码、运行可用的测试并提交证据；未经执行不能声称通过。
- 仓库 `volcano-code/Spin_test`。禁止修改其 `main`、历史 `volcano-code/Spin`、`volcano-code/test/main`、他人 W 分支；不覆盖此前保存的失败 CI、历史报告、原始 CAD。
- 与其他窗口沟通通过 GitHub 的合同版本、提交 SHA 和文件链接；等待依赖时先完成自己的解析/纯代码 smoke，不得捏造依赖已完成。
- 每个里程碑提交新分支，反馈更改文件、通过/未通过的真实测试、误差/性能和下一步；所有优化必须保留完整材料与强真值独立验收。
- 按先前资源协议，大型原生作业串行、24GiB/swap0、每次≤60分钟、编译最多4并发；GPU 训练避免与其他窗口冲突。

