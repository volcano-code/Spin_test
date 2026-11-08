# W3 M21.6B｜用户本地 14/14 回归验收与 native-layers 交接

## 本地回归证据

用户于 2026-11-08 在 `/data/xvxinyao1/Spin_test-W3` 执行：

```bash
$HOME/.venvs/spin-w3-313/bin/python -m unittest discover \
  -s research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/tests \
  -p test_h9_m21_6b_moment_layers.py -v
```

终端记录：`Ran 14 tests in 0.009s`、`OK`、`TEST_EXIT_CODE=0`。同步后 `git rev-parse HEAD` 为 `f542a41521a1a697b2a0622705e6f05c0b9cf76b`。工作区额外未跟踪的 `external/` 仍须保留，不应清理或加入本次提交。

本记录来源为用户粘贴的本地终端结果，不将其冒充 GitHub Actions CI。

## 下一里程碑

执行 `source/h9_m21_6b_moment_layers.py --phase native-layers`，读取六份已有材料、M20 精确账本、M21.6A 报告和六份 source-motion 附件。该阶段不调用新的 Cherchi Boolean，不重新运行 source-only，不编译原生核心，不使用 GPU。它对保存网格进行精确有理矩积分与 dual-number J7 分组，并验证：
- 每个样本的十个独立精确矩与 M20 ledger 逐项相等；
- dual-number 总 J7 与已有 `moment_tangent` 逐项精确相等；
- 六个区间 × 十个矩分量的 `R_native = R_replayed + ΔJ` 恒等式；
- 每个独立面片组残差之和与重放总残差精确相等。

运行前必须检查所有输入、六个 source-motion 附件以及 M21.6A 文件 SHA。任何缺失或哈希不符均停止；不得重跑 Boolean 补材料或放宽 SHA/构造合同。输出写入新目录，保留失败日志。

## 验收状态

14/14 单元测试已由用户本地通过。**真实六材料 native-layers 尚未执行**；不能提前声称 60/60 质量矩/J7/区间分解通过。该阶段是 CPU 精确算术离线计算，需要可访问六份本地材料；不要求 Cherchi 重编译、Boolean、GPU。执行后上传 `moment-layers.json` 和 `run.log` 供独立审计。

Newton、连续构造邻域、根因最终判定和最终 Heart OBJ 均保持 false / 未完成。
