# W3 Heart H9｜M21.5A：M20 六材料精确割线账本独立复核

**分支：** `research/neuralmoments-w3-heart-h9-20261019`  
**范围：** 只复核已上传的 M20 `precision-ledger.json`；不读取原始 Cherchi 压缩包，不调用原生模块，不运行 Newton。

## 输入与可复现性

- 输入 SHA256：`95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703`
- Schema：`heart-h9-m20-exact-difference-rounding-ledger-v1`
- 输入报告记录：六份保存表面已重积分；状态为 `SIX_SAVED_SURFACES_REINTEGRATED_DIAGNOSTIC_ONLY`。
- 独立复核器：`source/review_w3_m20_ledger.py`
- 复核器 SHA256：`b938a41a4bd4eb6c9c59bd59fb569a4eccc017d078d85d3b348a850791488fa1`

从已上传账本独立重算后：

| 检查 | 结果 |
|---|---:|
| 精确表面割线 binary64 逐位匹配 | **60/60** |
| 精确矩舍入值与保存 binary64 匹配 | **60/60** |
| 残差分解恒等式 | **60/60** |
| 半 ULP 输入舍入界记录 | **60/60** |
| 区间分割恒等式 | **20/20** |

完整机器可读摘要见本目录的 `H9_M21_5A_M20_LEDGER_REPLAY.json`。

## 左右区间复核

| 侧别 | 全区间最大精确表面缩放误差 | 最差半区间 | 半/全 |
|---|---:|---:|---:|
| Left | 3.8755856069e-9 | 1.7468320646e-8 | 4.50727 |
| Right | 6.9308568623e-9 | 1.5845097156e-8 | 2.28617 |

两侧的最差分量均为 Mzz。异号半区间残差分量数：Left 7/10，Right 10/10。

### 抵消比例语义修正

原始 M20 字段 `weighted_cancellation_fraction` 表示**抵消后剩余残差 / 两半区间绝对残差加权和**，并非“已抵消比例”。因此：

`fraction_cancelled = 1 - weighted_cancellation_fraction`

据此，最强抵消为：

- Left：Mxz，抵消 **92.13%**；两半残差为 +2.2555327913e-9、−1.9264452126e-9，全区间残差为 +1.6454375939e-10。
- Right：My，抵消 **85.76%**；两半残差为 +2.6701845970e-11、−3.5571179797e-11，全区间残差为 −4.3947405182e-12。

对于 Mzz：Left 抵消 71.49%；Right 抵消 22.25%。

因此，上一版 M21.4 对“抵消比例”的字段命名/解释已在 `H9_M21_4_CANCELLATION_AUDIT.json` 修正：明确区分“剩余比例”和“抵消比例”。原始 M20 ledger 未被修改。

## 科学解释边界

1. 这次复核证明 M20 账本内六个精确十质量矩向量、割线计算和其记录的误差分解在数值上自洽。
2. 全区间误差低于最差半区间误差，且多个分量存在明显异号抵消；不能只用全区间最大误差代表局部区间行为。
3. 这不是渐近阶证明，不是连续可微邻域证明，也不是对六份原始 Cherchi 材料及其运行来源的重新认证。
4. `newton_admitted=false` 保持不变；没有最终 Heart OBJ 或终态物理指标。

## M21.5B：真实六点 LPI 运动复核的剩余输入

已有分析器 `source/h9_m21_3_lpi.py` 需要以下文件组合：

- M20 `precision-ledger.json`；
- 原始 H8f artifact 与冻结事件证书；
- Stage17 四点原生材料目录；
- M19 完整运行目录；
- M21 source-only 运行目录，其中必须有 `layered-report.json`、`worker/layered-report.json` 及六份 `*.source-motion.json` 附件。

本轮 Library 中可读取 M20 ledger，但未检索到 M21 source-run 的六份 source-motion 附件及完整六份原始材料。因此本轮**没有**运行六包 × 三种 LPI 的 18 项真实数据诊断；不得将 60/60 ledger replay 误写成 18/18 LPI 复核。

M21.5B 不需要重新编译 Cherchi，也不需要新的 Boolean。若上述文件仍在原工作站现有运行目录，直接执行只读分析即可；若附件缺失，再评估是否需要重新执行六次 source-only 调用。不得重新跑 Boolean 来补齐 source-motion 附件。

## 本阶段云端/本地划分

- **云端已完成：** 账本独立复核、M21.4 抵消比例语义纠正、复核器入库和结果报告。
- **本地必要：** 只有在六份原始 packet/source-motion 文件仍只保存在工作站时，真实 18 项分析必须在能读取这些文件的机器上执行。
- **不需要本地编译：** M21.5B 是保存材料的只读 Python 分析；不调用 Cherchi Boolean。

