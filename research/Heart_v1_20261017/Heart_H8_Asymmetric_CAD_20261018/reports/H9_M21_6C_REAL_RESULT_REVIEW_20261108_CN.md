# W3 Heart H9｜M21.6C 真实六样本结果复核

日期：2026-11-08  
分支：`research/neuralmoments-w3-heart-h9-20261019`  
输入附件：`moment-layers(1).json`  
附件 SHA256：`62c69598747623121314cdf88055315dc7617726c3bfc0b8a9e7c3fd57ae3915`  
文件大小：33,942,260 bytes；JSON 解析成功；6 samples / 6 intervals。

## 1. 结果身份与输入指纹

- schema：`heart-h9-m21-6c-support-subgroup-audit-v1`
- status：`SIX_SAVED_SURFACES_FACE_SUPPORT_SUBGROUP_TEN_MOMENT_J7_DIAGNOSTIC_ONLY`
- 原四类面片保留，新增五类支持子组。
- M20 ledger SHA256：`95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703`
- M21.5B LPI SHA256：`d353486cafb3b81a97c302c51d8a034eedee327fabe92f2497df2c48b49c522e`
- M21.6A full-boundary SHA256：`759b4df5111fa51e0d51f1e62ff36b5c84e02e85f13d6e3fc5edece95dbab793`
- native core SHA256：`d66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd`

四个输入指纹与本轮冻结合同一致。

## 2. 六样本精确复核

六个保存样本均满足：
- `exact_moment_ledger_reintegration_match=true`；
- `dual_vs_existing_retained_tangent_exact_match=true`；
- 活动面片数均为 2010；
- 最大 native-vs-independent J7 归一化差异介于 (1.3474\times10^{-17}) 与 (4.2274\times10^{-17})。

样本最大差异：`4.227315311159306e-17`（side-02-right-near）。

注意：活动面片 2010 与全部三角面 16910 是不同统计口径。

## 3. 面片支持细分

六个样本的分类数量一致：

| 子组 | 面片数 | 占全部面片 |
|---|---:|---:|
| EXPLICIT_ONLY | 14948 | 88.40% |
| LPI_ONLY | 103 | 0.61% |
| MIXED_1_LPI_2_EXPLICIT | 394 | 2.33% |
| MIXED_2_LPI_1_EXPLICIT | 1465 | 8.66% |
| TPI_TOUCHING | 0 | 0% |
| **Total** | **16910** | **100%** |

原 MIXED_EXPLICIT_LPI 共 1859 个，其中：
- 1-LPI / 2-explicit：394（21.19%）；
- 2-LPI / 1-explicit：1465（78.81%）。

六个样本中，五个子组的 J7 向量之和逐项等于原四类组的 J7 总和。源码的 `grouped_faces` 同时对五个子组的十个 moments 和十个 J7 做精确守恒断言；但本次 JSON 的 `face_support_subgroup_moment_j7_summary` 只序列化了 `face_count` 与 `j7_contributions_exact`，没有逐子组导出十个 moments 向量。因此可以确认内部 moment 守恒门禁已执行，但不能从此 JSON 直接检查每个子组的十矩具体值。若后续需要逐组审阅矩值，应补充 serializer 字段。

## 4. 六个区间结果

| Side / interval | 最大残差分量 | 最大归一化独立残差 | 最大 endpoint J7 disagreement |
|---|---|---:|---:|
| left / full | Mzz | 3.8756e-9 | 1.9134e-17 |
| left / first-half | Mzz | 1.7468e-8 | 1.2085e-17 |
| left / second-half | Mzz | 9.7171e-9 | 2.5671e-17 |
| right / full | Mzz | 6.9309e-9 | 2.7848e-17 |
| right / first-half | Mzz | 1.5845e-8 | 2.7770e-17 |
| right / second-half | mass | 4.1177e-9 | 1.9269e-17 |

重新解析 exact fractions 后：
- 60/60：五个支持子组的区间 residual 精确求和等于总 independent replay residual；
- 60/60：`R_native = R_replayed + (J7_replayed - J7_native)`；
- 每个区间的十个分量均通过原分层恒等式检查。

## 5. 新发现：两类 mixed support 对残差的贡献不同

对每个区间的最大残差分量，按 exact subgroup residual 比较绝对贡献：

| 区间 | 分量 | 最大绝对贡献子组 | 该子组 residual（约） |
|---|---|---|---:|
| left / full | Mzz | MIXED_1_LPI_2_EXPLICIT | +1.564e-9 |
| left / first-half | Mzz | MIXED_1_LPI_2_EXPLICIT | +1.093e-8 |
| left / second-half | Mzz | MIXED_1_LPI_2_EXPLICIT | -7.802e-9 |
| right / full | Mzz | MIXED_1_LPI_2_EXPLICIT | +4.762e-9 |
| right / first-half | Mzz | MIXED_1_LPI_2_EXPLICIT | +8.170e-9 |
| right / second-half | mass | MIXED_2_LPI_1_EXPLICIT | -2.787e-9 |

因此，1-LPI/2-explicit 子组虽然只有 394 个面，却在 6 个区间中有 5 个区间的最大残差分量里贡献绝对值最大；2-LPI/1-explicit 子组数量更多，但只在 right/second-half 的 mass 最大残差分量里占主导。

这是有价值的**支持类型相关性证据**，但不是因果归因。所有这些 subgroup residual 都是独立 Dual-number replay 分层，不是原生 C++ 逐子组 J7。当前不能据此宣称 1-LPI 支持就是 LPI 算法根因。

## 6. 半区间残差反号复核

对 left/right 的 first-half 与 second-half exact replay residual 逐分量检查：
- left：10 个分量中 7 个反号；
- right：10 个分量中 10 个反号。

Full interval 的小残差仍会掩盖半区间内更大的反号残差。该现象与 M21.6B 诊断一致，支持继续增加真实区间采样，而不是放宽残差门槛。

## 7. 当前限制与证据缺口

JSON 明确保留：
- `root_cause_determined=false`
- `continuous_neighborhood_certified=false`
- `asymptotic_order_certified=false`
- `newton_admitted=false`
- `final_heart_obj_produced=false`
- `per_group_native_jacobian_available=false`
- `per_support_subgroup_native_jacobian_available=false`
- `native_runtime_origin_cryptographically_attested=false`
- 本轮新增 Boolean 调用 0；新增 native source 调用 0。

GitHub 源码分支当前有 18 项单元测试，但用户本轮只上传了 JSON，没有上传 `run.log` 或测试输出。因此**本报告不声称 18 项测试已通过，也无法从 JSON 单独确认测试退出码、实际命令和运行环境**。

## 8. 下一步

### M21.6C 收尾
1. 补齐并归档本轮 `run.log`，确认 18 项单元测试实际通过。
2. 若需逐子组审阅十质量矩，扩展输出 JSON，显式序列化五类子组的十个 exact moment 向量；保持当前 J7 输出与精确守恒合同不变。

### M21.6D：真实 quarter-point 采样
1. 在 left/right 两侧分别取得真实 1/4 与 3/4 状态；
2. 不能用端点线性插值伪造新表面；
3. 固定输入身份、构造语义、约束与三角面合同；
4. 对新点重新做十矩 ledger、J7、原生 source-motion 绑定及支持子组 residual 检查；
5. 先检查现有 Cherchi/原生接口是否可复用；若需新 Boolean、source 调用或编译，单独报告后再执行。

在 quarter-point 证据完成前，不进行 Newton 准入。M21.6C 已证明混合面细分的离散精确守恒成立，但尚未解决连续邻域光滑性与 J7 根因。
