# W3 Heart H9｜M19：真实 Cherchi 左右分支二分加密与两尺度导数诊断

## 当前证据与目标

**唯一可写分支**：`research/neuralmoments-w3-heart-h9-20261019`。基于 W3 M18（`de50fb40bc16232dd0e327fae40e319295579364`）已在用户本机完成的四点原生/独立审计。用户报告 M18 原始审计 SHA256 为：

`68ee61282caac38d160a4226d9e44df694b7723094890fd62cc61ada434e12e2`

用户实际测得：4/4 新 Cherchi 侧点通过独立十质量矩积分；左、右两侧有限构造分别与历史 H8f sample59 / sample60 的精确符号支撑一致，事件定向符号 `+,+,-,-`。每侧端点间隔约 `9e-8`；两端 Jacobian 平均与独立割线的最大缩放误差左侧 `4.425174903810794e-9`、右侧 `7.018424627819146e-9`，最大分量均为 `Mzz`。此处“缩放误差”以 `max(1,abs(J))` 归一化，不应误写为严格相对误差。

M19 新增 **2 个**本地真实采样候选，不复写 Stage17 四份材料：

| 序号 | 侧别 | 候选 c[7] | 意义 |
| --- | --- | ---: | --- |
| 0 | `left-mid` | 在 `left-coarse` 与 `left-near` 间做精确 binary64 中点 | 左侧两段半间隔 |
| 1 | `right-mid` | 在 `right-near` 与 `right-coarse` 间做精确 binary64 中点 | 右侧两段半间隔 |

参考数值约为左 `2.225586228344433e-6`，右 `2.3355862283444326e-6`；**实际执行必须使用已锁定 M18 4 个真实 binary64 端点重新计算的十维 q，不要手输这些显示近似值。** 每个新点的其他 9 维系数严格保持不变。不会跨越条件性事件根。

## 本阶段开发

- `source/h9_stage19_multiscale.py`：先对历史 ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9` 及条件解析证书重新验真；严格要求 M18 审计的已报告 SHA256、4 个原生 JSON/gzip 材料 SHA 和构建/参数/十质量矩身份；只生成两个真正位于同侧区间内的二分采样计划。拒绝 1 ULP、符号零、材料哈希、身份、其他系数或分支次序改变。提供纯函数 `compare_refinement`，比较原尺度和两个半尺度的端点 Jacobian 平均/割线误差及误差比例，**不预先假设二阶收敛**。
- `source/h9_stage19_native_midpoints.py`：在高内存、零 Swap、干净 W3 分支以及本地新构建证据全部通过后，以 24 GiB 地址空间上限、单次 60min 以内的进程组约束执行 **2 次新的** Cherchi 原生 in-process midpoint 求值；保持与 Stage17 相同的冻结 CAD、固定二进制身份和求值器配置。每次运行先排他持久化 `*.unverified.json.gz`，再执行真实精确边界、独立十矩积分、LPI/TPI 身份和事件符号检查；失败只保留取证材料，不冒充已认证侧点。随后独立打开两个新 gzip，重新积分真实十质量矩并生成误差报告。与历史 M18 及同构建四点的 `evaluation_map_identity` 必须一致，不声明跨构建历史二进制相同。
- `tests/test_h9_stage19_multiscale.py`：18 项新增离线用例，包含二进制系数等价、区间位置、阶数教学合成多项式、历史四点 SHA 绑定（模拟材料明示为 fixture）、篡改拒绝、无覆盖的取证保存、低内存安全阻断。**没有使用合成数据冒充真实 Cherchi 数据。**

## 已真实执行的云端测试与限制

- M19 新增：**18/18 PASS**。
- 与 W3 第 11、14、17 阶段原有测试合并：**43/43 PASS，3.644 秒，0 skip**，其中使用原始真实历史 H8f ZIP 的 sample59 存档检查。ZIP SHA256 精确匹配。
- 首次阶段11回归用过时离线探针镜像导致 1 项失败；恢复到 GitHub 探针 blob `083ea0075d9df7d71f97e77591a18f5453691665` 后，已重跑 PASS；首次 M19 合成三次曲线测试因为使用超出实验上限的 `c7` 尺度报错，改为 `1e-6` 后完整通过。没有隐瞒旧失败。
- 真实云端调用 `--phase run` 被资源/checkout 预检以 **exit 2** 阻断，未执行 Cherchi：M19 **新原生采样 0/2**，独立新两点审计 0/2，Newton `false`。当前没有 M19 真实导数误差下降倍数，不能宣称二阶收敛。
- 原始 M18 用户本地审计与四份材料**未上传到此云端**；M19 的完整基线文件 SHA 和两点原生结果需要用户在本机复核，不能把此次合成单元测试写成原生验收。

## Ubuntu 60GiB 工作站可执行命令

**前提：** `git pull --ff-only` 更新到此 M19 提交，`git status` 无跟踪文件修改，Swap=0；Python 3.13 虚拟环境和原有固定 Cherchi/GMP/CGAL 模块保留，使用系统 `libstdc++.so.6` 动态库。

```bash
cd /data/xvxinyao1/Spin_test-W3
export H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
export W3_PY="$HOME/.venvs/spin-w3-313/bin/python"
export W3_STDCXX="$(readlink -f /usr/lib/x86_64-linux-gnu/libstdc++.so.6)"
export ARTIFACT="$HOME/Research/W3_H9_Evidence/h8f-original-12135528290.zip"
export CERT="$PWD/$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json"
export M18_AUDIT="$HOME/Research/W3_H9_Results/stage18-audit-20261102_170733/independent-audit.json"
export OLD_NATIVE="$HOME/Research/W3_H9_Results/20261026_172959-2185128/native-4side-s17/serial-native/native"
export M19_RUN="$HOME/Research/W3_H9_Results/m19-multiscale-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$M19_RUN"
sha256sum "$M18_AUDIT" "$ARTIFACT"

# 1. predeclared two-point plan; does not execute native
"$W3_PY" "$H9/source/h9_stage19_multiscale.py" \
  --artifact "$ARTIFACT" --certificate "$CERT" \
  --stage18-audit "$M18_AUDIT" --stage17-native-dir "$OLD_NATIVE" \
  --output "$M19_RUN/midpoint-plan.json"

# 2. independent tests, no Native Boolean; must not skip actual original sample59 checks in old tests
H9_EVIDENCE_ZIP="$ARTIFACT" "$W3_PY" -m unittest discover -s "$H9/tests" \
  -p 'test_h9_stage19_multiscale.py' -v

# 3. pinned build evidence for *this* Git HEAD. Cached C++ outputs can be reused.
# If your Python is based on Anaconda, avoid Conda library search:
env -u CONDA_PREFIX -u LD_LIBRARY_PATH -u LIBRARY_PATH -u CMAKE_PREFIX_PATH \
  -u PYTHONPATH -u PYTHONHOME -u BOOST_ROOT -u Boost_ROOT -u Boost_DIR \
  -u PKG_CONFIG_PATH \
  PATH="$HOME/.venvs/spin-w3-313/bin:/usr/local/bin:/usr/bin:/bin" \
  "$W3_PY" -u "$H9/source/prepare_h9_pinned_native.py" \
  --phase build --repo "$PWD" --output "$M19_RUN/build"

# 4. actual two new native midpoints + independent exact re-integration.
# Preserve exit code and logs; DO NOT overwrite Stage17 native outputs.
env -u CONDA_PREFIX -u LD_LIBRARY_PATH -u LIBRARY_PATH -u CMAKE_PREFIX_PATH \
  -u PYTHONPATH -u PYTHONHOME -u BOOST_ROOT -u Boost_ROOT -u Boost_DIR \
  -u PKG_CONFIG_PATH LD_PRELOAD="$W3_STDCXX" \
  PATH="$HOME/.venvs/spin-w3-313/bin:/usr/local/bin:/usr/bin:/bin" \
  "$W3_PY" -u "$H9/source/h9_stage19_native_midpoints.py" \
  --phase run --repo "$PWD" --artifact "$ARTIFACT" --certificate "$CERT" \
  --stage18-audit "$M18_AUDIT" --stage17-native-dir "$OLD_NATIVE" \
  --plan "$M19_RUN/midpoint-plan.json" \
  --build-evidence "$M19_RUN/build/build_evidence.json" \
  --output "$M19_RUN/native-two-midpoints"
```

M19 成功状态：`native-two-midpoints/launch_result.json` 的 `status=TWO_NEW_NATIVE_MIDPOINTS_INDEPENDENTLY_VERIFIED_NO_NEWTON`，并生成 `independent-refinement.json` 的左右全间隔、两个半间隔误差和实测倍率。若失败，查看 `worker.stderr.txt` / `two-midpoint-native/failure.json` / `audit.stderr.txt` 并保留 `*.unverified.json.gz`；**不要将失败的 2 点材料计为正式通过**。

## 科学结论边界与后续

已证明：原来的四个有限点可被独立审计（根据用户实际本地结果）；本次新增了多尺度的严格可执行采样/验收入口。尚未证明：在任意连续系数邻域内拓扑不变、所有 10 个系数方向可微、跨事件的 Newton 安全步、最终 Heart 优化 OBJ、收敛残差或物理模拟。

M20 需要根据实际 M19 二分点结果决定是否继续缩步长及设计连续分支的认证路径。即使观测两尺度近似二阶规律，也不能把有限点事实升级为连续性定理。
