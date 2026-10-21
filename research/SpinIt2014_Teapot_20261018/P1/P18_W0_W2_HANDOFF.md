# W4 P18：供 W0/W2 审阅的具体交接

**本文件是候选证据交接，不是 MomentContractV1、W0 批准或 W2 教师发布。**
仅保存于 W4 自己的分支。没有向其他窗口发送外部消息或修改其文件。

## 被审阅对象

- P17 源提交：`c0f21c28b58fe05cf46a892934cfbcb2fccdac62`。
- 物理案例：`P13_RECONSTRUCTED_REFERENCE_UNIFORM_SOLID_PROPOSAL`。
- M SHA256：`4c2e4d480d1041f4817128a8b4b61675d80a699e448e7a5a253311c1805a3aa2`。
- F SHA256：`47c08ee597d5666069416985e0dc8900d204481c590b73596f90daccd2b068d1`。
- D SHA256：`1d4a0673e9297d95adfb5722158ba1d859a83099046d01116a2b363cb3cb386b`。
- 原 shaft SHA256：`65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0`。
- 机器证明：[P18_EXACT_SOLID_AND_SHAFT_REPORT.json](P18_EXACT_SOLID_AND_SHAFT_REPORT.json)。

## 可以消费的新证据

| 事项 | 实际证据范围 | P18 结果 |
|---|---|---|
| M/F/D 曲面嵌入 | 保存 binary64 坐标；原始索引；含相邻面全部候选 | 通过 |
| 实体包含与分区 | 有界保存后 regular solids；F 两边界为 +M/-D | 通过 |
| D 到 M 外边界间距 | 全域有理下界，尺度提案下约 8.07709485 mm | 通过 |
| 十矩与 SI 核算 | 原顺序与普通交叉矩，沿用 P17 精确结果 | 重算通过 |
| 完整原轴杆保护 | 精确 32 边棱柱与全部 640 个 D 面 | **失败：74 顶点、283 面严格侵入** |
| 保守轴心 core | 常截面段内约 1.49277709 mm 半径不被 D 删除 | 通过；不等于完整轴杆 |
| 原生 Cherchi 隐式区域等价 | 本轮只验证序列化坐标 | 未证明 |
| 原生与微焊实体严格相等 | P16 非零体积差仍有效 | 不成立 |
| W0/W2/优化/训练 | 无本对象的外部批准或正式教师收据 | 未准入 |

因此当前候选仍不应直接用于正式图9三目标优化。即使物理尺度后来获准，轴杆的实际几何反例也必须单独解决。

## 机器报告冻结快照及提交前追加核对

W0 HEAD：`51cbfd33d08063404d7e0c40e4256dd0e38efa1a`。

- [公共合同 README](https://github.com/volcano-code/Spin_test/blob/51cbfd33d08063404d7e0c40e4256dd0e38efa1a/research/NeuralMoments/contracts/README.md)
- [schema_v1.json](https://github.com/volcano-code/Spin_test/blob/51cbfd33d08063404d7e0c40e4256dd0e38efa1a/research/NeuralMoments/contracts/schema_v1.json)
- [M6_NATIVE_HANDOFF.md](https://github.com/volcano-code/Spin_test/blob/51cbfd33d08063404d7e0c40e4256dd0e38efa1a/research/NeuralMoments/contracts/M6_NATIVE_HANDOFF.md)
- [MASTER_BOARD.md](https://github.com/volcano-code/Spin_test/blob/51cbfd33d08063404d7e0c40e4256dd0e38efa1a/research/ParallelLaunch/MASTER_BOARD.md)

机器报告生成时核对的 W2 提交（M19，冻结快照）：`fef549dd57ea7b8bc72ab4ca4e5b307e4063762b`。

- [teacher_manifest.json](https://github.com/volcano-code/Spin_test/blob/fef549dd57ea7b8bc72ab4ca4e5b307e4063762b/research/NeuralMoments/teacher/teacher_manifest.json)
- [M19_EVIDENCE.md](https://github.com/volcano-code/Spin_test/blob/fef549dd57ea7b8bc72ab4ca4e5b307e4063762b/research/NeuralMoments/teacher/M19_EVIDENCE.md)

在这些已发布记录中未找到与 P17 提交、三份材料 SHA 及物理配置同时绑定的明确批准。
这只是固定版本的只读观察，不声称遍历未发布渠道。对应 Git blob 身份也嵌入 P18 JSON。
W2 M19 是 Noodles 的 94 个未布尔合并源部件、940 项精确矩，`J_D_released=false`，不能用作 Teapot 教师。

### 提交前追加核对：W2 已发布 M20，准入结论不变

2026-10-21 14:50 UTC 前的只读复核发现，W2 分支已推进到
`b52cb2af0260041900fc03560b5dc182cb088750`。P18 源码及可重放 JSON 中的
`dependency_snapshot` 保留上述原始 M19 观察身份；它不是对活动分支最新状态的声明。
本小节单独记录新证据，没有修改已测试的几何结论或其冻结输入。

| 不可变记录 | Git blob |
|---|---|
| [最新核对的 teacher_manifest.json](https://github.com/volcano-code/Spin_test/blob/b52cb2af0260041900fc03560b5dc182cb088750/research/NeuralMoments/teacher/teacher_manifest.json) | `cafbeaa6d5ba41d952f9d742b6c8951498be625e` |
| [M20_EVIDENCE.md](https://github.com/volcano-code/Spin_test/blob/d94b6ec4eae38e58b68635ec37c324a9881344fa/research/NeuralMoments/teacher/M20_EVIDENCE.md) | `b191f119e7e232865df4d57cb991dc27ee9edb34` |
| [M20_REAL_94_INPUT_FDA_PREFLIGHT.json](https://github.com/volcano-code/Spin_test/blob/d94b6ec4eae38e58b68635ec37c324a9881344fa/research/NeuralMoments/teacher/M20_REAL_94_INPUT_FDA_PREFLIGHT.json) | `5b6602c10bcd541779f2d617f83046f5bcab8da5` |

M20 新增 Noodles 的 96 步 CSG DAG（92 次固定部件 union 加 4 次最终操作）以及未来六份有理材料包的精确十矩检查器。
该 DAG 尚未执行；真实 preflight 仍是 `BLOCKED_NO_SIX_PINNED_RATIONAL_CSG_PACKET_BYTES`。
本里程碑新增 CGAL 与 Cherchi 调用均为 0，`jacobian_J_D=null`，`training_admitted=0`。
最新提交另记录 M19+M20 的 51/51 本地回归，不是 CI 或教师准入。

这些新发布记录仍没有绑定本 P17 提交、M/F/D SHA、0.025 尺度、1200 密度与 tip 的 Teapot 专属批准或教师。
W2 的六份 Noodles 包阻塞也不构成 W4 继续修复自身轴杆保护的前置条件；W4 可立即推进新的严格保护候选。

## 对接时不能混淆的合同内容

十矩顺序是：

```text
M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY
```

交叉矩不乘二。原生系数顺序是 `CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY`；最后三项为对称矩阵元素，所以单项式系数需要相应的 2 倍映射。
固定 F 仅积分缓存一次：`r_total(c)=r_F+r_D(c)`，`J_total=J_D`，不能重复累加或用重叠组件矩替代已合并 F。

P17 的 `0.025 m/reference unit` 是参考模型到 SI 的尺度。
**它不应被无条件写成 W0 的 `length_original_per_normalized`。** 必须先锁定优化器系数所处的归一化框架、原点和实际变换矩阵，并严格绑定同一材料。
本轮保留 1200 kg/m³、+Z、tip0 为提案，未擅自构造一个看似通过的正式合同。

W0 M6 要求原生 `check_exact_material_partition` 的实际 owned material-region 证据，包括完整覆盖、无正体积交叠、各部分子集、missing/excess 为零等。
P18 的保存后整数/Fraction 证明可以作为独立几何证据，不能冒充那条原生执行路径。
新的保留/空腔求值还必须绑定同一次 Cherchi 的源码、原生二次曲面系数、保留侧、材料和 frame 身份，以及正式 r/J。

下一份可准入交接应附上解决轴杆反例的新候选源身份、正间隙预算、本轮证明重放结果，以及 W0/W2 自己发布的材料专属批准。
本文件没有请求忽略任何失败，也没有将等待依赖作为不完成 W4 自有几何验证的理由。
