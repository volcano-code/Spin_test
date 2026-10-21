# W4 P19：完整原轴杆保护候选的具体交接

这是待 W0/W2 按各自职责审阅的材料证据；没有向其他窗口发送消息，没有改写其分支，也没有代签准入。

## 固定输入

- 选定包：`P19_material_case/manifest.json`
- 外部 manifest SHA256：`c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6`
- 完整可重算报告：`P19_COMPLETE_MATERIAL_REPORT.json`
- 报告 SHA256：`62212e828e6c9a021bca8085bfa85a4c20f5d1a3607e978aa264dbaceebc7b6b`
- 原 Cherchi commit：`7bd6c2697695f555f9a15d7e154e084d841316f0`
- 最终候选使用原版 CLI；无 APAP、CGAL 或保存后修复。

| 对象 | 包内路径 | SHA256 |
|---|---|---|
| M | `material/M_native.obj` | `0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704` |
| F | `material/F_native.obj` | `5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8` |
| D | `material/D_native.obj` | `d64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073` |
| 完整原 S | `source/shaft-reference.obj` | `65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0` |

## W4 已经证明的范围

保存 binary64 坐标下：全部边界嵌入；M=F∪D；F/D 无正体积交叠；D 严格在 M 内；完整 S⊆M；S 与 D 距离至少 `1249999999/500000000000` reference unit；因此完整 S⊆F。
原 tip、+Z 轴和轴杆高度保持，原 S 字节未改。
本地 137 项完整测试无跳过，真实三操作重建再次通过。

原生输出会改变索引排列。接收端不能只用 OBJ 文本 SHA 判断几何不等，也不能直接忽略 SHA：保留每个实际 SHA，再精确比较顶点与定向三角多重集，并按各自实际 SHA 审计。任何坐标微移、反向面、额外抵消面或未使用顶点均拒绝。

## 物理配置仍是提案

`0.025 m/reference unit`、`1200 kg/m³`、已转换好的 Z-up 坐标；tip `(0,0,0)`、轴 `+Z`。
不能重复应用历史 `.4` 缩放、Y-up→Z-up 旋转或 `.15` 高度平移。
报告提供完整精确十矩、密度加权 SI 矩、COM、惯量张量及边界。
M 提案质量约 31.118997337 g；F 约 30.623879229 g；D 约 0.495118108 g。
S 已包含于 F，不能再叠加其质量。

本轮 XY 外包络有意扩大，D 缩小；公共壶体继承已披露的 P9/P13 重构，不是作者原 CAD。
保存几何证明不能签发物理材料、打印或接触性能证明。

## W0 仍需完成的具体门

只读核对的 W0 HEAD 为 [`51cbfd33d08063404d7e0c40e4256dd0e38efa1a`](https://github.com/volcano-code/Spin_test/commit/51cbfd33d08063404d7e0c40e4256dd0e38efa1a)。
[M6_NATIVE_HANDOFF.md](https://github.com/volcano-code/Spin_test/blob/51cbfd33d08063404d7e0c40e4256dd0e38efa1a/research/NeuralMoments/contracts/M6_NATIVE_HANDOFF.md) 的 blob 是 `d650228bbd69c8927f64e815fe9dc935463c55d9`。

需要把此候选与实际 `SpinArtifactProblem` / native evaluator 同一输入锁定，明确系数 c 所在归一化框架。
`.025 m/unit` 不能未经变换推导就写成 `length_original_per_normalized`。
预先固定 native binary、Cherchi bridge、adapter、c vector、locked problem、evaluation context 六项身份。

在实际 owned native material regions 上检查：

1. `M = F + D`；
2. `D = retained + cavity`；
3. `M = F + retained + cavity`。

必须有 completed、complete partition、union equals whole、各部分 subset、无正体积 overlap、missing/excess 为零等真实谓词收据，及同一次源的精确物理坐标反变换和十矩。
P19 的外部保存三角网证明未被冒充成这个 native M6 收据。
完整原生作业遵守已登记的 nominal 24 GiB/swap0、单作业 60 分钟、编译≤4、同环境大任务串行；本轮小型参考 CLI 研究不是该 M6 大任务执行。

## W2 状态与后续教师工作

只读核对的 W2 HEAD 为 [`b52cb2af0260041900fc03560b5dc182cb088750`](https://github.com/volcano-code/Spin_test/commit/b52cb2af0260041900fc03560b5dc182cb088750)。
[teacher_manifest.json](https://github.com/volcano-code/Spin_test/blob/b52cb2af0260041900fc03560b5dc182cb088750/research/NeuralMoments/teacher/teacher_manifest.json) blob 为 `cafbeaa6d5ba41d952f9d742b6c8951498be625e`。
M20 涉及 Noodles 的 96 步计划与六份历史有理包缺口；`native_teacher_runs=0`、`training_samples=0`，未发布此 Teapot 的准入 r/J。
这些 Noodles 状态没有被当作 P19 的失败或通过；P19 候选需要自己的输入和教师收据。

收到合格 Teapot 原生 material partition 后，仍需真实参数评价、导数作用域与稳定邻域证据；有限差分稳定或解析盒实验不足以放行训练。
图9的惯量、降低质心、减质量三项消融及同条件优化前后 MuJoCo 对照继续保持未执行。

本轮只读快照及时间见 [P19_W0_W2_READONLY_SNAPSHOT.json](P19_W0_W2_READONLY_SNAPSHOT.json)。所有外部批准标志继续为 false。
