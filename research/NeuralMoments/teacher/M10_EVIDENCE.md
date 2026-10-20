# W2-M10｜只读消费者门槛、真实 81 材料源绑定与导数训练拒绝

**执行日期：** 2026-10-20  
**唯一写入：** `research/neuralmoments-w2-teacher-20261019` / `research/NeuralMoments/teacher/`  
**冻结 H8f 原生源码：** `0bcc187b3005478baa586a6d6f450e73811ca342`  
**原始 GitHub Actions：** [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402)，结论为 **failure**（绝不重写）。

## 完成的工作

新增 `w2_consumer_gate.py`：只读解析已经固定的 **M9 81 点物理矩候选索引**，强制核对原始 JSON 文件的 SHA256（`fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a`），以及 W2 manifest 中冻结的 H8f 原生 GitHub run、报告、分类、请求、候选文件与 W0 M9 handoff 身份。

检查 81 个编号连续且唯一的原生系数向量、`q=Bc` 的交叉项双倍映射、`r_D` 与 `r_F` 的十项有限性、固定矩不变性、25+81 历史样本范围没有被错误转换成新原生调用、每个点精确矩复验为真、81/81 的 `J_D=null`、`split=excluded`、`training_admitted=false`。point60 的五处构造位置、2+2 个 LPI 特征和 17+17 个有向三角面变化不得被降级为“已稳定/已认证”。

通过 `--archive` 可重新打开原始 **H8f 81 点 GitHub Actions ZIP**，逐文件校验 81 个 gzip SHA、存档真实原生 c / r_D / 材料几何 / 拓扑和 **81 个真实 Jacobian 摘要**（只核对摘要，不输出或训练 Jacobian 内容）；还复查 `r_F+r_D`。不运行新的 Cherchi Boolean，不重复 M9 的 810 个 Fraction 积分。

输出专门区分：

- `PINNED_M9_INDEX_ONLY_DERIVATIVES_BLOCKED`：只核对冻结索引和 manifest，不宣称本次打开原始材料。
- `ARCHIVED_81_MATERIALS_REBOUND_DERIVATIVES_BLOCKED`：真正打开原始 ZIP 并完成 81 个同次材料与 Jacobian 摘要重绑定。
- `REJECTED`：任何来源漂移、身份缺失、构造降级、导数越权或损坏输入均明确拒绝，CLI 退出码 2。
- `export_training()` **始终拒绝**，不能通过调用者自报 W0/W3 证明、手工修改 manifest 布尔字段或传入 `--force` 绕过。

写证据使用同目录临时文件 fsync 后排他硬链接发布，绝不覆盖前阶段结果。

## 实际运行

本轮从连接器核对 W2 M9 候选 JSON / manifest、W0 M9 handoff、W3 Stage9 报告与原始 ZIP。当前容器已安装 Python/NumPy，但**没有**编译的 Spin/Cherchi 原生模块；真实 ZIP 文件来自历史 GitHub Actions artifact `12135528290`，不是新生成的材料。

本地命令（完整原始 81 点 ZIP 已提供）：

```bash
python -m unittest discover -s /mnt/data/w2_m10 -p 'test_*.py' -v
# Ran 37 tests: OK, 0 failures; real archive rebind test did execute.

W2_H8F_ARCHIVE=/mnt/data/h8f_81_real.zip \
W2_M9_CANDIDATES=/mnt/data/w2_m9/candidates_81_exact.json \
python -m unittest discover -s /mnt/data/w2_m9 -p 'test_h8f_81_teacher.py' -v
# Ran 14 tests: OK, 0 failures.

python /mnt/data/w2_m10/w2_consumer_gate.py \
 --candidate /mnt/data/w2_m9/candidates_81_exact.json \
 --manifest /mnt/data/w2_m10/teacher_manifest_m9_fields_fixture.json \
 --archive /mnt/data/h8f_81_real.zip \
 --output /mnt/data/w2_m10/M10_REAL_H8F_GATE_RESULT.json
# Exit 0, 81 real packets rebound; elapsed 12.87s; process maxRSS ~251 MiB.
```

**注意测试来源边界：**本地 M10 单元测试针对实际原始候选和原始真实 ZIP；为了避免未授权修改其它分支，`teacher_manifest_m9_fields_fixture.json` 是从当次 GitHub 连接器读取到的 W2 M9 锁定字段重建的局部测试夹具，**不是**远端 `teacher_manifest.json` 的逐字节副本。已单独通过 GitHub 连接器重新核查真实 manifest 的 M9 关键字段。远端提交源文件并未经新的 GitHub CI 执行，不能报告远端测试通过。GitHub 检出后的推荐命令见下。

**真实原始 ZIP 再绑定结果：**

| 指标 | 实测 |
|---|---:|
| 原始 H8f 归档 SHA | `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9` |
| 81 份原生 gzip 材料与候选 SHA | 81/81 |
| 原始 10×10 Jacobian 摘要重绑定但不发布数值 | 81/81 |
| M9 历史独立精确积分分量 | 810（本轮不重复积分） |
| 原始固定矩/变量矩加法最大偏差 | `2.220446049250313e-16` |
| 本轮新 Cherchi 原生调用 | 0 |
| 本轮新可训练导数标签 | **0** |
| M10 本地新测试 / 既有 M9 回归 | **37/37、14/14** |

生成的 `M10_REAL_81_READONLY_GATE_RESULT.json`（提交前本地 SHA256：`a1e1bfb6d1e48e018dbe29fcb51ae4d7185f3f8f12a134308e3a880c12b4b0eb`）保存了原始 workflow failure、全部拒绝导数的原因和真实检查结果。

## W0/W3 独立现状（只读观察）

- W0 分支已发布 M9 的真实 H8f 独立复验 [handoff](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w0-contract-20261019/research/NeuralMoments/contracts/M9_REAL_H8F_81_HANDOFF.md)，但当前 `w2_teacher_gate.py` Git blob `b42ec6d9b389675123250d79f9cc9efb1b658c07` 仍明确只接受 W2 **v1**，不能将其假定为适配 W2 **v2** 的可信证明器。
- W3 分支的 [Stage9 报告](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w3-heart-h9-20261019/research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_STAGE9_SOURCE_AND_PROCESS_GUARD_CN.md) 及 [条件性解析穿越证书](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w3-heart-h9-20261019/research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json) 表明可以解释观测到的穿越趋势，但没有新原生 Cherchi 侧点、没有 native 连续区间证明、没有已验收 Newton 步。因此此阶段报告中 `w3_point60_event_resolved=false` 指**真实原生科学准入尚未完成**，不否定条件性解析证据。

## 在完整 W2 checkout 上的复现

```bash
export W2_H8F_ARCHIVE=/path/to/original-artifact-12135528290.zip
python -m unittest discover -s research/NeuralMoments/teacher \
  -p test_w2_consumer_gate.py -v

python research/NeuralMoments/teacher/w2_consumer_gate.py \
  --candidate research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json \
  --manifest research/NeuralMoments/teacher/teacher_manifest.json \
  --archive "$W2_H8F_ARCHIVE" \
  --output /new/exclusive/path/M10_REAL_81_GATE.json
```

新检查器的所有输出均为**物理矩有限点证据**。允许 W5/W6 做只读科学审计，但**不授权生成训练集、派生 Jacobian 标签、标定连续性或宣称心形 Newton 收敛**。待 W0 推出真正可验证的 W2 v2 导数合同、W3 完成原生一侧导数/事件位置测试和独立终态验收后，须另写、另审正式发布门槛，禁止直接把本脚本的拒绝状态改为允许。
