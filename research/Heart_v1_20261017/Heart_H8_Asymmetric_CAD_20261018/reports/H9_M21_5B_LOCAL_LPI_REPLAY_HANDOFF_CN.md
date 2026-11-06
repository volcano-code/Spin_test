# W3 Heart H9｜M21.5B 本地只读六点 LPI 运动复核交接

**唯一分支：** research/neuralmoments-w3-heart-h9-20261019  
**脚本：** source/h9_m21_3_lpi.py  
**科学范围：** 六份既有材料 × 三个固定 LPI 构造 = 18 个真实数据诊断；不执行 Boolean、不重新构建 Cherchi、不运行 Newton。

## 为什么本阶段需要本地执行

M21.5A 已在云端对上传的 M20 ledger 完成 60/60 精确割线重算。但 Library 中没有检索到 M21 source-run 的六份 source-motion 附件和完整六份原始材料字节。此前对话记录给出的工作站路径如下；本阶段只读取它们。

## 已知输入路径

- W3 checkout：/data/xvxinyao1/Spin_test-W3
- H9：research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
- Python：$HOME/.venvs/spin-w3-313/bin/python
- M20 ledger：$HOME/Research/W3_H9_Results/m20-bigint-20261104-134610-284358250-2185128/precision-ledger.json
- H8f artifact：$HOME/Research/W3_H9_Evidence/h8f-original-12135528290.zip
- Stage17 native：$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native
- M19 run：$HOME/Research/W3_H9_Results/m19-20261103-195004-2185128
- M21 source run：$HOME/Research/W3_H9_Results/m21-source-20261104-221452-033013175-1861607

## 执行命令

    cd /data/xvxinyao1/Spin_test-W3 || exit 1
    H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
    W3_PY="$HOME/.venvs/spin-w3-313/bin/python"
    M20_LEDGER="$HOME/Research/W3_H9_Results/m20-bigint-20261104-134610-284358250-2185128/precision-ledger.json"
    H8_ARTIFACT="$HOME/Research/W3_H9_Evidence/h8f-original-12135528290.zip"
    STAGE17_NATIVE_DIR="$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native"
    M19_RUN="$HOME/Research/W3_H9_Results/m19-20261103-195004-2185128"
    SOURCE_RUN="$HOME/Research/W3_H9_Results/m21-source-20261104-221452-033013175-1861607"
    CERT="$PWD/$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json"
    OUT="$HOME/Research/W3_H9_Results/m21-5-lpi-$(date -u +%Y%m%dT%H%M%SZ)-$$"

    # 0. 必需输入检查；任何一项缺失都停止，不重跑原生计算
    for f in "$M20_LEDGER" "$H8_ARTIFACT" "$CERT"       "$M19_RUN/midpoint-plan.json"       "$M19_RUN/native-two-midpoints/launch_result.json"       "$SOURCE_RUN/layered-report.json"       "$SOURCE_RUN/worker/layered-report.json"; do
      test -s "$f" || { echo "MISSING_INPUT=$f"; exit 2; }
    done

    # 六份材料及六份 source-motion 附件必须全部存在
    for stem in side-00-left-coarse m19-mid-00-left-mid side-01-left-near                 side-02-right-near m19-mid-01-right-mid side-03-right-coarse; do
      test -s "$SOURCE_RUN/worker/$stem.source-motion.json" || {
        echo "MISSING_SOURCE_MOTION=$SOURCE_RUN/worker/$stem.source-motion.json"; exit 2;
      }
    done

    # M20 ledger 必须与本次云端复核使用的输入完全一致
    echo "===== M20 ledger SHA ====="
    sha256sum "$M20_LEDGER"
    echo "===== Original H8f artifact SHA ====="
    sha256sum "$H8_ARTIFACT"

    # 1. 仅运行 M21.3 离线回归；不调用 Cherchi
    "$W3_PY" -m unittest discover -s "$H9/tests" -p 'test_h9_m21_3_lpi.py' -v || exit $?

    # 2. 六包三类 LPI 精确运动复核；输出目录必须是新目录
    mkdir -p "$OUT"
    "$W3_PY" -u "$H9/source/h9_m21_3_lpi.py"       --precision-ledger "$M20_LEDGER"       --artifact "$H8_ARTIFACT"       --stage17-native-dir "$STAGE17_NATIVE_DIR"       --m19-run "$M19_RUN"       --source-run "$SOURCE_RUN"       --output "$OUT/m21-3-lpi.json"
    RC=$?
    echo "M21_3_LPI_EXIT_CODE=$RC"
    test "$RC" -eq 0 || exit "$RC"

    # 3. 冻结输出哈希并打印关键计数
    sha256sum "$OUT/m21-3-lpi.json"
    "$W3_PY" - "$OUT/m21-3-lpi.json" <<'PY'
    import json, sys
    p=json.load(open(sys.argv[1]))
    print("schema:", p.get("schema"))
    print("status:", p.get("status"))
    print("samples:", len(p.get("samples", [])))
    print("LPI rows:", sum(len(x.get("constructions", [])) for x in p.get("samples", [])))
    print("same-side intervals:", len(p.get("same_side_interval_lpi_secants", [])))
    print("new source calls in this diagnostic:", p.get("new_native_source_calls_this_run"))
    print("root cause determined:", p.get("root_cause_determined"))
    print("continuous neighborhood certified:", p.get("continuous_neighborhood_certified"))
    print("Newton admitted:", p.get("newton_admitted"))
    PY

    echo "M21_5B_OUTPUT=$OUT/m21-3-lpi.json"

## 预期验收

- m21-3-lpi.json 状态为 SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY。
- samples=6，LPI rows = 18，same-side intervals = 6。
- 每条 LPI 行都包含精确 d,d',N,N',t,t'、两种商法则/隐式约束分解、物理坐标和速度。
- 输出保留 new_native_source_calls_this_run=0、root_cause_determined=false、continuous_neighborhood_certified=false、newton_admitted=false。

若预检报告缺少任意 source-motion 附件，停止并返回缺失文件列表；不要为补附件重新运行 Boolean。M21 source-only 调用是否需要补跑，必须先确认附件确实缺失及原始 source run 的日志/哈希状态。

## 回传与下一步

将整个 m21-5-lpi-* 输出目录打包上传，或至少上传 m21-3-lpi.json、命令日志及 SHA256。云端随后审计 18 行真实诊断，确认 LPI 分母变化、法向变化、锚点运动和线运动的贡献，再决定是否有足够证据定位 M21 的运动/Jacobian 偏差。

**本阶段不需要本地编译 Cherchi、不需要 GPU、不需要新的 Boolean 求值。**
