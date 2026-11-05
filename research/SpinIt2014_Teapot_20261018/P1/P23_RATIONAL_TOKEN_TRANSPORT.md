# P23：精确有理数传输接口复现与 W0 修复验收

P23 是 W4 独占目录内的接口兼容性回归，不调用 Cherchi、不运行原生几何、不执行正式 M6，也不改变 W0/W2 科学准入。它把 P22 的实际失败变成可在云端重复执行的最小测试，并为 W0 修复提供可执行验收条件。

P22 的实际数据和根因见 [P22_CAPACITY_RATIONAL_FORMAT_FAILURE.md](P22_CAPACITY_RATIONAL_FORMAT_FAILURE.md)；跨窗口修复交接见 [W0 issue #4](https://github.com/volcano-code/Spin_test/issues/4)。

## 冻结接口事实

- W0：`51cbfd33d08063404d7e0c40e4256dd0e38efa1a`
- core：`58fd12c1306c1c01679a19172e276eef0cb30542`
- Cherchi binding 输出精确二进制 token，例如 `0b101101/0b1101`、`-0b101/0b11`，零可为 `0/1`。
- W0 `native_teacher_replay.frac()` 已接受二进制 token。
- core `spin_problem._canonical_rational_vertices()` 的公共边界只接受规范十进制文本。
- 两个 retained-boundary 调用点需要在调用 `MeshSnapshot.from_rationals()` 前采用同一精确规范化函数：`native_teacher_replay.py` 和 `full_partition_m6.py`。

建议 W0 暴露 `canonical_mesh_rational_rows(vertices)`：用现有 `frac()` 转成 `Fraction`，再用 core 的 `fraction_to_rational_text()` 生成规范十进制文本。不得经过 float，也不得放宽 MeshSnapshot 的十进制输入合同。

## 本轮新增的 W4 资产

- `p23_rational_token_transport.py`：从实际冻结 W0/core checkout 动态加载解析器与 mesh 输入合同。
- workflow job `p23-rational-token-transport`：GitHub Actions 分别 checkout 固定 W4、W0、core 版本，安装 NumPy 后执行纯 Python 接口回归，并保存证据 artifact。

当前基线模式预期状态：

`P23_KNOWN_W0_FORMAT_MISMATCH_REPRODUCED_PENDING_FIX`

测试覆盖：
1. W0 replay parser 接受二进制有理数。
2. MeshSnapshot 十进制边界拒绝原始二进制 token。
3. 精确 adapter 将正、负、零 token 转成规范十进制，并被同一边界接受。
4. 20,000-bit 级分子/分母精确往返，不使用浮点转换。
5. 非法 token、分母和顶点行形状被拒绝。
6. 当前两个 W0 retained-boundary 调用点尚未使用共同 helper；基线模式明确复现这一事实。

W0 发布修复后，将 workflow 的 W0 SHA 更新为新 commit，并启用 `--require-fixed`。固定模式要求 W0 实际导出共同 helper，且两个调用点均在 MeshSnapshot 边界前使用该 helper。

## 云端/本地判断

| 下一项工作 | 执行位置 | 原因 |
|---|---|---|
| P23 当前基线复现 | GitHub Actions | 固定源码、Python 与 NumPy 即可，无需原生构建或用户本机 |
| W0 精确转换修复 | W0 独占分支，云端 GitHub 开发与 CI | 不需要本地 Teapot 运行；由 W0 维护者提交 |
| W4 更新 W0 commit/blob/request/pins | GitHub 云端 | W0 修复提交后在 W4 分支完成 |
| 修复后的 8 GiB P22 重放 | GitHub Actions 可先做 | 用 cgroup 8 GiB 和真实 pinned native evaluator，记录峰值/OOM |
| 完整正式 M6 | 合格云端 runner 或本地 | 按真实资源观察和正式准入规则执行；不预设 26 GiB 是算法最低需求 |

## 验收边界

P23 成功只表示接口缺陷已复现或修复。它不代表 source/Boolean、三材料集合分区、Jacobian 正确性、导数邻域、Newton 收敛、W0/W2 准入、优化或 MuJoCo 优化前后比较通过。P22 的 544 MiB 峰值只对应接口异常前的阶段，不是完整 M6 峰值。
