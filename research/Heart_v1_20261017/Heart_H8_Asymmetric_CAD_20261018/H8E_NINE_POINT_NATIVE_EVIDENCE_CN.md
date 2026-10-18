# H8e 真实 Cherchi Jacobian 单方向九点试验（2026-10-18）

## 已通过的原生证据
- GitHub Actions 原生 job：<https://github.com/volcano-code/Spin_test/actions/runs/39120089309>，**success**；执行 SHA `287718e8e768b3bd4876f7a135aa7d85bb605798`。
- Workflow 附件 ID `12133943977`，名称 `heart-h8e-real-jacobian-pilot-proof-or-failure`，包含 9 点完整数值记录 `artifacts/h8e-jacobian-col0/report.json` 与 `point-000..008.json`。
- 原生报告 SHA-256：`7f85144f5fcdc0eff112221134db247a392c21c32874f8706587fff980f2e5bc`；冻结 Faster 请求 SHA-256：`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`。
- 每点依次执行真实 `InProcessCherchiEvaluator`：Cherchi 原生 Boolean、十质量矩/10×10 Jacobian 原生 GMP、原生精确有理边界审计、独立 Fraction 十矩积分、同次材料身份校验。9/9 点成功，无降精度或动态 CGAL 后备。
- 柱方向 `q[0]` 的五点差分、三尺度检查：
  - `3e-6`: scaled error `2.9987497227573026e-11`
  - `1.5e-6`: scaled error `6.708998947717519e-11`
  - `0.75e-6`: scaled error `2.6229806854310685e-10`
  - 3/3 `numerical_passed=true`，阈值 `1e-6`。
- 9 点同一 `SOURCE_FEATURE_BRANCH_V2` 构造特征摘要：`all_tested_stencils_same_feature_hash=true`，`changed_feature_hash_points=0`。
- 系数缩放零方向：`||Jq||₂=1.0649829225206779e-15`。
- 9 次端到端积分/精确审核/证据记录耗时 `129.782507698 s`，约 `14.4s`/次。sum of isolated stages：`source=0.03653s`, `Boolean=11.67069s`, `intersection_motion=6.71961s`, `derivative=4.19107s`, `integration=2.92186s`；独立 Fraction 和 native geometry audit 不应算作 Boolean 内核耗时。

## 坐标系一致性的重要核验
直接 H8d 单点材料 `actual-cherchi-packet.json.gz` 的十质量矩位于**模型坐标系**；正式 H8e 求解器通过 `target_origin=[0,0,-0.11499998450279236]` 移至目标坐标系。两条管线基点的质量、x、y 和其他部分逐项一致；按照刚体坐标平移公式转换 H8d 的独立十矩至 H8e frame，最大绝对差为 `5.551115123125783e-17`。**直接比较原始两个坐标系的 z、z² 而不变换会出现假性差异**。下一批试验必须把此核验设置为自动关卡。
 
## 严格限制
- 这是 **H8 重建非作者 CAD**，并不是原作者 CAD。
- 当前只覆盖 `q[0]` 一列（9 点），**不能声明十列 81 点 Jacobian 已验收**。
- 特征哈希相同不等价于邻域连续性证明，不授予真正 smooth-stratum 或 Newton 准入。
- 已有 H8d 单点质量 25.9522459043 g，质心偏轴 5.6268584807 mm，仍不是平衡优化结果。
- 完整的优化材料、物理接触稳定性、3D 打印验收全部未做。
 
## 下一步
在已有原生成功环境上完成 `0,4,8` 三列 25 点（记录每点 exact construction packet + SHA），在实际数值与构造身份观察后再决定是否推进 81 点；不能用旧 H6 Heart V4 的雅可比或已保存优化 q 充当新输入验收。
