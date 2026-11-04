# W3 M21.1｜六材料分层运动诊断：源码与本地交接

## 当前基线与本轮范围

基于 W3 `b1ec4bad3653912565cf9f6e566e71cfe346bb28`。只新增 W3 独占 source/tests/reports 文件；不修改生产求值器、冻结 H8f、其他窗口或 main。当前会话 GitHub 连接器仅提供读接口；写接口发现为空，因此本轮交付可应用 patch，而不是声称已经远端提交。当前远端 SHA 不等于本轮新成果 SHA。

用户上传 M20 ledger SHA256：
`95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703`。
该文件记录六个已保存表面的精确十矩和差分，但没有原始六材料的全部几何、源速度。报告不能替代原始材料；本会话未获得用户的六份新原生压缩包。

## 核查到的实际接口

`python/make_it_stand/verification/cherchi_inprocess.py`（基线 blob `f9fa539f699df8baf8b8d30729048269a26ecb3c`）在 `__call__` 中调用 `_make_it_stand.evaluate_spin_it_faster_source_motion`，读取 `vertices/faces/vertex_velocity`，转换到物理坐标后执行 Boolean，再恢复交点速度，最后计算质量矩 Jacobian。

`material` 保存了 `quadric_source_vertices/faces`、原始/已解析构造记录、精确交点、`moment_jacobian`；**没有保存源顶点速度**。因此不把缺失速度当成 0，也不把位置割线冒充生产导数。源速度通过可选 SOURCE-ONLY 模式重新取得，明确标记“新重放的 binary64 速度”，不是此前执行时的密码学见证。

## 新实现

### h9_m21_motion_math.py

独立 Fraction 算法重建 EXPLICIT3D、LPI 和 TPI 的位置及给定源速度下的切向运动。LPI 直接微分线平面求交分式；TPI 使用精确 3×3 系统及其微分。对原始 operand 的 input_object/input_vertex、唯一性和精确坐标作绑定；拒绝奇异约束、歧义、重复约束键和不完整顶点覆盖。

物理交点必须逐顶点等于材料 proof 的精确坐标，变换到冻结 target frame 后必须等于 variable_rational_vertices。顶点比较按构造键、面片按有向语义三角形，不按数组位置对齐。只支持冻结 H9 的 normalization L=1、origin=0 场景，且逐点验证坐标合同；不能泛化为任意归一化实验。

质量矩导数使用独立的有向四面体行列式/多项式微分，而不是复用生产 Reynolds 系数实现。它对**给定的重放源速度**作精确有理传播，不会使源速度本身变成精确导数真值。

### h9_m21_layered_replay.py

- `ledger`：绑定真实上传 M20 文件，生成六包索引和残差摘要；不宣称原几何已经复核。
- `geometry`：通过上传 ledger 中的压缩包/metadata SHA、M19 plan/launch/refinement SHA 和冻结 archive/request SHA 读取六材料，重建所有已保存约束，检查同侧语义对应；不加载原生模块。
- `source`：在独立子进程中只调用 **6 次原生源曲面求值**，不实例化 `InProcessCherchiEvaluator`、不调用 `_cherchi_core_boolean.boolean`。源坐标必须与已保存坐标 binary64 字节一致，原生核心 SHA 必须与 M19 相同。随后独立恢复交点运动和十矩导数。
- 源模式沿用 W3 资源预检、24GiB 地址空间限制，父进程3480秒超时后终止整个进程组。每包独立存 checkpoint，失败不销毁已保存诊断。
- 新速度附件、独立链式导数与旧 J7 的逐分量绝对/缩放/相对差异、源运动割线比较、按 EXPLICIT/LPI/TPI 分组的边界运动比较分别报告。不设“看到结果后恰好通过”的阈值，不自动归因，不允许 Newton。

`source` 的 source-geometry bitwise mismatch 不是建议放宽容差：此时先检查解释器、原生二进制、请求/变换和源求值复现条件。成功退出只说明诊断执行完毕，不表示所有差异足够小。

## 实际执行证据

- M21 28/28 unittest PASS，无跳过。解析 LPI/TPI、平移/缩放四面体、奇异/歧义/篡改拒绝、槽位重排、合成六包 I/O、源接口模拟及子进程失败处理。
- 真正的历史 H8f sample59、60 各 **8,455 个顶点**精确重建成功；59 的 EXPLICIT3D=7,671、LPI=784。两个历史点构造键确有变化，跨分支运动比较被拒绝。
- M20 13/13 原回归 PASS，无跳过。合计41项测试；测试中模拟接口不代表真实源调用。
- 对用户上传的真实 M20 ledger 执行 `ledger` CLI 成功；新的 source calls=0、Boolean calls=0。
- 尚未运行用户六份新材料的 `geometry`/`source` 阶段；最终偏差根因未确定。没有新的远端 CI 结果，没有远端 M21 commit。

## 本机执行

外部交接包提供 `APPLY_M21.sh` 和 `RUN_M21_LOCAL.sh`；应用脚本只接受专属W3分支与基线HEAD，拒绝跟踪文件修改，运行测试后才提交/推送。运行脚本按已知SHA查找正确的M19和M20目录，不按“最新文件名”猜测。

先 `bash APPLY_M21.sh --commit-and-push`，再 `bash RUN_M21_LOCAL.sh geometry`；geometry通过后才 `bash RUN_M21_LOCAL.sh source`。不重编译，不重跑Boolean，不覆盖旧证据。source模式需要已有原生核心和原有 swap0/内存条件；不要为通过预检在内存紧张时强制 swapoff。

## 解释下一份结果的边界

1. 精确位置无法重建：停在几何/坐标/构造合同层，不讨论导数正确性。
2. 源重放位置无法逐字节复现：停在生产源映射复现层，不用旧材料搭配不匹配的速度。
3. 位置复现、独立链式 J7 与旧 J7 差异明显：优先检查交点运动/积分导数的数值传播；不是直接判定哪个实现正确。
4. 独立链式 J7 与旧 J7 接近，但源速度与有限位置变化不一致：调查源映射数值行为或步长效应；有限差分仍不是连续源导数真值。

所有输出保留 newton_admitted=false、continuous_neighborhood_certified=false、root_cause_determined=false。M21.1 是可执行定位工具，不是M22准入证书。
