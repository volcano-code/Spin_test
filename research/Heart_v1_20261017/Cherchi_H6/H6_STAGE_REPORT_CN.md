# Heart H6：真实 Cherchi 质量矩 Jacobian 局部验收与构造分支诊断（2026-10-18）

## 本轮完成的事实

本轮实际使用原生 `_make_it_stand`（SHA-256 `24386389631f9bbeaa3a331fe14dce43eda150f020c7d1d07e9784dc4e63208f`）、Cherchi 7bd6c269 的 `_cherchi_core_boolean`（SHA-256 `e96e0ef827764f2d30cdf0ad9e4cc1cf990fd4e622bfd44c1eec27918aeefc0a`）及项目正式 `InProcessCherchiEvaluator`，对**历史 Heart V4 代理输入**进行真实源面、布尔、构造来源运动、十项质量矩及 10×10 Jacobian 求值。**未使用 CGAL 代替动态布尔，未运行 Newton，没有将历史代理升级为真正 eval60。**

- 输入：归档 V4，原文件 931258 字节，V4 输入 SHA-256 为 `fa0a7eac8046be48fbfac495c7e6e283ebe7033d6242b64997aa28216b5c92f4`。该 V4 原文件已以 `input/archived-heart-v4-request.json.gz.b64` 无损保存，解码后核验 SHA-256；登记的 q 在 `input/registered-eval60-coefficients.json` 中。
- 首次完整同次调用计数：source 25、Cherchi Boolean 25、intersection_motion 25、derivative 25、integration 25；每个状态都返回实际 10 项质量矩和 10×10 Jacobian。共用时 **214.629 秒**。
- 选取参数方向 **0、4、8**，在 3e-6、1.5e-6、0.75e-6 三个登记尺度执行五点差分，唯一真实 Cherchi 材料求值点 **25 个**。全部 **9/9** 数值检查低于 1e-6 门槛；最大相对差异 **2.560e-11**。系数尺度方向 `||Jq||₂` 为 **2.991e-15**。
- 在另一个 25 点只读 Cherchi 来源取证中，二次曲面源面始终 **168 顶点 / 328 三角面**，Cherchi 输出 **793 顶点 / 1570 三角面**，源面法向边、法向顶点、projective rays、截断半径一致。
- **不能授予导数分支认证：** 与基点相比，24 个扰动点中的 **22** 个存在规范化材料面连接特征不同，其中 **4** 个还存在构造顶点来源特征不同。面和顶点数量不变≠邻域拓扑和构造分支认证；不据此认定实体拓扑变化或全部等价重三角化。
- **正式配置仍缺失：** 原 `heart-certified-formal-seed-1-job-01/output/run/configuration.json` 与 `events.jsonl` 因历史归档排除运行输出而不可用。严格收集器要求各自 SHA-256 为 `071c799c92b522fb3d4de4b9aacf9a9ae8bcae102a49940f33f4037f28a74141` 与 `2333a9e3c87d9e6b7d3a73676fe9bd940f6e500c9c20b7ce34867d2475269b70`。直接使用 V4 文件或缺失文件会失败，绝不自动填补。
- **新版本构建未完成：** 本轮复用已恢复的 2026-10-15 历史原生二进制，不宣称最新 Spin 源码重新编译通过。

## 真实测试与证据

- `evidence/three-column-numerical-report.json` 保存完整 10×10 J、十质量矩、9 组差分、25 点后端/几何摘要及调用次数。
- `evidence/three-column-feature-classification.json` 保存 25 点 source/Boolean 构造分支的逐字段对照；变化于规范面和来源标签，不是已证实的真实实体拓扑变化。
- `evidence/three-column-stdout.log` 记录 25 个真实 Cherchi 完整材料点的逐次时间；`evidence/feature-probe.log` 记录额外 25 个 Cherchi 只读布尔取证点。
- `evidence/pytest-all.log` 为 **20 passed**；其中纯 Python 测试只检测身份、导数采样约定、归档无损性和保存的报告约束，不能当作 GitHub 原生 CI。
- `evidence/collector-real-absence-test.log` 是预期失败：`MISSING_AUTHENTIC_HEART_EVAL60_FILES:configuration,events`，被明确记录而非重构伪造。

## 尚未通过 / 下一阶段

1. 必须获取原始文件（配置、事件及同次依赖）并验证实际 SHA-256；历史 V4 仅用于局部数学研究。
2. 进一步分辨 22 份材料面片连接变化：实际布尔特征切换、有效共面重三角化、或数值输出编号；四份构造来源改变更需保留真实分支事件。
3. 正式协议为十个参数方向共 **81** 个唯一材料求值点，而非当前 25 点；只有适用分支认证和独立材料矩验证满足后才可讨论全面通过。
4. 真正 Heart seed0/1 的 Cherchi + Faster Newton 收敛、终态封存与 OBJ、MuJoCo 接触仿真仍未运行或验收。

**阶段判定：`REAL_CHERCHI_V4_PROXY_JACOBIAN_3_OF_10_NUMERIC_PASSED_BUT_BRANCH_NOT_CERTIFIED_AND_FORMAL_INPUT_MISSING`。**
