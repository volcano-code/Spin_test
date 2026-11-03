# W3 M20：既有六份材料的精确差分与舍入误差复核

## 触发证据：M19 两点合格，不等于步长收敛通过

用户贴出的本机 M19 报告（源提交 `265bafc0525cc56f94c3f440e9337231ce805a52`）显示 `worker_exit_code=0`、`audit_exit_code=0`、两份中点材料获准用于有限点分析。已有 M18 四点另由 SHA256 `68ee61282caac38d160a4226d9e44df694b7723094890fd62cc61ada434e12e2` 报告绑定。本轮未取得用户本地六份材料字节，不能宣称已复算六份新材料。

| 侧别 | 全区间平均 Jacobian 最大缩放误差 | 两个半区间最大值 | 半/全 |
|---|---:|---:|---:|
| left | 4.425174903810794e-9 | 1.698752726496649e-8 | 3.8388374774378904 |
| right | 7.018424627819146e-9 | 1.588000657869442e-8 | 2.26261695762185 |

当前 `h9_stage19_multiscale.compare_refinement` 中字段 `half_vs_full_trapezoid_max_error_ratio` 实际为 `full / max(halves)`，名称与方向相反。0.2605、0.4420 不是半区间误差变为 26%/44%。本轮不更改历史报告，新结果使用 `binary64_full_over_worst_half` 与 `binary64_worst_half_over_full` 等无歧义字段。

端点 Jacobian 的半区间最大误差/全区间最大误差分别约 0.5503、0.5418，有所改善；但平均 Jacobian 误差未表现出此次步长减半下的改善，不能据此宣称二阶收敛、全 Jacobian 通过或 Newton 可准入。

## 为什么做本轮只读计算

既有 `check_mass_snapshot` 先对有理材料精确积分，再转换为 `float`；M19 `trapezoid_error` 用这些浮点数相减、除以约 4.5e-8 的步长。对表示的表面能精确积分，不等于后续差分没有舍入误差。

本脚本分别计算：

1. 复现 M19 原有二进制浮点运算结果；
2. 把已保存浮点输入按 `Fraction.from_float` 精确展开，然后作差/除法；
3. 从材料的有理坐标与三角面重新计算**精确十矩**，先作差/除法，最后仅为展示转换为浮点数。

路线 2 不会恢复已舍弃的精确积分信息。路线 3 消除这些特定表示多面体的积分结果转浮点及后续运算误差，但不消除原生源几何生成的 binary64 舍入，也不会把记录的浮点 Jacobian 变成数学真导数。

每个分量输出严格相等的残差分解：

`R_binary64 - R_exact_surface = moment_input_contribution + arithmetic_contribution`。

记录的十矩如果不等于精确积分的最近浮点表示，会单独标记，不能无条件把该差异都解释成舍入。使用同一个分量尺度 `max(1, abs((Ja+Jb)/2))`，避免在三条路径之间改变归一化分母。

此外输出两个半区间**有符号**残差、它们的加权和、中点 Jacobian 曲率修正，并精确核验分割恒等式。全区间较小的残差可能包含相反符号抵消；现有仅含绝对值的输出不能区分这种情况。

## 执行和验证边界

- 新源码 `source/h9_m20_precision_replay.py`：纯标准库，不加载原生 `.so`，不调用 Cherchi，不修改旧报告/材料；只把结果写入全新输出目录。
- 测试 `tests/test_h9_m20_precision_replay.py`：实际运行 **13/13 PASS，0 skipped**。包括精确四面体十矩、二/三次函数、共享中点扰动抵消、两种浮点舍入贡献的精确恒等式、不等距分割恒等式、文件 SHA 篡改拒绝、完整六包**合成存储夹具**读取，以及真实历史 H8f sample59 的十矩积分复验。
- 真实历史测试使用原始 ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。该测试不是用户的新侧点求值。
- **当前未执行用户六份实际材料的 M20 复核。新原生调用为 0。没有新远端 CI 结论。**
- 完整测试日志见 `M20_TESTS.log`。

## 本地命令

`M19_RUN` 保持为原成功实验的根目录，其中包含 `midpoint-plan.json`、`native-two-midpoints/launch_result.json`、`native-two-midpoints/two-midpoint-native/`。不重复原生实验，也无需因这次新增离线脚本重编译。

```bash
cd /data/xvxinyao1/Spin_test-W3
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
W3_PY="$HOME/.venvs/spin-w3-313/bin/python"
M20_OUT="$M19_RUN/precision-replay-$(date +%Y%m%d-%H%M%S)-$$"
"$W3_PY" -u "$H9/source/h9_m20_precision_replay.py" --stage18-audit "$HOME/Research/W3_H9_Results/stage18-audit-20261102_170733/independent-audit.json" --stage17-native-dir "$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native" --m19-run "$M19_RUN" --output "$M20_OUT"
```

结果 `precision-ledger.json` 显式保留 `newton_admitted=false`、`asymptotic_order_certified=false`、`native_geometry_generation_roundoff_removed=false`。先观察舍入贡献与精确差分残差，再决定是否需要更改步长或检查源运动/Jacobian 合同；不根据两个尺度拟合出的数值直接宣布收敛阶。

参考：Python 3.13 `fractions` 文档 https://docs.python.org/3.13/library/fractions.html 说明浮点到有理数转换的精确语义；GSL 数值微分文档 https://www.gnu.org/software/gsl/doc/html/diff.html 讨论截断误差与舍入误差的步长权衡。
