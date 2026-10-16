# Noodles v6 · Cherchi C2 精度修复与完整静态设计域验证

**阶段性质：待用户审阅的实验成果；未在 GitHub 创建提交或推送。**

**结论**：C2a 的「有理网格转 binary64 时出现 24 组别名、48 个退化面」已经通过**精确等价局部重三角化**修复。修复后的完整设计域通过了真正的 Cherchi **intersection 和 difference**，且与完全相同 binary64 输入下独立运行的 CGAL 结果，精确有向表面链和 10 个质量矩均完全一致。**不能由此推导动态二次曲面来源/Jacobian/Newton/旋转仿真通过。**额外查出了 independently rounded `F,D,A` 无法保持严格表面链一致，需在后续 C3 显式处理。

## 1. 基线和真实来源

- 原 v6 精确几何：`/mnt/data/Spin_v6_stage3/p1-construction-01/*-rational.json`，为先前 84 次 CGAL 精确构造结果，未重新生成。
- `design-rational.json` 原始 SHA-256：`a7671c75a427e7c182dd5fcce2a4178dfce58dfce9dcf56c79cded11fc277efc`。
- 当前运行的 Cherchi C++ 模块 SHA-256：`e96e0ef827764f2d30cdf0ad9e4cc1cf990fd4e622bfd44c1eec27918aeefc0a`，坐标导出 profile 为 `GMP_CONSTRUCTION_OPERANDS_V1`。
- 本轮主扩展还是较旧的在线二进制检查点，未从最新 GitHub `a17ff49...` 全量重编译；这不得归作最新正式仓库生产版本验收。
- CGAL Epeck 精确布尔可执行文件 SHA-256：`d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3`。

## 2. 根因追踪：24 个簇全部可回溯

- `design`: 24 组不同 exact rational 顶点舍入后同一 binary64 坐标，共 48 个非零有理面积面舍入后退化。
- `fixed`: 12 组、24 个面；`initial`: 12 组、24 个面。
- 对完整 v6 `design` 的所有受影响 CGAL `birth_faces`，逐级追踪先前 80 次 union 的来源：**12 组是 `pin-fixed`/`outer-ellipsoid` 交界，12 组是 `pin-fixed`/`hub-fixed` 交界**，不是 79 根管束本身的问题。
- 最小被证实的顶点分离距离包括约 `1e-34` 与 `1e-18` 模型单位；直接改小/调大求解容差、焊点或删面均不是合法修复。
- 本次在 24 组中每组找到一个**在两个精确支撑平面上均处于直线边界中间**的冗余三角化顶点；另一个顶点是非共线材料拐点，保留。其几何依据记录在 `design-24-groups-source-provenance.json`、`design-alias-analysis.json`、`design-exact-retriangulation-proof.json`。

## 3. 实际精确重三角化

| 静态实体 | 原顶点/面 | 修复顶点/面 | binary64 别名组/零面积面 | 原/新精确有向表面链 |
|---|---:|---:|---:|---|
| `design` | 41384 / 83408 | **41360 / 83360** | **0 / 0** | **完全相等** |
| `fixed` | 46344 / 92692 | **46332 / 92668** | **0 / 0** | **完全相等** |
| `initial` | 16092 / 32180 | **16080 / 32156** | **0 / 0** | **完全相等** |

- 修复脚本**没有修改任何保留顶点的有理坐标**；每次只替换该顶点局部两组精确共面三角形，并用 exact ear-clipping 重新填充相同有向平面区域。
- 每次局部原/新补片的 10 个 Fraction 原始质量矩逐项相等；总共 24+12+12 个局部顶点操作通过。
- 使用项目现有的、独立于修复器的 `oriented_planar_chain_signature` 对完整原/新静态网格验算：三份均 **非零支撑平面 0、精确退化面 0**。其中完整 `design` 对比耗时约 **67.3 秒**。
- `design` 原始与修复后的每条无向边均恰有 2 个入射面、无非流形边，Euler 特征都为 **-320**。另外，*实际舍入后的设计域 double 网格*经原生 `audit_exact_triangle_boundary(OutwardPositive)` 审查：封闭、边/顶点流形、方向有效、无退化、完整自交检查完成且 **PASS**（约 85.3 秒）。
- 附带 `design-retessellated-static-face-provenance.json`：66 个最终新增补片面追踪到原始面集合，**不伪造单一原生 birth-face ID**。其动态二次曲面来源尚未验证。
- Python 回归 **8 passed**，包含原有理文件 SHA 锁定、再运行的输出字节一致、局部精确十矩复算、输入类型 guard、三模型实际数据等。

## 4. 完整 Cherchi 真实计算与 CGAL 独立交叉验证

测试均以修复后的 **41,360 顶点／83,360 面完整设计域**及经过 `float64` 转换的同一静态切割盒体为输入；CGAL 使用从 **实际 binary64 数值精确恢复的二进制有理数**，而不是拿原始更高精度坐标误作同一输入。

| 操作 | Cherchi 实际输出顶点/面 | Cherchi 调用 | CGAL 输出顶点/面 | 独立精确面链 | 10 个 Fraction 质量矩 |
|---|---|---:|---|---|---|
| `intersection` | **26212 / 52784** | 约 **1.2 s** | 26212 / 52784 | **相等，差异 0** | **10/10 完全相等** |
| `difference` | **17296 / 34912** | 约 **1.2 s** | 17296 / 34912 | **相等，差异 0** | **10/10 完全相等** |

- 实际保存了两次 Cherchi 完整精确坐标的 `.json.gz`，CGAL 独立输出和原始证明日志。
- 第一次交集质量矩验证的日志出现 `ValueError: Exceeds the limit (4300 digits)`：原因是测试报告把超大 Fraction 直接转十进制字符串。保留该失败日志，并从未改变的实际 Cherchi/CGAL 输出**重新运行质量矩计算，改用整数原始字节摘要**，最终 10/10 通过。
- 此处的 1.2 秒仅是**单次静态盒体布尔**的 Python→C++ 调用耗时，不是动态二次曲面、Jacobian、Newton 或整篇论文的求解速度。

## 5. 发现的另一项严格表示边界：独立 binary64 分区不是 exact-zero

在精确有理数域，先前通过了 `F+D=A`、`K+D=E` 和 `K+R=F`。重三角化已证明没有改变这些精确实体。然而**将修复后的 `F`、`D`、`A` 三份几何各自舍入为 double**，再作为精确二进制有理数计算，`F_double + D_double - A_double` 的有向面链**不为零**：非零支撑平面 **18,445**。

Python Fraction 对这些单独舍入网格独立重算了 10 个质量矩；十项严格都存在非零差异，但数量很小：

- 三者有向体积残差：约 **3.4728906554e-19 模型单位³**。
- 按 25 mm 单位和 1200 kg/m³ 换算的有向质量残差：约 **6.511669979e-21 kg**。
- 相对十矩误差约 `1e-19` 量级。

**不能因为误差很小，就把单独舍入的 `F,D,A` 判为精确分区相等**；质量矩的差分也不能代替局部集合对称差和缝隙的几何上界。因此，C3 接入时必须显式确立：精确有理几何作为静态权威、float64 作为 Cherchi 计算近似的边界，独立建立几何偏差／质量矩误差预算或协同共享三角化表示，禁止静默混用两种状态。

## 6. 当前状态与下一步

| 关卡 | 状态 |
|---|---|
| C2a 全部别名溯源与有理数无损重三角化 | **PASS（独立链和质量矩）** |
| C2a 设计域 binary64 原生合法性 | **PASS** |
| C2b 83,360 面 Cherchi 真实交集与差集 | **PASS（与 CGAL 精确集合及十矩一致）** |
| C2c 三份独立 double 网格精确分区 | **NOT PASS — 报告 18445 个不相消的平面** |
| C3 动态二次曲面真实来源、质量矩与 Jacobian | **NOT TESTED** |
| C4 Newton 合格终态；C5 最终面条；C6 旋转仿真 | **NOT TESTED** |

**立即建议的下一步**：先明确 C3 的 exact/static vs binary64/compute 数值契约，使用已导出的 `cherchi-static-input-01/noodles-v6-design-cherchi-f64.npz` 建立真实二次曲面运动测试；核对 Cherchi 返回的 LPI/TPI 等来源记录，逐状态比较质量矩、有限差分/高精度 Jacobian 和 CGAL 独立结果；固定材料只计一次。C3 未过前不启动长时 Newton；制造验收继续后置。

**备份与审批**：本轮尚未写入 `Spin_test` 和原 `Spin`。先提供 ZIP 和报告审阅；用户批准后才上传备份仓库。原正式仓库需另行明确批准。