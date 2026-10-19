# W3 Heart H9｜第五阶段：真值材料重积分与新原生构造准入加固（2026-10-19）

**唯一修改分支：** `research/neuralmoments-w3-heart-h9-20261019`，继承上一阶段 `fc08c229ecf966f9a4453414dbb54095d22cc118`。冻结 H8f 源祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。

## 严格结论

**本次没有四个新的原生 Cherchi Boolean 成功求值，不能宣称 Heart Newton 通过、连续可微邻域成立或获得最终模型。** 历史 GitHub Actions [run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 仍是 `failure`（不是新 W3 CI）。原始 [artifact 12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290) ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9` 未改动。历史 81/81 Cherchi 实际调用、30/30 FD numerics 的事实与唯一 sample 60 构造异常同时成立，不能将前者替代后者。

## 本次实际完成的独立数学工作

新增 `source/reintegrate_h9_true_moments.py`：不信任已保存的输出浮点十矩，而是读取原始 H8f gz 材料，严格解析 Cherchi 十进制及 0b 二进制有理数，用 **Python Fraction** 独立重做每个有向三角形的原点四面体积分，求体积、一阶矩和六个二阶矩；另外独立复核每条无向边恰有一条正向与一条反向面链。严禁用网格代用品或近似求积。该审计不包含 CGAL 全局自交证明；历史单点原生边界审计仍仅依赖 H8f 的事实。

| 原始样本 | c7 扰动 | faces | 独立检查边数 | 重新积分体积 | 与归档 native 10 raw moments 的最大 scaled error |
|---|---:|---:|---:|---:|---:|
| 59 | +1.5e-6 | 16910 | 25365 | 0.4638104339398362 | 0.0（double 展示一致） |
| 60 | +3e-6 | 16910 | 25365 | 0.4638104342688899 | 0.0（double 展示一致） |

sample 59→60 的真实历史十矩割线与基点解析 Jacobian 第 7 列的最大缩放偏差 `1.4456094976282303e-05`。它是有限点差分误差，不足以判断分支连续或 Newton 安全。保存 `reports/H9_HISTORICAL_EXACT_REINTEGRATION.json`，其中包括每个原始样本 gzip SHA、积分量、重新计算耗时及每个矩向量，不覆盖原始证据。

## 为未来四个新原生快照新加的独立验收门槛

新增 `source/audit_h9_new_native_sides.py`：

1. 重新读取完整历史 artifact，并重新运行第四阶段的条件代理证书；拒绝仅凭篡改的报告、已过期的 JSON 或宣称完成四次调用的空 manifest。
2. 对四份 **必须真实存在** 的 `side-??-*.json.gz` 材料逐一按 SHA256 对照 side JSON，检查 pinned Cherchi 后端、同调用证明、q[7] 根两侧计划、另九维原样、`quadric_source_faces` 与归档一致、native exact audit pass、真实 `subtraction` 操作、GMP 算术模块哈希及导数 map 身份。
3. 对**每份新材料**重新独立计算 Fraction 10 矩和有向边链，校验保存的 native raw moments；精确重算原生源边和设计域边的有理事件符号与内点参数，重新用既有 H7 精确语义分类器比较历史 59、60（绝不直接信任侧快照写入的 LPI/TPI 状态）。记录不同构建的二进制 SHA 差异，要求单独解释，不能冒充历史精确可重放。
4. 就算四点全部合法，也只报告**有限采样**和“同构造支撑分离”的诊断；不自动放行连续光滑邻域、Newton 接受或最终 OBJ。真实持续构造支持证明、实际算法接受状态仍需后续工作。

新增 `source/run_h9_native_serial.py`：不修改 `.github/workflows` 或其他 W 分支。它在完整 W3 checkout 上要求冻结祖先、原生 Python 扩展齐全、宿主/容器可用内存满足单作业安全阈值和 swap=0；将进程虚拟内存上限设置为 24 GiB，`OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`，四次原生调用顺序执行，总预算 ≤60min（原生 3100s、独立审计 ≤360s）。整个任务仍禁止 GPU 训练和 Newton 自动启动。

## 实际执行记录及限制

- 基于实际 ZIP 的新 stage5 13/13 测试通过，含原始两样本重积分、真 `subtraction` 操作、源面/算术身份篡改拒绝、空 manifest 伪装四次调用拒绝、以及内存/swap/非 W3 分支保护。
- 把上一阶段 11 项一同回归，**24/24 PASS，30.309s**；日志在 `reports/H9_STAGE5_ALL_TESTS.log`。
- 本地 `run_h9_native_serial.py` **实际调用**，出口 `2`，记录 `reports/H9_STAGE5_PREFLIGHT_BLOCKED.json`：有效 cgroup 内存上限约 4 GiB（/proc/meminfo 物理 5.8GiB），本地不是 W3 Git 完整 checkout，且三个原生扩展缺失。未启动任何编译或 Boolean 求值。
- 本地 `audit_h9_new_native_sides.py` **实际调用**，无四份原生快照，出口 `1` 并生成 `reports/H9_STAGE5_NO_NATIVE_AUDIT.json`：`NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT`、`newton_admitted=false`。这份失败是正确、安全的拒绝，**不能当成验收通过**。
- 新的后处理器成功路径未在真实新 Cherchi 四点材料上执行；仅测试了数学积分及 fail-closed 分支。没有触发新的 GitHub CI；不能把本地测试写成远端 CI。

## 重放

在 `volcano-code/Spin_test` W3 checkout 根目录中使用：

```bash
export H9_EVIDENCE_ZIP=/path/to/heart-h8f-original-artifact.zip
export H9_CROSSING_CERTIFICATE=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json
H9_DIR=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$H9_DIR/source/reintegrate_h9_true_moments.py" --artifact "$H9_EVIDENCE_ZIP" --output /tmp/h9-historical-exact-moments.json
H9_EVIDENCE_ZIP="$H9_EVIDENCE_ZIP" H9_CROSSING_CERTIFICATE="$H9_CROSSING_CERTIFICATE" \
  python -m unittest discover -v -s "$H9_DIR/tests" -p 'test_h9_stage5*.py'
# 仅当已经编译并注入真实原生扩展、具备 24GiB/swap0 对应资源的 W3 checkout：
python "$H9_DIR/source/run_h9_native_serial.py" --artifact "$H9_EVIDENCE_ZIP" \
  --certificate "$H9_CROSSING_CERTIFICATE" --output /tmp/h9-s5-native-one-shot
```

## 下一阶段必须拿到的证据

在符合资源协议的原生机器上，真实编译固定 Cherchi/GMP/CGAL 后执行四点原生 smoke，保留 CI 或终端日志、编译版本、4 个 SHA 一致的 gzip 材料和相应新 Jacobian；再运行 `audit_h9_new_native_sides.py` 生成四点独立积分及 H7 语义比对。若二进制 SHA 与 H8f 不同，应额外重跑真实基点并做跨构建等价证明；而且**即使四点有限一致，也不等于在邻域上证明可微**。未满足连续准入证明和真实接受状态时仍然 `DENY_NEWTON`。
