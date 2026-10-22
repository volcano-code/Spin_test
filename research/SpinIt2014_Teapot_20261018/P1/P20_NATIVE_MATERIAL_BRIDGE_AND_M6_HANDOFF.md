# P20：P19 Teapot 原生材料接入与正式 M6 交接

## 本关结果与边界

P20 已在实际编译的原生核心上，把 P19 冻结的 M、F、D 建成不可变材料对象，并通过 **M = F ∪ D、正体积内域不交、没有遗漏或多余材料** 的原生集合分区检查。实际准备过程耗时 93.512698 秒，worker 最大 RSS 为 419176 KiB；执行前后 33 个源码/测试文件及 3 个 ELF 的字节完全一致。

这完成了进入正式 M6 前的材料与求值器准备。正式 M6 尚未执行：当前物理 RAM 为 9.7336616516 GiB，容器有效上限为 8 GiB，swap 为 0。正式入口要求物理与有效内存均至少 20 GiB，按约定使用名义 24 GiB / swap0 主机。因此其真实预检在启动 worker、导入 factory、调用原生求值器之前拒绝运行。原生材料准备检查没有降低正式入口的资源门槛。

W0 owner、物理案例、W2 teacher/training、导数邻域、优化终点与 MuJoCo 优化前后比较的准入均保持 false。P20 没有完成最初的论文 Teapot 优化/物理复现目标。

## 已实际完成什么

| 项目 | 实际结果 | 证据 |
|---|---|---|
| 固定 native core 构建 | 103/103，exit0，1052.965872 s | `P20_NATIVE_BUILD_SUMMARY.json`、构建证据 ZIP |
| 原版 Cherchi 两扩展构建 | 36/36，exit0，62.079613 s | 同上；原始 Cherchi commit 固定 |
| 三模块共同导入 | 实际 ELF 路径、SHA、API 与关键动态库已核对 | ZIP 内 import-only 报告 |
| P19 M/F/D 原生对象 | 三个实际 `MeshSnapshot` 与 `ExactMaterialRegion` | `P20_OWNED_MATERIAL_PREPARATION.json` |
| M = F + D | 完整原生集合分区通过 | 报告中的 `native_M_equals_F_plus_D_partition` |
| 原始输入保留 | 每个坐标、面索引、exact rational boundary 均匹配冻结 OBJ | 报告中的三个 native regions |
| 独立矩核对 | 从真实几何重新作 Fraction 四面体积分，30 个分量匹配 P19；10 个 M−F−D 残差精确为零 | 同上；沿用已冻结 P16 积分实现 |
| 参考、目标、SI 坐标合同 | 完整十矩精确往返、COM、完整惯量张量与 P19 提案一致 | `P20_EXACT_FRAME_AND_PHYSICS_REPORT.json` |
| 原生 factory | 返回真实 problem、真实 Cherchi evaluator 与新 unit c；source/boolean/integration/derivative 计数全部 0 | 原生准备报告与 `P20_NATIVE_SIX_PINS.json` |
| 本关回归 | 74/74，0 skip | `P20_TEST_INVENTORY.json`、`P20_LOCAL_TEST_RECEIPT.txt` |
| W0 源码与启动输入 | 1892 个 W0 源码、47 个 factory Python/config、6 个材料输入及 3 个 ELF 真实字节核对通过 | `P20_W0_SOURCE_BINDING_REPORT.json`；只读，不调用 factory |
| 正式 M6 | 在输入路径齐备时实际执行 CLI，exit3 资源拒绝，未执行 M6 | `P20_FORMAL_M6_READY_INPUT_RESOURCE_VETO.json`、`P20_FORMAL_M6_CLI_EXECUTION.json` |

构建和准备严格串行，编译为单 worker；实际编译子进程地址空间限额 6 GiB，准备 worker 地址空间限额 6 GiB、最长 900 秒。这里的 6 GiB 限制只约束这次有限的准备任务。正式 M6 的 20 GiB 最低资源门槛与最多 3600 秒时限保持独立。

核心构建有效最大单进程 RSS 为 2602917888 bytes，Cherchi 为 1247285248 bytes。原始构建记录中的一个 PID namespace 错配采样已在摘要与 ZIP 的 `resource-validation.json` 标为 `NOT_VALID`，不用于任何资源结论。

## 几何与质量身份

| 角色 | 冻结输入 | 顶点 / 面 | 本关解释 |
|---|---|---:|---|
| M | `P19_material_case/material/M_native.obj` | 4035 / 8070 | 原始完整材料域 |
| F | `P19_material_case/material/F_native.obj` | 4235 / 8470 | 固定保留材料；直接读取冻结 F，没有用新算的 M−D 替代 |
| D | `P19_material_case/material/D_native.obj` | 200 / 400 | 可变设计域 |
| S | `P19_material_case/source/shaft-reference.obj` | 258 / 512 | 完整原始轴；已包含在 F 内，不能再次计入质量 |

P19 的材料构造仍来自固定原版 Cherchi。P20 调用的是既有原生 CGAL Nef **独立集合检查器**，没有用 CGAL 布尔构造替换 Cherchi。当前证明的对象是冻结 binary64 OBJ 所表示的精确有理多面体集合；它不自动证明这些序列化边界与更早的未舍入 Cherchi 隐式构造完全相同，也不证明其为原论文作者 CAD。

本次原生分区 digest：

```text
81ca886b90fbc9d93529374d83fbee5fd672fdc95114d6907a2a5883ca8a5866
```

完整事实包括 `union_equals_whole=true`、`no_positive_volume_overlap=true`、`part_subset_whole=[true,true]`、`missing_whole_content=false`、`excess_union_content=false`，并绑定 whole M 和有序 parts [F,D] 的实际原生 digest。十矩相等仅作为独立补充，不代替集合分区证明。

## 单位、坐标与候选系数

原 OBJ 保持 reference 坐标，F、D 的模型密度均为 1。外部物理提案采用：

\[
s=\mathrm{exactBinary64}(0.025)
=\frac{3602879701896397}{144115188075855872},\qquad
1\,m_{ref}=1200s^3\,\mathrm{kg}.
\]

次数为 d 的原始矩换算到 SI 时乘以 \(1200s^{3+d}\)，其中质量 d=0、一阶矩 d=1、二阶矩 d=2。没有把已舍入的 `1200*s**3` 再当作原生密度，也没有对原网格先缩放再二次转换。P19 的材料密度与尺度是提案参数，并非实测打印材料证书。

实际 core normalization 为 L=2.5716、R=1，target axes=I。M6 的 original frame 指 P19 reference 单位，`length_original_per_normalized` 必须是 L，不能写成 SI 比例 s。requested tip 保持 (0,0,0)；实际 binary64 归一化和逆变换导致 represented tip 约为 (-3.2822079856e-18,0,4.0519317046e-17) reference，报告保存了其精确分数，没有移动原几何来消除该舍入事实。

原生系数顺序为 `[a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy]`，后三项在多项式中分别乘 2yz、2xz、2xy。raw10 的交叉矩仍是普通、未加倍的 QYZ、QXZ、QXY。

P20 新登记的单点探针为：

\[
q_{ref}(x,y,z)=x^2+y^2+(z-43/64)^2-(1/8)^2.
\]

它不是优化终点。登记完整记录了 reference 精确系数、实际 frame 变换、binary64 投影、显式正范数以及最后的 unit c。正比例系数并不等于相同 J 身份；正式评价必须在登记的实际 c 上重新产生同次 J，不能复用其他尺度的导数。

两侧锚点 (3/32,0,43/64) 与 (3/16,0,43/64) 对固定 D 的精确成员测试均为严格内部，且在原多项式及登记 c 下保持相反符号。这只说明解析多项式两侧在 D 中非空，尚未证明 native 三角源的实际切割分区。

实际 c SHA-256：

```text
57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca
```

新请求登记的最小外壁探针为 1/32 reference，SI 显示约 0.78125 mm。登记这个参数不等于已执行整物体墙厚、打印性或强度验收。

原生 `_prepare` 会对已舍入的 normalized F 积分，再进行 binary64 target 变换。本次 evaluator 固定矩与“原 F 精确仿射所得矩”的最大绝对差为 1.7754528434353378e-16。完整逐分量精确差保存在原生准备报告中，没有把这个浮点结果称为精确相同。

## W0 启动器问题与本关修复范围

固定 W0 为 `51cbfd33d08063404d7e0c40e4256dd0e38efa1a`。其 `live_native_m6_cli.py` Git blob 为 `45cea486061e88741bf29ada1b45da40a090a54d`。

该 CLI 的 worker 在 `report.update(result)` 时，会把外层 `W0_M6_NATIVE_FULL_PARTITION_RUNTIME_V1` 覆盖为内层 `W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1`；父进程仍只接受前者，因此即便内层几何成功也会进入 `NATIVE_WORKER_NO_VERIFIABLE_FULL_PARTITION`。

本关没有改 W0。新增 `p20_m6_launch.py` 调用固定 W0 的公开 `audit_native_full_partition_once`，保留独立的 W4 runtime/worker envelope，并把完整原版 W0 evidence 嵌套保存。回归测试覆盖该 schema 冲突、资源不足、six-pins 错误、源码与输入漂移、旧 bytecode、错误准入、超时和禁止覆盖旧报告。正例 fixture 全部标记 TEST_ONLY，不是 native 收据。

正式 launcher 还要求：固定 W0 HEAD 的所有源码后缀文件与 CMakeLists 实体化且与 Git blob 相同；factory 及其 Python 依赖、请求、manifest、canonical report、M/F/D/S 在运行前后不变；实际加载 native/bridge/adapter 文件、真实 c、problem 与 context 绑定六个外部摘要。它不能由普通 JSON 的 PASS 字段代替真实原生对象。

## 下一次正式 M6 的可执行入口

当前真实六项身份保存在 `P20_NATIVE_SIX_PINS.json`，文件 SHA 为：

```text
d067726f7e1b25489087f6577a6f37e8ea148ae9ae58d1b69c4cda05ac06eb96
```

当前 factory 文件 SHA：

```text
34c401592747d6397e958eaff85fed90561d1adc3b06d2561eec2f54bbebd06f
```

它们绑定本次实际构建的 ELF。换机器重新编译后，应先用实际准备入口生成该构建自己的新 pins，并在正式评价前另行冻结；不能把本次本地 binary SHA 填给不同的 CI 或重编译产物。自登记的摘要只提供字节绑定，不能冒充独立运行时认证或 owner 批准。

先在名义 24 GiB / swap0、物理与有效内存均至少 20 GiB 的主机准备固定 W0 source checkout。可使用完整 checkout，或包含所有源码后缀文件及 CMakeLists 的 sparse checkout，无需历史网格资产。Python 原生扩展必须具备完整 Faster support；仅有材料 checker 的最小模块不够。还必须采用实际 build summary 的运行环境，包括动态库搜索路径；本次临时 sysroot 的 LD_LIBRARY_PATH 已记录在构建摘要中。

```bash
: "${P20_P1:?P20 P1 directory}"
: "${P20_W0_CHECKOUT:?W0 source checkout at 51cbfd33d08063404d7e0c40e4256dd0e38efa1a}"
: "${P20_CORE_PYTHON:?Directory of the actual _make_it_stand ELF}"
: "${P20_CHERCHI_PYTHON:?Directory of both actual Cherchi ELF modules}"
: "${P20_PINS_FILE:?Actual externally frozen six-pin JSON file}"
: "${P20_PINS_EXTERNAL_SHA256:?Independently registered pre-run pins-file SHA}"
: "${P20_FACTORY_EXTERNAL_SHA256:?Independently registered pre-run factory SHA}"
: "${P20_NEW_REPORT:?New output JSON path; must not exist}"

python "$P20_P1/p20_m6_launch.py" \
  --w0-checkout "$P20_W0_CHECKOUT" \
  --factory-file "$P20_P1/p20_native_factory.py" \
  --factory-function prepare_one \
  --pins "$P20_PINS_FILE" \
  --external-pins-sha256 "$P20_PINS_EXTERNAL_SHA256" \
  --external-factory-sha256 "$P20_FACTORY_EXTERNAL_SHA256" \
  --python-path "$P20_CORE_PYTHON" \
  --python-path "$P20_CHERCHI_PYTHON" \
  --output "$P20_NEW_REPORT"
```

若需重新构建，`p20_build_native_ci.py` 接受独立、互不嵌套的 `--source-checkout`、`--build-root`、`--evidence`，core source 必须固定在 `58fd12c1306c1c01679a19172e276eef0cb30542`。完整 Ubuntu 24.04 依赖与命令已放入新增 CI 作业 `p20-native-owned-material-preparation`。

## 正式 M6 之后仍须完成的研究工作

1. 在上述合规主机上取得真实 M6 收据：一次实际 source generation、同一个保存 source 的两次 Cherchi 布尔、D=R+C 与 M=F+R+C 的原生分区，完整十矩交叉核对及同次 10×10 Jc 身份。当前 P20 只完成这三组分区中的初始 M=F+D。
2. 分别取得 W0 对物理 tip、F/D 案例与所有者采用的实际确认。原生几何通过不会自动生成这些确认。
3. 完成 W2 所需的导数可信邻域、分支与 teacher 数据准入。点上的 derivative_defined 或单次 J 都不能代替邻域证明。
4. 才能运行原定 Teapot 优化，完成图 9 对应的惯量、降低质心、减质量三目标消融，并核验各真实优化结果的质量、COM、完整惯量张量与约束；随后交付相同初始条件下真实优化前后的 MuJoCo 视频及对应比较证据，并完成原定物理验证。单次综合优化或仅有数值对比均不足以完成原研究目标。

提交只新增 W4 P1 文件，并在原工作流末尾追加 P20 job。P19 网格、既有报告和历史失败证据保留；W0、W2 和其他分支未修改。新 CI job 不依赖历史失败 job，也不会把旧的失败记录变成成功。

本地来源记录另有一个需要保留的细节：47 个 factory 同目录文件清单如实包含 7 个既有辅助文件的本地副本，每个副本比对应 Git blob 多一个末尾 LF。这 7 个文件均不在本次实际准备的 33 个冻结源码/测试文件中，P20 的静态和动态加载路径也不引用它们；它们不进入此次提交。实际复用的 P16/P17/P18 源码及执行清单中的全部 25 个既有文件均与基线 Git blob 完全相同。因此本地 47 文件清单是本地字节快照，不能称为整个 P1 的 canonical Git 快照；远端树仍直接保留全部原有 Git blob。
