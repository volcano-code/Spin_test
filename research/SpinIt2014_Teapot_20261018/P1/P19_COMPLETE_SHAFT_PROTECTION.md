# W4 P19：完整原轴杆保护通过，保存后材料分区与原生复现完成

## 本阶段结果

**已得到新的、未经后处理的真实 Cherchi M/F/D 候选。对保存后的 binary64 几何，完整原始轴杆 S 属于固定材料 F，S 与可删域 D 有预登记的严格正间隙，且 M=F∪D、F/D 无正体积交叠。**

机器状态为 `P19_EXACT_SAVED_SOLID_AND_COMPLETE_ORIGINAL_SHAFT_PASS_NOT_ADMITTED`。
这一状态完成 P18 明确留下的保存后轴杆保护门；W0 原生 material-region 合同、Teapot 教师、导数准入、优化和同条件优化前后物理对照仍未完成。

主证据：

- [完整可重算报告](P19_COMPLETE_MATERIAL_REPORT.json)
- [冻结材料包](P19_material_case/manifest.json)
- [137 项真实本地测试](P19_LOCAL_TEST_RECEIPT.txt)；[完整报告重播](P19_LOCAL_REPORT_REPLAY.txt)
- [旧 M 的完整轴杆反例](P19_OLD_OUTER_SHAFT_COUNTEREXAMPLE.json)
- [研究、失败及真实调用索引](P19_EVIDENCE_INDEX.json)
- [全部构造研究与失败原件](P19_CONSTRUCTION_STUDY.zip)；[真实构建、解析实验和原生重建证据](P19_NATIVE_EXECUTION_EVIDENCE.zip)
- [W0/W2 具体交接](P19_W0_W2_HANDOFF.md)

冻结 manifest SHA256：`c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6`。
完整报告 SHA256：`62212e828e6c9a021bca8085bfa85a4c20f5d1a3607e978aa264dbaceebc7b6b`。
源 P18 提交：[b33fc93bd1fecd5b42fbd8d2eabfefd6ec9db7be](https://github.com/volcano-code/Spin_test/commit/b33fc93bd1fecd5b42fbd8d2eabfefd6ec9db7be)。

## 1. P18 之外又发现了一个真实问题

P18 已证明旧 D 侵入完整原轴杆。本轮进一步检查了原始 M：即使原轴的全部 258 个顶点都保留在 M 中，M 也没有完整包含 S。

完整精确审计检查 M 的 7558 张面与 S 的 512 个星形四面体。
3,869,696 个组合中有 23,794 个闭 AABB 候选；逐一有理裁剪后，433 个面/四面体组合、314 张不同 M 面具有 S 的严格内部点。
另有 75 个旧 M 顶点严格进入原轴内部。
这些事实结合 M 的嵌入闭合曲面证书，证明 `S \ M` 有正体积。

因此，只修改 D 无法补齐完整固定材料保护；旧 M 也必须重新构造。
原来的 M、F、D 和全部 P18 失败证据均保持原样。

## 2. 最终候选怎样生成

固定原版源码为 [Cherchi reference commit 7bd6c2697695f555f9a15d7e154e084d841316f0](https://github.com/gcherchi/InteractiveAndRobustMeshBooleans/tree/7bd6c2697695f555f9a15d7e154e084d841316f0)。
直接编译原 `main.cpp`；没有 CGAL 替代、APAP 补丁、焊接、自动修复或保存后重新编号。
本地原版编译单 worker，68.392 秒，最大 RSS 924980 KiB。
可执行文件 SHA256 为 `dfd285727c760b2616e6c8628614b9ee57980f1402950e020d854f878c7c8e5c`。

实际三项调用如下。这是原生操作记录；保存输出与原生隐式有理集合的严格等同性仍未认证。

| 输出 | 真实 Cherchi 调用 | 操作数 |
|---|---|---|
| M | `union(B,E)` | P13 的冻结壶体 B 与新的完整轴杆外包络 E |
| D | `subtraction(C,G)` | P17 的冻结 cavity 假设 C 与精确 dyadic 内保护体 G |
| F | `subtraction(M,D)` | 本轮实际生成的 M 与 D |

B 是 P13 已登记的公共 Teapot 重构壶体，SHA 为 `46774afb1eaf4c7687c694493becfd96babe77b7c54748cfc03b3e9b75dec61c`。
它继承此前已披露的 P9 手柄几何偏移及 P13 参考坐标变换；没有被重新标记为作者原始 CAD。

E 使用完整原轴杆的原面索引，XY 径向比例为 `9/8`，旋转显示角为 7°。
执行的严格规则绑定 cosine/sine 的 binary64 十六进制值：`0x1.fc2f025a23e8bp-1`、`0x1.f32d44c4f62d3p-4`。
把原 binary64 坐标视作精确有理数进行 XY 仿射计算，再对每个输出坐标舍入一次为 binary64。
所有 Z 坐标完全不变，原尖端仍为 `(0,0,0)`，轴向仍为 `+Z`，原顶部仍是保存值 `binary64(1.71)`。
原始 S 文件从未被替换成更细的轴心柱或外包络 E。

G 的精确参数是：

```text
x,y ∈ [-1/16,+1/16]
z   ∈ [3/8,1]
预登记完整 S 到 D 的最小间隙：1/500 reference unit
```

最终原生保存材料：

| 材料 | 顶点 | 三角面 | SHA256 |
|---|---:|---:|---|
| M | 4035 | 8070 | `0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704` |
| F | 4235 | 8470 | `5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8` |
| D | 200 | 400 | `d64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073` |
| 原始 S | 258 | 512 | `65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0` |

最终包的 manifest 由程序内独立固定的 SHA 认证，并检查完整文件集合、实际内容、三份 native receipt 和原始轴身份。包内自洽改写 manifest 不能替换它。

## 3. 保存后实体证明具体通过了什么

### 3.1 曲面嵌入与分区

复用 P18 的整数/有理判定，对所有闭 AABB 候选检查精确三角交集，包括相邻面；相邻候选跳过数为 0。

| 材料 | 全部 AABB 候选 | 非法交集 | 边界组件 |
|---|---:|---:|---:|
| M | 60,905 | 0 | 1 |
| F | 63,923 | 0 | 2 |
| D | 3,018 | 0 | 1 |
| 原始 S | 4,283 | 0 | 1 |

M/D 各有一个紧致、闭合、嵌入且外向的边界组件；这里允许非零亏格。
精确射线确认 `C=(0,0,binary64(.67))` 在 M 内。
C 到全部 8070 张 M 面的最小距离下界大于包围全部 D 的凸球半径上界：

```text
distance(C, boundary M) >= 0.523947105
enclosing radius(D,C)   <= 0.200000002
distance(D,boundary M)  >= 323947103/1000000000
                        = 0.323947103 reference unit
```

所以整个 D 严格包含于 M。按 `.025 m/reference unit` 提案，最后一个间距下界约为 **8.098677575 mm**。
F 的两组组件逐面精确等于 `+M` 与 `-D`，无隐藏的正反重复面抵消；独立精确十矩全部满足 `r(M)-r(F)-r(D)=0`。
完整证明得到 `M=F∪D`、`int(F)∩int(D)=∅`。十矩等式不是单独的实体依据。

### 3.2 完整 S 包含于 M

在固定核点 `(0,0,1/64)` 下，把原始 S 分成 512 个精确星形四面体。
M 的 8070 张面与这些四面体共有 4,131,840 个组合，17,060 个闭 AABB 候选全部接受精确裁剪。
结果为 **0 个**具有严格 S 内部点的组合。
内部四面体接缝不被跳过；共享的真正 S 外边界允许接触。
结合核点在 M 内，证明整个闭原始 S（含两端和全部边界）属于 M。

### 3.3 完整 S 与整个 D 的距离

对 D 的全部三角形求 XY 最小半径，利用柱内一个精确 `OUTSIDE` 锚点和边界分离，排除整个轴心开柱进入 D 实体；对 S 的全部顶点求最大半径，其凸柱包络包含完整 S。
有理平方根界给出：

```text
r_D lower >= 62499999999/10^12
r_S upper <= 60000000001/10^12
distance(S,D) >= 1249999999/500000000000
              = 0.002499999998 reference unit
              > 1/500
```

按尺度提案约为 **0.06249999995 mm**，超过预登记的 **0.05 mm**。
这是整个保存实体 S 与 D 的欧氏距离下界，涵盖 S 的全长，不只是有限采样或缩小轴心。

最后由已证明的分区、`S⊆M` 和 `distance(S,D)>0`，得到 **`S⊆F`**。
局部 gap 子证书没有单独评价 F；最终完整包含结论以顶层 `complete_original_shaft_in_fixed=true` 为准。

## 4. 几何改动的代价与物理提案

继续使用 P17 的同一提案：`.025 m/reference unit`、均匀密度 `1200 kg/m³`、已转换的 Z-up 参考框架，不重复执行 P13 的缩放或旋转。

| 材料 | P18 提案质量（g） | P19 提案质量（g） | 变化 |
|---|---:|---:|---:|
| 完整 M | 31.097634683 | 31.118997337 | +0.021362654 g；+0.0686954% |
| 固定 F | 30.571975493 | 30.623879229 | +0.051903737 g；+0.1697755% |
| 可删 D | 0.525659190 | 0.495118108 | −0.030541083 g；−5.8100540% |

原 S 的提案质量为约 0.345228763 g，已经包含在 F 中，不能再与 M 或 F 相加。
完整 M 的质心高度由约 16.307401082 mm 变为 16.317786547 mm。
整体包围盒保持约 `64.29 × 40 × 42.75 mm`。
报告保存全部精确十矩、SI 矩、完整惯量张量与主惯量；只有 LAPACK 主惯量显示值的跨 runner 重播允许既有 P17 的 `1e-12` 相对差异，几何、精确矩、完整张量和批准标志严格比较。

E 的径向上界约 0.067500000001 reference unit；对应顶点的最大位移上界为 0.010799359783 reference unit（尺度提案下约 0.269984 mm）。
这个对应顶点位移界不是整个 M 的 Hausdorff 距离，也不是原生隐式点误差界。
原尖端坐标保持并不认证物理接触曲率、打印效果或结构强度。
本轮改动服务于保护约束，惯量优化、降低质心和减质量三项消融均未执行。

## 5. 被拒绝与未选用的路径完整保留

| 路径 | 实测结果 | 处置 |
|---|---|---|
| 在旧 M 上加两个局部 dyadic collar | 136 条边关联错误，非流形 | 拒绝；未生成 F |
| 在旧 M 上加完整 `257/256` 同心外包络 | 原生输出 2 张精确零面积面；14 对显式塌缩后仍有 21 对非法交集 | 拒绝，原件和两种序列化均保留 |
| 旧 M + 三个预登记径向/旋转外包络 | 非法交集分别 18、5、12 对 | 全部拒绝 |
| APAP 导出器两个独立对照 | 非法交集 4、18 对 | 全部拒绝；明确 patched provenance |
| 早期壶体直接重建、Z 仍有轻微外扩 | M/F 曲面及完整轴包含通过，但尖端发生 `−1/16384` 位移 | 未选用；改为 Z 完全保持版本 |
| 最终保持 tip/Z 的直接重建 | 曲面、分区、完整轴和正间隙均通过 | 冻结为本候选 |
| 第一次严格 byte-equal 原生重建 | M 文件哈希不同，顶点与定向三角多重集精确一致 | 原字节门拒绝保留；另登记精确几何复现协议 |

APAP 仅在原固定 Cherchi 的两个最终导出调用上加 `true`，完整 patch SHA 为 `de6300e25eea6ec84808c7a45c78f6288c92c266f9715dd688529c681ee87b84`。
它仍输出 double，不能由“更精细”推导拓扑正确；最终候选没有使用该补丁。
显式微塌缩也未用于最终候选，其精确十矩确实变化，未声称与原生输出实体相等。

## 6. 真实原生复现与测试

原生并行实现的输出索引顺序会变化。
后续另行预登记的比较协议要求：精确 binary64 有理顶点 **Counter** 相同，带方向的三角形 **Counter** 相同；不能正反抵消，不能坐标近似，不能焊接、重三角化或覆盖原件。
每份实际输出继续保留独立 SHA，并按自己的 SHA 完整重做几何证明。

本地成功重建执行了新的 M/D/F 三次原版调用，三个输出的 raw SHA 均与冻结文件不同，但精确顶点和定向面多重集全部相同，新的全材料审计再次通过。
因此 `same_frozen_material_output_bytes=false` 被如实保留。

实际本地调用总计 **22** 次：

- Teapot 构造研究 12 次（其中 2 次 APAP 对照）；
- 首次 byte-strict 复现 1 次；成功精确几何复现 3 次；
- 初次及可移植解析盒实验各 3 次，共 6 次。

其中最终材料的创建涉及 3 次原版调用。所有 Teapot 原生调用串行执行。
解析实验覆盖 `A=[0,2]^3`、`B=[1,3]^3` 的 union/intersection/subtraction，体积分别 15/1/7；每轮全部 30 个十矩精确相等。
这些解析实验不替代 Teapot 的完整审计。

完整本地测试 **137/137 通过，52.975 秒，0 failures、0 errors、0 skips**。
包括旧 M 的真实反例、新包的完整正例、内部星形接缝、相邻面穿透、原轴替换拒绝、缺失轴端、间隙不足、链与矩相等但区域错误、原生来源/receipt 变化，以及极小坐标改动的拒绝。
mock 的测试调用没有计入上述真实 native 次数。

新增独立 CI job：`p19-positive-gap-complete-material`。
原有 workflow 的 47432 字节完整保留为前缀，旧 P13/P14 作业未被绕过或改成成功。
新 job 必须执行 137 项且禁止跳过、重算冻结报告、真实构建原版 Cherchi、3 个解析操作、3 个 Teapot 操作以及新输出的完整几何证明。
本提交文件只登记 CI 验收要求；实际 run ID、日志与结论以提交后的 Actions 观察为准，不预先声称绿色。

## 7. 复现命令

```bash
python -m pip install numpy==2.3.5 scipy==1.17.0 trimesh==4.12.2 networkx==3.7
P1=research/SpinIt2014_Teapot_20261018/P1
export W4_P19_CASE_ROOT="$PWD/$P1/P17_material_case"
export W4_P19_FINAL_CASE_ROOT="$PWD/$P1/P19_material_case"
python -m unittest discover -v -s "$P1" -p 'test_p19*.py'

python "$P1/p19_material_candidate.py" audit --packet "$P1/P19_material_case" \
  --report /new/path/p19-proof.json
python "$P1/p19_material_candidate.py" verify --packet "$P1/P19_material_case" \
  --report "$P1/P19_COMPLETE_MATERIAL_REPORT.json"

python "$P1/p19_native_smoke.py" --native-bin /path/w4_cherchi_reference_native \
  --upstream-checkout /path/pinned-cherchi --mode unmodified --out /new/path/boxes
python "$P1/p19_material_candidate.py" rebuild --packet "$P1/P19_material_case" \
  --native-bin /path/w4_cherchi_reference_native --upstream-checkout /path/pinned-cherchi \
  --out /new/path/teapot-rebuild
```

所有输出目录和正式报告要求新建。成功的几何报告退出 0，几何拒绝为 2；错误身份、字节变化、伪造报告或复现不一致会硬失败。

## 8. 下一门已具备具体输入

将此冻结包与物理提案接入真实 `InProcessCherchiEvaluator` 的 owned material regions，锁定系数所在坐标框架、实际归一化矩阵、密度及同一次调用的源身份，执行 W0 M6 的完整 native material partition。
随后才是这个 Teapot 的真实 r/J 与导数合同、图9三个目标消融、收敛终点审计，以及同条件优化前后 MuJoCo 对照。

本轮没有修改 W0/W2 分支、替其他窗口签发批准、生成优化终点或训练数据。
