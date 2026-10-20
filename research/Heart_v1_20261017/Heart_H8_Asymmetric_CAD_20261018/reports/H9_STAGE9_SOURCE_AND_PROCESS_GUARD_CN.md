# Heart H9 W3｜第九阶段：W3 源码身份锁定、原生子进程超时隔离与构建交接

日期：2026-10-20。**唯一写入分支** `research/neuralmoments-w3-heart-h9-20261019`；本阶段起始 HEAD `63f7dc490313013bc821eed32d30b848a7289c99`。冻结 H8f 祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。

## 为什么必须修复

此前 `prepare_h9_pinned_native.py` 仅检查 Git HEAD 与冻结祖先，而非实际工作树字节。对同一 HEAD 修改 `src/*.cpp` 或新增 Python import 模块后，构建与运行仍可能声称“冻结源码”。此外旧 `subprocess.run(timeout=...)` 只约束直接子进程；被 CMake/Ninja 启动的孙进程可能在超时后残留，外层启动器使用 `MAX_SECONDS+30` 还可能超出 60 分钟协议。这两项都是**原生执行正确性/证据身份缺口**，不只是离线代理分析。

## 实际代码修改

1. `source/prepare_h9_pinned_native.py`：新增 `source_contract()`，通过真正的 `git status --porcelain` 禁止未提交的 tracked 修改，通过 `git ls-files --others --exclude-standard` 拒绝 `python/ src/ bindings/ research/ .github/` 的未跟踪代码文件；对 H8f 工作流实际本地文件运行 `git hash-object`，要求 Git blob 等于 `a6dda4d04998f1244ce0a7f80991d6198c037cdb`；阻断 checkout 根路径/HEAD 不符。在 build 前后及 run 前后记录/复核源码合同；旧版没有这份合同的编译证明不得直接复用。
2. `source/h9_process_isolation.py`：新增无 shell 的 Linux process group wrapper。每次启动 `start_new_session=True`；无论正常返回、失败、超时，均对子进程组 `SIGKILL` 清理并 `wait` 回收，避免孤儿 CMake/Ninja worker 持续占用原生资源。
3. `source/run_h9_native_serial.py`：真实原生求值和独立复算均通过上述进程组执行器，并保留子进程原先 RLIMIT_AS=24 GiB。
4. `prepare_h9_pinned_native.py` 外层运行总时限由之前 `3600+30` 改为根据 `time.monotonic()` 实际剩余秒数，严格不超过 3600 秒；即使进程返回成功，源码在运行期间变更也会拒绝记录四点验收成功。
5. 更新第七、八阶段三个原回归测试文件以适配严格的源码合同和进程组入口，并新增第九阶段专门测试 `tests/test_h9_stage9_native_source_and_process_guard.py`。

**注意：** 冻结 H8f workflow 正确 blob SHA = `a6dda4d04998f1244ce0a7f80991d6198c037cdb`；本阶段代码中的 `H8F_WORKFLOW_BLOB_SHA` 和实际验证均使用此值，绝不使用其他值。测试用的临时 Git repo 会将测试常量替换为其真实 `git hash-object` 结果，并明确不代表上游构建。

## 实际本地回归（历史材料参与）

- 真实原始 H8f artifact ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`，历史 run #39123384402 的结论仍为 `failure`。历史 81/81 原生点和 30/30 数值 FD 不代表连续可微邻域。
- 带 `H9_EVIDENCE_ZIP` 与 `H9_CROSSING_CERTIFICATE` 重新执行第 5–9 阶段全部相关 `unittest`：**63/63 PASS，16.939 秒，没有跳过或失败**，包含真实历史材料的 Fraction 重新积分，不包含任何新 Boolean 求值。
- 新增的 9 项源码/进程测试：使用新建临时 Git 仓库实际验证 tracked 源码篡改、未跟踪 importable 源码、H8f 工作流漂移，验证父进程超时/正常退出均能清理真实孙进程，验证外层返回成功但源码变更时必须拒绝。
- `--phase plan` exit 0；`--phase build` exit 2；`--phase run` exit 2；内层 `run_h9_native_serial.py` exit 2；预检拒绝原因主要是当前沙箱不是完整 W3 Git checkout，cgroup 有效内存仅 4 GiB，缺少原生模块。**没有运行新 Cherchi Boolean、没有新四份材料、没有 Newton 或终态 OBJ**。

## 复现命令

```bash
cd /path/to/Spin_test   # W3 的完整 checkout，非 main
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
export H9_EVIDENCE_ZIP=/path/to/real-artifact-12135528290.zip
export H9_CROSSING_CERTIFICATE="$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json"
python -m unittest discover -v -s "$H9/tests" -p 'test_h9_stage[56789]*.py'
python "$H9/source/prepare_h9_pinned_native.py" --phase plan
# 以下仅限 ≥24 GiB 有效内存、swap=0、Python3.13 和固定依赖的隔离 W3 主机：
python "$H9/source/prepare_h9_pinned_native.py" --phase build --output /tmp/h9-w3-build
python "$H9/source/prepare_h9_pinned_native.py" --phase run --artifact "$H9_EVIDENCE_ZIP" --certificate "$H9_CROSSING_CERTIFICATE" --build-evidence /tmp/h9-w3-build/build_evidence.json --output /tmp/h9-w3-four-native
```

当前 GitHub 连接器没有启动 W3 Actions workflow 的写操作，且独占约束禁止修改 `.github/workflows`；**新远端 CI 尚未触发**。本阶段重点是让下次在合格主机上运行时得到干净、身份可追溯且不会留下孤儿编译作业的真实四点结果，而不是继续声明原生求解已完成。

## 下一关键验收

在合格原生 W3 机器上构建 Cherchi/GMP/CGAL，运行真实四点 q[7]，保留 `.json.gz`、源/二进制 SHA、实际边界审计、独立十质量矩重积分和左右侧 Jacobian，然后在未经连续分支/真实接受状态认证前持续拒绝 Newton。**当前无最终 Heart OBJ、收敛残差和物理终态**。
