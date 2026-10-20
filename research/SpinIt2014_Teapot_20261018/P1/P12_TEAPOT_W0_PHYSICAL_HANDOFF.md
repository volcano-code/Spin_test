# W4 P12｜真实 Cherchi 材料的物理尺度与设计空间合同预验收（W0 签核前）

**实现分支仅为** \`research/neuralmoments-w4-teapot-p1-20261019\`，修改范围为 W4 P1 和单独授权的 W4 GitHub Actions 工作流。本里程碑不修改 W0/W2/main，不声称已运行 Spin-It Faster 优化。

## 真实输入及来源

全部输入是从原 GitHub Actions **run 39403411538**（成功）下的真实 Cherchi P9/P11 材料下载、逐字节重读，并以外部已存储 SHA 锁定；当前 P9 跨 runner 的重新构造曾失败，所以此项目明确采用归档真实材料做 **只读物理审计**，而非声称再生成了原生 P9。

| OBJ / 审计 | SHA256 |
|---|---|
| M 原始候选（P9 Cherchi，带 \`+0.005\` 把手移动） | \`154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4\` |
| F（真实 P11 Cherchi subtraction） | \`22593c5ab3b5f6ee786f2d17ce15f3beae16fcb09589dce2314d1615b3f115ba\` |
| D（P11 icosphere 试验区） | \`4cc61b54939fe9c9acdfe9e956af24f2a411d6016acd83fd32d46722749a99b9\` |
| P11 原生审计记录 | \`798ee3092487a4797a427e9a36dad11791f21835b897235c25f4b6518aee404f\` |

M/F/D 仅表示一份实际可重读的 **试验材料划分**；F/D 尚未经过 W0 的 Teapot 物理与可删域签核，也不等于作者原 CAD。模型原始几何为 Y-up。W4 提议的坐标映射是 \`(x,y,z)->(x,-z,y)\`（proper rotation），暂定旋转轴 \`+Z\`。**尚未定义实际轴尖/固定轴杆 CAD**，以前 MuJoCo 中的轴尖球只是虚拟接触替身。

## P12 仅作诊断的物理案例

\`p12_teapot_proposed_case.json\` 将**人为的** 15 cm 整体高度、1,240 kg/m³ 类 PLA 均匀实心密度和以前的 0.25 kg MuJoCo 演示质量明确列为假设，且所有 W0、打印与优化通过标志固定为 false。真实材料 M 的原始高度为 3.15 个单位，故比例 \`s=0.15/3.15=0.047619047619 m/单位\`。

从 M/F/D 的**真实保存网格**重新计算 W0 十项普通质量矩，按 \`m ∝ ρs³, L ∝ ρs⁴, Q ∝ ρs⁵\` 正确变换，并用 \`I0=tr(Q)E-Q\` 与平行轴定理得到完整惯量：

| 实体 | 若为该诊断实心材料的质量 (kg) | 质心高度 (m) |
|---|---:|---:|
| M | 3.460898891677 | 0.0596109643 |
| F | 3.393164097633 | 0.0595651752 |
| D | 0.067734794044 | 0.0619047619 |

数值重读质量矩最大原始单位残差 \`4.873879078104437e-14\`；SI 变换后最大加和残差 \`3.469446951953614e-16\`。该试验腔体移除质量约为 1.957%，质心降低约 **0.04579 mm**，并使暂定 Z 轴的中心惯量降低约 \`1.50806e-5 kg·m²\`。这些变化是**试验减法的客观效应，不是优化结果**。

**重大物理不一致：** 要让上述 M 在 15 cm 高度时仅重 0.25 kg，需要等效密度 \`89.5721 kg/m³\`，而不是实心类 PLA 的 1,240 kg/m³。对应质量差约 **13.84 倍**。因此以前 0.25 kg MuJoCo 视频不能与此诊断实例混用为同一个物理问题。更不能默认这份 Teapot 是可打印的 15 cm 实心 PLA 陀螺。

几何预检给出的腔体到外表面保守距离下界约 \`0.0380943 m\`（按暂定尺度），这**不是**整件模型的制造/局部薄壁强度认证，且没有真实轴尖/杆体约束。P12 的全部科学发布与优化权限仍然关闭。

## 可复现命令与验收

W4 checkout 中 \`P1=p12\` 不是实际目录；真实代码在 \`research/SpinIt2014_Teapot_20261018/P1/\`。

1. 从成功的 P11 GitHub Actions artifact \`12255852225\` 下载并展开源 M/F/D 及审计 JSON；核验四项 SHA。
2. 将上述文件放到独立 \`p12-real-input\` 文件夹，分别命名 \`P10_Cherchi_Original_Yup.obj\`、\`P11_F_Trial_Cherchi_Real_Subtraction.obj\`、\`P11_D_Trial_Interior_Sphere.obj\`、\`P11_real_Cherchi_subtraction_audit.json\`。
3. 运行 \`W4_P12_REAL_INPUT_DIR=/path/to/p12-real-input python -m unittest discover -v -s research/SpinIt2014_Teapot_20261018/P1 -p test_p12_physical_case.py\`。
4. 执行 \`python research/SpinIt2014_Teapot_20261018/P1/p12_physical_case.py --m <M.obj> --f <F.obj> --d <D.obj> --p11-report <P11.json> --case research/SpinIt2014_Teapot_20261018/P1/p12_teapot_proposed_case.json --output <new-report.json>\`。

本轮源码已在当前容器中对**真实原生归档 M/F/D**运行：**8/8 unittest PASS**，并生成 \`DIAGNOSTIC_PHYSICAL_CASE_ONLY\` 的 JSON 报告。另有单独的 GitHub Actions 轻量只读 P12 job 从确切历史 run 拉取源文件重新测试；CI 状态应以对应 GitHub Actions 实际完成记录为准。

## 致 W0 的必需签核问题（从不自行标记为 approved）

1. **量纲与材料**：最终 Teapot 的实体高度、实际密度、内外壁空腔/填充定义及预期总质量是什么？若以 250g 为目标，须先建立真实空心/填充材料模型，而不是将实心 PLA 密度改成 89.57 kg/m³ 后宣称是可打印实物。
2. **接触物理**：真正接触地面的轴尖和固定轴杆几何（OBJ/封闭实体），转轴方向、相对原始几何的精确刚体变换及 tip 的物理位置；virtual tip 不能直接升级。
3. **F/D 设计域**：固定材料 F 必须包括真实外壳、承力连接、轴杆和轴尖；可删域 D 满足指定最薄厚度、连通性和实物强度条件。当前内部单球只是一份布尔算法测试材料。
4. **Faster 求解接口**：冻结的单位法向/二次曲面 c（\`CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY\`）、保留符号、两倍交叉项映射、固定矩缓存、独立数值真值、每目标容差及终态 KKT/Newton 检查。未经 W0/W2 允许，不得假定平滑导数或训练有效。
5. **MuJoCo 公平比较**：前后必须由两份不同的真实材料 OBJ 提供各自质量与惯量、真实接触网格与相同外部条件，不可用任意修改惯性张量的反事实案例作为最终论文效果。

**下一项可执行工作：** 获得经 W0 审查的物理案例后在 W4 进一步生成封闭轴尖/支撑 F 与合法 D、运行 Cherchi 原生 subtract/intersection 并重新密封 r(M)=r(F)+r(D)；之后才进入三目标 Faster 优化。该文件是交接建议，并不代表 W0 已批准。
