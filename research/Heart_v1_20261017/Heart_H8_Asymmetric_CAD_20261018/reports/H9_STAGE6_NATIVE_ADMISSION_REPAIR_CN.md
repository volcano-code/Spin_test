# Heart H9 · W3 第六阶段：真实材料验收修复与左右单侧 Jacobian 诊断

- 唯一目标仓库/分支：`volcano-code/Spin_test` / `research/neuralmoments-w3-heart-h9-20261019`
- 起始分支 HEAD：`0918529a1b6097a44434fe515b027e699dc830e6`
- 冻结祖先：`0bcc187b3005478baa586a6d6f450e73811ca342`
- 历史 GitHub Actions run [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 结论：**failure**（保留）；原始 artifact 12135528290 ZIP SHA256：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- **研究状态：拒绝 Newton（DENY_NEWTON）；没有新的 Cherchi 生产 Boolean 成功样本、真实收敛残差、最终 Heart OBJ 或终态独立物理指标。**

## 已实际修复的缺陷

此前第五阶段源码 `source/audit_h9_new_native_sides.py` 的四点真实材料验收分支存在未定义变量 `native_saved`（可在父提交 `0918529a` 的 `moment_audit=check_mass_snapshot(material,point_saved,native_saved)` 找到）。旧版 24 项测试主要覆盖“失败时拒绝”和旧材料计算，未穿透四个新快照成功情况下的数值复核分支。该缺陷会使未来成功获取四点原生结果时在独立重积分处异常终止。

第六阶段新增 `validate_new_same_call_numerics(material, meta)` 并接入真正的 `audit` 主路径：

1. 对保存的十质量矩以及同调用 `material['variable_raw_moments']` 强制检查 10 个有限数；交叉比对二者的缩放差异以及保存的 `independent_scaled_moment_error`，先拒绝篡改材料，不做无意义的大规模 Fraction 积分。
2. 检查 **全部 100 个**生产 `moment_jacobian` 值有限，而不是像旧代码只验证第七列；对第七列与单点 JSON 保存的同调用列做数值一致性检查。
3. 对通过上述前置条件的材料调用原 `check_mass_snapshot`，独立计算有向闭合边链、全部面片的精确有理十质量矩，与记录的两个浮点矩向量逐分量比对，并验证结果与保存的误差指标一致。
4. 使用**原始 H8f sample 59 的真实材料**执行本函数的完整成功路径，得到 16,910 个三角面、25,365 条严格相反定向的流形边、十质量矩重算误差 0.0。这只是原有材料的复算测试，**不是一次新原生求值**。

## 新增分支内单侧数值诊断

新增 `source/h9_one_sided_derivative_audit.py`，并在主验收器拿到 4 个完整、重新积分的原生材料后调用。它对 `left-coarse → left-near` 和 `right-near → right-coarse` **分别**作十质量矩割线，和各自两个同调用 Jacobian 第 7 列核对，记录最大缩放误差及同侧两点的精确构造身份是否一致。严禁使用横跨事件根的割线代替同侧导数；纯数值吻合仍不认证连续光滑邻域或 Newton 接受。

测试数据中独立生成的线性 `m(q[7])` 只是单元测试算术样例，与真正的 Cherchi Boolean 没有关联；正式 `audit` 函数仍需要 4 份带 SHA 的全材料、固定 q 计划、原生构造、严格边界和 H7 语义重放才会产生诊断报告。对于跨构建二进制 SHA 不一致的情况，新增 `cross_build_same_semantic_baseline_admitted` 只会为 false，保留对比记录供后续单独验证，不会把不同构建的有限点误当作冻结 H8f 同一可微分支。

## 本地真实执行记录

- 本轮增补的 `tests/test_h9_stage6_native_success_contract.py`：**12/12 PASS**（真实旧归档成功路径 1 项、变造旧归档负例 4 项、单侧数学与安全负例 7 项）。
- 与上一阶段所有 H9 11+13 项联合：**36/36 PASS**，`Ran 36 tests in 34.020s`，详见 `reports/H9_STAGE6_ALL_TESTS.log`。
- 在当前容器**实际运行** `run_h9_native_serial.py`：退出码 **2**。`reports/H9_STAGE6_NATIVE_PREFLIGHT.json` 明确记录本环境有效内存上限不足、不是拥有冻结祖先的 W3 完整 Git checkout、三个真正原生扩展缺失。**0 次新原生调用**，没有谎称构建/Boolean 运行。
- 在没有四份新原生材料的目录中**实际运行**独立验收器：退出码 **1**，`NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT`，机器可读拒绝见 `reports/H9_STAGE6_EXPECTED_NO_NATIVE.json`，其 `newton_admitted=false`。
- 原有 H8f 81 点历史数值差分虽为 30/30，通过不等于历史 CI 和 H9 准入成功；历史 sample 60 的有理边界构造分支异常仍然有效。
- 本阶段新增证据只来自本地测试与独立旧归档复算：没有本分支新 CI 结果。

## 重放命令（仅在 W3 checkout；无需原生扩展的测试）

```bash
export H9_EVIDENCE_ZIP=/path/to/heart-h8f-artifact-12135528290.zip
export H9_CROSSING_CERTIFICATE=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json
python -m unittest discover -v \
  -s research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/tests \
  -p 'test_h9_stage6*.py'
```

在原生模块齐全且满足 `24 GiB / swap0 / 串行≤60分钟 / 编译最多4并发` 的机器上，先按先前保留的 W3 原生入口 `source/run_h9_native_serial.py` 运行四点采样，再执行本版 `source/audit_h9_new_native_sides.py`。即便四点全部重新积分通过，本阶段依旧不启动 Newton，必须另获**生产构造连续准入/真实优化接受状态**的审查证据。
