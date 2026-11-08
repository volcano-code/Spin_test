# W3 Heart H9｜M21.6C 混合面 LPI 支持数细分

日期：2026-11-08  
分支：`research/neuralmoments-w3-heart-h9-20261019`

## 1. 为什么做 M21.6C

M21.6B 的真实结果中，六个区间“最大残差分量”的独立 dual-number 分组残差，均由 `MIXED_EXPLICIT_LPI` 提供绝对值最大的组贡献。但这一类将“一个 LPI 顶点 + 两个显式顶点”与“两个 LPI 顶点 + 一个显式顶点”混在一起，不能判断哪一种混合支持更重要。

M21.6C 只细分现有面片分类，不改几何、顶点运动、积分公式、M20 ledger、M21.6A 边界报告或 Newton 门槛。

## 2. 新增分类

保留原四类及原字段，新增五类支持细分：

- `EXPLICIT_ONLY`
- `LPI_ONLY`
- `MIXED_1_LPI_2_EXPLICIT`
- `MIXED_2_LPI_1_EXPLICIT`
- `TPI_TOUCHING`

每个三角面按三个顶点的构造类型计数。原有 `MIXED_EXPLICIT_LPI` 输出保持不变；新增 `face_support_subgroup_moment_j7_summary` 和每个分量的 `support_group_residuals_exact`。

新输出 schema：`heart-h9-m21-6c-support-subgroup-audit-v1`。

## 3. 精确合同

每个保存表面均检查：
- 五个支持子组的面片数之和等于全部面片数；
- 五个支持子组的十个精确矩之和逐项等于原四组总矩；
- 五个支持子组的十个精确 J7 之和逐项等于原四组总 J7。

每个区间均检查：
- 五个支持子组的十个 exact residual 之和逐项等于总独立 replay residual；
- 原有 `R_native = R_replayed + ΔJ` 与四组 residual identity 继续保留。

因此新增支持细分不会替换或改变 M21.6B 原有结果定义。

## 4. GitHub 变更

- `source/h9_m21_6b_moment_layers.py`：加入 `support_group()`、可选支持子组累积、精确矩/J7/区间残差守恒门禁；schema 升级为 M21.6C。
- `tests/test_h9_m21_6b_moment_layers.py`：新增 3 项测试，覆盖 1-LPI/2-LPI 分类、面片/矩/J7 总量守恒、区间 residual 子组求和。
- 预期单元测试总数：18 项（原 15 项 + 新增 3 项）。

代码已推送，但**本地 18 项测试尚未运行，本次真实六材料的子组计算也尚未运行**。不把代码提交误报为验收通过。

## 5. 本地执行范围

只需同步代码、运行 18 项单元测试，然后重跑既有 `native-layers` 离线阶段，输出到全新目录。

本轮无需：
- 新 Cherchi Boolean；
- 新 native source 调用；
- CGAL；
- GPU；
- 重新编译 native binary。

但仍需本地访问六份历史材料及 source-motion 附件。M21.6C 的真实分组数和残差值必须等本地输出后再报告。

## 6. 科学限制

`support_group_residuals_exact` 仍是**独立 dual-number 重放**的面片支持分层，不是 C++ 原生逐子组 J7。新增细分可以定位 1-LPI 与 2-LPI 混合面在独立重放残差中的不同贡献，但不能单独证明某组是唯一根因。

`per_support_subgroup_native_jacobian_available=false`、`root_cause_determined=false`、`continuous_neighborhood_certified=false`、`asymptotic_order_certified=false`、`newton_admitted=false` 均继续保持。若要区分半区间内部变化，还需要在固定身份/拓扑合同下获取真实 quarter-point 材料和 source-motion 证据；不能用线性插值冒充新的真实表面。
