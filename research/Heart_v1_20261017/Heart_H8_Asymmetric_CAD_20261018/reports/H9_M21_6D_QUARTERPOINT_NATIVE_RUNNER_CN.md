# W3 Heart H9｜M21.6D-P1 单点 Cherchi + source-motion 执行器

日期：2026-11-08  
唯一写入分支：`research/neuralmoments-w3-heart-h9-20261019`

## 本里程碑实现

新增：
- `source/h9_m21_6d_quarterpoints.py`
- `tests/test_h9_m21_6d_quarterpoints.py`

执行器按 `--index 0..3` 一次只执行一个 quarter-point，不并行、不一次性提交四个长作业。每次 run 包含：

1. 重新生成并逐字段比较 M21.6D 计划；重新绑定 M20、M18、Stage17、M19、M21.6A、M21.6C 与六份 source-motion 输入；
2. 验证干净 W3 分支、Python 3.13、24 GiB 地址空间限制、Swap=0、固定 Cherchi/GMP/core 二进制 SHA 和 build evidence；
3. 仅对指定 q 调用一次真实 `InProcessCherchiEvaluator` Boolean，同调用材料立即写入 unverified gzip；
4. 严格原生有理边界检查、独立精确十质量矩重积分、H7 符号支撑/事件定向符号检查；
5. 对同一材料调用一次 `evaluate_spin_it_faster_source_motion`，要求源几何逐位匹配、source 离散签名与区间两端一致；
6. 用精确保留构造重建 8455 个点、独立重算 J7，检查与原生同调用 Jacobian 第 7 列的一致性；
7. 独立第二进程重新读取材料、重新做边界/十矩/H7/J7 审计，全部通过后才将 unverified 包提升为正式 quarterpoint 包。

## 资源与安全边界

- 每次只允许 1 个新 Boolean 和 1 个 source-motion 调用。
- worker 最多 3200 秒，独立审计最多 330 秒，总 run 上限 3600 秒。
- 子进程地址空间上限 24 GiB；复用已固定的原生二进制，不在本阶段重新编译。
- 每个点独立目录、create-only 证据文件；失败保留 unverified 包，不覆盖历史材料。
- 不执行 Newton，不宣称连续光滑性，不生成最终 Heart OBJ。

## 当前状态

代码与 15 项纯合同测试已提交；尚未在用户本地执行新 Cherchi Boolean 或 source-motion。四个点必须串行执行。建议先运行 index 0，审查完整证据后再继续 index 1、2、3。

## 本地前置文件

- quarterpoint plan：M21.6D-P0 输出的 `quarterpoint-plan.json`
- build evidence：必须在**当前最新 W3 HEAD** 上重新生成；不能复用旧 M19 的 build evidence，因为其 HEAD/source-contract 指纹已过期。可复用已编译缓存，但需要新鲜证据文件。
- 其余输入路径沿用 M21.6D-P0 已验证的 M20/M18/Stage17/M19/M21 source 目录。

## 单点成功条件

`launch_result.json` 必须是：
`ONE_QUARTERPOINT_INDEPENDENTLY_VERIFIED_NO_NEWTON`

同时 `independent-audit.json` 必须记录：
- 新 Boolean 调用 1；
- 新 source-motion 调用 1；
- 独立十矩重积分通过；
- 严格有理边界通过；
- H7 同侧构造身份和精确事件符号通过；
- source 几何逐位匹配、离散签名与区间两端一致；
- exact retained-chain J7 与同调用 native J7 对照通过。

四点全部完成后，才开展 quarter-point 分层残差汇总；不能在单点结果上宣称 Newton 已准入。

## 当前 HEAD 的本地 build evidence

先同步本分支，再在当前 HEAD 上生成一次新的 pinned build evidence。M19 的旧 build evidence 绑定的是旧 HEAD，`verify_build_evidence` 会拒绝旧 HEAD；即使二进制缓存可复用，也必须重新生成当前 HEAD 的 evidence：

```bash
QPT_BUILD="$HOME/Research/W3_H9_Results/m21-6d-native-build-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$(dirname "$QPT_BUILD")"

env -u CONDA_PREFIX -u LD_LIBRARY_PATH -u LIBRARY_PATH -u CMAKE_PREFIX_PATH \
  -u PYTHONPATH -u PYTHONHOME -u BOOST_ROOT -u Boost_ROOT -u Boost_DIR \
  -u PKG_CONFIG_PATH \
  PATH="$HOME/.venvs/spin-w3-313/bin:/usr/local/bin:/usr/bin:/bin" \
  LD_PRELOAD="$W3_STDCXX" \
  "$PY" -u "$H9/source/prepare_h9_pinned_native.py" \
  --phase build --repo "$PWD" --output "$QPT_BUILD"
```

验收要求：生成 `$QPT_BUILD/build_evidence.json`，其 core/Boolean/GMP 三个模块 SHA 必须与 M19 计划中的 `native_binary_sha256` 完全相同。若不同，执行器会在 Boolean 前阻断，不得绕过。



## 单点执行命令（先 index 0）

同步最新分支并运行 15 项测试后，必须在当前 HEAD 生成新的 build evidence。确认二进制 SHA 与计划完全一致后，先执行 index 0；不要并行运行四个点。

```bash
cd /data/xvxinyao1/Spin_test-W3
export H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
export PY="$HOME/.venvs/spin-w3-313/bin/python"
export W3_STDCXX="$(readlink -f /usr/lib/x86_64-linux-gnu/libstdc++.so.6)"

export M20="$HOME/Research/W3_H9_Results/m20-bigint-20261104-134610-284358250-2185128/precision-ledger.json"
export ART="$HOME/Research/W3_H9_Evidence/h8f-original-12135528290.zip"
export S17="$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native"
export M19="$HOME/Research/W3_H9_Results/m19-20261103-195004-2185128"
export SOURCE="$HOME/Research/W3_H9_Results/m21-source-20261104-221452-033013175-1861607"
export M18_AUDIT="$HOME/Research/W3_H9_Results/stage18-audit-20261102_170733/independent-audit.json"
export CERT="$PWD/$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json"
export PLAN="$HOME/Research/W3_H9_Results/m21-6d-plan-20261108T110852Z-3084537/quarterpoint-plan.json"

# 重新定位 SHA 固定的 M21.6A / M21.6C 文件
BOUNDARY_SHA=759b4df5111fa51e0d51f1e62ff36b5c84e02e85f13d6e3fc5edece95dbab793
M21_6C_SHA=62c69598747623121314cdf88055315dc7617726c3bfc0b8a9e7c3fd57ae3915
BOUNDARY=""
MOMENT_LAYERS=""

for f in "$HOME"/Research/W3_H9_Results/m21-6a-*/full-boundary.json; do
  [[ -f "$f" ]] || continue
  [[ "$(sha256sum "$f" | awk '{print $1}')" == "$BOUNDARY_SHA" ]] && { BOUNDARY="$f"; break; }
done

while IFS= read -r -d '' f; do
  [[ "$(sha256sum "$f" | awk '{print $1}')" == "$M21_6C_SHA" ]] && { MOMENT_LAYERS="$f"; break; }
done < <(find "$HOME/Research/W3_H9_Results" -type f -name 'moment-layers*.json' -print0)

test -s "$BOUNDARY"
test -s "$MOMENT_LAYERS"
test -s "$PLAN"

# 1. 单元测试
PYTHONINTMAXSTRDIGITS=100000 "$PY" -m unittest discover \
  -s "$H9/tests" -p 'test_h9_m21_6d_quarterpoints.py' -v

# 2. 当前 HEAD 的 build evidence（不可复用旧 M19 build_evidence.json）
QPT_BUILD="$HOME/Research/W3_H9_Results/m21-6d-native-build-$(date -u +%Y%m%dT%H%M%SZ)-$$"
env -u CONDA_PREFIX -u LD_LIBRARY_PATH -u LIBRARY_PATH -u CMAKE_PREFIX_PATH \
  -u PYTHONPATH -u PYTHONHOME -u BOOST_ROOT -u Boost_ROOT -u Boost_DIR \
  -u PKG_CONFIG_PATH \
  PATH="$HOME/.venvs/spin-w3-313/bin:/usr/local/bin:/usr/bin:/bin" \
  LD_PRELOAD="$W3_STDCXX" \
  "$PY" -u "$H9/source/prepare_h9_pinned_native.py" \
  --phase build --repo "$PWD" --output "$QPT_BUILD"

test -s "$QPT_BUILD/build_evidence.json"

# 3. 先运行左侧第一个 quarter-point（单个 Boolean + 单个 source-motion）
RUN_ROOT="$HOME/Research/W3_H9_Results/m21-6d-qpt-$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$RUN_ROOT"

env -u CONDA_PREFIX -u LD_LIBRARY_PATH -u LIBRARY_PATH -u CMAKE_PREFIX_PATH \
  -u PYTHONPATH -u PYTHONHOME -u BOOST_ROOT -u Boost_ROOT -u Boost_DIR \
  -u PKG_CONFIG_PATH \
  PATH="$HOME/.venvs/spin-w3-313/bin:/usr/local/bin:/usr/bin:/bin" \
  LD_PRELOAD="$W3_STDCXX" \
  "$PY" -u "$H9/source/h9_m21_6d_quarterpoints.py" \
  --phase run --index 0 \
  --repo "$PWD" \
  --precision-ledger "$M20" --artifact "$ART" \
  --stage17-native-dir "$S17" --m19-run "$M19" \
  --source-run "$SOURCE" --boundary-report "$BOUNDARY" \
  --moment-layers "$MOMENT_LAYERS" --certificate "$CERT" \
  --stage18-audit "$M18_AUDIT" --plan "$PLAN" \
  --build-evidence "$QPT_BUILD/build_evidence.json" \
  --output "$RUN_ROOT/point-00"

echo "QPT_BUILD=$QPT_BUILD"
echo "QPT_RUN=$RUN_ROOT/point-00"
```

index 0 的 `launch_result.json` 必须显示 `ONE_QUARTERPOINT_INDEPENDENTLY_VERIFIED_NO_NEWTON`，且 `independent-audit.json` 中 Boolean/source-motion 调用计数分别为 1。只有通过后才继续 index 1、2、3。
