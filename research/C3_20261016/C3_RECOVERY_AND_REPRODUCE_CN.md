# C3 成果恢复说明

本成果包里的 `C2_frozen_inputs/` 是 C2 已通过精确重三角化的三个主实体；未直接拷贝使用旧 v5 的包壳设计。`code/` 是本轮新增实际运行脚本；`evidence/` 包含 Cherchi 与 CGAL 同次真实输出、数值 Jacobian、差分和误差预算。其他老依赖需要从原 `Spin` 项目及已有构建检查点提供：`_make_it_stand`、`_cherchi_core_boolean`、`_cherchi_rational_moments`、CGAL 程序。

**现有脚本含原执行工作目录 `/mnt/data/...` 的绝对路径。** 直接在别的机器上运行前必须根据存放位置替换这些路径与 `env.sh`，但不得改变文件内容 SHA 对应的几何意义；不要把复制脚本语法成功当作原生重新验收。

实际运行顺序：

```text
00_probe_real_moving_quadric.py
01_compare_real_quadric_cgal.py       # CGAL + 精确面链通过；其超长 Python Fraction 积分段未完结
02_provenance_and_source_velocity.py
03_real_quadric_moment_jacobian.py
07_compare_native_gmp_cross_backend.py
04_real_quadric_finite_differences.py
04b_finite_differences_remaining.py
05_static_rounding_rigorous_moment_bound.py
06_vertex_feature_motion_finite_differences.py
08_dynamic_topology_branch_audit.py
09_verify_and_summarize_C3.py
test_C3_receipts.py
```

**全量验证受版本和计算资源约束。** 本包未附完整原 `Spin` 构建环境；已上传的 `Spin_test` 源码备份分支 `upstream-spin-it-strict-computational-v2` HEAD 是 `a17ff49...`，而本轮 C3 原生二进制从旧 `b0a13e3` 检查点加载。不要将此运行声称为最新分支的正式 Newton 收敛。

C3 状态见 `C3_STAGE_STATUS.json`；`formal_C3_admitted=false` 是防止误判的明确设计。完整新阶段差异与失败证据请以实际文件 SHA-256 manifest 核查。