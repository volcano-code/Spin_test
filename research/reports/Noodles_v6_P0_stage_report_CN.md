# Noodles v6 · P0 原生环境修复与独立小型验证（待审阅）

状态：**P0 离线诊断路径已通过，小型真实原生回归 8/8 PASS**；不代表 v6 复杂几何、真实优化或模拟通过。

## 原始失败与修复

- 原来的 `build.ninja` 不存在、临时 `ld-linux` 路径不存在：本次重新从源码配置 CMake，指向实际存在的 GMP 6.3.0、MPFR 4.2.1、CGAL 源码和 Python 3.13，使用系统实际加载器。
- v6 CMake 原来强制 C++20，旧 libigl 的比较重载编译失败；只将隔离的诊断项目调整为 C++17，未改第三方源码或物理公式。
- 原 `_noodles_exact_audit` C++ 绑定调用不存在的 `auditExactTriangleBoundaryMatrix` 和虚构的字段，无法编译；改为 Python 薄适配器，直接调用主原生扩展已有的 `audit_exact_rational_triangle_boundary` 与 `audit_exact_rational_material_boundary`，不以近似测试取代几何核。
- 原候选 `test_native_checks` 把字典中的 `valid` 作为旧原生返回字段，实际原生字段为 `boundary_valid`；已与实际 API 对齐。
- 原分区检测把签名字典直接做真假判断，可能出现虚假拒绝：现在检查 `signature` 有向表面链，并且对精确零面积三角形拒绝，保留源域检查。

## 实际测试

- CGAL 精确布尔程序：**真实编译、链接并执行**。
- GMP 有理质量矩 Python 扩展：**真实编译、链接并加载**。
- 原主 `_make_it_stand` 扩展：已真实加载，但它来自此前上传的旧源码快照。
- `test_native_checks.py`：**8 项 PASS**，其中包含相邻实体分区的精确有向链、重叠与缺失拒绝、CGAL 实际布尔运算的三式核验。
- v6 源部件 manifest：82 个部件、164 个 OBJ 文件按清单 SHA256 匹配。**摘要核对不是完整几何审计。**

## 源码身份与未完成项

本次离线使用的主工程快照为 `b0a13e3f7050630e84e3fbe19e7cf4004540a06e`，先前查看的线上最新分支为 `a17ff49cd8a1e6e8b388bc591410bda56d67c28a`。尚未完成对后者的全量生产构建。

P1 全部 81 个固定部件精确并集、新设计域与整域审计，P2 导数，P3 求解，P4 最终材料，P5 旋转仿真仍未被 P0 结果授予通过。

**未修改 GitHub；任何未来推送均需用户明确批准。**