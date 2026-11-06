# W6 全部先进方案差距矩阵（2026-11-06）

## 口径

- 本表覆盖当前候选库全部 **31 个条目**，不是只列本轮实际接入的模型。
- “已接入”严格区分：源码/适配器存在、CPU smoke 通过、已训练、与真实 Cherchi 数据准入、Newton 认证、真实 Spin 端到端验收。任何一个不能替代另一个。
- PINO 是唯一主干。所有其他方案只能作为 PINO 插件、训练策略、求积器、几何表示、独立数值参考或力学/MMDO 支线。
- 无 root LICENSE 或仓库身份不清的项目，只做论文研究/独立复现，未经许可不复制原始代码。

## 全部候选方案状态

| 方案 | 技术角色 | 当前已完成 | 一个月内决策/下一步 | 云端/本地 | 真实差距 |
|---|---|---|---|---|---|
| P-CRAFT PINO / UFNO3d | 主干 | 已适配 PINO U 形 F-FNO 主干；9 项 CPU 数学测试曾通过；M2b 加入材料支持掩码，最新 CI 有 1 项测试失败待修 | 保留唯一主干；M2b 修复测试后冻结模型接口，继续训练 | 云端 CPU；4090 负责 64³+ 与原生验收 | M0 已完成；训练精度不足，许可证/权属需核实 |
| NeuralOperator GINO / FNOGNO / UQNO | 几何/不确定性插件 | GINO 与 UQNO 适配器 CPU 测试通过；没有 Spin 训练权重 | GINO 做可选几何编码对照；UQNO 做残差不确定性，不替代 PINO | CPU 可做小实验；GPU 本地 | 已适配未训练，未校准 |
| Transolver++ | 物理注意力插件 | 尚未接入 | 30 天内只做小型特征插件或对照；不能替代 PINO | 云端 CPU 小型 smoke；GPU 本地 | 未接入 |
| Neural-Solver-Library（FNO/U-FNO/Transolver/UPT/GNOT 等） | 模型比较套件 | 已锁定 MIT 源；未完成统一训练对照 | 从中选一个最有价值的 UPT/GNOT/Transolver 对照，避免重复实现 | 云端小模型；GPU 本地 | 候选库登记，比较缺失 |
| NVIDIA PhysicsNeMo（GeoTransolver/DoMINO/FIGConvNet/MeshGraphNet/VFGN/Active Learning/AeroJEPA/GLOBE） | 几何/力学/主动学习 | 尚未接入 W6 | 30 天只选 GeoTransolver 或 DoMINO 一个插件；FIGConvNet 留作后续；Active Learning 只迁移 query 策略 | CPU 接口可做；大几何本地 GPU | 整体未接入 |
| GAOT | 图神经算子 | 仓库无 root LICENSE | 论文/算法对照；先取得授权，不复制源码 | 方法可云端复现 | 权限阻塞 |
| GAOT-3D | 三维多尺度图算子 | 仓库无 root LICENSE | 保留高分辨率对照，不纳入 30 天核心 | 方法可云端；规模测试本地 | 权限阻塞 |
| GINOT | 点云几何算子 | 仓库无 root LICENSE | 研究其 point grouping / cross-attention；仅方法复现或取得授权后接入 | CPU 小型复现；GPU 本地 | 权限阻塞 |
| PhysGTO | 流形图 Transformer | 仓库无 root LICENSE | 用于非结构网格对照，不能替代 PINO | 方法可云端 | 权限阻塞 |
| EqGINO | 等变几何算子 | 仓库无 root LICENSE | 只做旋转协变数学对照；30 天不复制源码 | 数学/小型实验云端 | 权限阻塞 |
| UNOP | 物理约束无监督算子 | 仅 README badge，未见 root LICENSE | 借鉴积分约束/几何适配/曲率门控，独立实现 | 云端原型 | 权限阻塞 |
| QuadrANN | 学习型求积 | MIT 模型核心提取；3D CPU 前向通过；未训练 | 保留为求积专家，必须在同一 PINO 数据集公平训练 | 云端 CPU；大模型本地 GPU | 适配通过，训练缺失 |
| NQR | 神经自适应求积 | SIGGRAPH 2026 方法已登记；仓库未核实许可证与运行资产 | 30 天复现自回归采样思想，不复制代码；比较是否减少精确积分预算 | 云端小规模 | 方法未实现/许可证阻塞 |
| Algoim | 独立数值积分参考 | 官方 pinned 源码编译；单位球十矩误差 7.50e-11 | 扩展 box/sphere/quadric 参考；不能替代 Cherchi | 云端 CPU 可做 | 基础测试通过，Spin Boolean 配对未完成 |
| fVDB | 稀疏体素后端 | 未接入 | 只定义 adapter/API；4090 上做 CUDA smoke 和显存测试 | 完整 CUDA 本地 | 未接入 |
| Kaolin | SPC/SDF/网格预处理 | 未接入 | 作为 fVDB 的 mesh/SDF 预处理对照，避免同时做两个生产后端 | 云端 CPU API；GPU 本地 | 未接入 |
| PyTorch3D | 可微网格工具 | 未接入 | 仅在需要表面采样时采用 | 云端小测试 | 未接入 |
| PyG | 图学习基础组件 | 已作为 QuadrANN 依赖安装 | 用于 QuadrANN/后续图插件，不算独立 W6 算子成果 | 云端 CPU | 依赖可用 |
| e3nn | E(3) 等变特征 | 未接入 | 30 天内做旋转协变小消融；不引入完整 EqGINO | 云端 CPU 小规模 | 未接入 |
| TorchOpt | 可微优化器 | 未接入 | 仅做隐式/展开优化器消融；不替代 Cherchi/Newton | 云端 CPU 原型 | 未接入 |
| torchquad | 积分基准 | GPL-3.0 | 隔离环境做积分性能基准，不进入 W6 核心 | 云端 CPU | 隔离基准缺失 |
| Active Operator Learning with Predictive UQ（JCP 2026） | 主动学习方法 | 论文已登记，无 verified code | 将 uncertainty/event-distance/query-value 组合成教师查询排序；依赖 W2 训练数据准入 | 云端合成实验 | 方法未实现，W2 标签阻塞 |
| Transolver-3 | 大规模几何 | 公告存在，独立代码仓未核实 | 观察项；不计入本月接入 | 待核实 | 代码未确认 |
| Opt-RNO | 优化型神经算子 | 仓库身份未核实 | 观察项；不计入本月接入 | 待核实 | 代码未确认 |
| DensiCrafter | 密度场/自支撑设计 | MIT 源码与损失审查完成；W6 adapter 未实现 | 独立 MMDO 模块；16³/32³ 质量/COM/支撑损失；不能称 FEM 强度求解器 | 云端 CPU；64³+ 本地 | 审查完成，适配缺失 |
| Stress-constrained differentiable GNN neural fields（2026） | 强度/拓扑优化 | 论文参考已登记，无 verified code | 只复现应力约束/支撑过滤数学，需独立 FEM 验证 | 云端公式/小例；真实 FEM 本地 | 论文方法阶段 |
| PI-GINOT（2026） | 物理约束力学算子 | 预印本参考，代码许可未核实 | 作为力学 PINO 参考；不是 Spin 十矩主干 | 云端小实验 | 未接入 |
| PI-CViT | PINO 训练策略 | 代码已审查但无 root LICENSE | 借鉴 loss balancing/gradient conflict/collocation sampling；不采用 CViT 替代 PINO | 独立实现策略可云端 | 许可阻塞原码接入 |
| PFEM | PINO + FEM warm start | 代码已审查但无 root LICENSE | 借鉴 PINO 预测作为精确 Newton/FEM 初值的 warm-start 思路；其 Transolver 主干不取代 PINO | 云端概念/小实验；真实 solver 本地 | 许可阻塞原码接入 |
| HyPINO | MMS/残差迭代改进 | MIT 源码已审查；未集成 | 借鉴 manufactured solutions 和 residual refinement；不采用其 Swin hypernetwork | 云端 CPU | 方法待适配 |
| TensorPILS | PINO 损失预条件 | Apache-2.0 源码与损失已审查；未集成 | 借鉴 preconditioned residual norm / loss conditioning；必须推导适用于 Spin moment residual 的正定预条件器 | 云端 CPU | 方法待适配 |

## 目前可量化的 W6 证据

- P-CRAFT PINO 主干：Spin-PINO v1 已实现，基础 CPU 数学测试 9/9 曾通过；M2b 新增材料支持掩码后测试 13/14 通过，1 项密度缩放测试因测试假设未隔离学习门控而失败，正在修正。
- M1 三种子：analytic continuum P0 数据训练成功，但留出椭球平均 r relative L2=0.4250、J relative L2=1.5802，精度不足。
- M2 未掩码三配置：8³/4³/0.04 组合分数 1.0026；8³/6³/0.02 为 0.7363（J 改善但 r 变差）；16³/4³/0.02 为 1.4660。说明单纯增加分辨率不等于改善模型。
- M2b：显式密度/occupancy 掩码已加入；三配置训练通过，已分析 artifact。最佳 8³/6³/eps=0.02：r relative L2=0.2561、J relative L2=0.8972；尚未达到 Newton 准入。
- M3 同数据架构对照（run 42192701882）：Spin-PINO 6-node r relative L2=0.2561、J=0.8972；W6 M7 Realizable U-FNO r=0.4372、J=0.4931（综合最好）；W5 voxel DeepONet r=0.7511、J=0.6994。PINO 在 r 上最好，M7 在 J/综合分上最好，下一步将 M7 的 Gauss-Legendre 正权重求积借鉴到 PINO head，而不是替换 PINO 主干。
- GINO/UQNO/QuadrANN：适配器 CPU smoke 通过；均未完成 Spin 数据训练/校准。
- Algoim：单位球解析十矩独立验证通过，最大绝对误差 7.50e-11；尚未和 Cherchi 在同一 Spin Boolean 几何上配对。
- DensiCrafter：源码/许可证审查完成，W6 适配器和联合优化尚未实现。
- W2：正式准入训练样本仍为 0，未准入 Jacobian；因此没有 Cherchi 监督训练和 Newton 神经导数使用。

## 30 天范围内的取舍

### 必须完成
1. PINO M2b 支持掩码修复和稳定训练；M3 与 W6 M13/M7、W5 DeepONet 在同一数据协议下公平比较。
2. 采用 PI-CViT 的训练稳定性方法（loss balancing、梯度冲突、collocation 策略）和 TensorPILS 的预条件残差思想，独立实现到 PINO 训练环节；不替换 PINO 主干。
3. UQNO 校准、风险—覆盖曲线、event gate 和安全精确回退接口。
4. QuadrANN/NQR 自适应求积思想小规模消融；Algoim 解析/几何参考扩展。
5. DensiCrafter 16³/32³ 的质量/COM/支撑/表面保护损失适配，并连接十矩接口。
6. 形成一个 GeoTransolver 或 Transolver++ 插件对照，不在一个月内同时移植全部几何网络。

### 只做接口/方法复现，不做完整集成
- DoMINO、FIGConvNet、GINOT、GAOT、GAOT-3D、PhysGTO、EqGINO、UNOP：保留完整差距和授权状态；仅选一个最有价值的小型方法对照。
- fVDB、Kaolin：云端定义接口；高分辨率 CUDA 验收放本地 4090。
- PFEM：借鉴 warm-start，不移植 Transolver 主干；若无授权，只独立实现策略。
- HyPINO：借鉴 MMS/残差迭代，不移植 Swin hypernetwork。
- stress-GNN / PI-GINOT：力学方法研究，真实强度验证另立 FEM/PINN 工作包。
- Transolver-3 / Opt-RNO：仓库身份确认前不进入实现承诺。

### 明确不承诺一个月内完成
- 31 个项目全部原代码集成。
- 任意 CAD/任意二次曲面 Jacobian 的完整认证。
- 512³ 全流程训练与性能证明。
- 完整 FEM/PINN 强度/失效载荷验证。
- 如果 W2/W0 未准入，则不承诺 Cherchi 监督训练和 Newton 使用。

## 一个月结束的验收定义

2026-12-06 前，必须有可重现的 PINO 主干训练、同协议基线对比、训练稳定性消融、不确定性/回退原型、MMDO 小规模耦合结果、4090 本地测试脚本和完整差距报告。其余项目必须明确标为未接入/方法借鉴/授权阻塞，而不能隐去。


## M3 architecture tournament evidence

The first same-data tournament passed in GitHub Actions run [42192701882](https://github.com/volcano-code/Spin_test/actions/runs/42192701882). It confirms the gap is not simply 'more projects need to be added': Spin-PINO currently leads moment accuracy, W6 M7 leads derivative accuracy and combined score, and W5 DeepONet is weaker on moment generalization. The next integration should transplant only M7's positive Gauss-Legendre quadrature rule into the P-CRAFT PINO head and rerun the same benchmark. The P-CRAFT PINO trunk remains frozen as primary.


## M3b Gauss-Legendre ablation result

The Gauss-Legendre node/weight option has been implemented inside the PINO head, with PINO trunk and support masking unchanged. Same-data run 42193467406 shows Gauss-PINO 6-node r/J relative L2 = 0.4727/1.2022, worse than midpoint-PINO 6-node 0.2320/0.8912. The Gauss rule is therefore retained as a negative ablation and is **not promoted**. M7's discrete positive measure idea remains useful; its Gauss node distribution does not transfer directly to this voxel-mask setting.


## M3b and M4 update

- M3b tested M7-style Gauss-Legendre nodes inside the PINO head; the Gauss variant was worse than midpoint PINO on the same analytic split and is retained only as a negative ablation.
- M4 is now under implementation: PI-CViT-inspired gradient-conflict diagnostics/PCGrad and TensorPILS-inspired fit-split diagonal residual preconditioning are applied to the existing PINO data/physics/J losses. The PDE-specific losses from those projects are not copied.
