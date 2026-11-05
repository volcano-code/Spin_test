# P22：8 GiB 原生 M6 容量探针与 Cherchi 有理数接口故障

## 本轮结论

P22 是明确标记为 `TEST_ONLY` 的容量探针，不是正式 M6 准入或科学发布。它在 8 GiB 容器内成功完成真实 Cherchi factory 准备、六项 pins 核对，并实际进入固定 W0 的 `audit_native_full_partition_once`。审计随后因精确有理数 token 的跨接口格式不兼容而失败；不是 OOM。

本轮没有完成正式 M6，也没有得到完整材料分区证书、完整 10×10 Jacobian 复核或训练/优化准入。

## 实际资源与阶段记录

P22 原始证据包 SHA-256：

```text
3998ffa490c0057d31130d091e9de84974a3a1b45cdcffb50c5a3a30a335eb53
```

从原始 `result.json` 复核：

| 指标 | 实际值 |
|---|---:|
| cgroup memory.max | 8,589,934,592 bytes（8 GiB） |
| cgroup memory.peak | 570,761,216 bytes（544.32 MiB） |
| 进程 max RSS | 425,768 KiB（415.79 MiB） |
| OOM / OOM kill | 0 / 0 |
| genuine factory + six pins | 通过，46.7116 s |
| 总耗时 | 47.2936 s |
| W0 M6 audit | 已调用，后续接口异常 |
| formal M6 / scientific release | false / false |

`result.json` 的状态为 `TEST_ONLY_FAILED`，`formal_M6_executed=false`、`formal_M6_passed=false`。探针在异常路径没有写入 evaluator call counters，因此本报告不声称已保存可审计的 source/Boolean 精确调用计数。Traceback 证明执行已越过 genuine factory 并进入 W0 M6 audit。

## 精确失败位置

W0 固定版本：

`51cbfd33d08063404d7e0c40e4256dd0e38efa1a`

异常：

```text
ValueError: rational coordinate must be numerator/positive-denominator text
```

调用链：

```text
full_partition_m6.audit_native_full_partition_once
  -> native_m5_bridge.audit_native_w0_w2_once
  -> native_teacher_replay.audit_live_native_once
  -> evaluator(c)
  -> same-call material replay and audit
  -> MeshSnapshot.from_rationals(proof['exact_vertices'], ...)
  -> spin_problem._canonical_rational_vertices
  -> decimal-only token validation rejects the Cherchi token
```

固定 Cherchi C++ binding 的 `exactRationalString()` 对非零有理数输出 `0b<binary numerator>/0b<binary denominator>`，零输出 `0/1`。W0 `native_teacher_replay.py` 的 `RATIONAL` 正则和 `frac()` 已支持这种二进制 token；但 `MeshSnapshot.from_rationals()` 的公共输入合同只接受规范十进制 `numerator/positive-denominator`。

因此这是**精确序列化格式交界不一致**，不是数值误差。不能用浮点转换或放宽几何容差解决。

另一个需要同步修复的 W0 使用点位于 `full_partition_m6.py`：它之后也会将 `saved['material_proof']['exact_vertices']` 直接传给 `MeshSnapshot.from_rationals`。两处应使用同一个精确规范化辅助函数。互补材料路径使用的 `variable_rational_vertices` 已是十进制文本，不应被不必要地改变。

## W0 修复交接

已创建 W0 issue：

[Issue #4 — Normalize Cherchi binary rational tokens before MeshSnapshot boundary](https://github.com/volcano-code/Spin_test/issues/4)

建议由 W0 在其独占目录 `research/NeuralMoments/contracts/` 修复：

1. 复用现有 `frac()` 将 Cherchi 二进制 token 精确解析为 `Fraction`。
2. 使用 `make_it_stand.verification.rational_text.fraction_to_rational_text` 转成规范十进制文本；不经过 float。
3. 在 `native_teacher_replay.py` 与 `full_partition_m6.py` 两个 retained-boundary 调用点应用相同 helper。
4. 增加二进制正/负/零、大整数、非法 token、分母和 MeshSnapshot 显示坐标一致性测试。
5. 保留 `MeshSnapshot.from_rationals` 的严格规范十进制公共合同、原 Cherchi 源、P19 M/F/D 字节及正式资源政策。

W4 不修改 W0 分支，也不通过 monkeypatch、未登记 overlay 或浮点近似绕过 W0 的源码/二进制身份检查。

## 下一阶段依赖与云端可行性

| 工作 | 需要本地吗 | 云端可否完成 |
|---|---|---|
| W0 精确 token 规范化及单元测试 | 否 | 可以；应由 W0 在其分支完成并运行 CI |
| W4 更新 W0 commit/blob/request/pins/CI 身份 | 否 | 可以；W0 修复提交后在 W4 分支完成 |
| 修复后的 8 GiB P22 重放 | 不必固定本地 | 可以用已构建的原生依赖或 GitHub runner；需真实运行并记录 cgroup/OOM |
| 正式 P21/M6 运行 | 否，取决于实际执行主机 | 可在合格云 runner 或本地执行；不能仅因 P22 8 GiB 探针通过而自动放宽正式门槛 |
| W0/W2 owner、teacher、导数邻域准入 | 否 | 主要是代码/证据合同，可云端完成；需对应窗口正式收据 |
| 优化与 MuJoCo 对照 | 不必固定本地 | 可云端；必须等真实 M6、导数/teacher 准入及优化候选形成后 |

## 当前状态

- P18：保存实体分区证明通过；旧候选完整轴杆保护失败的反例已保留。
- P19：新候选完整原轴杆保护、正间隙及保存几何分区通过；canonical-source CI 作业通过。
- P20：真实原生模块构建、M/F/D 材料准备和独立 CI 通过；正式 M6 未通过。
- P21：同次捕获和离线回放实现、控制测试及 CI 通过；正式 M6 未执行。
- P22：8 GiB 真实容量探针进入 W0 M6 审计，因 binary-rational/decimal-rational 接口错误失败；没有 OOM。

本文件只记录已观察事实与 W0 交接，不将 P22 失败升级为 M6 通过，也不改变任何科学准入标志。
