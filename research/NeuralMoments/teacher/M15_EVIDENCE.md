# W2-M15 — 实际 Frozen Heart / Noodles V7 双模型教师落地与失败留证

日期：2026-10-20。**唯一写入分支** `research/neuralmoments-w2-teacher-20261019`；唯一写入目录 `research/NeuralMoments/teacher/`。不改 main、W0、W1、W3、W4、其他窗口、公共原生 core 或任何历史 Actions 证据。

## 1. 真实冻结数据与所执行的工作

本轮**实际执行了** `m15_dual_teacher_campaign.py --execute-native`，使用真实 H8f GitHub Actions artifact 12135528290（运行 [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402)）。原始 Actions `failure` 保留，原始源码冻结 SHA `0bcc187b3005478baa586a6d6f450e73811ca342`。

冻结 H8f ZIP SHA256：
`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。

冻结 native request JSON SHA256：
`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`。

对原始 ZIP 中的三个**真正的**物理毫米 OBJ 做实际独立数值和身份验收：

| 冻结输入 | 顶点 | 三角面 | SHA256 |
|---|---:|---:|---|
| `initial_top.obj` | 15646 | 31288 | `fbada64691e30b458bc5b5375f8d4ad351cb0b383d800512bb659077b29532f6` |
| `fixed_shell.obj` | 28768 | 57532 | `45c83ffd19c94b6c75ea63e7e7261fda645cd00ec0920c1a6ecc68e703c3a5b0` |
| `design_domain.obj` | 13122 | 26244 | `391fbeb80b8e7e4e2f12217880f4642c5fccd30ae5bb9ba2b5703d0dbd05b092` |

- **输入身份**：外壳/设计域用 `physical_mm/25` 与保存的原生请求做 binary64 顶点字节和有向三角面索引的完全一致核对。固定材料有独立的冻结 SHA 及保存的独立原始输入审计。
- **单位修正**：原始物理 OBJ 是毫米，归一化尺度是 **25 mm/单位**；`SpinItFasterRequest.original_units_per_normalized_unit` 则是 **0.025 m/单位**。两者不可直接当成相同单位数值比较。
- **独立有向四面体十矩**：固定材料的十矩对保存 `r_F` 最大绝对差 `7.704947790898586e-14`，`F+D` 与原外壳十矩最大绝对差 `2.220446049250313e-16`；两者均通过 H8 源代码预先声明的 `1e-9` 输入分区数值误差界限。这里是**真实原始浮点几何/质量矩核验**，不是重新执行原生精确 Cherchi 布尔。
- **原生单次输入已生成**：按冻结原生请求逐字节生成新的 **normalized view OBJ**（不是替换原始 CAD），SHA256 `929abe196ce4811b545599e79f17cfb1f4ea22482e8695583883de2dee29989e`。当原生模块与资源可用时，工具可以组装 `w2-one-cherchi-request-v3`，交给此前真实 Cherchi 单次运行入口 `run_native_smoke.py`。固定/设计/原始 OBJ SHA 全部在几何 identity 中绑定；`J_D` 仍不授予训练准入。

## 2. 实际原生运行尝试与失败原因

当前容器中 `make_it_stand`、`_cherchi_core_boolean` 和 `_cherchi_rational_moments` 均不存在，且 cgroup 有效内存只有 **4294967296 bytes（4 GiB）**，不满足原始团队 **24 GiB/swap0** 的串行原生安全协议。

已执行：

```bash
python research/NeuralMoments/teacher/m15_dual_teacher_campaign.py \
  --heart-archive /path/to/real-h8f-81.zip \
  --output-dir /new/exclusive/path/m15 \
  --execute-native
# exit code = 2: real missing native module, failure JSON retained
```

**实际生成的失败证据** `M15_CAMPAIGN_RESULT.json`：
- Heart 状态：`BLOCKED_COMPILED_NATIVE_MODULE_FILE_ABSENT`。
- Noodles 状态：`BLOCKED_FROZEN_NOODLES_NATIVE_F_D_INPUT_ABSENT`。
- 本轮新启动 Cherchi 原生布尔/教师求值：**0**。
- 本轮新可训练 Jacobian 标签：**0**。
- 不改历史 W0 或 W3 连续光滑性/ Newton 准入结论。

工具实现了串行、24 GiB RLIMIT_AS、最多 3590 秒超时、进程组清理；但由于预检失败，这些原生运行机制**尚未在实际已编译 Cherchi 生产任务中验证**。

## 3. Noodles V7：真实输出已经独立复算，但 F/D 原始输入并未备份齐全

本轮 GitHub 连接器**真实读取** main 上的 4233138 字节完整优化后 OBJ Git blob `f803c45274d7721b854cfd19a5173e4b43e79af1`（预期源 SHA256 `e979bd3980a5efaf9b03d047c4e19e9296ddb426267a7322ff4e1a4b954fe80a`），使用独立 JavaScript Kahan 有向四面体积分和有向边配对，产出 GitHub 文件：

[`M15_NOODLES_V7_HISTORICAL_OBJ_AUDIT.json`](./M15_NOODLES_V7_HISTORICAL_OBJ_AUDIT.json)。

- 真正的模型是 **42932 顶点／86076 三角面**；无非配对或方向冲突的边；质量 **18.483894783801567 g**（冻结密度 1200 kg/m³），十矩与原 V7 独立数值最大绝对差 `6.661338147750939e-16`。
- V7 终态十矩报告使用 **原点 z=-4 mm** 的轴尖目标坐标系，所以必须按 `(x_mm/25,y_mm/25,(z_mm+4)/25)` 积分。若错误在 OBJ 世界坐标直接对比 z/z²，会产生假失败。
- Noodles V7 在 `053756f5091ab3e07d6bd29c40baab146e910121` 阶段的真实单次数字求解可证明该输入上历史一轮 warm restart 收敛；但所用二进制基于旧 `b0a13e3`，不能称作本轮最新源码重跑。
- 关键阻碍是完整冻结 source outer／fixed／design 原始实体及 exact F/D SHA 绑定**未全部进入该公开 GitHub 检查点**。最终 `complete-mm-repaired.obj` 是**优化输出而非新 Cherchi 教师的原生 F/D 输入**。旧 `evidence/newton/warm-resume/request.json` 仅保存 SHA / solver 控制，缺少原生顶点/面片数组。因此本轮**明令禁止**以最终 OBJ 拼凑假教师请求。只允许拿它做上述终态几何数值审核。

Noodles 本地 Python 的最终 OBJ 检查通过 `--noodles-final-obj /path/to/main/.../complete-mm-repaired.obj` 可复跑；当前 Python 沙箱没有该 4.23 MB OBJ，故此项单独标记 skip。真实 GitHub blob 的独立十矩检查由连接器同一轮 JS 计算完成，不是 Python 已执行该选项的声称。

## 4. 新文件、测试与复现

- `m15_dual_teacher_campaign.py`：已真实执行的双案例来源绑定、独立物理矩审计、资源预检、无同次教师时失败入账、原生模块可用时准备调用先前 `run_native_smoke.py`。
- `test_m15_dual_teacher_campaign.py`：真实 H8f ZIP、单位区分、原始 F/D/outer 三种冻结输入、二次曲面原生 c、模型篡改、资源不足、Noodles 输入缺失与假请求拒绝。
- `M15_DUAL_MODEL_PREFLIGHT_RESULT.json`：实测两模型失败和 Frozen Heart 数值结果的紧凑取证。
- `M15_NOODLES_V7_HISTORICAL_OBJ_AUDIT.json`：从真正主分支完整 Noodles OBJ Git blob 直接进行的独立几何/十矩核对。

本地测试命令：

```bash
W2_H8F_ARCHIVE=/path/to/real-h8f-81.zip \
 python -m unittest discover -s research/NeuralMoments/teacher \
 -p 'test_m15_dual_teacher_campaign.py' -v
```

本轮本地参考 21 个测试：**20 通过、0 失败、1 跳过**（Noodles 终态完整 OBJ 尚未在该 Python 容器挂载），约 **2.485 秒**。该 21 用例测试文件与最终提交的 compact GitHub 测试文件**并非逐字节相同**，不能将本地 20/21 误报为已执行了提交版本的每一行代码；生产主文件的 Git blob 在提交时已与本地实测字节核对一致。历史原生 ZIP 与数学结果是真实重算，不是 Mock 产物。

## 5. 真正进入生产阶段还缺什么

1. 在具备 **≥24 GiB 有效内存、swap=0、Python3.13、冻结一致的编译原生模块**的 W2 研究机器上用 `--native-module /path/to/compiled.so --execute-native` 串行执行 Frozen Heart 的第一份真正 W2 原生单次材料，保存 (r_D)、原生同次 Jacobian 附件、十矩独立误差、布尔合法性、真实 stage 时间/RSS。仅物理矩通过后 J 仍保持 excluded。
2. 先恢复 Noodles V7 完整原始 source `initial/fixed/design`、原生请求 native c 和其精确来源 SHA，重新跑输入预检后才能在**相同**原生模块上执行一份 Noodles V7 教师。当前优化输出不足以充当输入。
3. W0 v2 正式 projective 与 W3 point60 真实连续/一侧导数批准尚不存在，不释放训练用 (J_D)，不擅自修改其他窗口。

**科学结论：** Frozen Heart 真正冻结输入及 F/D 十矩已在本轮逐字节/独立重算验收，Noodles V7 真正优化终态 OBJ 已在本轮直接按完整 GitHub Blob 独立检查；**本运行环境未能执行新原生 Cherchi，因此 M15 是有真实进展但尚未完成原生教师验收的部分里程碑**。
