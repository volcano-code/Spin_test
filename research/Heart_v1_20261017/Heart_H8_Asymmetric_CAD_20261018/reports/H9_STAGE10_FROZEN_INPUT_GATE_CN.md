# W3 Heart H9｜第十阶段：冻结输入门禁（2026-10-20）

**唯一可写分支：** research/neuralmoments-w3-heart-h9-20261019。冻结 H8f 祖先：0bcc187b3005478baa586a6d6f450e73811ca342。本阶段只涉及该分支 Heart H8 目录下的新 H9 source/tests/reports 与现有 W3 文件。

## 已实际实现

- 新增 source/h9_frozen_input_gate.py：不依赖 Cherchi、CGAL 原生扩展，核对真实 H8f artifact 12135528290 的 SHA256，再从归档材料独立重算条件性内部边—边穿越证书；逐字段比对用户给出的证书，而非只信任自报哈希。
- source/prepare_h9_pinned_native.py 增加 --phase inputs，并在真原生模块导入与昂贵求值**之前**执行此门禁。缺失、篡改、不合法浮点值、重复 JSON 键都会 fail closed。
- 新增 12 项测试：8 项使用真实归档或测试控制流，4 项无需归档也可验证拒绝逻辑。旧第八、九阶段的 5 个**显式模拟**成功路径测试相应更新，仍不允许将这些测试说成新 Boolean。
- 冻结 CI [run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 原始结论 **failure**；原始 [artifact 12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290) 的 SHA256 为 99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9，request SHA256 为 1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c。

## 真实输入结果（不是新的 native 求值）

--phase inputs 返回 **exit 0**，输出 H9_STAGE10_REAL_INPUT_GATE.json。四个预定 q[7] 为：

| index | side | q[7] | 代理模型预期符号 |
|---:|---|---:|---:|
| 0 | left-coarse | 2.1805862283444328e-6 | +1 |
| 1 | left-near | 2.2705862283444327e-6 | +1 |
| 2 | right-near | 2.2905862283444326e-6 | -1 |
| 3 | right-coarse | 2.3805862283444325e-6 | -1 |

这些符号仅来自固定法向 inverse-Gauss 条件性模型。尚未取得新 Cherchi 生产 Boolean、连续光滑分支、Newton 接受状态或 Heart OBJ。

## 实际测试与环境

当前 Python 3.13.5，cgroup 内存上限 4 GiB，swap 0，非完整 W3 git checkout，缺少三个 native 模块；git clone github.com 因 DNS 失败。构建预检 **exit 2**，运行预检 **exit 2**；这意味着 **新 native 样本仍然 0/4**。

独立 Python unittest 完整 H9 回归：**86/86 PASS，33.087 秒，0 skipped**（包含原始 H8f Fraction 材料复算）。一次中途超时的复跑未计为成功，后续完整复跑结果另存。

## 可重放

在真实 W3 checkout 的根目录：

```bash
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$H9/source/prepare_h9_pinned_native.py" --phase inputs \
  --artifact /path/to/real-H8f-artifact.zip \
  --certificate "$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json" \
  --output /tmp/h9-w3-input-gate
python -m unittest discover -v -s "$H9/tests" -p 'test_h9*.py'
```

只有在符合 **24 GiB 有效内存、swap=0、正确源分支与固定原生依赖** 的机器上，才能执行已有 --phase build 与 --phase run。Newton 准入仍为拒绝；最终 Heart OBJ、收敛残差与独立积分的终态物理指标均尚无真实证据。
