# Heart H8 — 非对称初始CAD和设计域（2026-10-18）

## 已完成

从数学心形轮廓构建了非对称、倾斜且相对轴杆偏置的初始心形实体，独立导出 `heart_input.obj`（未加杆）、`shaft.obj`、`initial_top.obj`（并集）、`fixed_shell.obj`（外边界与反向内边界）、`design_domain.obj`，以及 `initial_top.glb`、`fixed_vs_design.glb`。

与旧版 0.72 整体缩小方案不同，设计域定义为三维心形场的等距偏置与轴杆避让区域交。三维点阵采用 marching cubes 形成离散网格；原始场属于 Lipschitz 约束数学函数，不等同于原论文 CAD、精确体布尔或任意形状 OBJ 的通用偏移算法。

- 默认网格 pitch=0.028 model units（每单位 25 mm）；初始完整实体 15,646 顶点、31,288 三角面；设计域 13,122 顶点、26,244 面；初始质量按假设密度 1187 kg/m³ 估计为 37.7494 g；质心偏轴 6.1043 mm。
- 独立审计基于所有三角面的外接球半径与质心最近邻，得到固定外边界和设计域表面间欧氏距离的**严格保守下界** 0.8832 mm（对连续三角面几何而非仅离散网格顶点）。这个宽松下界满足先前登记的 0.375 mm 验收门槛，但**不等于已认证设计壁厚 2.4 mm**。没有进行全部表面自交原生精确审计。
- 分辨率 pitch=0.018 的复核：质心偏轴 6.1038 mm，距离下界 1.4329 mm；高分辨率完整实体 37,900 顶点、75,796 面。
- F 的内边界严格使用 D 面片反向，离散分区面链零差异，独立体积/一阶矩验证通过。所有单件与初始完整实体 OBJ 均可读、闭合、方向一致；F 的两层封闭表面是预期中的两个表面分量。
- 源代码 `source/build_heart_h8.py`、独立审计 `source/audit_h8.py`、7 项 pytest 测试 `tests/test_h8_cad.py` 已在本地环境验证 7/7 PASS。

## 不可宣称的内容

这不是作者 CAD 的等比例重建，也没有量化与论文 Figure 1 的几何相似度。尚未运行 H8 的真实动态 Cherchi Boolean、10x10 Jacobian、Faster Newton、收敛模型导出、MuJoCo 自由接触或打印。静态 F/D 面链与浮点网格审计不代表原生精确有理几何证明。原始正式 Heart eval60 仍缺 SHA 匹配的历史配置/事件文件。现有旧 H7 云端原生构建在 Boost 静态库非 PIC 链接时报错，另待修正。无数据支持心形最终旋转性能。

## 复现

要求 Python 3.13，numpy 2.3.5、scipy 1.17.0、shapely 2.1.2、trimesh 4.11.1、scikit-image 0.26.0、pytest 9.0.2（实测版本，依赖兼容版本可能亦可）。

```bash
python source/build_heart_h8.py --output /tmp/heart-h8-build --pitch 0.028
python source/audit_h8.py --output /tmp/heart-h8-build
python -m pytest -q tests
```

务必以 `H8_CAD_AUDIT.json`、`H8_INDEPENDENT_AUDIT.json`、原始 OBJ 和 SHA256 重新核验，不要将 GLB 预览当作模型验证。