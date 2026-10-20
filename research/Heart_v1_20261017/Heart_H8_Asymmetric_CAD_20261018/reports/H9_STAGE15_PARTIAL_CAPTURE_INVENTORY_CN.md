# W3 Heart H9｜第十五阶段：原生失败后的取证清点（2026-10-20）

**唯一写入分支**：`research/neuralmoments-w3-heart-h9-20261019`，冻结祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。本阶段**没有新 Cherchi Boolean 真实成功调用**，没有最终 Heart OBJ、收敛残差、物理终态或 Newton 接受状态。历史 [H8f run #39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 继续是 `failure`；禁止把历史 H8f 81/81 原生点和数值差分 30/30 视为 W3 的四次新原生调用。

## 当前原生环境为何阻断

本地真实读取 `/sys/fs/cgroup/memory.max=4294967296`（**4 GiB**），`_make_it_stand`、`_cherchi_core_boolean` 和 `_cherchi_rational_moments` 均未安装。`git ls-remote https://github.com/volcano-code/Spin_test.git HEAD` 返回 `Could not resolve host: github.com`。当前容器不是完整 W3 checkout；依照 **24 GiB 有效内存、swap0、单次原生作业 ≤60min、编译 ≤4 并发** 的协议，没有绕开预检编译。

真实 CLI：冻结输入 exit **0**，单独取证清点 exit **0**（`NO_NATIVE_SIDE_DIRECTORY`），原生 build exit **2**，外层 launch exit **2**，内层 serial native exit **2**；当前真实新原生求值为 **0/4**。

## 第十五阶段新增代码与实际意义

1. **`source/h9_capture_inventory.py`**：纯 Python、只读的独立失败证据清点器。先验证原始 H8f ZIP SHA 与第四阶段精确事件证书，重新生成四个预定 `q[7]` 并绑定各个新材料的 **完整十维 q**，之后仅扫描 `unverified-XX` 和 `side-XX` 的 gzip/元数据。精确比较 gzip/JSON SHA、backend、schema、系数、状态、index、side；拒绝 symlink、损坏 gzip、重复 JSON 键、跨系数调包。识别缺失、部分取证文件、完整未认证快照、完整正式文件对；任何完整文件对仅意味着**结构完整，非原生运行来源的加密认证**。
2. **`source/run_h9_native_serial.py`**：真实原生 probe 非零退出时自动产生 `forensic-inventory.json`，并将状态写入 `run_status.json`；哪怕取证清点再失败，**原始 probe 退出码仍然保留**，且 `newton_admitted=false`、`new_native_calls_verified=0`。没有引入任何假的 Boolean 后端、自动升格和 Newtown 启动。
3. **`tests/test_h9_stage15_forensic_inventory.py`**：九项新测试，明确用合成的存储夹具检验成功结构；另外一项读入**真实历史 sample59 Cherchi 材料**，尝试伪装成新 q[7] 候选时必须拒绝。

## 真实测试与结果

- 新阶段 9/9 PASS（13.69s，保留 `STAGE15_FINAL_TESTS.log`）。
- 第 11–15 阶段材料相关 41 tests + 4 unittest subtests PASS（21.12s，保留 `STAGE11_TO_15_REGRESSION.log`）。
- 第 5/7/9/10 阶段运行入口 35 tests PASS（13.59s，保留 `STAGE5_7_9_10_RUNNER_COMPATIBILITY.log`）。
- 另外一次**合并长回归在达到 100% 测试进度后，整体命令超时，未报告 PASS**；该次未计入上面的已完成测试，保留 `STAGE15_FINAL_COMBINED_TESTS.log`。以上两组已完整通过的交叉回归计数为 **76 tests**（其中 9 项新测试包含在 41 项中），不宣称这次长回归正式通过。
- 原始冻结 H8f ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。条件解析根证书是旧的**离线代理模型**结果，不是生产 Cherchi 连续拓扑证明。

## 实际运行与可复现命令

```bash
export H9_EVIDENCE_ZIP=/path/to/original-12135528290.zip
export H9_CROSSING_CERTIFICATE=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$H9/source/h9_capture_inventory.py" \
  --artifact "$H9_EVIDENCE_ZIP" --certificate "$H9_CROSSING_CERTIFICATE" \
  --native-dir /path/to/failed-serial-native/native \
  --output /new/path/forensic-inventory.json
python -m pytest -q "$H9/tests/test_h9_stage15_forensic_inventory.py"
```

在真实具备 24 GiB 和已构建固定 Cherchi/GMP/CGAL 的独立 W3 checkout 上，照第七至十四阶段提交的 build/run 脚本继续执行 4 个 side。若中途中断，保存所有 `unverified-*` 原始字节和本报告清单；**只有原生求值日志、四个独立精确积分和单侧 Jacobian 等完整通过后，才能声称四个有限新样本完成**。哪怕通过也不是连续光滑邻域的证明，Newton 准入依然需要后续独立科学验收。
