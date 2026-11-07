# W3 Heart H9｜M21.5B：本地 12/12 回归通过，转入六份真实材料复核

**唯一分支** `research/neuralmoments-w3-heart-h9-20261019`。本报告依据用户在聊天中提供的 Ubuntu 终端输出，属于**用户本地运行记录的文字转录**，而不是云端重新执行的实验或 GitHub Actions 结果。保留该来源差别，不把其计入未经复核的 CI 通过。

## 实际回归验收

- 用户工作站：`/data/xvxinyao1/Spin_test-W3`，`$HOME/.venvs/spin-w3-313/bin/python`。
- 测试：`python -m unittest discover -s research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/tests -p test_h9_m21_3_lpi.py -v`。
- 结果：`Ran 12 tests in 0.006s`；`OK`；`TEST_EXIT_CODE=0`。
- 运行时本地 `git rev-parse HEAD`：`20e496795643ab6f60712bba62c05194d2935e76`，与当时 W3 远端一致。
- 工作区 `git status --short --branch`：仅 `?? external/`；不得删除、覆盖或把第三方原生依赖加入 W3 提交。
- 包括：严格有理数 token 往返、逆序 LPI 构造、拒绝无效几何/歧义、线性位置零割线残差、三次位置有符号残差、历史附件哈希绑定等合成/接口回归。
- **本次通过的是 12 项单元测试，不是六个生产材料各三个 LPI 共 18 项真实运行诊断。**

## 接下来的真实数据阶段

使用现存原始 H8f artifact、M18/Stage17 四侧材料、M19 两个中点材料、M20 `precision-ledger.json` 及 M21 source-only worker 的六份 `*.source-motion.json`。

以 `source/h9_m21_3_lpi.py` 实际读取以上文件；程序依照 `h9_m21_layered_replay.py` 的严格文件 SHA、冻结请求、原生核心和资料身份证据逐项验证。随后对 Repeated、Left-full、Right-first 三类 LPI 进行每样本位置/速度/分母/参数导数分析，并产生 6 个同侧区间残差比较。

**输入脚本与现存默认路径：**`reports/H9_M21_5B_LOCAL_LPI_REPLAY_HANDOFF_CN.md`。
注意它包含需要用 `bash` 子进程执行的旧式 `exit` 行，不应直接粘贴执行以免关闭当前交互终端；建议逐步检查路径后直接运行以下命令，不包含主动退出终端的语句。

```bash
cd /data/xvxinyao1/Spin_test-W3
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
W3_PY="$HOME/.venvs/spin-w3-313/bin/python"
M20_LEDGER="$HOME/Research/W3_H9_Results/m20-bigint-20261104-134610-284358250-2185128/precision-ledger.json"
H8_ARTIFACT="$HOME/Research/W3_H9_Evidence/h8f-original-12135528290.zip"
STAGE17_NATIVE_DIR="$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native"
M19_RUN="$HOME/Research/W3_H9_Results/m19-20261103-195004-2185128"
SOURCE_RUN="$HOME/Research/W3_H9_Results/m21-source-20261104-221452-033013175-1861607"

for f in "$M20_LEDGER" "$H8_ARTIFACT" "$M19_RUN/midpoint-plan.json" "$M19_RUN/native-two-midpoints/launch_result.json" "$M19_RUN/native-two-midpoints/independent-refinement.json" "$STAGE17_NATIVE_DIR/report.json" "$SOURCE_RUN/layered-report.json" "$SOURCE_RUN/worker/layered-report.json"; do
  test -s "$f" || printf 'MISSING_INPUT=%s\n' "$f"
done
for stem in side-00-left-coarse side-01-left-near side-02-right-near side-03-right-coarse m19-mid-00-left-mid m19-mid-01-right-mid; do
  test -s "$SOURCE_RUN/worker/$stem.source-motion.json" || printf 'MISSING_ATTACHMENT=%s\n' "$stem"
done
```

若任一输入缺失，停止于路径/归档定位；不要重跑 Cherchi Boolean，更不要放宽哈希/身份校验。若存在，使用唯一新输出目录执行：

```bash
OUT="$HOME/Research/W3_H9_Results/m21-5b-lpi-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$OUT"
"$W3_PY" -u "$H9/source/h9_m21_3_lpi.py" \
  --precision-ledger "$M20_LEDGER" \
  --artifact "$H8_ARTIFACT" \
  --stage17-native-dir "$STAGE17_NATIVE_DIR" \
  --m19-run "$M19_RUN" \
  --source-run "$SOURCE_RUN" \
  --output "$OUT/m21-3-lpi.json" >"$OUT/run.log" 2>&1
RC=$?
printf 'M21_5B_REAL_RUN_EXIT_CODE=%s\n' "$RC"
test "$RC" -eq 0 && sha256sum "$OUT/m21-3-lpi.json"
printf 'M21_5B_OUTPUT=%s\n' "$OUT"
```

所有输入数据必须保留原位，结果写到新目录。失败时保留 `run.log` 与原始报错，不在未证实原因时改代码。

## 科学门槛与资源

- 目标真实分析：`samples=6`、`sum(len(constructions))=18`、`same_side_interval_lpi_secants=6`，`status=SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY`。
- `new_native_source_calls_this_run=0`、`new_boolean_calls_this_run=0`、`root_cause_determined=false`、`continuous_neighborhood_certified=false`、`newton_admitted=false`。
- **此轮不要求再编译 Cherchi，不需要 GPU，不需要新的 Boolean。** 若原始六份文件及附件无法提供给云端，真实数据运行必须在能读取它们的 Ubuntu 本机完成；分析器维护与后续解释报告仍可在云端进行。
- 12/12 通过不代表 M21.5B 的真实六样本任务已经完成，更不代表 Newton 准入或 Heart 最终 OBJ 已完成。
