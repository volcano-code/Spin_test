# W3 Heart H9｜M21.6D-P1 单点 Cherchi + source-motion 执行器

日期：2026-11-08  
唯一写入分支：`research/neuralmoments-w3-heart-h9-20261019`

## 本里程碑实现

新增：
- `source/h9_m21_6d_quarterpoints.py`
- `tests/test_h9_m21_6d_quarterpoints.py`

执行器按 `--index 0..3` 一次只执行一个 quarter-point，不并行、不一次性提交四个长作业。每次 run 包含：

1. 重新生成并逐字段比较 M21.6D 计划；重新绑定 M20、M18、Stage17、M19、M21.6A、M21.6C 与六份 source-motion 输入；
2. 验证干净 W3 分支、Python 3.13、24 GiB 地址空间限制、Swap=0、固定 Cherchi/GMP/core 二进制 SHA 和 build evidence；
3. 仅对指定 q 调用一次真实 `InProcessCherchiEvaluator` Boolean，同调用材料立即写入 unverified gzip；
4. 严格原生有理边界检查、独立精确十质量矩重积分、H7 符号支撑/事件定向符号检查；
5. 对同一材料调用一次 `evaluate_spin_it_faster_source_motion`，要求源几何逐位匹配、source 离散签名与区间两端一致；
6. 用精确保留构造重建 8455 个点、独立重算 J7，检查与原生同调用 Jacobian 第 7 列的一致性；
7. 独立第二进程重新读取材料、重新做边界/十矩/H7/J7 审计，全部通过后才将 unverified 包提升为正式 quarterpoint 包。

## 资源与安全边界

- 每次只允许 1 个新 Boolean 和 1 个 source-motion 调用。
- worker 最多 3200 秒，独立审计最多 330 秒，总 run 上限 3600 秒。
- 子进程地址空间上限 24 GiB；复用已固定的原生二进制，不在本阶段重新编译。
- 每个点独立目录、create-only 证据文件；失败保留 unverified 包，不覆盖历史材料。
- 不执行 Newton，不宣称连续光滑性，不生成最终 Heart OBJ。

## 当前状态

代码与 13 项纯合同测试已提交；尚未在用户本地执行新 Cherchi Boolean 或 source-motion。四个点必须串行执行。建议先运行 index 0，审查完整证据后再继续 index 1、2、3。

## 本地前置文件

- quarterpoint plan：M21.6D-P0 输出的 `quarterpoint-plan.json`
- build evidence：既有 M19 `build/build_evidence.json`
- 其余输入路径沿用 M21.6D-P0 已验证的 M20/M18/Stage17/M19/M21 source 目录。

## 单点成功条件

`launch_result.json` 必须是：
`ONE_QUARTERPOINT_INDEPENDENTLY_VERIFIED_NO_NEWTON`

同时 `independent-audit.json` 必须记录：
- 新 Boolean 调用 1；
- 新 source-motion 调用 1；
- 独立十矩重积分通过；
- 严格有理边界通过；
- H7 同侧构造身份和精确事件符号通过；
- source 几何逐位匹配、离散签名与区间两端一致；
- exact retained-chain J7 与同调用 native J7 对照通过。

四点全部完成后，才开展 quarter-point 分层残差汇总；不能在单点结果上宣称 Newton 已准入。
