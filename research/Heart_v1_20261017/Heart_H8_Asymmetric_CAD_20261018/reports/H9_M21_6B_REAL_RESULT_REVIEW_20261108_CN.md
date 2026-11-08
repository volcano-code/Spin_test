# W3 Heart H9｜M21.6B 真实六表面十质量矩/J7 结果复核

日期：2026-11-08  
分支：`research/neuralmoments-w3-heart-h9-20261019`  
输入结果：用户本地生成并上传的 `moment-layers.json`  
结果 SHA256：`5af24c36dbf704383144d94ed2ec2d373cec4be024b2b26aceda83c15012252e`

## 1. 结果身份与完整性

输出 schema：`heart-h9-m21-6b-moment-layer-audit-v1`  
输出状态：`SIX_SAVED_SURFACES_FACE_GROUP_TEN_MOMENT_J7_DIAGNOSTIC_ONLY`

输入指纹与冻结合同一致：

- M20 exact ledger：`95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703`
- M21.5B LPI report：`d353486cafb3b81a97c302c51d8a034eedee327fabe92f2497df2c48b49c522e`
- M21.6A full-boundary report：`759b4df5111fa51e0d51f1e62ff36b5c84e02e85f13d6e3fc5edece95dbab793`
- Native core identity：`d66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd`

结果包含 6 个保存表面、6 个区间、10 个矩/J7 分量和 4 个面片支持类别。六个样本均通过：
- 重新积分的十个精确质量矩与 M20 ledger 逐项相等；
- 独立 dual-number J7 与 retained-construction tangent 逐项精确相等。

每个样本的 `active_faces=2010` 是**至少一个顶点速度非零的活动三角面数量**；而 face-group 的 14948 + 103 + 1859 + 0 = 16910 是**全部三角面的分类总数**。二者统计口径不同，不矛盾。

## 2. 60 项精确残差分解复核

逐项重新解析 JSON 中的大整数有理数，使用精确整数/分数运算复核：

- 60/60：`R_native = R_replayed + (J7_replayed - J7_native)`；
- 60/60：四类面片的 `R_replayed` 精确求和等于总 `R_replayed`；
- TPI_TOUCHING 在本数据中面片数为 0，故 60 项对应残差均为 0。

统一归一化定义沿用源码：每个分量除以 `max(1, |mean endpoint native J7|)`。

最大归一化量：
- endpoint native-vs-independent J7 disagreement：`2.7848051385721656e-17`；
- finite-interval native secant residual：`1.746832064607797e-08`；
- 两者之比约 `1.5942e-9`。

这说明当前有限区间残差并非由独立 dual-number 重放与已保存 endpoint J7 的差异主导；但它**不证明**原生运行来源，也不证明连续构造邻域光滑。

## 3. 分量与区间现象

每个区间的最大归一化 native residual：

| Side / interval | 最大分量 | 最大归一化残差 |
|---|---:|---:|
| left / full | Mzz | 3.8756e-9 |
| left / first-half | Mzz | 1.7468e-8 |
| left / second-half | Mzz | 9.7171e-9 |
| right / full | Mzz | 6.9309e-9 |
| right / first-half | Mzz | 1.5845e-8 |
| right / second-half | mass | 4.1177e-9 |

Mzz 是 6 个区间中 5 个区间的最大残差分量；右侧 second-half 的最大分量是 mass。

### 半区间符号反转

用每侧 full、first-half、second-half 的 exact replay residual 对十个分量逐一比较符号：

- left：10 个分量中 7 个在两个半区间之间反号；
- right：10/10 个分量反号。

例：Mzz
- left：full +3.8756e-9；first-half +1.7468e-8；second-half -9.7171e-9；
- right：full +6.9309e-9；first-half +1.5845e-8；second-half -1.9831e-9。

因此 full interval 的较小残差会掩盖半区间内部的较大、反号残差；不能只用 full interval 的数值判断局部稳定性。

### 中点切线偏离量

在 full interval 与两个等长 half interval 的 exact residual 之间，计算：

`D_mid = 2 R_full - R_first - R_second = J7_mid - (J7_left + J7_right)/2`

该量在所有分量上约为 `1e-13` 或更小，而半区间残差达到 `1e-8` 量级。也就是说，三个保存点上的中点 J7 接近两端 J7 的线性插值，但两个半区间各自的 secant-vs-endpoint-trapezoid residual 仍然较大且常常反号。**这不能说明半区间内部没有变化**；它反而说明只检查三个保存点的 endpoint tangent 不足以解析半区间内部行为，需要更密的真实采样。

## 4. 面片组贡献：可定位但不能定因

在每个区间“最大残差分量”对应的独立 replay group residual 中，`MIXED_EXPLICIT_LPI` 的绝对值均为四类中最大。以该最大分量为例：

| 区间 | 分量 | EXPLICIT_ONLY | LPI_ONLY | MIXED_EXPLICIT_LPI |
|---|---|---:|---:|---:|
| left full | Mzz | +1.094e-9 | +5.024e-10 | +2.279e-9 |
| left first-half | Mzz | +5.366e-9 | -1.272e-9 | +1.337e-8 |
| left second-half | Mzz | -3.178e-9 | +2.275e-9 | -8.814e-9 |
| right full | Mzz | +3.303e-9 | -8.088e-10 | +4.437e-9 |
| right first-half | Mzz | +5.359e-9 | -7.908e-10 | +1.128e-8 |
| right second-half | mass | -3.935e-10 | -4.187e-10 | -3.306e-9 |

这里是**独立 dual-number 分层的有限区间 residual**，不是 C++ 原生逐组 J7。当前数据明确标记 `per_group_native_jacobian_available=false`，所以不能把 mixed group 的较大残差直接认定为 LPI 缺陷或唯一根因。混合面同时含 EXPLICIT3D 与 LPI 顶点；还需细分其 1-LPI/2-LPI 顶点支持，并取得原生分组证据。

## 5. 当前科学结论与限制

已完成：
- 六个真实保存表面的精确十矩重积分；
- 六个样本的 dual-number/retained tangent 精确对照；
- 60 项精确总残差与四类面片分层恒等式；
- 半区间符号反转与 full-interval cancellation 诊断。

仍未完成：
- J7 残差的唯一根因判定；
- 每类面片的原生 C++ J7；
- 连续构造邻域/光滑性证书；
- 渐近阶数认证；
- Newton 准入；
- 最终 Heart OBJ。

保持原报告声明：`root_cause_determined=false`、`continuous_neighborhood_certified=false`、`asymptotic_order_certified=false`、`newton_admitted=false`、`final_heart_obj_produced=false`。本轮没有新增 Boolean 或 native source 调用，且 native runtime origin 未经密码学认证。

## 6. 下一阶段建议：M21.6C

### 云端可做
1. 把 mixed faces 再分成 1 个 LPI 顶点 + 2 个 EXPLICIT3D 顶点，以及 2 个 LPI 顶点 + 1 个 EXPLICIT3D 顶点；
2. 对新的子组重复精确十矩/J7 dual-number 分层与 60 项 residual identity；
3. 保留完整 SHA、输入顺序、面语义与严格分母合同。

### 必须本地取得的新证据
1. 在 left/right 两侧各增加 quarter-point（c7 的 1/4、3/4）真实状态与 source-motion 证据；先复核现有 Cherchi/原生接口能否在固定拓扑约束下完成，不能擅自用线性插值冒充真实新表面；
2. 复用现有 native binary identity，记录每个新点的原生 J7 与 source-motion 绑定；若必须重新求 Boolean/编译，先单独报告资源与运行门槛；
3. 用 quarter-point 将两个半区间再拆分，检查 residual 是否持续反号、是否收敛，以及是否出现面分类/语义变化。

M21.6C 的目标是区分“半区间内的高阶变化/局部非光滑/源运动重建误差”，而不是提前放宽 Newton 门槛。新点未通过身份、拓扑、精确矩与原生 tangent 门禁前，不得推进 Newton。
