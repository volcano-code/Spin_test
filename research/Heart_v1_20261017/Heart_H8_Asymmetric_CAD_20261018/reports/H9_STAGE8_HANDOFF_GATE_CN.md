# W3 Heart H9 第八阶段｜原生四点证据闭环与外层拒绝门禁

日期：2026-10-19。唯一写入分支：`research/neuralmoments-w3-heart-h9-20261019`。冻结 H8f 祖先：`0bcc187b3005478baa586a6d6f450e73811ca342`。

## 真实结论

原始 [H8f Actions run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 仍为 **failure**。artifact 12135528290 的原始 ZIP SHA256 已重新核对：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。81/81 历史点完成和 30/30 数值差分通过，不等于连续可微邻域，也不等于已执行 Heart Newton。

本阶段 **0/4 新 Cherchi 原生调用**。无终态 OBJ、收敛残差、可接受 Newton 步或终态物理指标，继续 `newton_admitted=false`。当前容器 cgroup 有效内存只有 4 GiB，缺少完整 W3 Git checkout 和三份原生扩展；原生构建预检退出码 2，原生运行预检退出码 2，无新材料时独立审计退出码 1。

## 实际修改与科学边界

- `source/verify_h9_live_handoff.py`：新增单独外层审计。子进程退出码 0 **本身不足以通过**；必须同时交叉验证原生 `report.json`、独立 `independent-audit.json`、`run_status.json`、两份执行日志、四对 side gzip/JSON 与各自 SHA256、gzip 完整性、c[7]、事件符号、三个 W3 编译模块哈希、有限左右 Jacobian 诊断。
- `source/prepare_h9_pinned_native.py`：原先只检查独立报告少数状态字段；现在调用上述审计器。任何缺文件、错误 gzip、SHA 漂移、跨构建等价性误称或执行标记不符，都写 `outer_handoff_error` 并以非零状态拒绝。
- `source/audit_h9_new_native_sides.py`：在读取 81 点 H8f 证据和开展昂贵精确有理积分前，先做证书语义、原生报告三份二进制 SHA 与四个真实 side 文件的廉价前置检查；保留旧第五阶段伪造证书/二进制的错误优先级。
- `tests/test_h9_stage8_handoff_contract.py`：新增 4 个已实际运行的拒绝测试；它们使用 synthetic/mocked 输入，只测试安全门禁，**不代表实际 Cherchi 原生结果**。

有限样本的结构一致性即使通过，也不是可微邻域证明；真实运行的来源尚无密码学远程证明；本阶段不执行或放行 Newton。

## 实际运行测试

在本地 Python 3.13.5 中：
- 现有 Stage5–7 已提交的相关测试：**35/35 PASS，15.032 秒，exit 0**（包括读取原始历史 H8f 真材料及 Fraction 重积分）。
- 此次新提交的 Stage8 门禁测试：**4/4 PASS，exit 0**。
- 更全面的本地 Stage8 扩展测试（含额外未单独提交的 15 个模拟负例测试）曾运行 **50/50 PASS，16.113 秒**；完整扩展源码及其日志另提供对话 ZIP，勿把 synthetic 成功类测试冒充 4 次新原生求值。
- build phase **exit 2**，run phase **exit 2**，没有四份新材料时独立 audit **exit 1**；记录的冻结 run 失败未覆盖。

## 合格主机的复现入口

在 ≥24 GiB 有效内存、swap 0、Python 3.13、固定 Cherchi/CGAL/GMP 构建依赖的完整 W3 checkout 中：

```bash
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$H9/source/prepare_h9_pinned_native.py" --phase build --output /tmp/h9-w3-build
python "$H9/source/prepare_h9_pinned_native.py" --phase run \
  --artifact /path/to/original-artifact-12135528290.zip \
  --certificate "$H9/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json" \
  --build-evidence /tmp/h9-w3-build/build_evidence.json \
  --output /tmp/h9-w3-four-new-points
```

串行执行，编译最多 4 并发、单次原生求值最长 60 分钟。只有新四点完整材料及独立审计通过，才进一步讨论 Cherchi 事件与连续分支；绝不以旧数值差分或代理模型代替真实 Newton 接受记录。W3 工作范围外的 CI workflow、main 和其他 W 分支未被更改。