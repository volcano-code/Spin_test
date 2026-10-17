# Spin / Heart Cherchi H1：真实 Boolean、精确有理材料与浮点导出风险

**日期：2026-10-17；研究范围：**仅针对*历史较早的 Heart V4 设计域*，配合从原 `seed1/eval60` 事件复制的真实十维二次曲面系数，复测一次 Cherchi 动态多面体 Boolean，并独立复核得到的精确材料。**这不是**原始 eval60 冻结几何重放、不是完整 Heart Newton 成功、不包含完整材料 Jacobian 或接触动力学验收。

## 结论（必须区分两种几何表示）

| 事实 | 实际结果 |
|---|---|
| 代理 Heart 设计输入 | 718 顶点 / 1,436 面；独立输入精确边界审核通过 |
| 当前 q 生成的源曲面 | 168 顶点 / 328 面；独立输入精确边界审核通过 |
| **正式布尔后端** | `_cherchi_core_boolean.boolean`，`intersection`，约 0.32 秒；无回退 |
| 实际 Cherchi 结果 | 793 顶点 / 1,570 面 / 793 份构造来源 |
| **有理数精确网格审计** | closed、edge/vertex manifold、合法组件方向，**0 对自相交**；通过 |
| **binary64 展示坐标审计** | 闭合/流形/方向检查通过，但**78 对自相交**；不通过 |
| 独立同操作数多面体 Boolean 集合比较 | `completed=true, a_subset_b=true, b_subset_a=true, equal=true, symmetric_difference_volume_exact=0/1` |
| 独立比较耗时 | 约 76.86 秒（包含有理区域构造/对照），不可与 Cherchi 单次 Boolean 速度混算 |
| 真正原始 eval60 配置/事件日志校验 | **未通过：备份中缺少哈希匹配的原始文件** |
| 完整 Heart Newton 优化 | **未执行；未收敛验收** |

Cherchi 导出的 2,379 个单坐标数值里，有 1,428 个精确有理数无法用 binary64 精确表示；所有展示浮点值都等于对应有理数进行一次正确二进制舍入后的值。这解释两种审核的输入为何不同，不能仅凭该统计直接推断全部 78 对自交的局部几何机理。

**技术判定：**本次有理数输出代表合法精确多面体材料，且与独立的同操作数参考 Boolean *实体集合* 完全一致。但是面向 OBJ 的 float64 材料网格必须拒绝：只有经过独立几何等价认证的导出修复才能成为正式模型，不能直接使用不合格浮点三角面或把有理网格通过冒充浮点网格通过。

## 算法分工

正式 Boolean 调用仅为 **Cherchi**。独立精确审核及实体比较运行了 native 几何工具（内部 CGAL），但只检查 Cherchi 输出正确性，**不参与参数优化、不返回替代保留材料、不作为 Newton 的后备 Boolean。**在 Cherchi 模块缺失、backend 伪装、构造来源不完整和精确审核失败时，保护程序明确拒绝。

## 验证过的二进制身份

- `_make_it_stand` SHA-256：`24386389631f9bbeaa3a331fe14dce43eda150f020c7d1d07e9784dc4e63208f`
- `_cherchi_core_boolean` SHA-256：`e96e0ef827764f2d30cdf0ad9e4cc1cf990fd4e622bfd44c1eec27918aeefc0a`
- V4 代理输入 fixture SHA-256：`2fa4867bc5ef8f62ab2a9c866a2493d49bd7788e5ef0c74318ad98f6f9e52d13`

以上扩展来自已存档原生运行检查点，**不是本轮对 `a17ff49` 最新主源码的全新生产构建**。实际求交操作数保持不变；没有算法收敛或性能外推。

## 新交付与回归

- `source/cherchi_heart_guard.py`：只接纳真实 Cherchi backend，检查来源记录、精确有理数与浮点网格，拒绝伪成功。
- `source/run_heart_h1.py`：明确指定 V4 代理输入，执行原生 source → Cherchi → 两套独立审核；仅封存有理 JSON，浮点非法则不导出 OBJ。
- `source/run_authoritative_eval60_cherchi.py`：未来只有获取真正原始 `configuration.json` 和 `events.jsonl` 并通过两份 SHA 时才允许重放；禁止使用 V4 代理替换。
- `source/compare_independent_exact_set.py`：独立验证程序，使用 CGAL 作为审核、不是 Boolean 生产路径。
- `input/heart_v4_proxy_fixture.json`：含 718 顶点设计域的精简重放输入，明确非原始 eval60。
- `output_proxy_v1/cherchi-authoritative-exact.json`：Cherchi 1,570 面原始精确有理数数据、构造来源。**并非合格浮点 OBJ。**
- `evidence/independent-exact-set-comparison.json`：独立双向包含 / 对称差 `0/1` 证据。
- `tests/`：16 条 pytest 纯 Python 防回退、来源绑定、精确/浮点隔离、真实 eval60 输入认证反例，全部通过。实际原生求交另外有成功记录。

## 尚未完成、不可误报

1. 备份缺少历史原始 eval60 的 `configuration.json`（预期 SHA-256 `071c799c92b522fb3d4de4b9aacf9a9ae8bcae102a49940f33f4037f28a74141`）和 `events.jsonl`（预期 `2333a9e3c87d9e6b7d3a73676fe9bd940f6e500c9c20b7ce34867d2475269b70`）。严格重放当前必然阻塞。
2. 新修复源面策略在**正式 Heart 冻结域**上的 81 点源速度、10 质量矩、10×10 Jacobian 和三尺度门仍需通过；此前 V4 的 30 项导数检查有一项 `7.824e-6 > 1e-6`。
3. 需恢复作者案例或当前正式 Heart 输入、重建并独立绑定 F、D、A 分区、最新二进制身份、真正 Cherchi Newton 多种子完整收敛、终态空腔、FLOAT/OBJ 认证以及 MuJoCo 接触实验。

**阶段结论：**`HEART_V4_PROXY_CHERCHI_EXACT_BOOLEAN_EQUIVALENT__FLOAT64_EXPORT_REJECTED__ORIGINAL_EVAL60_UNAVAILABLE`。
