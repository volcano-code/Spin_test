# W6 31 项先进项目筛选：功能去重与 PINO-first 最佳候选（2026-11-07）

**源版本**：`volcano-code/Spin_test@a3a117023f9a4e1a8e9ecb9a5e280448ab192a06`，候选库 `catalog.json`，本次人工审查覆盖 31/31。
**绝对要求**：P-CRAFT U-FNO/F-FNO 作为唯一主干；原生 Cherchi 是正式教师/精确回退；不同角色优先一个主选；源码复用须许可证和 exact commit；已设计/已接入/已训练/已晋升是不同状态。

## 筛选依据

功能唯一性 > 与 Spin 十矩/Jacobian 的物理关联 > 原始源码许可/可追溯 > 本月云端+本地可执行性 > W6 实际消融成本收益。
此处不打虚构的论文性能分数：跨 CFD、可制造设计、积分、PINO、稀疏体素的作者报告不能直接比较。

### 最小研究闭环（本月必须聚焦）

1. **唯一主干** P-CRAFT Spin-PINO：已适配并通过解析 P0 训练，不替换成其他 operator。
2. **512³ 稀疏数据** fVDB：先做数据接口、局部特征数据保真、GPU 显存/吞吐；与现有 Torch 2.5.1 W6 CI 保持环境隔离。当前源码尚未接入。
3. **不规则几何编码** GINO：已有 W6 CPU 适配器；仅作可关闭的 PINO 几何特征插件，首次需证明优于已有失利的 M10b 全局池化。
4. **c 条件神经求积** QuadrANN：已有 CPU 适配但未训练；尝试切割边界敏感节点/权重并审查十矩/Jacobian。
5. **独立数值对照** Algoim：现有官方 C++ 基础验证通过；对比算法正确性而不是替代 Cherchi。
6. **可信度与拒绝** UQNO：已有 smoke；必须证实校准、误放概率、精确回退开销。

这个闭环并不意味着上述全部已经集成；真正默认路径仍主要是原 PINO 和数学约束。

### 独立支线/下阶段候选

- **DensiCrafter（P1）**：MIT，质量/质心/自支撑与表面保留；做 MMDO 独立支线，不是 FEM 强度计算，更不替换 PINO。
- **e3nn（P1）**：MIT，实现局部旋转协变表征的受控小消融；避免无许可复制完整 EqGINO。
- **PhysicsNeMo FIGConvNet**：高分辨率点云的 **唯一几何编码挑战者**，与 GINO 二选一；使用 NVIDIA 原代码前先配适依赖。
- **PhysicsNeMo Active Learning（P2）**：选择昂贵 Cherchi 查询的策略，仅在 W2 准入后转真实教师实验。
- **TorchOpt（P2）**：对合法平滑问题尝试隐式微分，绝不代替 Cherchi Newton 或非光滑事件拒绝。
- **HyPINO（P2）**：只借鉴 manufactured-solution 测试思想，保留 PINO 主干。
- **Neural-Solver-Library（P2）**：独立评测入口，绝非额外叠加到默认模型的模块。

## 每种功能的主选与挑战者

| # | 角色 | 主选组件/来源 | 优先级 | 当前建议 | 仅一位挑战者/备用 |
|---:|---|---|---|---|---|
| 1 | PINO 核心神经算子 | P-CRAFT PINO / U-FNO source / P-CRAFT UFNO3d / factorized FNO + Spin ten-moment head | CORE | 冻结唯一主干 | 无；其他模型只作特征插件或对照 |
| 2 | 512³ 稀疏体素与 GPU 数据后端 | fVDB / fVDB sparse grids / CUDA | P0 | 主选，尚未实现 | Kaolin 仅保留为几何转换的备选，不同时建设第二条生产后端 |
| 3 | 不规则几何到 PINO 的编码适配 | NeuralOperator: GINO / FNOGNO / UQNO / GINO (GNO input/output geometry port) | P0 | 主选，已有 CPU 接口测试 | PhysicsNeMo FIGConvNet 作为唯一高分辨率挑战者；GAOT-3D/GINOT/PhysGTO 暂因许可和接口风险不并入 |
| 4 | 切割感知求积节点与权重提议 | QuadrANN (Numerical Algorithms 2026) / QuadrANN geometry-aware quadrature proposal | P0 | 主选，已有 3D CPU smoke | NQR 只作策略参考直到完整许可确认 |
| 5 | 独立高阶数值积分对照 | Algoim / official Algoim implicit quadrature | P0 | 主选，C++ 基础 smoke 已过 | torchquad GPL 保持独立进程基准，不复制到核心 |
| 6 | 预测不确定性与精确回退 | NeuralOperator: GINO / FNOGNO / UQNO / UQNO residual/uncertainty head | P0 | 主选，已有 CPU smoke | 主动查询策略单独由 PhysicsNeMo 借鉴，不以 UQNO 概率直接代替准确性证书 |
| 7 | 独立密度/内腔可制造优化 | DensiCrafter: Physically-Constrained Generation and Fabrication of Self-Supporting Hollow Structures / differentiable density, mass/COM/support/surface loss | P1 | 主选，独立 MMDO 支线 | stress-GNN/PI-GINOT 仅作为真实强度子课题的论文参考 |
| 8 | 旋转协变几何特征 | e3nn / e3nn O(3)/SO(3) tensor features | P1 | 条件入选，先小消融 | EqGINO 原项目代码仍处许可阻塞；Transolver++ 已有成本负结果 |
| 9 | 昂贵教师样本的主动选择 | NVIDIA PhysicsNeMo: GeoTransolver / DoMINO / FIGConvNet / active learning / AeroJEPA / PhysicsNeMo active_learning_aero strategies (method port) | P2 | 条件入选；等 W2 准入 | JCP 2026 主动 UQ 论文仅作方法参考，不自称已有开源实现 |
| 10 | 可微优化与隐式梯度实验 | TorchOpt / TorchOpt implicit differentiation / optimizer library | P2 | 条件入选，非当前瓶颈 | PFEM 的 warm-start 思想可借鉴但源码许可未明 |
| 11 | 解析制造解与训练验证 | HyPINO: Multi-Physics Neural Operators via HyperPINNs and Method of Manufactured Solutions / HyPINO manufactured-solution methodology | P2 | 方法入选，不移植主干 | TensorPILS-inspired preconditioning / PI-CViT-inspired PCGrad 曾负结果，不默认 |
| 12 | 受控架构竞争基线 | Neural-Solver-Library / MIT baseline suite (select exactly one GNOT/UPT alternative) | P2 | 仅评测入选 | Transolver++ 已完成负结果，不重复单纯堆叠 |

## 代码实证与晋升门槛

- M8 Transolver++ 适配已真实对照：参数量增加约 86%，CPU 训练增加约 3.6×，SO(3) 综合分仅小幅改善；**不再列为待默认融合的几何主选**。
- M10b 多尺度细节在 16³ 小样本下有平均改善，但 32³ / 180 步时 r/J 反而退化；**不把未经训练验证的 FIGConv/GINO 细节路径默认启用**。
- fVDB 官方 0.6 安装矩阵要求 PyTorch 2.13、CUDA 13.0/13.2；现有 W6 CPU CI 用 Torch 2.5.1。必须独立 GPU 环境兼容审查，不能声称 512³ 已训练。
- Algoim 的单位球数值 smoke ≠ Cherchi 在真实 CAD/Boolean 上的正式认证；UQNO 输出的分数 ≠ 牛顿导数有效证书。
- 假设来自文献、Python 接口已写入、CI CPU smoke 通过、GPU 压力测试通过和端到端目标达成，都必须分别在报告中标识。

## 可操作的 30 天分阶段顺序

| 时间/阶段 | 云端工作 | 本地工作 | 明确出口 |
|---|---|---|---|
| 立即：核对合同 | 冻结 PINO c/r/J、许可 SHA、候选矩阵；GINO、QuadrANN、UQNO 一致数据加载 | 无 | 31/31 状态与源 pin；不再误把候选当已集成 |
| 第一周 | QuadrANN 切割条件查询、GINO geometry adapter 和 UQNO 不确定性，同 P0 新数据与原 PINO 配对 | 分离 fVDB CUDA 环境的驱动/torch 检查 | 新形状/旋转分布，3 种子，r/J+时间+RAM 报告 |
| 第二周 | Algoim 独立二次曲面基准 + DensiCrafter MMDO 16³/32³ CPU 损失合同 | fVDB 官方 pin 构建与 64³/128³ 稀疏烟测 | 十矩误差、有无外表污染、材料一致性 |
| 第三周 | 小规模 cut-aware 几何对照；FIGConvNet 是否比 GINO 值得多付成本 | 256³/512³ *稀疏* 吞吐和显存，不能用极低活性体素替代极限压力 | 多档激活比例、保真误差、显存和真实输入 |
| 第四周 | UQNO 覆盖/回退、所有失败消融保留、论文式实验总结 | 现有 Heart/Teapot/ Noodles 与 Cherchi 原生验收（若 W0/W2 准入） | 是否实际减少精确调用/端到端耗时，未准入就阻断 |

## 全部 31 项逐一筛查（不遗漏）

| 序号 | 候选库项目 | 本轮决策 | 理由 |
|---:|---|---|---|
| 1 | P-CRAFT PINO / U-FNO source | CORE | 唯一主干已实现；对外分发需明确内部权属 |
| 2 | NeuralOperator: GINO / FNOGNO / UQNO | PRIMARY | GINO 几何适配与 UQNO 可信度分头复用，均需完整训练验收 |
| 3 | Transolver++ | NEGATIVE_ABLATION | CPU 对照收益接近零，参数和训练成本增加；不晋升默认 |
| 4 | Neural-Solver-Library | BASELINE_ONLY | MIT 可用于统一对照；不放进生产 PINO |
| 5 | NVIDIA PhysicsNeMo: GeoTransolver / DoMINO / FIGConvNet / active learning / AeroJEPA | CHALLENGER_AND_CONDITIONAL | FIGConvNet 是高分辨率挑战者，Active Learning 是 W2 许可后备；不安装整个框架替代 PINO |
| 6 | GAOT (NeurIPS 2025) | LICENSE_HOLD | 与 GINO/FIGConv 角色高度重叠且根许可证未确认 |
| 7 | GAOT-3D | LICENSE_HOLD | 高分辨率图算子候选，根许可证未确认；保持论文化对照 |
| 8 | GINOT (CMAME 2026) | LICENSE_HOLD | 点云/交叉注意力功能与 GINO 重叠且许可阻塞 |
| 9 | PhysGTO (Communications AI & Computing 2026) | LICENSE_HOLD | 流形图注意力与 GINO/FIGConv 重叠且许可阻塞 |
| 10 | EqGINO (ICML 2026) | LICENSE_HOLD | 等变几何模块有价值，但选用 MIT e3nn 而不复制未授权主干 |
| 11 | UNOP: Physics-Constrained Unsupervised Neural Operator | LICENSE_HOLD | 数学积分约束理念可参考；根许可证未确认 |
| 12 | QuadrANN (Numerical Algorithms 2026) | PRIMARY | 已有 GNN 求积适配；下一步做 c 条件采样与 r/J 精度验收 |
| 13 | Neural Quadrature Rule and Autoregressive Adaptive Sampling (SIGGRAPH 2026) | LICENSE_HOLD | 同类神经求积; 许可和资源复现存在障碍，不复制代码 |
| 14 | Algoim | PRIMARY | 官方 C++ 基础验证通过；独立数值参照而非 Cherchi 替代 |
| 15 | fVDB | PRIMARY | 唯一首选高分辨率稀疏 GPU 后端；需独立 CUDA/torch 环境 |
| 16 | NVIDIA Kaolin | BACKUP | 保留 mesh→SPC/SDF 转换作 fVDB 备用，不建双后端 |
| 17 | PyTorch3D | DEFER | 仅在需要额外表面点采样时调用 |
| 18 | PyTorch Geometric | DEPENDENCY_ONLY | QuadrANN/GINO 图算子基础库，不计成独立创新 |
| 19 | e3nn | CONDITIONAL | MIT 等变特征，小型协变消融通过才晋升 |
| 20 | TorchOpt | CONDITIONAL | 只作为可微优化实验，不能绕过 Cherchi/Newton 认证 |
| 21 | torchquad | ISOLATED_BENCHMARK | GPL-3.0 隔离外部比较，不并入 W6 核心 |
| 22 | Active operator learning with predictive uncertainty quantification (JCP 2026) | PAPER_ONLY | 论文无已核验原始开源代码；策略参考 |
| 23 | Transolver-3 | WATCHLIST | 单独原始仓未核实，不能算候选源码可接入 |
| 24 | Opt-RNO (previously proposed candidate) | WATCHLIST | 原始项目身份与许可尚待确认 |
| 25 | DensiCrafter: Physically-Constrained Generation and Fabrication of Self-Supporting Hollow Structures | PRIMARY_SIDE_BRANCH | 密度、质心、自支撑与表面约束；不等于结构强度 FEM |
| 26 | Differentiable graph neural fields for manufacturable topology optimization under stress constraints | PAPER_ONLY | 强度子方向另立真实 FEM 对照，尚无核验源码 |
| 27 | PI-GINOT: Data-free geometry-informed neural operator learning for finite-strain hyperelasticity on parametric DogBone specimens | PAPER_ONLY | 超弹性力学预印本；与十矩算子不是同一个物理任务 |
| 28 | PI-CViT: On the training of physics-informed neural operators for solving parametric PDEs | LICENSE_HOLD_METHOD_ONLY | 方法借鉴后收益未明显胜出，未许可原始模型不复制 |
| 29 | PFEM: Pretrain Finite Element Method via Physics-Informed Neural Operators | LICENSE_HOLD_METHOD_ONLY | 只借 warm-start 验收思想；正式 native Newton 不可替代 |
| 30 | HyPINO: Multi-Physics Neural Operators via HyperPINNs and Method of Manufactured Solutions | METHOD_ONLY | 选用制造解验证思想，不复制非 PINO 主干 |
| 31 | TensorPILS: Preconditioned Physics-Informed Neural Operator Training | NEGATIVE_METHOD_ABLATION | W6 已测试类似残差预条件且未证明收益；原版模块不纳默认 |

## 法律及工程边界

候选库中 15 项属于当时审计分类的「可直接复用/许可初步明确」，不是 15 项已经集成。特别是 P-CRAFT 内部仓库仍需厘清对外授权；GAOT/GAOT-3D/GINOT/PhysGTO/EqGINO/NQR/UNOP/PI-CViT/PFEM 等许可或完整权属不足项目仅做独立方法对照。GPL torchquad 仅做隔离基准，不直接嵌入核心代码。

## 来源

- 本分支 `catalog.json`、`LICENSE_AUDIT.md`、`ADOPTION_MATRIX.md`、`spin_pino/M8_TRANSOLVER_PLUS_REPORT.md`、`spin_pino/M10B_RESULTS.md`。
- 官方 fVDB 安装：https://github.com/openvdb/fvdb-core/blob/main/docs/installation.rst
- 官方 PhysicsNeMo FIGConvNet：https://github.com/NVIDIA/physicsnemo/blob/22bb35ec6e700c2f8d6088ddbf88af12b157e5f2/physicsnemo/models/figconvnet/figconvunet.py
- 官方 GINO：https://github.com/neuraloperator/neuraloperator/blob/a6648eeeb60fe0837f2d7d021517a945a159a0c8/neuralop/models/gino.py
- 官方 QuadrANN：https://github.com/kesmarag/QuadrANN
- 官方 DensiCrafter：https://github.com/idvxlab/DensiCrafter

本轮是**全项目筛选决策与可复现登记**，并非实现、训练或晋升未接入的模块。
