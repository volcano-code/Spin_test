# H8d 真实 Cherchi 材料十质量矩独立认证（2026-10-18）

## 经 GitHub Actions 实际执行通过

- Workflow: https://github.com/volcano-code/Spin_test/actions/runs/39118951636
- Workflow 执行提交：`f8937034ccc275305a107cd1603fb81c7605636b`
- Run 产物 artifact ID：`12132634988`，名称 `heart-h8c-cloud-native-input-or-point-evidence`，包含原始 `actual-cherchi-packet.json.gz`、`result.json`、`exact-ten-moment-certificate.json`、CAD OBJ 和冻结 `prepared-request.json`。
- 模型输入：`H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED`；**作者原始 CAD 不是本实验输入**。
- 新 Heart 模型的 `initial_top.obj`、`fixed_shell.obj`、`design_domain.obj` 均通过真实 native exact boundary 检查：closed、edge/vertex manifold、oriented、self_intersection_completed、self_intersection_free。
- 本次探测的源二次曲面边界：162 顶点、320 面，同样通过原生精确边界审计。
- 真实 Cherchi intersection/difference 材料：**8455 顶点、16910 面**；通过原生**有理**审计，零相交对；动态布尔单次 `0.8065607009999667 s`，**不代表完整算法计时**。
- 精确材料数据 SHA-256：`ba47a6d6f9fad2dce2569434bf9340252cceaeaf99c14a82df02b637092b6464`。
- 冻结 Faster 请求 SHA-256：`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`。
- 原生动态库 SHA-256：`_make_it_stand=ad0c4fe3527954c611743dbbccb384cc1521909e8a39d68c3b7554b3a3919d40`；`_cherchi_core_boolean=3cc8bf789168752f8b921c160ca9937cdf0f61c845d3088760811b9e5a4596b7`（**云端新编译二进制**，不是历史 H6）。
- 纯 Python Fraction 和原生 GMP 双独立积分对同一份材料得出**10/10 质量矩 0 ULP 差异**；Python Fraction `2.614737232s`，原生 GMP `0.266871130s`（单次，仅原始十质量矩）。
- 此单点材料加固定壳质量：`25.9522459043g`；质心偏轴 `5.6268584807mm`（**尚未优化到旋转轴上**）。
- 完整原生 CI 结果：**success**。

## 明确未验收

- 上述结果只对应一个注册的探索性球形二次曲面 q；与历史 H6 Heart V4 代理不混淆。
- 虽然合法且十质量矩独立复核，**当前质心并未对齐目标轴**；不能当作完工陀螺。
- 生产 Jacobian 10×10、9 点 / 81 点三尺度导数、构造分支平滑邻域、Faster Newton、多种子、真实碰撞接触、制造尚未验证。
- 原生十质量矩一致性指明数值积分程序输出在浮点结果相同；独立网格分区与可打印的物理固体仍需专门认证。

## 下一步

实际云端运行 H8e `probe_h8_jacobian.py --columns 0` 的 9 点测试。每点必须通过真正 Cherchi + 原生有理边界 + 独立 Fraction 十矩后，才能对基点 10x10 Jacobian 进行三尺度五点差分的数值比较。特征哈希相同本身也**不能**证明连续邻域可微性。
