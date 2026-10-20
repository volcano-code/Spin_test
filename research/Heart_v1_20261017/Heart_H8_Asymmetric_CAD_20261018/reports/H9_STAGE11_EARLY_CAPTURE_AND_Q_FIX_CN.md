# Heart H9 W3｜第十一阶段：真实 Cherchi 同调用材料提前持久化与完整 q 修复

**仅允许写入** `research/neuralmoments-w3-heart-h9-20261019`；冻结祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。历史 GitHub Actions [run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 仍为 **failure**，artifact 12135528290 ZIP SHA256 为 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。H8f 的 81/81 实际调用和 30/30 数值差分检查通过，不等价于 sample 60 构造分支门禁通过。

## 本轮修复

**1. 原生生产端未保存完整 `q` 的真实验收错误。** 旧 `probe_h9_crossing_sides_live.py` 的 side 元数据保存了 `c7`，但 `audit_h9_new_native_sides.py` 必须对完整 10 维 `q` 调用 `check_vec(meta.get('q'), q, 10, ...)`。即使四个原生 Boolean 点计算成功，旧侧写入的数据也无法通过独立验收。现将完整 `q.tolist()` 与 `newton_admitted=false`、`actual_accepted_step=false` 一起保存，并由独立验收再次核对所有系数。

**2. 真正 Cherchi 同调用数据保存太晚。** 旧生产流程在几何严格审计、Fraction 十质量矩积分和 H7 精确构造身份分析之后才首次保存同调用 `material`。只要后续审计失败或超时，已产生的真实 Cherchi 几何可能丢失。新模块 `source/h9_same_call_capture.py` 在 `engine.validate_same_call_material(...)` 后立即输出原子保存的 `unverified-XX-*.json.gz` 和 manifest，记录压缩字节 SHA256、未压缩 JSON SHA256、后端和完整 `q`。该状态**不可被视为验证通过、不可计入新原生完成样本、也不会放行 Newton**。只有经过 native 有理边界、独立 Fraction 积分和精确符号身份验证后，才将**同一份压缩字节**提升为 `side-XX-*.json.gz`，并写入完整 side JSON；校验失败仍保留未认证材料，供调查 sample 60。

## 实际验证

- 使用**原始 H8f artifact 中 sample 59 的真实同调用材料**测试保存及失败留证，但**这不是新增 Cherchi 求值**。
- 第十一阶段新增 **8/8 PASS**，覆盖真实历史材料留存、故障注入、重复文件拒绝、错误后端或 q 拒绝、SHA 篡改、gzip 确定性与升级字节不变、以及审计前先保存的源码顺序。
- 带原始 ZIP 与第四阶段证书分批重跑：第四至八阶段 **65/65 PASS**，第九阶段 **9/9 PASS**，第十至十一阶段 **20/20 PASS**。累计 **94/94 PASS，跳过 0**。首次整批运行遇到两处旧版错误码/常量断言不一致（已同步为当前严格拒绝契约），第二次整批运行触发当前环境单命令超时；**均未计入最终通过**。
- 本地实际执行：`--phase inputs` 退出码 **0**，`--phase build` **2**，`--phase run` **2**；缺少四份新材料时独立审计 **1**（`NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT`）。原生 Cherchi 求值 **0/4**；内存 cgroup 上限 4 GiB、swap 0，无三个 Cherchi 原生扩展，也非完整 W3 checkout。**没有新的远端 CI**。

## 重放

```bash
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
export H9_EVIDENCE_ZIP=/path/to/original-h8f-12135528290.zip
export H9_CROSSING_CERTIFICATE="$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json"

python -m unittest discover -v -s "$H9/tests" -p 'test_h9_stage11_*.py'
python "$H9/source/prepare_h9_pinned_native.py" --phase inputs \
  --artifact "$H9_EVIDENCE_ZIP" --certificate "$H9_CROSSING_CERTIFICATE" --output /tmp/h9-w3-inputs
```

在满足至少 24 GiB 有效内存、swap0、Python3.13、固定 Cherchi/CGAL/GMP 及完整 W3 checkout 条件的机器上，再执行现有 `--phase build`、`--phase run`，验证真实四点材料完整性、独立十质量矩及左右单侧 Jacobian。

**终态：继续拒绝 Newton；没有新原生四点结果、Heart 最终 OBJ、Newton 收敛残差或重新积分的终态物理指标。**
