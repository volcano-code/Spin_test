# Heart H9 W3｜第四阶段：真实两侧证据＋条件性的内点边—边穿越认证

**日期：** 2026-10-19；**唯一可写分支：** `research/neuralmoments-w3-heart-h9-20261019`；**冻结 H8f：** `0bcc187b3005478baa586a6d6f450e73811ca342`。

**严格结论：`DENY_CHERCHI_FASTER_NEWTON_ADMISSION`。** 本轮没有新的生产 Cherchi Boolean 成功调用，未获得真实 Heart 终态 OBJ、Newton 收敛残差或独立重新积分的最终物理指标。

## 1. 真实历史证据与原样保留的失败事实

- 原始 [GitHub Actions run #39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) **failure**；[artifact #12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290)，ZIP SHA256：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- 冻结 request SHA256：`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`。
- H8f 历史 **81/81 实际采样完成，30/30 数值差分通过，但整体构造 gate 为 failure**。精确规范化语义身份只有 sample 60 是非基点异常，不构成连续可微邻域认证。
- 本阶段从真实归档 sample 59（`q[7]=1.5e-6`）、sample 60（`q[7]=3e-6`）的**原生构造材料源边坐标（IEEE binary64 输入的精确有理解释）**与冻结设计域边坐标做独立计算；每个 point 的材料 gzip SHA、source face identity、原生边界审计 pass 状态皆验证，不改变原始 artifact。

## 2. 新增科学结论：穿越发生在有限线段的内部（有前提）

- 源边 `S=(source[24],source[90])`，设计边 `D=(design[5517],design[5518])`，两边各属于恰好两片原始三角形；分别为源侧 `(24,89,90),(24,90,151)`，设计侧 `(5516,5517,5518),(5517,5518,5523)`，已在归档实际检查。
- 对二元线段，记 `u=S1-S0`、`v=D1-D0`、`r=D0-S0`、`n=u×v`，严格有理计算无穷直线间最短投影参数 `s=(r×v)·n/|n|²`、`t=(r×u)·n/|n|²` 和有向体积 `det(u,r,v)`。`s,t∈(0,1)` 证明最近点位于各自**有限边段内部**，却不代表两个不同历史 q 的两条边已经相交。
- 真正原生历史 sample 59：`s=0.6140709255537691`、`t=0.4476520309721671`、有向体积 `+1.5630561011148573e-8`、两直线最短距离² `1.3424617471982359e-11`（模型单位²）。
- 真正原生历史 sample 60：`s=0.6140308627115632`、`t=0.4474835883856242`、有向体积 `-1.4405585247826644e-8`、距离² `1.1402896329483086e-11`。上述每个量均以 **Fraction 严格精确计算**，浮点数仅展示。
- 基于第三阶段已说明限制的 **固定法向逆 Gauss 解析代理模型**，本阶段重新独立使用 `10^40` 有理定点端点、向外舍入四则运算、整数 `isqrt` 上下界及区间自动微分认证。在完整 `q[7]∈[1.5e-6,3e-6]` 内，`s∈[0.6139295228,0.6141722897]`、`t∈[0.4471624614,0.4479733010]`、`|u×v|²≥1.81970658e-5`、`D'(q[7])∈[-0.020025039533,-0.020023155419]`，严格不平行且单调变号。
- 代理模型中唯一有向体积零点位于 **`[2.28058622834439e-6,2.2805862283444754e-6]`**，44 次严格有理二分得宽度 `8.526512829121202e-20`。此零点处 `s≈0.6140500773065187`、`t≈0.4475643757150983`，两者严格在 `(0,1)`，所以在**代理模型内**是内部边—边穿越，而不只是延长线共面。

**证明范围警示：** 本轮新证明仅严格适用于从归档二进制浮点顶点抽取常量法向构造的**解析代理模型**。没有证明生产原生顶点在整个区间内保持上述法向、source 三角划分、运动误差界；没有新原生样本证实连续参数空间的 Cherchi Boolean 事件发生处；也不证明实际 Boolean 集合不连续。不能放行 Newton。

## 3. 新增实际代码、回归测试与原生失败记录

- `source/certify_h9_interior_edge_crossing.py`：完全 stdlib 的哈希验证和**二段真实归档坐标精确有理证据**、独立的条件解析边—边内部交会区间认证；证书 `reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json`。
- `source/probe_h9_crossing_sides_live.py`：在具备真实 pin 版 Cherchi/GMP/native 环境后，**串行四点**：`2.1805862283444328e-6`、`2.2705862283444327e-6`、`2.2905862283444326e-6`、`2.3805862283444325e-6`。每点必须先进行真实 source/Boolean 求值、native 精确有理边界审计、独立 Fraction 10 质量矩复核、Jacobian 有限性与左/右 LPI/TPI 符号身份比较。按原值保存每次 material JSON gzip + SHA，绝不 fallback 或启动 Newton。
- `tests/test_h9_interior_edge_crossing.py` 和 `tests/test_h9_crossing_native_contract.py`：验证精确代数公式、区间端点负分母、有理 sqrt、伪造 ZIP、真实历史材料、四点位置、伪造 Newton 准入、篡改证书拒绝及缺原生依赖时 fail-closed。**本机 11/11 PASS**，见 `reports/H9_STAGE4_TESTS.log`。
- **实际试运行原生探针：exit code 1**，`failed_stage=IMPORT_REAL_PINNED_NATIVE_CHERCHI`，`new_real_native_calls=0`，`newton_admitted=false`；原始失败 JSON 见 `reports/H9_STAGE4_NATIVE_FAILURE.json`，不是成功 CI 或新 Cherchi 样本。
- 未运行新 GitHub CI，原因：此 W3 分支没有自动匹配的 workflow，独占范围明确不允许改动 `.github/workflows`；GitHub 连接器未提供原生 workflow_dispatch 能力。

## 4. 重放命令

```bash
export H9_EVIDENCE_ZIP=/path/to/heart-h8f-all81-artifact.zip
ROOT=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$ROOT/source/certify_h9_interior_edge_crossing.py" --artifact "$H9_EVIDENCE_ZIP" --output /tmp/h9-stage4-edge-proof.json
H9_CROSSING_CERTIFICATE="$ROOT/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json" \
  python -m unittest discover -v -s "$ROOT/tests" -p 'test_h9_*crossing*.py'
# 仅限已有 pinned core+Cherchi+GMP build 的隔离环境；原生任务串行，限 <60 分钟；编译并发 <=4：
timeout 3300s python "$ROOT/source/probe_h9_crossing_sides_live.py" \
  --artifact "$H9_EVIDENCE_ZIP" \
  --certificate "$ROOT/reports/H9_INTERIOR_EDGE_CROSSING_CERTIFICATE.json" \
  --output /tmp/h9-real-crossing-four-points
```

## 5. 下一门槛

待真实原生环境可用，比较四个真实样本的 `native_event_sign`、左右真实 LPI/TPI support、`source_faces`、exact material moments、Jacobian，分别判断是否如代理预期。严禁以零点唯一性代替**真实 Boolean 生成、可接受 Newton 步、最终 OBJ 和物理积分**。
