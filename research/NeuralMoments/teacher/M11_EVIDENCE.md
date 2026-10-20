# W2-M11｜W0 MomentContractV1 与真实 Cherchi 81 点的只读 v2 兼容性桥接

**执行日期：** 2026-10-20  
**唯一写入：** `research/neuralmoments-w2-teacher-20261019` 的 `research/NeuralMoments/teacher/`  
**冻结历史原生源码：** `0bcc187b3005478baa586a6d6f450e73811ca342`

## 科学上的新发现：H8f 有 64/81 个原始 c 不满足 W0 的单位范数保存合同

从历史 GitHub Actions 运行 [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 的**真实**冻结归档 SHA `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9` 及 W2 M9 独立精确复验的 81 条候选 SHA `fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a`，逐点检查 `numpy.linalg.norm(c)`：

| 判定 | 真实数量 |
|---|---:|
| 满足 `abs(||c||₂-1)<=1e-12` | **17/81** |
| 不满足（有限差分中的原生未归一化扰动） | **64/81** |
| 最大 `abs(||c||₂-1)` | **2.282620930493806e-6** |

满足 W0 范数条件的真实点索引：
`[0,21,22,23,24,61,62,63,64,69,70,71,72,77,78,79,80]`。

**严禁静默归一化 64 个存档 c**：`c` 的正比例投影等价是一个数学约定，但保存的 Cherchi 同次调用、材料快照 SHA、导数及有限差分参数是对**原始字节 c** 建立的。改变它再声明同一原生计算，既违背 W0 SHA 合同，也可能遗漏离散重三角化差异。

## 本阶段实现

- `w2_w0_v2_bridge.py`：独立接收 W2 v2 标签封装，严格要求外部给定的模型 SHA、native module SHA、几何 SHA 和原生系数 c；复核 v2 的标签 SHA、`q=Bc` 交叉项 2 倍约定、固定矩独立计算、不可发布 `J_D` 的状态。调用者声称 `native_cherchi=True` **不能授权原生材料认证或训练**。
- 同一模块用现有 W2 M10 的只读门槛重新绑定真实 81 点 ZIP（81 个 gzip SHA、81 个 Jacobian 摘要，均不发布 Jacobian），计算全部原始 c 的范数差。只在**原始 c 已满足** W0 单位范数时，从已绑定的冻结请求内的 `initial_top.obj` / `fixed_shell.obj` / `design_domain.obj` 文件 SHA、密度、目标坐标与真实 retained-side 生成**W0 结构诊断记录**。记录虽使用 W0 schema 字段名，`w0_diagnostic_record_is_release=false`，绝不冒充 W0 已独立审核的正式标签。
- point0：真实 81 份材料重绑定通过，W0 结构诊断记录可生成，但 **`J_D=null`、训练准入=0**。
- point60：native `c[7]=3e-6`，多项式 `q[7]=6e-6`；原始 c 不满足 W0 单位范数，明确拒绝该点的 W0 结构诊断记录，保留真实构造特征变化，不能改为稳定分支。
- 可选 `--w0-schema` 与 `--w3-report`：只能读取指定来源的 Git blob SHA，不能用任意 JSON 自称是 W0/W3 验证通过。缺少时必须记录为 `observed=false`；**输入 W0 schema 的存在本身也不意味着 W0 独立验证器完成准入**。
- `export_training()` 固定拒绝。新脚本仅在 W2 独占目录，无共享 core 修改。

## 实际执行与证据

本地基于**真实**历史 H8f ZIP 和 M9 候选数据，使用已逐字节恢复到 GitHub W2 M10 Git blob `e22060d6bd199529662de93c844439db9d38bcd0` 的 `w2_consumer_gate.py` 执行：

```bash
python -m unittest discover -s /mnt/data/w2_m11 -p test_w2_w0_v2_bridge.py -v
# Ran 22 tests in 13.767s — OK
```

22 项包括：真实 81/81 材料归档重绑定、17/64 项单位范数分组、来自真实 frozen request 的 F/D/outer SHA、point60 不可偷偷归一化、系数交叉项映射、v1/v2 结构错用、篡改独立身份、伪造 `J_D` 发布、伪造 `native_cherchi` 布尔授权、损坏 W0/W3 schema SHA 的拒绝。

**来源限制：**本地 M11 测试读取的是真实 M9 候选文件和真实 Actions ZIP；其用于 `validate_manifest` 的 manifest 是根据 GitHub W2 M9 已锁定字段明确重建的 **semantic fixture**，不是声称获取了逐字节相同的远端 `teacher_manifest.json`。在完整 W2 checkout 上运行的脚本则会读取原始远端 manifest。没有调用原生 Cherchi、没有运行 W0 独立 `validate_contract_v1`、没有执行最新原生 W3 侧点。不得把“W0 结构诊断”写成正式 W0 v2 验收。

本地输出（未伪造 GitHub Actions CI）：

| 文件 | 内容 | SHA256 |
|---|---|---|
| `M11_H8F_W0_BRIDGE_POINT0.json` | 真实归档 81/81 重绑定后，原始 c[0] 的 W0 结构诊断 | `bc05185d261660fb5f4571e2282043af59e3e096d3ae78a6a2413a055e9208ab` |
| `M11_H8F_W0_BRIDGE_POINT60.json` | 仅固定索引源审计，point60 W0 结构诊断拒绝 | `02ca3eccd79842db35f268c4b850b5a27316d9cd4cdd19b1fe4cb29e118afaef` |
| `unittest_m11_remote_m10_exact.log` | **22/22 PASS** | `c5462f9e77af39ff2af53daed4035a8134960d8f3f450d1335534c544de1fdb3` |

GitHub 上新文件：`w2_w0_v2_bridge.py`、`test_w2_w0_v2_bridge.py`、`M11_REAL_H8F_V2_COMPATIBILITY_RESULT.json`、本文件，以及 `teacher_manifest.json` 的增量更新。前两者代码的本地 Git blob SHA 应为 `96ef6b41ca3e29bf599dd6469603b519c9ddd4c9` 和 `508496a6f46049f78086861e475a1735a0f9c85b`。

## W0/W3 只读依赖现状

- W0 `schema_v1.json` Git blob `52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc`；`w2_teacher_gate.py` 仍只认 `w2-cherchi-teacher-v1-pre-w0`（Git blob `b42ec6d9b389675123250d79f9cc9efb1b658c07`），没有证据表明 W0 已正式验收 W2 v2。
- W3 `H9_STAGE9_EXECUTION_EVIDENCE.json` Git blob `ec6995c2b60cb5158d94f79a783a60d9ad64f23d` 明确写着：0 次新 Cherchi 原生侧点、0 个新四点材料、Newton 无接受、连续邻域无认证。条件性解析线边穿越证据是重要解释，但不能代替真实一侧导数或独立 native 分支连续性证明。
- W0 依赖不得通过修改其他分支实现；W2 为未来的 W0 v2 审核保留原始 c、所有物理矩和所有失败见证。**正式 `J_D` 教师数=0**，所有历史 81 点仍是 excluded。

## M12 应解决

由 W0 在其独占分支讨论如何**显式表示保存的非单位范数 c 的 projective ray 身份**，不能覆盖原始样本或把重新归一化向量冒充新的同次调用；再由 W3 在满足 ≥24 GiB/swap0 和冻结构建条件的原生机器独立取得 point60 一侧材料与导数。经完成 W0/W3 的独立审核、终态 Newton 验收后，另建正式签名/准入协议，不得让 M11 只读门槛自行切换到 release。
