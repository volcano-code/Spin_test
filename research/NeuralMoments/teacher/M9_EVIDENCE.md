# W2-M9｜真实 H8f 81 点 Cherchi 材料独立复验与排除训练候选索引

**2026-10-20** · 仅写入 `research/neuralmoments-w2-teacher-20261019` 分支的 `research/NeuralMoments/teacher/`。M5–M8 原始记录未覆盖，未改其他 W 分支、main 或共享 core。

## 研究进展：H8f 历史原生 81 点已存在

找到并核实 [GitHub Actions 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402)，执行源码 `0bcc187b3005478baa586a6d6f450e73811ca342`，结论严格保持 **failure**。历史原生 Cherchi 81 次计算于 **2026-10-18** 执行。本阶段使用 GitHub 连接器下载当时的真实 artifact `12135528290`，随后执行的是 **CPU 离线取证**，没有再启动一次 Cherchi 原生 Boolean，也没有与 W1/W3 竞争原生计算资源。

来源固定 SHA：

- 原始 81 点 ZIP：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`
- ZIP 中的 `report.json`：`28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5`
- ZIP 中的 exact-construction classification：`f82801aa26d3f4228b8cb68f08abab5ef45458cc2368703e9187e0745662d6c5`
- 冻结请求 JSON：`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`

## 已实际运行的 W2 M9 复验

- **81/81** 个真实历史同次原生材料快照重读；逐个核验 ZIP 中 gzip SHA、原生 c、布尔源与精确材料几何哈希、Cherchi 与算术模块身份、定向材料面和固定矩的目标坐标变换。
- 独立 Python `Fraction` 对 **81/81** 个已保存闭合材料重新执行有向四面体积分（**810** 个原始质量矩分量）。精确积分后的双精度数值与存档物理矩最大绝对差 **0.0**；固定与变量矩分离及目标坐标变换最大绝对差 **2.220446049250313e-16**。
- 利用真实存档 81 个 native `c` 和 `r_D` 独立重算 **30/30** 组五点差分，最大归一化误差 `9.451443496526779e-10`。原始哈希不稳定差分组仍然有 **9** 组；数值检查通过不等于连续光滑。
- 从 point59 与 point60 的真实同次构造点记录独立规范化 LPI 线/平面身份、三角面朝向：索引 `8043..8047` 处有五个位置变化，两个构造特征消失、两个新特征出现，**17 个有向面特征移除、17 个新增**。对应 native `c[7]` 从 `1.5e-6` 到 `3e-6`，但不据此声称事件确切位置或 Boolean 体真实连续性变化。79 个有限扰动点归为 `STABLE_NOT_CERTIFIED`，point60 为 `FEATURE_CHANGE`。
- 单进程本轮全量离线积分及材料身份核验 wall `257.108172096 s`；**不是**原生 Cherchi 加速结论，不与历史原生 wall 混用。
- 复验器新增专项测试 **14/14 PASS**（真实 ZIP 和全量候选索引均作为输入），包含原始工作流 failure 不篡改、数值 FD 篡改拒绝、开放四面体拒绝、point60 特征伪稳定拒绝、q=Bc 交叉系数 2 倍和正式训练准入全零。

## 本次新成果文件

- `audit_h8f_81_teacher.py`：独立同次材料 SHA、原始 Native c / 多项式 `q=Bc`、十矩/F 分离、81 点规范构造分类、30 组有限差分、point60 原始特征 witness；支持 `--exact-mode none|focus|all`。
- `test_h8f_81_teacher.py`：针对真实 81 点归档的 14 个专项回归测试（无原生 Cherchi 求值）。
- `M9_H8F_81_EXCLUDED_CANDIDATES.json`：**81** 条完整物理矩候选记录；每条都有材料 gzip SHA、两个系数约定、`r_D` / `r_F`、几何与拓扑 hash、已存在 Jacobian 的摘要，但显式 `J_D=null`、`split=excluded`、`training_admitted=false`。全部 81 条的 `independent_moment_rechecked=true`。
- `teacher_manifest.json`：登记原始历史 native 81、新 native 0、真实数值重算 81、正式可训练 0；原有 H8e 25 点记录保留。

候选 JSON SHA-256：`fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a`；Git blob SHA：`213ed8db8e411aaa5c25a6fdd2afb1860c094b39`。

## 真实复现命令

```bash
# 下载历史原生 GitHub Actions run 39123384402 的 artifact 12135528290
sha256sum h8f_81_real.zip  # 必须 99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9

python research/NeuralMoments/teacher/audit_h8f_81_teacher.py \
  --archive h8f_81_real.zip --exact-mode all \
  --output /new/fresh/path/candidates_81_exact.json

W2_H8F_ARCHIVE=/path/to/h8f_81_real.zip \
W2_M9_CANDIDATES=/new/fresh/path/candidates_81_exact.json \
  python -m unittest discover -s research/NeuralMoments/teacher \
  -p 'test_h8f_81_teacher.py' -v
```

实际完整复验输出 SHA 与上述候选 JSON 匹配；源文件与专项测试通过 GitHub 连接器重新读取，并与本地执行版本按 Git blob SHA 比较。

## 不得越过的科学边界

1. `completed_samples=81` 与 `complete_eighty_one_samples=false` **可以同时成立**：前者是 81 点原生运行完成，后者表示严格构造/连续性准入仍失败。历史 Actions status 必须保留为 `failure`。
2. **没有获得整个连续邻域的光滑证明**，point60 不可用作平滑导数标签。30 个有限差分数值通过不能单独批准 `J_D` 进入训练。
3. W0 已有 [M9_HANDOFF](../contracts/M9_REAL_H8F_81_HANDOFF.md) 的独立 81 点复验与真实特征变化记录，但 W0 的独立原生/连续局部证明、W3 事件定位与完成的 Newton 终点证据仍是另行依赖。
4. 当前完成的是对 H8 **重建 CAD 非作者原 CAD** 已归档材料的独立数值核验；没有证明整个 CAD 几何/打印/接触稳定性，也没有解决原生模块本环境缺失。
5. 不新增正式 `train`、`val`、`test` 标签。本阶段 81 条**仅为 excluded 的候选物理矩**，无权作为 W5/W6 已认证平滑 Jacobian 教师。

### M10 建议

在 W2 独占目录新增只读跨窗口消费者门槛，对候选记录 SHA、来源 artifact、point60 等额外做不可降级校验；W3 独立修复构造事件，W0 提交经证明的连续邻域合同之后才能考虑解除相应限制。不得在等待期间凭 81 个有限点自发解除 `excluded`。
