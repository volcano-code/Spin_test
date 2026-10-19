# W3 Heart H9｜第七阶段：固定依赖原生构建与四点材料验证交接

日期：2026-10-19。唯一允许推送的分支为 `research/neuralmoments-w3-heart-h9-20261019`，冻结 H8f 祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。本阶段不修改 `main`、其他 W 分支、任何原始 H8f 历史报告、工作流或 CAD。

## 真实执行结论

**未成功运行任何新的原生 Cherchi Boolean；仍无 Heart 最终 OBJ、真实 Newton 接受状态、收敛残差或终态物理指标。** 原始 [H8f Actions run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 始终为 `failure`，原始 artifact 12135528290 SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。H8f 81/81 实际点与 30/30 数值差分通过，不能覆盖 sample 60 的真实 LPI 分支异常，也不能作为 Newton 准入。

本阶段重心是构建**可以移交给 ≥24 GiB 有效内存、swap=0 的隔离 W3 checkout 执行的原生引导工具**，而不是继续把离线代理分析冒充原生测试。

## 新增代码

- `source/prepare_h9_pinned_native.py`：提供 `--phase plan` / `build` / `run`。构建配方严格采自冻结 H8f 工作流 `.github/workflows/heart-h8f-81-point.yml`（Git blob `a6dda4d04998f1244ce0a7f80991d6198c037cdb`）：Cherchi 源码提交 `7bd6c2697695f555f9a15d7e154e084d841316f0`，CGAL 提交 `f7c3c8212b56c0d6dae63787efc99093f4383415`；保持 `SPIN_IT_FASTER=ON`、`EXACT_GEOMETRY_CHECKS=ON`、`FILTERED_BOUNDARY_KERNEL=ON`、`CHERCHI_RATIONAL_ARITHMETIC=ON`。显式编译并行 2（≤4），单次构建最长 3500s；原生执行复用现有 `run_h9_native_serial.py` 的独立 3600s 上限。
- 新构建产物**仅在 W3 本地** `build/h9-w3-core` 和 `build/h9-w3-cherchi`，不覆盖原历史 H8f 构建目录；仅修改生成的 `build.ninja` 中 Boost `.a` 链接参数为共享 `.so`，绝不移动、删除或使用 sudo 修改操作系统 Boost 静态库。
- 构建依赖受 Git commit 强固定，已经存在但不匹配的 Cherchi 或 CGAL checkout **直接拒绝覆盖**；先验证冻结祖先与当前分支、Python 3.13、内存/swap 和编译工具。
- 从已编译扩展导出三份 SHA256，确认真实 `_make_it_stand`、`_cherchi_core_boolean`、`_cherchi_rational_moments` 都从 **新 W3 构建目录**装入（不允许使用全局环境里的旧 `.so`）。构建成功才写 `build_evidence.json`。
- 运行阶段要求同时提供原始 H8f ZIP（校验原始 62 MiB 文件 SHA）、第四阶段独立事件证书、以及构建证据；三份编译二进制的 SHA 和 W3 HEAD 与构建记录重新比较。执行现有四点真实 Cherchi 和独立 Fraction 十质量矩审计后，即使成功也仅标记 **四点有限证据完成**，绝不批准连续邻域/Newton。
- `tests/test_h9_stage7_native_handoff.py`：10 个新单元测试，覆盖原始依赖及 CMake 配方锁定、内存/分支拒绝、Boost 局部改写、不可信旧全局模块拒绝、模块 SHA 漂移拒绝、构建证据篡改拒绝以及资源不够时不得执行任何 subprocess 构建。

## 实际运行结果与日志

Python 3.13.5，本环境真实 cgroup 内存上限 `4294967296` 字节（4 GiB），当前并非完整 Git checkout，原生扩展与 CGAL/Eigen 不存在，访问 `github.com` 的 DNS 失败。

- `--phase plan` → **exit 0**，输出 `reports/H9_STAGE7_BUILD_PLAN.json`，冻结依赖、CMake 参数、资源预检与命令计划完整生成；该操作不修改系统。
- `--phase build` → **exit 2**，写入 `reports/H9_STAGE7_BUILD_PREFLIGHT.json`：`NOT_FROZEN_W3_BRANCH_OR_ANCESTOR`、`LESS_THAN_24GIB_EFFECTIVE_MEMORY`、`NOT_A_COMPLETE_SOURCE_CHECKOUT`。**没有运行 apt、git clone 或编译。**
- `--phase run` → **exit 2**，写入 `reports/H9_STAGE7_LAUNCH_PREFLIGHT.json`：`BLOCKED_NO_NATIVE_EVALUATION`；未生成新四点材料。
- **新第七阶段 10/10 本地 unittest PASS**（不到 1s），原 H9 第五、六阶段 25/25 项相关测试在本轮较早的一次单独执行中确实 PASS（约 28.45s），但后来尝试进行的跨阶段大测试在重复昂贵的 Fraction 积分时**超时中断**，不作为完整成功。其部分输出记录在 `reports/H9_STAGE7_COMBINED_TIMEOUT.log`。
- GitHub Actions：本次尚未运行新的远端原生 CI；连接器不能派发 W3 原生 workflow，且 W3 独占规则禁止修改 `.github/workflows`。

## 下一次在 ≥24 GiB 主机直接执行的命令

进入实际 W3 完整仓库 checkout，检查源分支及 SHA（不能切到 `main`）：

```bash
cd /path/to/Spin_test
git branch --show-current
git merge-base --is-ancestor 0bcc187b3005478baa586a6d6f450e73811ca342 HEAD
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018

# 24 GiB 有效内存、swap=0；Python 3.13；已安装 Ubuntu 24.04 原生开发依赖。
python "$H9/source/prepare_h9_pinned_native.py" --phase plan > /tmp/h9-build-plan.json
python "$H9/source/prepare_h9_pinned_native.py" --phase build \
    --output /tmp/h9-w3-pinned-build

# 只能使用原始 GitHub Actions artifact ZIP（SHA256 必须完全一致），
# 不能使用重新打包、改名内容或 H8f 81 点数值报告代替。
sha256sum /path/to/original-h8f-12135528290.zip
python "$H9/source/prepare_h9_pinned_native.py" --phase run \
    --artifact /path/to/original-h8f-12135528290.zip \
    --certificate "$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json" \
    --build-evidence /tmp/h9-w3-pinned-build/build_evidence.json \
    --output /tmp/h9-w3-native-four-sides
```

**注意：** 上述 host build/run 未在本轮成功执行，源码配方不等于已完成 CGAL/Cherchi 原生编译。成功完成后也要读取 `/tmp/h9-w3-native-four-sides/serial-native/independent-audit.json`、原生四份 gzip、SHA、单侧 Jacobian 和 `launch_result.json`，严格保留 `newton_admitted=false`，直到另有连续准入证明与实际接受状态。
