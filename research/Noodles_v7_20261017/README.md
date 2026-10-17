# Spin / Noodles V7 — 2026-10-17 frozen research checkpoint

**性质**：照片引导的输入重建，以及在该输入上一次 Cherchi / Faster Newton 数值收敛和最终浮点网格几何审核。**不是**原作者 CAD 的严格复现，也**没有**通过完整桌面接触动力学、多随机种子或 3D 打印验收。

此目录是从原研究会话独立封存的 V7 成果；它保留原始源码、Newton 事件、CGAL 精确布尔/精确链证明、质量矩和静态枢轴测试证据。原 `volcano-code/Spin` 仓库不被修改；现有 Spin_test 历史不覆盖。源码的部分 `/mnt/data/...` 路径来自原实验环境，须根据本地 Cherchi/CGAL/Faster 工具和输入位置适配，不应宣传为开箱即跑。

## 已记录并验收的一次 V7 运行

- 79 根弯曲管束；94/94 源部件几何审核通过，96 次原生 CGAL 精确布尔。
- 固定材料 112,982 面；可优化设计域 106,684 面。
- **第一次试跑接受 3 步**，随后由保存的已接受 `q` 重新启动另一轮原生求解并接受 5 步，第二轮 `CONVERGED`，残差 **2.8251949346891595e-14**。这属于 warm restart，不是同一 solver 线程恢复。
- 终态精确材料输出经一般化有理等价重三角化，`complete-mm-repaired.obj` 为 **86,076 面**；终态 0 个毫米尺度零面积面、单连通、无自交，质量矩独立误差 **2.22e-16**。
- 密度 1200 kg/m³ 时，初始质量 **26.989669 g**，终态质量 **18.483895 g**（减少 **31.5149%**）。
- 探索性理想固定尖端旋转测试**不等同**于真实地面接触仿真或真实稳定性验证。

## 证据导航

- [V7_STAGE_REPORT_CN.md](V7_STAGE_REPORT_CN.md) — 范围、求解结果、静态物理测试、尚未通过的验收。
- [V7_STAGE_STATUS.json](V7_STAGE_STATUS.json) — 冻结计算状态和精确数值；`GitHub_write_performed=false` 是**原报告生成时**的历史状态，不表示该目录没有随后备份。
- [source/](source/) — 重建生成、求解恢复、精确布尔导出与修复、独立几何/物理审计源码。
- [evidence/newton/](evidence/newton/) — 接受事件、初始/继续求解、最终真实收敛记录。
- [evidence/terminal/](evidence/terminal/) — 独立终态检验与质量矩。
- [evidence/input/](evidence/input/) — 构造输入、分区与精确证明记录。
- [frozen-parts-v7c/manifest.json](frozen-parts-v7c/manifest.json) — 源几何构件摘要，而非全部实体文件。
- [frozen-inputs/author-rational/](frozen-inputs/author-rational/) — 原始有理输入的结构证明概要；**大型有理输入本体不在本次文本证据快照中**。

## 模型资产与限制

`models/complete-mm-repaired.obj` 是本阶段唯一被认证的终态完整模型；其原始文件 SHA-256 为 `e979bd3980a5efaf9b03d047c4e19e9296ddb426267a7322ff4e1a4b954fe80a`。若 `models/` 下没有该文件，说明原始模型**尚未传入此 GitHub 检查点**，不能用未修复的 `complete-mm.obj` 代替。预览为 `models/Noodles-v7-paper-guided-optimized-preview.glb`；本地归档中的参考图/大型分区数据如果未见于仓库，也应视为尚未备份。

以上状态来自 2026-10-17 冻结实验产物；推送本身不等于重新运行仿真或本地编译验收。
