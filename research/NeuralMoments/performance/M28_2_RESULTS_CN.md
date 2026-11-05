# W1 M28.2 — 输出三角形内部跨输入边界精确相交审计

**日期：** 2026-11-05  
**仓库：** `volcano-code/Spin_test`  
**分支：** `research/neuralmoments-w1-native-20261019`  
**原始证据 ZIP SHA-256：** `0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976`  
**M26 输出自相交证书 SHA-256：** `44867677606ea8437a5d94777df8214b879aca31ccb2fb047dd0e27cef3d79ff`

## 目标

M28.1 已经逐面核实输出三角形唯一来源、朝向，并对顶点、边中点和重心进行精确 point-in-solid 侧别分类；但离散采样本身不能排除三角形内部存在一条未穿过采样点的相反输入边界交线。M28.2 为每个非空输出三角形补上与另一输入实体全部三角面的精确跨边界检查。

## 算法

新增 `m28_cross_boundary_exact.cpp`：

- GMP 有理数用于三角形平面、线段/平面交点、共面多边形裁剪、点是否位于输出三角形边界等全部窄相判定。
- 3D AABB/R-tree 只负责候选对宽相；每个有理数边界都向外舍入，避免漏掉候选。
- 非共面三角形求精确交集点/线段；只有交集完全位于输出三角形边界上才允许。若线段端点都在输出边界、但中点进入输出三角形内部，仍判失败。
- 共面三角形执行精确二维裁剪；正面积重叠或零面积交集落入输出三角形内部均判失败；只沿输出边界接触才允许。
- 区分 `disjoint_candidate_pairs`、`boundary_contact_pairs` 和 `interior_cross_boundary_intersections`，避免把无相交的候选误报成接触。

Python 驱动器先以精确平面索引将输出面唯一归属到 design/source，再将每组输出面与相反输入边界交叉检查；原始 ZIP、成员清单、M26 证书、Boolean packet SHA、操作类型和顶点/面数量均固定核验。M26 自相交审计被复用，不重复执行。

## 真实四点结果

三个非空点的全部输出三角面都已对相反输入边界完成精确检查：

| 求值点 | 操作 | 输出面 | 对侧候选对/精确检查 | 不相交 | 仅边界接触 | 内部相交 |
|---:|---|---:|---:|---:|---:|---:|
| 4 | intersection / design | 9,898 | 442,809 | 442,184 | 625 | 0 |
| 4 | intersection / source | 414 | 356,705 | 354,637 | 2,068 | 0 |
| 116 | difference / design | 10,858 | 34,930 | 34,036 | 894 | 0 |
| 116 | difference / source | 574 | 39,799 | 37,436 | 2,363 | 0 |
| 117 | difference / design | 10,856 | 13,269 | 12,372 | 897 | 0 |
| 117 | difference / source | 576 | 40,152 | 37,780 | 2,372 | 0 |

**合计：** 33,176 个输出三角面；927,664 对候选面全部执行 GMP 精确窄相判定；918,445 对精确不相交，9,219 对交集仅限输出三角形边界，**0 对进入输出三角形内部**。六组检查总计约 20.34 秒。

第 123 点输出严格为空，不存在输出三角形可检查。复用 M28.1 的输入边界联合精确非相交检查（231,565 对）、两输入边界各自单连通，以及设计边界样本位于源实体内部的嵌套论证，支持 `D\S=empty`。

## 复现命令

先编译精确检查器：

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Wno-deprecated-declarations \
  m28_cross_boundary_exact.cpp -o m28_cross_boundary_exact -lgmpxx -lgmp
```

对每个求值点分别运行 design/source 两组（示例为 evaluation 4）：

```bash
python m28_cross_boundary_replay.py \
  --archive /path/to/material-evidence.zip \
  --m28 m28_saved_boolean_set_semantics.py \
  --certificate m26-saved-post-boolean-summary.json \
  --binary ./m28_cross_boundary_exact \
  --evaluation 4 --owner design \
  --output /tmp/m28-4-design.json --max-seconds 90
```

## 自动测试

跨边界检测器新增 11 项合成/对抗测试：非共面穿越、边界边接触、端点在边界但弦穿过内部、共面面积重叠、共面边界接触、内部点接触、边界顶点接触、平行分离、反转输出朝向、次 ULP 有理间隙等。

M26 + M27 + M28 + M28.2 全套回归：**42/42 通过，0 失败，0 跳过**。

## 科学边界

本阶段证明：对已保存的每个非空输出三角形，整个三角形内部不与相反输入边界相交；结合 M28.1 的精确侧别样本、唯一输入面归属、朝向规则和 M26 自相交证书，可将这些输出面内部分类到正确的 inside/outside 一侧。

**这仍不是最终的全局 Boolean 边界完整性证明。** 当前没有证明所有理论上应该出现在 intersection/difference 结果中的输入边界片段都已被输出覆盖，也没有排除遗漏一个完整的额外连通分量。因此 `full_boolean_boundary_completeness_certified=false`，不授予生产准入。

没有重新执行 Cherchi Boolean、生产十矩、Jacobian 或 Newton；`full_solver_speedup=null`。

## 云端/本地评估

M28.2 的代码、精确窄相算法、真实四点离线检查和 42 项测试全部在云端完成，不需要本地操作。下一阶段可以继续云端完成边界片段覆盖/完整性检查。生产 Cherchi 同输入十矩、真实 Jacobian、Newton 收敛及最终 A/B/B/A 仍需要固定原生模块环境。