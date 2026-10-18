# Heart H8e：真实 Cherchi/Faster 三列 25 点有限样本导数＋构造取证

日期：2026-10-18；对象是 H8 非对称 **重建 CAD，非作者原 CAD**。

## 一、原生数值运行（保留其严格原始失败标志）

- GitHub 原生 job：<https://github.com/volcano-code/Spin_test/actions/runs/39121571756>，artifact ID `12134772056`（`heart-h8e-25point-real-jacobian-proof-or-failure`）。
- 真实 25/25 点 Cherchi Boolean、精确有理材料边界、独立 Fraction 十质量矩、原生 GMP 十维导数和十矩都完整返回；没有 CGAL 动态 Boolean 后备。
- 25 次端到端总 wall `379.493727883s`（~15s/点，含每点独立审计和持久化；**不是完整 Newton 求解时间**）。
- 完整 25 份 `point-XXX-material.json.gz` 连同逐文件 SHA-256 均已保存。
- 与 H8d 冻结基线模型坐标十质量矩做目标轴尖坐标变换，最大绝对误差 `5.551115123125783e-17`，`baseline_model_to_target_ten_moments_verified=true`。
- 完整 10×10 解析 Jacobian 在基点实际计算，`||Jq||₂=1.0649829225206779e-15`。
- 三列九项差分：\n
| 系数方向 | 3e-6 | 1.5e-6 | 0.75e-6 |
|---|---:|---:|---:|
| q[0] | 2.9987497227573026e-11 | 6.708998947717519e-11 | 2.6229806854310685e-10 |
| q[4] | 3.169429428617817e-11 | 1.1993909808427568e-10 | 2.2908089765398788e-10 |
| q[8] | 2.0798009771003743e-11 | 1.158580847327133e-11 | 1.2073109287083335e-10 |

九项全部低于 `1e-6`。原生 CI **failure** 仅因严格原始 `all_tested_stencils_same_feature_hash=false`（8/24 点）而触发，必须保留这份失败原始取证，不能修改既有 job 结论。

## 二、真实 25 份有理构造离线复核（成功）

- 独立 GitHub job：<https://github.com/volcano-code/Spin_test/actions/runs/39122997405>，**success**；artifact ID `12134499573`（`heart-h8e-twenty-five-exact-source-classification`）。
- 该审计独立下载上述**失败**原生 job 上传的 25 份真实同次 Cherchi 材料，并校验全部 SHA、原始 q、后端身份、构造点几何及模型操作数。
- 结果：`complete_material_snapshots_verified=25`，`exact_plane_diagnostics_resolved_points=25`，`unresolved=0`；相对基点 **24/24** 份分类均为 `SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED`，没有其他类别。
- 源面 `quadric_source_faces` 对所有 25 个点一致，输出顶点 8455 / 面 16910、输出 material_faces 完全一致，构造点始终 7671×EXPLICIT3D + 784×LPI。
- 八处原始 hash drift **只发生于 q[8] 方向**。根据原始 `resolved_construction_records`，每个失败采样点只有一个交点的 LPI **直线两个端点顺序互换**：
  - 交点 8161：`(source,6),(source,104)` ↔ `(source,104),(source,6)`
  - 交点 8164：`(source,100),(source,7)` ↔ `(source,7),(source,100)`
  - 对应构造平面三顶点不变；LPI 所定义的无向直线与平面交点不因线端点互换而改变。独立精确支撑面/三角面观察确认两种表示位于同一离散符号面片身份。
- 这解释了生产 `SOURCE_FEATURE_BRANCH_V2` 的原始 hash 对定义点方向敏感；**不能因此修改历史源码或篡改原始 hash**。数学上等价的端点表示应当在单独经过验证的规范化构造关系中比较。

## 三、未验证的关键事实

- 24 个有限扰动点有精确构造身份一致证据，但不代表任意更小实数步长或整个连续球面邻域已证明无拓扑切换。报告仍有 `certified_smooth_neighborhood=false`。
- 十个系数方向尚未全部检查；不能宣称完整 81 点通过。
- 这不是 Newton/KKT 收敛认证。所有优化结果、OBJ、桌面接触动力学及 3D 打印仍未完成。

## 四、下一验收

在**不替换当前固定 H8 输入、不更换 Cherchi 求解后端**的前提下运行 `0,1,2,3,4,5,6,7,8,9` 全十列 81 点：
- 每点完整 same-call 有理材料 archive＋SHA；每点独立 Fraction 十矩及原生自交审核；
- 30 项三尺度有限差分的量化误差；
- H8d 基点目标坐标系十矩自动核验；
- 禁止原始端点方向敏感 hash 直接作为唯一连续性准入；用独立精确构造分类器报告 80 个扰动点。
- 若有不能解析的构造/真实分支、数值门失败，则保留失败结果，不进入 Newton。
