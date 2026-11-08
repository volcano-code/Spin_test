# W3 Heart H9｜M21.6D-P0 四个真实 quarter-point 采样计划

日期：2026-11-08  
唯一写入分支：`research/neuralmoments-w3-heart-h9-20261019`

## 1. M21.6C 关闭条件

用户本地执行 `test_h9_m21_6b_moment_layers.py`：18/18 PASS，0.016 s，exit code 0。M21.6C 关闭。测试验证的是离线精确数学/输入门禁，不代表连续光滑性或 Newton 资格。

## 2. M21.6D-P0 本轮实际交付

新增：
- `source/h9_m21_6d_quarterpoint_plan.py`
- `tests/test_h9_m21_6d_quarterpoint_plan.py`

该阶段只做**计划生成与输入再验真**，不执行 Cherchi Boolean、不调用 native source、不修改原始六个材料包。计划器：
1. 重新核对 H8f 原始 artifact、M18 audit、Stage17 原生报告、M19 midpoint plan、M19 两个新 midpoint 的独立审计；
2. 复用 M21 M20 ledger 和六个材料包加载门禁，逐份重放六个既有 source-motion attachment；
3. 固定六个已认证点的顺序：left coarse / left near / right near / right coarse / left mid / right mid；
4. 对每个同侧半区间取 binary64 端点的精确有理中点，并只将 q[7] 改为该值；其余九个系数必须逐位不变；
5. 输出四个预声明新点，所有点必须严格位于各自区间内部。

四点顺序：
- left coarse → left M19 midpoint；
- left M19 midpoint → left near；
- right near → right M19 midpoint；
- right M19 midpoint → right coarse。

每个新点预期需要一次 Cherchi Boolean same-call material 和一次 source-motion 证据；本计划器实际执行计数必须保持 0。

## 3. 为什么不能直接线性插值

quarter-point 必须是真实原生 Cherchi 同调用材料及独立重积分结果。端点几何、端点 source velocity 或 J7 的线性插值不能生成新的有效边界、LPI/TPI 语义、原生 moment Jacobian 或独立十矩真值。计划器只生成 q，不伪造几何。

## 4. 当前验收状态

- M21.6C：用户本地 18/18 测试通过。
- M21.6D-P0：计划器与 11 项纯函数回归测试已提交；**尚未由用户本地运行**。
- 四个 quarter-point 原生 Boolean：0/4（尚未执行）。
- 四个新 source-motion：0/4（尚未执行）。
- 连续邻域、渐近阶数、根因、Newton、最终 Heart OBJ：仍未认证/产生。

## 5. 本地执行命令

见本次回复。计划器成功状态：
`FOUR_REAL_QUARTERPOINTS_PREDECLARED_NOT_EXECUTED`；
必须同时满足：
- `M21_6D_PLAN_POINTS 4`
- `M21_6D_NEW_BOOLEAN_CALLS_EXECUTED 0`
- `M21_6D_NEW_SOURCE_CALLS_EXECUTED 0`
- `M21_6D_NEWTON False`

先验收 plan 和 11 项测试，再编写/运行受资源约束的四点原生 worker。不得跳过计划审阅直接运行四次 Boolean。

## 6. 云端/本地分工

云端可完成源码、计划数学、单元测试设计、报告及 GitHub 推送。当前云端没有用户的本地六个原始材料、source-motion 运行目录及锁定 Cherchi 原生构建，因此**四个真实 quarter-point Boolean 和 source-motion 必须在用户本地固定环境执行**。不需要额外云服务器；本阶段也不需要 GPU。

保持 `newton_admitted=false`、`continuous_neighborhood_certified=false`、`root_cause_determined=false`。
