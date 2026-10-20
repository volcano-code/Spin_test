# W3 Heart H9｜第十二阶段：同调用材料的崩溃一致性及安全恢复

日期：2026-10-20。仓库 `volcano-code/Spin_test`；**唯一写入分支** `research/neuralmoments-w3-heart-h9-20261019`；冻结 H8f 祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。本次只修改 W3 独占目录下现有 H9 源码/测试与新增报告；不触及 `main`、其他研究分支、历史 CAD 或 `.github/workflows`。

## 一、真实执行状态

- 历史 [H8f Actions run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 的实际结论仍为 **failure**。原始 [artifact 12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290) ZIP 的 SHA256 实测是 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- 第十二阶段**没有取得任何新原生 Cherchi Boolean 样本（0/4）**，没有真实 Newton 接受状态、收敛残差、最终 Heart OBJ 或重新积分的最终物理指标。历史样本绝不作为新的原生采样冒充。`newton_admitted=false`。
- 本地 cgroup memory.max 只有 **4 GiB (4294967296 字节)**、swap=0；不具备规定的 24 GiB 原生作业条件，三个原生扩展 `_make_it_stand`、`_cherchi_core_boolean`、`_cherchi_rational_moments` 均缺失，容器也不是完整 W3 checkout；向 `github.com` 克隆依赖时报 DNS 错误。

## 二、本轮实际排查并修复的错误

第十一阶段已经在耗时的边界、Fraction 积分、LPI/TPI 语义审计之前保存 `unverified-XX-*.json.gz` 及 SHA manifest。然而 `promote_after_full_audit` 曾先使用 `os.replace(pending, final)` 移走唯一未认证 gzip，然后才原子写出 `side-XX-*.json`。如果第二步因为磁盘写入错误或进程崩溃失败，原始 forensic manifest 仍在，但其 gzip 已被移走，导致**单次真实 Cherchi 调用得到的取证材料不再构成完整可审计检查点**。

修改 `source/h9_same_call_capture.py`：

1. 首先验证同调用的 `q`、backend、存档 SHA、manifest、材料元数据以及 `native_geometry_valid=True`，拒绝篡改或与计划不一致的材料。
2. 采用同目录 `os.link(unverified, side)` **硬链接保留原始 gzip**，然后原子写出正式 JSON 元数据并同步目录元数据；这两个步骤失败时回滚未完成的正式输出，原始 `unverified` gzip 和 SHA manifest 保持不变。
3. 正式 gzip + JSON 均已存在且落盘后，才清理原始未认证副本；清理失败会被标记为 forensic 残留，不会清除正式验证对，也不会将其当作 Newton 证明。
4. 如果进程在硬链接创建后、正式元数据写入前中断，重试时**仅在遗留 gzip 与原始 gzip 是同一设备、同一 inode 的普通文件**时允许清理该孤儿硬链接并重新提交。字节相同但不同 inode 的外来文件或符号链接一律拒绝覆盖。
5. 本变更只提升取证材料的崩溃可恢复性；任何未认证存档都不能被独立材料验收器作为四个成功样本之一。

额外修正 `tests/test_h9_stage8_handoff_contract.py` 的两处已过期错误码断言：`HISTORICAL_H8F_SHA_CHANGED` 与 `MISSING_OR_OVERSIZED_EVIDENCE:run_status.json`。**生产验收逻辑未放宽。** 首轮 90 项测试中确实有这两项断言失败，原始日志完整留在 `H9_STAGE12_INITIAL_COMPAT_FAILURE.log`；修正后才重新运行并确认通过。

## 三、真实测试与故障注入

- **新增阶段 12：7/7 PASS**。覆盖正常升级、磁盘写入失败、目录同步失败、硬链接创建失败、真实独立 Python 子进程 `os._exit(83)` 崩溃、同 inode 恢复、外来孤儿禁止覆盖，以及**真实 H8f sample 59 同调用材料**的失败保全。
- **阶段 5–12 本地可重放相关回归：90/90 PASS，27.855 秒、无跳过项**（测试分布不包括另有独立文件的阶段 1–3）。原始历史材料只用于重放和负例测试；该计数不代表新原生 Boolean 成功。
- 本地测试日志：`reports/H9_STAGE12_ALL_TESTS.log`；阶段新代码和证据 JSON 中均包含具体 SHA。

真实入口试运行与退出码：

| 入口 | 实际退出码 | 结论 |
|---|---:|---|
| 冻结 ZIP + 条件证书 `--phase inputs` | **0** | 真实历史证据重放、四点计划验证通过，不进行新 Boolean |
| `--phase build` | **2** | 当前非完整 W3 checkout，内存不足，未启动 CMake |
| `--phase run` | **2** | 资源阻断，未启动原生作业 |
| 内层 `run_h9_native_serial.py` | **2** | 原生模块缺失/内存不足/缺失 W3 checkout |
| 独立审计无新材料 | **1** | `NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT`，按预期拒绝 |

## 四、可重放命令

从包含本文件的完整 W3 checkout 执行；原始 H8f artifact ZIP 必须逐字节与 GitHub 下载一致：

```bash
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
export H9_EVIDENCE_ZIP=/path/to/original-h8f-12135528290.zip
export H9_CROSSING_CERTIFICATE="$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json"
sha256sum "$H9_EVIDENCE_ZIP"
python -m unittest discover -v -s "$H9/tests" -p 'test_h9_stage12_forensic_commit.py'
python -m unittest discover -v -s "$H9/tests" -p 'test_h9_stage*.py'
python "$H9/source/prepare_h9_pinned_native.py" --phase inputs \
    --artifact "$H9_EVIDENCE_ZIP" --certificate "$H9_CROSSING_CERTIFICATE" \
    --output /tmp/h9-stage12-input-gate
```

## 五、下一阶段必须取得的真实结果

在 **至少 24 GiB 有效内存、swap=0、Python 3.13、固定 Cherchi/CGAL/GMP 依赖**的完整 W3 checkout 中，执行已提交的 `prepare_h9_pinned_native.py --phase build` 及 `--phase run`；取得四份真实 `side-XX.json.gz` 与元数据后，进行独立十质量矩、严格有理边界和左右单侧 Jacobian 验收。所有计算保持串行原生作业、编译并发≤4、单次≤60分钟。只有实际原生验收和 Newton 的独立严格准入同时成立时，才讨论真实 Heart 优化；当前仍然 **拒绝 Newton**。
