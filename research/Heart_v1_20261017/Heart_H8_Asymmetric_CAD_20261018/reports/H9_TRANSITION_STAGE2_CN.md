# W3 Heart H9：sample 60 邻域边-边事件定位（第二里程碑）

**裁决：继续拒绝 Cherchi/Faster Newton 准入，未得到连续可微邻域或最终优化模型。** 本阶段不改 H8f 原始历史运行及失败结论。

## 验证身份

- W3 唯一工作分支：`research/neuralmoments-w3-heart-h9-20261019`；冻结 H8f `0bcc187b3005478baa586a6d6f450e73811ca342`。
- [历史失败 CI #39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402)；[原始 artifact #12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290)。
- artifact ZIP SHA256：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`；冻结 request SHA256：`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`。
- 全部原始 81/81 点有效；30/30 数值差分通过但整体 H8f 构造门禁 **failure**，80 个非基点只有 index 60 精确构造分支异常。不能以数值成功覆盖构造失败。

## 实际完成：输入共享边的精确有理符号反转

source 原始网格的边 `(24,90)` 分别属于 `(24,89,90)` 和 `(24,90,151)`；design 原始网格的边 `(5517,5518)` 分别属于 `(5516,5517,5518)` 和 `(5517,5518,5523)`。两边均经实际归档材料/请求逐一检查，恰好各有两个邻接三角形。

使用输入边四点行列式 `det(source[24], source[90], design[5517], design[5518])`（Fraction **精确求值**，不经 double 近似决定符号）：

| 历史样本 | q[7] 扰动 | 严格符号 | 浮点展示近似值 |
|---|---:|---:|---:|
| 0 | 0 | 正 | +4.566691773253687e-8 |
| 57 | -3.0e-6 | 正 | +1.0574026262460174e-7 |
| 58 | -1.5e-6 | 正 | +7.570348493289463e-8 |
| 59 | +1.5e-6 | **正** | +1.5630561011148573e-8 |
| 60 | +3.0e-6 | **负** | -1.4405585247826644e-8 |
| 61 | -0.75e-6 | 正 | +6.06851750218784e-8 |
| 62 | +0.75e-6 | 正 | +3.0648713062168615e-8 |
| 63 | -0.375e-6 | 正 | +5.317603979933585e-8 |
| 64 | +0.375e-6 | 正 | +3.8157808819713754e-8 |

按这些实际端点的**精确行列式值**作割线预测：`q[7] ≈ +2.2805875399117463e-6`。注意这并不是 Cherchi 原生真实调用得到的根，不是区间内零点的证明；只有在后续证实原始边坐标随 q 连续后才可从变号进一步推断存在连续运动的共面事件。

历史原始 59→60 两点的真实独立积分质量矩割线相对于基点解析 Jacobian 第 7 列的最大缩放偏差约 `1.4456094976282303e-5`。**这个小误差不构成同一可微分支证明。** H9 的旧报告已经证实 60 的两处非共面 LPI 支撑身份替换、17 删除/17 新增符号三角形、434 个 face-array 槽位差；本阶段精确符号反转与该异常对应。

## 实现与本地执行

- `source/locate_h9_transition.py`：精确验 ZIP/request/sample material SHA、原始边邻接语义、9 点行列式符号；输出含完整有理分子分母和归档质量矩的 JSON；所有拒绝 fail-closed。
- `source/probe_h9_transition_live.py`：**只能在真实原生模块存在时**执行的四点 Cherchi 微区间探针；串行新样本 `q[7]` 为 `1.875e-6、2.25e-6、2.2805875399117463e-6、2.625e-6`，仍保持其余 9 维系数不变，精确 native boundary、自立 Fraction 十质量矩复核、样本语义比对、保留完整同调用快照；每次保存哈希与失败现场。无替代 Boolean/无假造采样。
- `tests/test_h9_transition.py`：5 个新增单元测试（原始 ZIP 九点端到端、符号割线、边邻接、错误 ZIP 拒绝、原生依赖缺失的 fail-closed）。与上一里程碑回归合计 **8/8 PASS**，真实本地执行。
- **已实际尝试** `probe_h9_transition_live.py`，本环境无 `_make_it_stand`、`_cherchi_core_boolean` / `CGAL` 已安装构建物，原生执行失败 `LOAD_NATIVE_CHERCHI_BINARY`，exit code 1、`native_calls_completed=0`。禁止将旧 81 次调用计算成新运行。完整错误及失败 JSON 保存在本地结果目录，报告附失败摘要。

## 本地复现命令

```bash
export H9_EVIDENCE_ZIP=/path/to/heart-h8f-artifact.zip
python -m unittest discover -v -s research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/tests -p 'test_h9*.py'
python research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/locate_h9_transition.py --artifact "$H9_EVIDENCE_ZIP" --output /tmp/h9-edge-event.json
# 仅在已构建并注入 Python 路径的 pinned H8f 原生 Cherchi/CGAL 环境下运行；外部 timeout 确保作业 <60 分钟，串行：
timeout 3300s python research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/probe_h9_transition_live.py --artifact "$H9_EVIDENCE_ZIP" --output /tmp/h9-native-microprobe
```

不得改其他 W 分支或 main；在 24GiB/swap0 的协议条件下串行运行原生任务，编译最多 4 并发。本里程碑**未实际新增原生求值成功样本，没有 Heart 终态 OBJ、收敛残差或独立物理终态验收**。待原生环境可用后对微区间进行真实调用与逐点判定，再根据左右支撑状态尝试更细的二分，而非直接放行 Newton。
