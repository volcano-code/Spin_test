# W3 Heart H9｜M21.6B 十质量矩 J7 分层误差审计：源码与派生数据预检

**唯一分支：** `research/neuralmoments-w3-heart-h9-20261019`  
**冻结研究范围：** `research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/`  
**本轮并没有运行新的 Cherchi Boolean、原生源求值或 Newton。**

## 一、真实六样本输入核对（已在云端执行）

用户上传的 `full-boundary.json`，SHA256：
`759b4df5111fa51e0d51f1e62ff36b5c84e02e85f13d6e3fc5edece95dbab793`。

验证时重新读取两份先前上传的文件：

- M20 `precision-ledger.json`：`95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703`
- M21.5B `m21-3-lpi.json`：`d353486cafb3b81a97c302c51d8a034eedee327fabe92f2497df2c48b49c522e`

账本与原输出 6/6 材料 SHA、6/6 source-motion SHA 对齐。报告包含每样本 8,455 个保留边界点（EXPLICIT3D=7,671、LPI=784、TPI=0）、162 个源点；同侧各 3 个区间，总 6 个；两侧各 8,617 个精确割线分段恒等式（8,455+162）。原始六份 `.json.gz` 本轮没有被云端重复读取，所以这是**派生报告独立验证**而非原生出处二次认证。

独立精确 `Fraction` 数值复核了报告中的 **90 个 top-k 残差向量范数**。M21.6B 的新 `--phase preview` 已实际成功运行，输出：

- `samples_verified=6`
- `intervals_verified=6`
- `exact_top_witness_norms_verified=90`
- `status=M21_6A_DERIVED_MOTION_RECHECKED_J7_LAYERS_NOT_RUN`
- `newton_admitted=false`，`native_j7_layer_comparison_done=false`

**注意数值修订：** 六个区间 LPI/EXPLICIT3D 的 RMS 比率真实范围约为 **12.92–22.82 倍**，不是 14–31 倍。两类 RMS 统计是不同顶点群的有限割线误差，不是 Jacobian 十矩误差的直接比率；在未经分层核算前不能据此归罪于 LPI 导数代码。

## 二、本轮新增的 M21.6B 源码（已在云端实际运行单元测试）

- `source/h9_m21_6b_moment_layers.py`：独立的**精确双数（dual number）自动微分**对每个定向边界三角形构造十个有向四面体矩与其 d/dc7。按 `EXPLICIT_ONLY`、`LPI_ONLY`、`MIXED_EXPLICIT_LPI`、`TPI_TOUCHING` 四种面片支持类别累积。
- 使用平衡分式加法，避免把每个三角片所有分子/分母同时保存在内存中；区间统计只存各面片类别的 10 个合计矩与切向，不做按顶点槽位的虚假跨包配对。
- 对每份保存材料，独立重算 `Σ_组 M`，必须**逐项精确等于**先前 M20 账本的十矩分数；独立双数算出的 `Σ_组 J7` 必须**逐项精确等于**已存在的 `moment_tangent` 算法。
- 对每个同侧区间的十个矩分量，计算三种残差：
  
  `R_native = saved exact M secant − mean(saved C++ J7)`  
  `R_replayed = saved exact M secant − mean(independent replay J7)`  
  `ΔJ = mean(independent replay J7 − saved C++ J7)`  
  
  逐项以 Fraction 严格验证 `R_native = R_replayed + ΔJ`。
- 将 `R_replayed` 按四类面片求和，确保其精确等于合并结果。`R_native` 同时与 M20 保存的精确表面割线残差 float 值逐项相等，避免以新的算法悄悄改变已有残差。
- **解释限制：** 此分解能区分有限材料的分片运动误差和重放导数相对保存原生 J7 的差别；但材料不包含 C++ 原生每面片 J7，不能把 `ΔJ` **唯一因果归属**于某一面片类别。
- `tests/test_h9_m21_6b_moment_layers.py`：包含 dual number 运算、完整十矩多项式 7 点精确差分验证、正向四面体、几何身份、哈希篡改和 Newton 误标识拒绝等 **14 项测试，14/14 PASS**。测试全为**合成/合同回归**，没有冒充原生数据验收。
- `reports/H9_M21_6B_DERIVED_PREVIEW.json`：云端对用户真实派生文件执行的预检结果；无需原始材料。

## 三、用户本地实际运行（不需要编译，代码已推送后执行）

先同步 W3，运行 14 项单元测试。`external/` 是未跟踪研究依赖，不要删除。若同步失败，停止后续计算，保留原样。所有结果写入**新目录**；不要用已有输出文件名覆盖旧材料。

```bash
cd /data/xvxinyao1/Spin_test-W3
BRANCH='research/neuralmoments-w3-heart-h9-20261019'
H9='research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018'
PY="$HOME/.venvs/spin-w3-313/bin/python"
git pull --ff-only origin "$BRANCH"
"$PY" -m unittest discover -s "$H9/tests" -p 'test_h9_m21_6b_moment_layers.py' -v
printf 'M21_6B_TEST_RC=%s\n' "$?"
```

以下假设上述 `git pull` 与 14 项测试均通过（不要求重新运行 M21.6A）：

```bash
M20="$HOME/Research/W3_H9_Results/m20-bigint-20261104-134610-284358250-2185128/precision-ledger.json"
ART="$HOME/Research/W3_H9_Evidence/h8f-original-12135528290.zip"
S17="$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native"
M19="$HOME/Research/W3_H9_Results/m19-20261103-195004-2185128"
SOURCE="$HOME/Research/W3_H9_Results/m21-source-20261104-221452-033013175-1861607"
BOUNDARY=''
for f in "$HOME"/Research/W3_H9_Results/m21-6a-*/full-boundary.json; do
  if [ -f "$f" ] && [ "$(sha256sum "$f" | awk '{print $1}')" = '759b4df5111fa51e0d51f1e62ff36b5c84e02e85f13d6e3fc5edece95dbab793' ]; then
    BOUNDARY="$f"
    break
  fi
done
OUT="$HOME/Research/W3_H9_Results/m21-6b-$(date -u +%Y%m%dT%H%M%SZ)-$$"
MISSING=0
for p in "$M20" "$ART" "$S17/report.json" "$M19/midpoint-plan.json" "$M19/native-two-midpoints/launch_result.json" "$M19/native-two-midpoints/independent-refinement.json" "$SOURCE/layered-report.json" "$SOURCE/worker/layered-report.json"; do
  if [ ! -s "$p" ]; then echo "MISSING_INPUT=$p"; MISSING=1; fi
done
for stem in side-00-left-coarse side-01-left-near side-02-right-near side-03-right-coarse m19-mid-00-left-mid m19-mid-01-right-mid; do
  if [ ! -s "$SOURCE/worker/$stem.source-motion.json" ]; then echo "MISSING_SOURCE_MOTION=$stem"; MISSING=1; fi
done
if [ -z "$BOUNDARY" ]; then echo 'MISSING_PINNED_M21_6A_REPORT'; MISSING=1; fi
if [ "$MISSING" -eq 0 ]; then
  mkdir -p "$OUT"
  "$PY" -u "$H9/source/h9_m21_6b_moment_layers.py" \
    --phase native-layers \
    --precision-ledger "$M20" --artifact "$ART" \
    --stage17-native-dir "$S17" --m19-run "$M19" \
    --source-run "$SOURCE" --boundary-report "$BOUNDARY" \
    --output "$OUT/moment-layers.json" 2>&1 | tee "$OUT/run.log"
  RC=${PIPESTATUS[0]}
  echo "M21_6B_REAL_RC=$RC"
  if [ "$RC" -eq 0 ]; then
    sha256sum "$OUT/moment-layers.json"
    echo "M21_6B_RESULT=$OUT/moment-layers.json"
  else
    echo "M21_6B_LOG=$OUT/run.log"
  fi
else
  echo 'M21_6B_INPUT_CHECK_BLOCKED'
fi
```

### 正式验收口径

- 用户回传 `moment-layers.json` 和 `run.log` 后，检查 6 个样本 × 10 个 M20 精确十矩、6 个样本 × 10 个独立 J7、6 个区间 × 10 个残差分解恒等式。预期 `total_component_split_checks=60`，但**本轮未运行原始六材料，不能提前宣布 60/60 成功**。
- 差异有可能来自重放 `source_only` binary64 速度、几何/分式传播、原生 J7 符号/算法差异、浮点舍入及非对称截断；任何实际失败必须保留证据，不修改历史结果、不调宽门槛。
- Newton 正式准入、连续邻域证书、最终 Heart OBJ 和物理强真值均为**未完成**。

## 四、云端和本地责任划分

本轮**云端可直接完成**：派生报告数据校验、独立 dual-number 分层积分代码、14 项回归、交付 GitHub。完整 6 份真实三角网格的分层矩积分仍需**读取本地保存的材料和速度附件**；其数学部分无原生 Cherchi/CGAL/GPU 依赖，故如果原始材料将来上传到云端，也可以云端离线执行。
