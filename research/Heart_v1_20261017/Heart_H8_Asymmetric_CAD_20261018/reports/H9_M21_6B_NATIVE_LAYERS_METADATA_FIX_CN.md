# W3 M21.6B｜native-layers 元数据参数错位修复

## 用户本地失败证据

用户于 2026-11-08 在 native-layers 阶段得到：

```
KeyError: 'attachment_sha256'
  verify_report_inputs(boundary,ledger,materials)
  boundary['inputs']['six_motion_sha256']==[x['attachment_sha256'] for x in materials]
```

该异常不是材料 SHA 不匹配，也不是原生模块/Boolean 失败。根因是 M21.6B 的 `run()` 已将六份材料作为 `materials` 传入 `compute()`，并且在循环中正确构建独立的 `metadata`（含 stem、material_sha256、attachment_sha256），但原始 `compute()` 忘记传入 metadata，`verify_report_inputs()` 因而错误地把原始材料字典当作 source-motion 元数据读取 `attachment_sha256`。

## 修复内容

- `verify_report_inputs(boundary, ledger, materials, motion_metadata=None)`：分离原始材料与 source-motion metadata；用 metadata 顺序核对六个 attachment SHA；用 boundary 与 ledger 核对材料 SHA 和 stem（若 ledger 项提供 stem）；保留 8455 顶点、162 源点和 7671 EXPLICIT3D/784 LPI 形状门禁。
- `compute(..., motion_metadata=None)`：将 metadata 独立传给 provenance verifier。
- `run()`：调用 `compute(..., metadata)`，不再丢弃已构建的元数据。
- `preview_derived()`：同时携带 sample 的 material SHA，继续做六份材料与附件身份绑定。
- 测试 `test_frozen_boundary_refuses_newton_claim` 增加原始材料占位对象与 motion metadata 分离的回归，覆盖之前的 KeyError。

## 已执行测试

从与当前 W3 提交相同的 release ZIP 解包分析器/测试，在隔离 Python 3 容器应用与 GitHub 完全相同的修改后执行：

- M21.6B 单元测试：**14/14 PASS**。
- 对本轮上传的真实派生文件执行 `--phase preview`：成功，`samples_verified=6`、`intervals_verified=6`、`exact_top_witness_norms_verified=90`。
- Preview 输出 SHA256：`7985987d47f354de9fa535b2bec72995b4541bf8e278b4ce876fee92ccd6329c`。
- 这些测试不等于六份 raw packet 的十质量矩 native-layers 已通过。完整真实分层计算尚未重新执行。

## 科学/执行边界

用户这次运行已经成功读取六份 raw materials、source-only motion attachments 并完成各自 `material_state` 重建，随后在 metadata verifier 处失败。该失败发生在矩积分之前。**没有新增 Cherchi Boolean、没有新 source-only native 调用、没有 Newton**。因此不需要重新编译，也不需要重跑 M21 source-only。修复后只需用一个新的输出目录重跑 `--phase native-layers`，重复离线文件读取及精确分式积分。

## 下一步本地命令

```bash
cd /data/xvxinyao1/Spin_test-W3
BRANCH='research/neuralmoments-w3-heart-h9-20261019'
H9='research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018'
PY="$HOME/.venvs/spin-w3-313/bin/python"
git pull --ff-only origin "$BRANCH"
"$PY" -m unittest discover -s "$H9/tests" -p 'test_h9_m21_6b_moment_layers.py' -v
printf 'TEST_RC=%s\n' "$?"
```

然后复用上一轮相同的 M20/ART/S17/M19/SOURCE/BOUNDARY 路径，但**必须创建全新的** `OUT` 目录（例如 `m21-6b-retry-<timestamp>-<pid>`），再执行：

```bash
OUT="$HOME/Research/W3_H9_Results/m21-6b-retry-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$OUT"
"$PY" -u "$H9/source/h9_m21_6b_moment_layers.py" \
  --phase native-layers --precision-ledger "$M20" --artifact "$ART" \
  --stage17-native-dir "$S17" --m19-run "$M19" --source-run "$SOURCE" \
  --boundary-report "$BOUNDARY" --output "$OUT/moment-layers.json" \
  2>&1 | tee "$OUT/run.log"
RC=${PIPESTATUS[0]}
printf 'M21_6B_REAL_EXIT_CODE=%s\n' "$RC"
if [ "$RC" -eq 0 ]; then sha256sum "$OUT/moment-layers.json"; fi
printf 'OUT=%s\n' "$OUT"
```

不要复用失败的 `m21-6b-20261108T060428Z-3084537` 输出路径，不要修改输入文件或放宽 SHA/构造合同。
