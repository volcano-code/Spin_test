# W2–M19：Noodles V7 完整源部件精确十矩复验与 F/D/A 证据准入门槛

**日期：** 2026-10-21。**唯一写入：** `volcano-code/Spin_test` 的 `research/neuralmoments-w2-teacher-20261019` 分支，`research/NeuralMoments/teacher/` 目录。没有改动 main、W0/W3/W5/W6、历史实验记录或共享原生求值内核。

## 本阶段独立完成的真实计算

使用 M18 已恢复的原始 Noodles V7 冻结源部件 ZIP（`W2_M18_Noodles_V7_94_Source_Recovery.zip`），在当前 Python 3.13.5 环境上执行 `m19_noodles_fda_audit.py`：

- **94/94** 个原始源网格；**188/188** 个模型单位与 SI 单位 OBJ 的 SHA-256 与历史 manifest 独立一致。每个网格的有向边配对通过，且坐标解析与目标单位 `0.025 m/model unit` 重新核对；此为拓扑必要条件，不是无自相交的严格证明。
- 以**保存的 binary64 OBJ 顶点的精确有理数**重建四面体，独立对 **94/94** 个源网格的 **88,040** 个三角面求取 **940** 个密度为 1、目标框架的质量矩分量（质量、三项一次矩、六项二次矩）。积分内部使用 `Fraction`，而不是仅在浮点结果上做近似核对；每个网格新增 `exact_rational_ten_sha256`，全体精确积分摘要也写入结果。
- 所得源体积与历史**各部件单体**浮点体积的最大绝对误差 `1.734723475976807e-18`。最外椭球源网格模型体积 `1.401599858658712`，其目标框架 10 矩见结果 JSON。
- 对历史原始 94 部件 manifest SHA256 `67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a`、Git blob `f476a8c3e87bd30ef186b24442f641c2602c32ec`、188 文件语义 digest `6b2da86949e4426986e2460167f1255f0c44d6e708be87bfec17fb78ce4a69c6` 独立核对；这些外部值**不由 W2 本轮生成器自行声明**。
- 另外，GitHub 连接器直接读取 `main` 的原始 manifest 和构造收据，核实 94/93 部件关系、历史 CGAL 后端 SHA `d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3`、历史 96 次 CSG 以及 6 份历史输出的独立 SHA 期望值。

完整真实输入审核 `11.06 s`；其中各源四面体精确积分在本机 CPU 执行完成。**并没有新运行 CGAL 或 Cherchi。** 记录中的“精确十矩”仅是**94 个尚未布尔合并的输入部件各自的矩**，因为 93 个固定部件存在重叠，**不能直接相加冒充固定实体 F 的十矩**，也没有证明 `A = F ∪ D` 的几何或物理分区。

本轮真实全量报告的 SHA256：`ce3e924f0de623dea693b2b61b10d70d25ff0806cc8b9662db9506ed53ea5d2e`。精确 94 网格十矩的聚合摘要：`d40304c23021ade4f185afc6f363524443798a879e341ac962b9632ce55cbe3b`。

## 历史 F/D/A CGAL 输出状态（真实阻断）

历史 `frozen-inputs/author-rational/construction.json` Git blob `1e824c72d5ee13cc484bbf60a0be9b79be86d787`，原始 ZIP 内 SHA256 `35f74fbdb432ee4eccebf21d7e4f1f07408f63420c659025857f1d83d15abfd0`。它记录原始 **96 次**精确 CGAL 运算，但**六份真实有理数据文件均不在当前 ZIP/Git 仓库**：

| 文件 | 历史三角面 | 真实材料 |
|---|---:|---|
| `envelope-rational.json` | 1,280 | 缺失 |
| `fixed-rational.json` | 114,942 | 缺失 |
| `design-rational.json` | 108,804 | 缺失 |
| `initial-rational.json` | 36,986 | 缺失 |
| `fixed-inside-envelope-rational.json` | 107,160 | 缺失 |
| `fixed-outside-envelope-rational.json` | 35,342 | 缺失 |

本阶段新程序 `historical_csg_gate()` 对六份原始文件逐个采用**历史收据中外部锁定的 SHA-256**校验；缺少即报告缺失，任何假文件/错误 SHA 直接拒绝。即便日后 6/6 字节身份匹配，程序也**不会自动宣称合法 F/D/A 划分或放行原生教师**：历史 receipt 本身明确 `independent_partition_verified=false`，后续还需独立精确边界、无交叠和覆盖证据。

原 `build_exact_v7.py` 依赖的 `common.py` 与原 `noodles-exact-boolean` 可执行文件也未在当前可访问 Git 工作树中找到；当前运行容器 **4 GiB 有效内存**，不满足串行原生计算需 ≥24 GiB 的协议，因此并未强行重算 96 次 CGAL。

## 实测测试与命令

M19 生产脚本和测试均在本地运行；原始冻结 OBJ bundle、完整 94 份精确结果参与验收：

```bash
export W2_M18_SOURCE_BUNDLE=/path/to/W2_M18_Noodles_V7_94_Source_Recovery.zip
python research/NeuralMoments/teacher/m19_noodles_fda_audit.py \
  --source-bundle "$W2_M18_SOURCE_BUNDLE" \
  --output /new/path/M19_NOODLES_ALL94_EXACT_SOURCE_MOMENTS.json
# 退出码 2：物理矩复验成功，但六份 CSG 原始数据缺失，教师准入阻断；JSON 已写入。

python -m unittest discover -s research/NeuralMoments/teacher \
  -p test_m19_noodles_fda_audit.py -v
# 在配套 94 部件输入与已提交的完整结果均可用时：24/24 PASS, 0 skip, 0 failure。
```

覆盖真实全量 SHA、94 部件 940 精确矩、目标框架的解析四面体预言机、原始 96 次运算历史信息、防篡改、缺文件、假 CSG、重复 ZIP、非法 OBJ、闭合性检查和排他原子持久化。本地最终 **24/24 PASS，2.228 s**。如果在没有用户指定真实 M18 bundle 的仓库环境执行，则 16 个真实资料测试会显式 `skip`，而不是伪称已经打开过历史数据；提供 bundle 即完整执行。

本轮环境结果另保存在 `M19_RUNTIME_BLOCKERS.json`：当前仍无 `make_it_stand`、`_cherchi_core_boolean`、`_cherchi_rational_moments`，4 GiB cgroup 内存不符合 24 GiB 协议，真实原生 Boolean 调用 0，正式导数教师 0。

## 下一项严格验收

1. 找到**真实**的六份历史 `*-rational.json`、原 CGAL 后端二进制和构造脚本依赖，并对全部文件 SHA 核对；否则在满足资源的原生研究主机上，以独立新实验身份重新精确构建。新结果即使几何等价也不能直接冒充历史 SHA。
2. 对六份有理实体进行独立有向闭合、精确十矩和实体分区验收，特别是 F 固定部件存在重叠，`F+D=A` 的质量矩等式是必要但不是充分几何证明。
3. 锁定完成的 Noodles `outer/F/D` Native Request 和原生 `c`，在合格主机上串行执行新 Cherchi 教师。另一侧 Frozen Heart 同样需要已冻结的三份原生扩展、独立预算和合格内存。
4. W0/W3 的连续导数和 Jacobian 教师审核仍须**独立完成**，不能靠源几何精确积分或历史 81 点有限差分放行。

**M19 阶段结论：已完成 94 个原始源网格的 940 项精确有理十矩及来源重绑定，并实现真实 CSG 缺失与篡改拒绝；F/D/A 布尔构造、最新原生 Cherchi 求值、可训练 Jacobian 仍未完成。**
