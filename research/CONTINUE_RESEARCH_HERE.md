# Spin / Noodles v6 — 研发续接索引（2026-10-16）

## 仓库来源与边界
- 原仓库： https://github.com/volcano-code/Spin
- 原始工作分支：`spin-it-strict-computational-v2`
- 当前记录基线：`a17ff49cd8a1e6e8b388bc591410bda56d67c28a`
- 在线原生构建中使用过旧基线：`b0a13e3f7050630e84e3fbe19e7cf4004540a06e`。**不可把旧二进制当作新源码生产验证。**
- 本仓库 `Spin_test` 是单独的研究备份；不向原仓库写入。
- 用户要求阶段成果每次审阅，经过明确批准才向正式原仓库推送。

## 项目目标
用 Spin-It Faster 二次曲面质量矩优化，**Cherchi 是 Newton 每次材料布尔求值的正式后端，CGAL 只作离线固定输入构造与独立验证**。输出没有永久椭球壳的连续面条陀螺、真实优化终态与旋转动力学仿真。不要求现阶段完成实物制造或切片。

## 截至最新已核对成果
- v6 输入 `F=union(81 fixed parts)`；`D=E\\F`；`A=E union F`，共有 79 根管加中心连接及转轴；80 次固定并集 + 4 次附加 CGAL 布尔 = **84 次**。
- 82 个输入部件及 164 个 OBJ 通过早期检查；P0 独立原生小型回归 **8/8**。
- CGAL 输出：fixed 92,692 面、design 83,408 面、initial 32,180 面（独立构造产物，不是 Newton 最终结果）。
- 三项有理有限有向表面链检查实际通过：`F+D=A`、`K+D=E`、`K+R=F`。
- **并未证明六个实体全部独立合法；Cherchi 对开放设计域仍未通过生产验收；质量矩/Jacobian/真实 Newton 收敛/完整材料重载/旋转仿真均不能声称已通过。**
- 面条的旧 v5 最终模型虽经过一部分几何封存，但永久椭球壳与论文案例不匹配；不能作为 v6 最终旋转效果。
- 用户批准将现有信息**备份到 Spin_test**，但原仓库改动仍需要单独批准。

## 下一阶段按顺序执行
C0 固定最新源码和二进制身份、构建/加载 Cherchi；C1 补齐六实体独立合法性与嵌套；C2 将生产求值从 CGAL 迁到 Cherchi，实际开放边界验证与 CGAL 交叉检查；C3 GMP 10 质量矩和 Jacobian；C4 Newton 多种子及独立复现；C5 合法最终 OBJ+完整惯量+外观比较；C6 无持续驱动的陀螺接触动力学仿真。制造暂缓。

## 必需的上下文文件
- `research/plans/Noodles_v6_Cherchi_simulation_acceptance_plan_20261016.md`
- `research/reports/Noodles_v6_P0_stage_report_CN.md`
- `research/reports/Noodles_v6_P1a_exact_construction_CN.md`
- `research/reports/Noodles_v6_P1b_exact_chain_proof_CN.md`
- `research/status/Noodles_v6_execution_status.json`

## 没有被文本索引替代的资料
本次 ChatGPT 会话另产生了 ZIP：`Noodles_v6_P0_native_build_and_tests_review.zip`、`Noodles_v6_P1a_exact_input_models_review.zip`（约29MB）、`Noodles_v6_P1b_three_exact_chain_checks_review.zip`、`Noodles_v6_exact_domain_review.zip`，以及此前整个 Spin 离线源码包。**只有仓库中实际出现相应文件或 GitHub Release 后才能称它们已持久备份。**不可把会话 sandbox 链接当成永久 GitHub 备份地址。

## 原源码迁移
`.github/workflows/backup-spin-upstream.yml` 提供一次性镜像操作。预期创建分支 `upstream-spin-it-strict-computational-v2`，HEAD SHA 应等于上文基线。没有实际可见分支前不可宣称原仓库已迁移成功。
