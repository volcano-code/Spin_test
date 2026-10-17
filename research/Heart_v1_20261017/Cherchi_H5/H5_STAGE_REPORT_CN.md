# Spin / Heart H5：后处理式 Cherchi OBJ 导出接口阶段报告

日期：2026-10-17。仓库目标：`volcano-code/Spin_test` 的 `research/heart-p0-p3-20261017` 隔离分支。原 Spin 和 Spin_test/main 不动。

## 结论

**H5 已为真实 Cherchi 输出实现可独立调用的通用、失败即拒绝的精确等价 OBJ 后处理器。**在既有 H1 历史 V4 代理模型上通过原生审核，且导出顶点和面连接与 H4 的成功证书**完全一致**。没有修改 Newton 求解算法及 Cherchi 布尔接口，也没有把它接进求解器内部，更没有实际完成正式 Heart/Newton 重放。

## 本轮开发

1. `source/cherchi_exact_flip.py`：抽取可复用的精确同平面/凸四边形换边、全局有向面链、十原始矩分析，未绑定 793 顶点或 H4 具体 SHA。
2. `source/cherchi_obj_export.py`：读取 H1 Cherchi packet，或从实际完成的 Cherchi 原生求解持久化目录验证终态材料绑定，再以保存材料为权威数据修复**独立导出件**；Cherchi 之外的布尔求值后端坚决拒绝。
3. 对正式运行的验证要求包括：`CONVERGED`、实际 accepted updates、原生 Newton q、材料 SHA、几何摘要、Cherchi producer identity、终态补集状态、材料来源，且禁止直接把 proxy packet 贴上正式运行标签。此部分通过的是**负例与结构性回归**，缺少真实正式收敛 Heart 记录，不能授予正式运行链路通过。
4. 修复前后对全部未更改面片做严格代数抵消，只对全局发生变更的面片重积分十个有理质量矩。此操作与整面重积分的*差值*精确相同，解决了旧版 Python `Fraction` 极大分子分母全模型独立积分在小型容器内超时的问题。保留原先执行 90 秒和 220 秒被杀的失败历史，不把这些超时计为通过。
5. 每个最终输出必须通过原生有理边界、binary64 边界与 OBJ 回读；出错时输出拒绝证书，且没有 .obj 产物。

## 实际 H1 V4 代理材料验收

| 指标 | 实测 |
|---|---:|
| 基准 Cherchi 输出 | 793 顶点、1570 面 |
| 初始 binary64 自相交 | 78 对 |
| 修复后 binary64 自相交 | **0 对** |
| 安全有理共面换边 | **38 次 / 5 轮** |
| 变化面片记录 | 64 面 |
| 全局精确有向支撑面链 | **完全一致** |
| 全局十项质量矩变化 | **逐项精确为 0** |
| 最终原生 exact-rational 审核 | **PASS** |
| 最终原生 binary64 OBJ 重新导入 | **PASS** |
| 与 H4 合格 OBJ（跳过头部注释） | **完全相同** |
| H5 测试 | **14/14 PASS**，含原生测试，约 22.71 秒 |

**原生审计模块**：历史 CPython 3.13 `_make_it_stand`，SHA `24386389631f9bbeaa3a331fe14dce43eda150f020c7d1d07e9784dc4e63208f`。该旧检查点不是从最新 GitHub 源码全量重编译的新正式 Heart 模块。

## 仍未通过

- 真正 `eval60` 对应配置和 accepted Heart 终态文件仍缺失。
- H5 已实现**正式运行目录的独立后处理入口**，但未在真实正式 Heart 收敛输出上运行，也未自动写入既有正式求解器工作流。
- 完整 Heart 主体/轴杆装配、有理模型坐标变换、真实 10×10 Jacobian、真正收敛与独立重复、接触动力学、制造未验收。
- 此次输出 OBJ 只代表 **H1 V4 代理的 Cherchi retained material（TARGET_NORMALIZED 坐标）**，不得称论文 Heart 终态或完整可打印 OBJ。

## 下一阶段 H6

取得与原始冻结 Heart 输入一致的持久化请求及源码/模块身份，使用正式求解器完成真正 Cherchi 材料 Jacobian 验收；若获得合格的 accepted terminal，再以 H5 `--formal-run` 实测真实 Heart 导出、独立复算组件及毫米坐标。只有正式输出通过，才考虑把本独立后处理接口显式接入生产封存后阶段。
