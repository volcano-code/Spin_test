# W1 M26 — 精确后 Boolean 表面审计与可复现重放修复

**实验日期：** 2026-11-04（首次），2026-11-05（独立复跑及重放器修复）  
**唯一可写分支：** `research/neuralmoments-w1-native-20261019`  
**输入：** 用户提供的 `material-evidence.zip`，SHA-256 `0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976`。原始包未改动，未纳入仓库。

## 代码与实际检查

- `m26_exact_intersection.cpp`：单独编译的 C++17/GMP 精确三角形相交审计，使用有向外舍入 AABB + Boost R-tree 枚举候选对，并用有理数判定相交。检验边 2-流形、有向性、非退化和 vertex link 单扇连通性。它**不依赖** CGAL 或生产 Cherchi Boolean。
- `m26_replay.py`：校验保存的 ZIP 成员、SHA、控制实验与操作类型，向独立 C++ 校验器输入精确坐标，不会将缺失包误判为空。修复了相对二进制路径被 `Path("./bin")` 字符串化后无法启动的问题，使用 `resolve(strict=True)`。将残留顶点空包独立拒绝。
- `test_m26_exact_intersection.py`：11 项原始合成与异常输入案例 + 3 项续接回归，共 **14/14 本地通过**。检查自相交、非流形、空材料、无效三角索引、二进制路径和异常包。
- 对原始冻结 ZIP 再次执行四点重放，逐点核对源包 SHA、输入流 SHA、候选对数量与旧报告一致，状态 `COMPLETE_SAVED_OUTPUT_SELF_INTERSECTION_CERTIFICATION`。这属于已保存材料的离线后处理，没有重新执行 Cherchi Boolean。

## 真实材料（来自同一冻结原生证据）

| 求值点 | Boolean | 顶点 | 三角面 | 精确候选面对 | 状态 |
| ---: | --- | ---: | ---: | ---: | --- |
| 117 | difference 控制点 | 5718 | 11432 | 131720 | `EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE` |
| 4 | intersection 候选 | 5158 | 10312 | 250083 | `EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE` |
| 116 | difference 候选 | 5718 | 11432 | 131392 | `EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE` |
| 123 | difference | 0 | 0 | 0 | `STRICT_EMPTY_NO_POSITIVE_MASS` |

**一共 513,195 对三角面候选经精确判定**。三份非空输出满足本检测器所检查的精确非自相交、闭合有向 2-流形；123 是四个材料数组都为空，不可作为正质量输入。

## 禁止扩大的科学结论

这个检查**没有**证明每个输出是其输入实体的正确 intersection/difference 集合，未完成独立完整实体包含/域标签证明。不能据此声称导数正确、光滑邻域已认证，也不能默认空包的 Jacobian 为零。未提供生产 Cherchi 十矩、完整 `10×10` Jacobian、生产 Newton 收敛、W0/W2 正式准入和同输入完整 A/B/B/A 性能增益；`full_solver_speedup=null`。不存在本轮新的 Boolean/ Newton 执行。

## 已执行命令

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Wno-deprecated-declarations m26_exact_intersection.cpp -o m26_exact_intersection -lgmpxx -lgmp
python -m unittest -v test_m26_exact_intersection.py
python m26_replay.py --archive /path/to/material-evidence.zip --binary ./m26_exact_intersection --output /tmp/m26-audit-new.json --max-seconds 90
```

复跑结果：**14/14** 测试通过，保存的四点审计状态与原记录一致。二进制路径缺陷的首次失败被修复；修复版已成功完成四点重放。

## 后续与本地必要性

**暂不需要本地：** 云端仍可继续对保存的输入/输出做精确集合语义与材料边界审计、源码修复、导数验证框架与回归测试。  
**必须真实原生环境（目前优先用户本地）：** 同输入生产 Cherchi 十矩比对、完整原生 Jacobian/有限差分、生产 Newton 真实收敛、最终 A/B/B/A 完整求解时间。遵守 24 GiB、swap0、串行、≤60分钟、编译≤4并发。  
**当前 W1 目标尚未达成：** 未取得完整收敛、材料数学准入和正式 end-to-end 提速。
