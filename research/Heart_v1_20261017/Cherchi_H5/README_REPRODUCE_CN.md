# Heart H5 — Cherchi 精确保留材料的收敛后 OBJ 独立导出

**适用范围：**已通过 Cherchi 精确布尔获得的材料输出，**只在求解器之外导出**；不能改变 Newton 内部的几何求值、来源导数、质量矩、科学事件或缓存。本目录用 H1 冻结的**历史 V4 代理 Heart**完成了真实原生审核，不能当成论文作者 CAD、完整心形终态或已完成的正式 `eval60`。

## 路线与输入

1. 只接受 Cherchi 原生输出，不提供 CGAL、trimesh 或其他布尔后端的求值回退。原生 `_make_it_stand` 只用于**独立几何验收**；需要显式指定已核验的模块 SHA-256。
2. 精确有理坐标始终是材料权威数据；浮点坐标必须与有理坐标的 binary64 显示值逐位相符，不允许人为平移、合并、删除三角形。
3. 从精确凸共面四边形选择不冲突的换边。每一步检查相同支撑平面、有向边界、十项原始有理质量矩；每轮浮点自交必须严格下降，否则拒绝。
4. 以独立全局精确支撑平面有向链比较、变化面片的十项有理质量矩差值以及原生 exact-rational / binary64 审核作为最终验收。对**完全没有改变**的面片，前后完整积分中的对应项严格抵消，因而只对全部变化面片积分就足以证明**全局**十项质量矩完全不变；这是精确的代数消元，不是数值近似。
5. 仅成功时原子替换生成 `retained-target-normalized.obj`。任何异常将清理临时 OBJ，写入 `rejected.json`，不颁发合格证书。

## 运行 H1 代理案例（已通过）

在仓库根目录：

```bash
export H5=research/Heart_v1_20261017/Cherchi_H5
export H1=research/Heart_v1_20261017/Cherchi_H1
export PYTHONPATH="$PWD/$H5/source:$PYTHONPATH"
export NATIVE_SHA="$(sha256sum /path/to/_make_it_stand*.so | awk '{print $1}')"
python "$H5/source/cherchi_obj_export.py" \
  --h1-proxy-packet "$H1/output_proxy_v1/cherchi-authoritative-exact.json" \
  --expected-native-sha256 "$NATIVE_SHA" \
  --output /tmp/heart_h5_proxy_01
python -m pytest -q "$H5/tests"
```

注意：这个例子的合格原生模块身份在 `evidence/native-and-material-manifest.json` 中；换成不同版本的模块时必须重新实测，不能自动继承通过结论。已封存的 H5 模型位于 `output/h1_optimized/`，只包含**可优化的保留材料，不包含固定外壳或旋转轴杆**。

## 尝试从真实收敛的 Cherchi/Faster 运行导出（尚未做真案例验收）

```bash
python "$H5/source/cherchi_obj_export.py" \
  --formal-run /path/to/accepted_cherchi_newton_run \
  --expected-native-sha256 "$NATIVE_SHA" \
  --output /tmp/heart_h5_formal_01
```

正式导出必须先核对：`result.json`、`complete.json`、`record-verification.json`、`native-result.json`、`configuration.json`、`terminal-material-reference.json`、已接受的 `evaluation-000xxx.json`；核验真实 `CONVERGED`、原生事件有更新、同一次 Cherchi 后端、最新终态系数、材料哈希和已完成补集封存。原始正式 Heart 的这些冻结运行附件还未恢复，因此**本次没有运行真实 Heart 全流程导出**。本工具不会自行优化、补做布尔、猜测缺失状态或伪造这些文件。

**坐标系约束：**输出仅为 `TARGET_NORMALIZED` 的保留设计域材料，不是毫米坐标、完整心形外壳与轴杆装配或可打印实体。物理空间转换、完整组件集合验证、Jacobian、正式 Newton 和动力学另设验收门。
