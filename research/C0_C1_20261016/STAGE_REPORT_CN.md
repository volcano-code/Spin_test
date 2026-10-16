# Noodles v6 — 今日 C0/C1 阶段成果与 C2 精度阻塞诊断

**状态：C0 原生小型和真实 v6 单管对照通过；C1 完整精确输入验收通过；C2 完整设计域接入仍受 float64 精度所阻；未启动 Newton 或动力学模拟。**

## 一、今天已备份什么

远端 `Spin_test` 的 `upstream-spin-it-strict-computational-v2` 与原 `Spin` 分支 HEAD 都是 `a17ff49cd8a1e6e8b388bc591410bda56d67c28a`；`main/research` 已备份规划、P0/P1a/P1b 报告、v6 生成器与研发续接索引。**原始大模型 ZIP、原生运行二进制及本轮新增代码/日志还没有自动上传到 GitHub。**本轮生成审阅包，先交用户批准，未对任何 GitHub 仓库执行新的写操作。

## 二、C0：Cherchi 真正调用 + 独立 CGAL 验证

- 基于已编译的原生 `_cherchi_core_boolean`：盒体重叠、分离、包含三组，交集/差集 6 项全部通过。逐项比较了真实 Cherchi 与独立 CGAL 的**精确有向表面链**、**10 个 Fraction 有理质量矩**，并核对 Cherchi 精确输出和构造来源字段。
- 使用真实 v6 `outer-ellipsoid-model.obj`（1,280 面）与 `tube-039-fixed-model.obj`（984 面），Cherchi 交集得 864 面、差集得 2,144 面；分别与 CGAL 独立精确面链和质量矩完全一致。Cherchi 布尔本体测时约 0.060 秒和 0.052 秒。**不能将此时间等同完整 Noodles 83,408 面设计域优化速度。**
- 该 Cherchi 编译库来自旧 `b0a13e3` 在线检查点；其 `InProcessBoolean.cpp` Git Blob `51252d2e2a4d128a6ad05f53799e29d329076482` 已与新分支上的同一路径一致；但不能因此称最新分支全项目生产构建已经完成。

## 三、C1：六个输入实体真实原生审计全部通过

此前 3 项 (`design`、`envelope`、`fixed`) 从原原生检查结果恢复、核验固定源码模块摘要与构造输入 SHA 后复用。本轮新增实际执行 `fixed-inside-envelope`、`fixed-outside-envelope`、`initial` 三项。结果：

| 实体 | 面数 | 通过 | 检查耗时（秒） | 实体连通分量 |
|---|---:|---|---:|---:|
| design | 83408 | PASS | 379.6 | 1 |
| envelope | 1280 | PASS | 0.5 | 1 |
| fixed | 92692 | PASS | 339.5 | 1 |
| fixed-inside-envelope | 81728 | PASS | 365.1 | 1 |
| fixed-outside-envelope | 30500 | PASS | 48.1 | 160 |
| initial | 32180 | PASS | 61.7 | 1 |

三项先前独立 Fraction 有向面链也实际证明：`F+D=A`、`K+D=E`、`K+R=F`，各非零支持平面数都为 **0**。本轮另外通过精确正面积重心/重心坐标，找到**设计域与初始外表面共面的真实开放边界见证**。这意味着：在已检查的有界 0/1 实体前提下，可将这三项链关系提升为精确集合分区依据。`fixed-outside-envelope` 存在 160 个独立材料分量，不等于整体 `fixed`（仅 1 个分量）不连通。

## 四、C2 的真实新阻塞：Cherchi 的 float64 输入无法无损表达完整设计域

原生 `design-rational.json` 在 exact rational 表示下是合法实体；然而当前 Cherchi API 只接收 `double` 输入顶点。独立扫描发现：

| 对象 | distinct exact 顶点在 float64 中碰撞的组数 | float64 退化三角形数 |
|---|---:|---:|
| design | 24 | **48** |
| fixed | 12 | 24 |
| envelope | 0 | 0 |
| initial | 12 | 24 |

其中 `design` 的 48 个坍缩三角形在**有理数精确几何下均非零面积**。多组不同精确顶点只相差约 1e-18 至 1e-35（模型单位）；以原比例转换为 double 会丢失拓扑信息。简单地“删除 48 面”“合并顶点”“忽略警告”都不能证明保留原集合、质量矩或原目标。因此当前**不应直接把完整 v6 rational design 送进 Cherchi 并宣称生产通过**。

新增 `cherchi_input_precision_guard.py`：输入有理数面网格、只检测别名顶点/坍缩面、返回明确错误；**不改动、焊接或删除任何面**。四项 pytest 已通过（含真实 v6 设计域拒绝）。此文件属于待批准的实验候选；目前没有替换你原项目的 Cherchi 求解代码。

## 五、下一阶段具体工作（C2）

1. 定位 24 组别名顶点及其 48 个非零有理面积面对应的 CGAL 出生面和源部件；先查是否源模型共轴角度/旋转计算造成微小裂片，避免优化后手工改网格。
2. 在不修改论文求解公式和原残差门槛前提下，尝试**精确集合等价**的局部重三角化；如这些微小面承载非零真实几何特征，必须认定精确无损重三角化不可行，另开版本化 v6.1 输入修复并重新计算独立几何。
3. 将通过的无损/有界新表示加入 Cherchi 入口，**以 Cherchi 作为每次 Newton 布尔求值的正式后端**。CGAL 仅执行静态输入构造和独立比较。
4. 通过 83,408 面新域的 Cherchi 真正求值、来源/Jacobian 对照，才能放行原生 Faster Newton、终态几何与旋转仿真。

**未推送 GitHub；制造暂缓。**