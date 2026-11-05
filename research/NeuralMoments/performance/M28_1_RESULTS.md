# W1 M28.1 — 可断点恢复的真实 Boolean 材料语义审计

**日期：** 2026-11-05  
**仓库：** `volcano-code/Spin_test`  
**唯一可写分支：** `research/neuralmoments-w1-native-20261019`  
**输入归档 SHA-256：** `0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976`

## 本里程碑实际完成

1. 修复 M28 长任务执行器：改为逐求值点运行，完成后原子写入 checkpoint 和报告，支持 `--resume`。
2. 复用 M26 已认证的输出自相交检查，不再重复运行昂贵 GMP 几何检查。复用前同时验证原始归档 SHA、M26 证书 SHA、原生 Boolean packet SHA、操作类型和顶点/面数量。
3. 重新对真实四点执行 exact plane ownership、面朝向和顶点/边中点/重心 point-in-solid 侧别检查。
4. 对 123 点另外检查设计边界与源边界之间的精确非相交；将设计边界点分类为源实体内部，以支持差集为空的嵌套边界论证。
5. 加入 M26 证书篡改、packet SHA 漂移、操作漂移、几何尺寸漂移、原子 checkpoint 等测试。

## 四点真实结果

| 求值点 | 操作 | 设计来源面 | 源来源面 | 唯一精确分类点 | 结果 |
|---|---|---:|---:|---:|---|
| 4 | Intersection | 9,898 | 414 | 31,770 | 所有来源、朝向和侧别样本通过 |
| 116 | Difference | 10,858 | 574 | 35,454 | 所有来源、朝向和侧别样本通过 |
| 117 | Difference | 10,856 | 576 | 35,458 | 所有来源、朝向和侧别样本通过 |
| 123 | Difference | — | — | — | 严格空包；输入边界 231,565 对候选全部精确检查无相交；设计边界点在源实体内部 |

非空输出的朝向符合 Boolean 规则：Intersection 中两类来源面均保持输入方向；Difference 中设计来源面保持方向、源来源面反向。三个输出分别由 10,312、11,432、11,432 个三角面组成，均为正体积的单连通闭合输出（M26 证书复用）。

## 自动测试

**31/31 通过**：M26 14 项、M27 4 项、M28 13 项；无失败、无跳过。M28 新增 7 项检查证书固定、输入绑定、错误拒绝和 checkpoint 原子写入。

## 科学边界

本阶段的非空输出检查包括：每个输出三角面被精确包含于唯一输入三角面、朝向规则、顶点/边中点/重心的精确侧别分类，以及复用 M26 的精确自相交证书。

`full_triangle_interior_cross_boundary_tested=false` 仍然成立：本阶段尚未对每个输出三角形内部与另一输入边界执行完整的精确三角形相交检查。因此不将本阶段称为最终 Boolean 集合语义证明，也不授予生产准入。

未运行新的 Cherchi Boolean、生产原生十矩、10×10 Jacobian 或 Newton；`production_admitted=false`，`full_solver_speedup=null`。

## 本地操作评估

M28.1 全部在云端完成，不需要用户本地运行。下一步 M28.2 的完整三角形内部跨边界精确检查仍可云端开发。只有生产 Cherchi 同输入十矩/Jacobian、真实 Newton 收敛和最终 A/B/B/A 性能验收需要固定原生模块环境（当前优先本地 Ubuntu）。

## 复现

```bash
python -m unittest -v test_m26_exact_intersection.py test_m27_intersection_adversarial.py test_m28_saved_boolean_set_semantics.py
python m28_saved_boolean_set_semantics.py \
  --archive /path/to/material-evidence.zip \
  --m26-binary ./m26_exact_intersection \
  --sample-level full --resume \
  --output /tmp/m28-all-points.json \
  --checkpoint-dir /tmp/m28-checkpoints
```