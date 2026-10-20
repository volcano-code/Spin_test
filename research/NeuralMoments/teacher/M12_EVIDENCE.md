# W2 M12｜精确正比例射线身份与 W0 非单位原生系数诊断（2026-10-20）

**唯一写入分支：** `research/neuralmoments-w2-teacher-20261019`，**唯一写入目录：** `research/NeuralMoments/teacher/`。所有 W0、W3 源码和历史 Actions 原始失败记录保持不变。

## 真实输入与身份

- 历史 H8f 原生 81 点 GitHub Actions [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402)，原结论严格保持 **failure**，artifact `12135528290`，ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- 原始 M9 81 点候选 SHA256 `fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a`；数据划分仍全是 `excluded`。
- M12 的真实执行在 M10 严格入口先对 **81/81** 份原生 gzip 材料重绑定，使用 W2 M10 Git blob `e22060d6bd199529662de93c844439db9d38bcd0` 的**字节一致**本地镜像；未启动新 Cherchi、原生 Boolean 或 Newton。

## 科学问题与 M12 改进

W0 `MomentContractV1` 规定：原生二次曲面系数 `c` 以 native symmetric-entry 顺序存储，W0 记录需 `abs(||c||₂-1)<=1e-12`，多项式交叉项使用 `q=Bc`、`Bdiag=(1,1,1,1,1,1,1,2,2,2)`。H8f 历史记录在有限扰动时保存实际**未重新归一化**的原生 `c`：

| 真实复验 | 数量 |
|---|---:|
| 原始 `c` 已满足 W0 单位范数 | **17/81** |
| 原始 `c` 未满足 W0 单位范数 | **64/81** |
| 最大原始单位范数偏差 | `2.282620930493806e-6` |
| 精确正向 projective ray 身份 | **81/81** |
| 不同的 projective ray 身份 | **81** |
| 与原始 binary64 **有理数射线精确相同**的单位显示向量 | **17/81** |
| 64 个非单位 `c` 归一化显示后与原始 binary64 有理数射线严格相同 | **0/64** |
| 单位显示向量最大范数偏差 | `2.8110846983508964e-13` |

新模块 `w2_projective_ray_m12.py` 使用所有原始 binary64 数值精确转 `Fraction`，取正的最大绝对值 pivot `a=|c[p]|`，形成十项精确有理比值 `c_i/a`，保存原始 `c` SHA、每项精确分子/分母、含**正负方向**的射线 SHA 和单独的 `float64` 单位显示向量。这一规范化身份对**正比例缩放**代数等价、对**整体负号**不等价。无论是否经过显示级归一化，都**不改写**已保存的 native `c`、材料 SHA 或原始有限差分系数。

特别重要：64 个显示级归一化后产生舍入的 binary64 坐标，其**精确有理数射线身份也可能不等于原始保存值**，所以除了规范化的精确 rational ray 外，不能把新的 float 单位显示向量冒充“原始原生同调用”。严格只证明二次多项式在**精确正比例代数**意义下有相同零集；**不证明浮点 Cherchi 重三角化、离散构造、精确材料、导数或 Newton** 相同。

## W0 项目交接与 W3 状态

- 针对选定真实 point60，从原始 ZIP 读取已保存并绑定的 Boolean 操作，用冻结的 outer/F/D 文件 SHA、归一化坐标和密度构造 **W0-schema-shaped、`moments.status=NOT_RUN`、`variable_r=null`、`jacobian.type=UNAVAILABLE`** 的诊断预览。其数据不得与原始 `c` 的已保存真实 `r_D` 拼接后伪造新归一化原生结果。`J_D=null`。
- point60 的 `c[7]=3e-6`、原始构造改变 **5 位置／2+2 LPI 特征／17+17 面特征**继续保留；`q[7]=6e-6` 的交叉映射只用于数学显示。
- W0 当前 `schema_v1.json` Git blob `52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc`；旧 `w2_teacher_gate.py` `b42ec6d9b389675123250d79f9cc9efb1b658c07` 仍为 **v1-only**。M12 **未执行 W0 独立 v2 verifier**，未发布正式合同；可选外部 W0 schema 输入必须匹配固定 Git blob，省略时输出 `observed=false` 而非猜测认证。
- 已通过 GitHub 只读查阅 W3 最新 Stage11 原生执行证据 Git blob `342b5e6968ba029c2af389de8de4a394543f422e`：修复材料失败留证和完整 `q` 保存，但新增 Cherchi **0 次**、新左右侧点 **0**、Newton **未放行**。M12 可选 W3 输入也必须按 Git blob 严格绑定；此次 CLI 没有加载 W3 本地文件，因此报告中的 `w3_stage11_observation.observed=false`，其 GitHub **远端已读信息**另由 manifest 保留。

## 本轮真实验收与数据

- `python -m unittest discover -s /mnt/data/w2_m12 -p test_w2_projective_ray_m12.py -v`：**21/21 PASS**，约 `14.487 s`，包含真实 81 包重绑定、17/64 身份分组、精确有理比值重算、正比例放大不变、负号不同、point60 维持失败、SHA/manifest 篡改拒绝、严格的 `NOT_RUN` W0 预览、无 J 和训练导出拒绝。
- M12 真实 CLI 以原始 H8f ZIP + 固定 M9 候选 + W2 M9 语义 manifest fixture 执行成功。此 fixture 是从 GitHub 读取并冻结所需字段显式构建的**测试夹具**，**不声称**与 W2 分支真实 manifest 逐字节相同。提交到 GitHub 的工具可以对完整 checkout 的真实 manifest 做重新认证。
- 完整 81 条证据 `M12_H8F_81_PROJECTIVE_RAYS.json`：**192610 bytes**，SHA256 `255769c4401a89449ef864bf0ef72ec99403d0085b5eb04891512dfe2daab473`，Git blob SHA1 `2d4cf4aae1368e22e760803d9bfe49479125ac4b`。
- 核心源码 Git blob `f5431994a8db1fb6634fc89c8be3797944799adb`；专项测试 Git blob `7d6e680b11e3fb26bfd83f7514e5f2fd58c5d080`。已由 GitHub 连接器再次读取核对。
- 原历史 `failure` 不变、新原生调用 `0`、新 `J_D` 训练标签 `0`、输出中的 W0 诊断状态 `NOT_RUN`。

## 复现

```bash
cd Spin_test
python -m unittest discover -s research/NeuralMoments/teacher \
  -p 'test_w2_projective_ray_m12.py' -v

python research/NeuralMoments/teacher/w2_projective_ray_m12.py \
  --candidate research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json \
  --manifest research/NeuralMoments/teacher/teacher_manifest.json \
  --archive /absolute/path/h8f_81_real.zip \
  --index 60 --output /new/path/M12_H8F_81_PROJECTIVE_RAYS.json
```

该命令只执行 CPU 归档审核，不与 W1/W3 原生 Cherchi 作业竞争。禁止覆盖既存输出；正式交接仍需 W0 在其独占分支对 raw-c 项、projective display 与 source identity 做**独立审查**，并需 W3 后续真实原生左右侧导数与连续性/独立 Newton 终点证据。只有另行建立并经过可信验收的正式发布门槛后，才能考虑 `train/val/test`，不得修改本里程碑的 `excluded` 状态来绕过认证。
