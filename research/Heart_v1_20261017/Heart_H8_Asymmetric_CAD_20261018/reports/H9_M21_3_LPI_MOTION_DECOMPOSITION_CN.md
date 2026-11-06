# W3 H9 M21.3｜LPI 交点运动分解

## 基线与范围
- 仓库：volcano-code/Spin_test
- 唯一写入分支：research/neuralmoments-w3-heart-h9-20261019
- 开发基线：e9e9fe9411c2c7194f4d64789fb96a52cefa246a（M21.2）
- 输入：M18/M19/M20 六份 SHA 绑定材料，以及 M21.1 的六份 source-motion 附件。
- 本阶段只读离线分解：0 次 Cherchi Boolean、0 次原生 source 调用、0 次构建、0 次 Newton 试步。
- 分析三个由用户六点输出确定的 LPI 特征，不把有限点结果扩展为连续区间证明。

## 调查对象
| 标签 | 直线端点（design object 0） | 平面顶点（source object 1） |
|---|---|---|
| repeated | 3756, 3813 | 24, 86, 87 |
| left-full | 9992, 10119 | 31, 105, 110 |
| right-first | 3168, 3618 | 24, 151, 152 |

M21.2 六点 incidence 约为 0.11010–0.11438，未显示趋近零；它只是角度代理，不是完整条件数。M21.3 分解交点分母和速度传播项。

## 数学分解
保持材料中 LPI operand 原始顺序，A、B 为直线端点，P、Q、R 定义平面：
- u=B-A，w=P-A
- n=(Q-P)×(R-P)
- d=n·u，s=n·w，t=s/d
- n'=(vQ-vP)×(R-P)+(Q-P)×(vR-vP)
- u'=vB-vA，w'=vP-vA
- d'=n'·u+n·u'
- s'=n'·w+n·w'
- t'=(s'd-sd')/d²

t' 分成平面法向量项、平面锚点/直线起点项、直线方向项。最终交点速度为 x'=vA+t'u+tu'。报告给出 |d|、|d'|/|d|、||n'||/||n||、t、|t'|、交点速度范数、各分项和归一化 incidence。所有有理量以分子/分母字符串保存；程序仅在本进程内解除 Python 大整数十进制序列化位数限制。

## 绑定与验收
- 核对 M21.1 layered-report、worker report SHA、六个 source-motion 附件 SHA、材料 SHA 和原生 core SHA。
- 通过现有 load_six 重新验证 M18/M19/M20 输入和六份原始材料 SHA。
- 按 input_object/input_vertex 将 operand 与设计顶点、源顶点速度绑定；设计对象固定速度为零，源对象速度来自 M21.1 附件。
- 独立 LPI 分解必须与 M21 Fraction 构造函数的物理位置/速度完全相等，并经冻结 target frame 变换后与 M21 state 中的位置/速度完全相等。
- 对左右全区间、前半区间、后半区间，逐特征计算位置割线、端点平均速度和有符号残差。
- 输入缺失、哈希不符、身份歧义、平行/退化分母、位置/速度不一致均 fail-closed。

## 测试与执行边界
- 新增 9 项解析/数学单元测试：平面平移、倾斜导致分母变化、分项恒等式、独立位置有限差分对照、平行拒绝、身份规范化、歧义 operand 拒绝、速度索引越界拒绝。
- 开发容器中的 9/9 测试通过；这些是隔离数学单元测试，不是六份用户材料的真实集成测试。
- py_compile 通过。
- 六份真实材料的 M21.3 分析尚未执行；不能预先声称 LPI 根因已确定。

## 本地运行
请在 W3 仓库更新后按以下路径设置变量：
- ARTIFACT：原始 H8f ZIP
- PRECISION_LEDGER：M20 precision-ledger.json
- STAGE17_NATIVE_DIR：四点原生材料目录
- M19_RUN：M19 实验根目录
- M21_SOURCE_RUN：M21.1 source 模式输出根目录

测试命令：
python -X int_max_str_digits=0 -m unittest discover -s "$H9/tests" -p 'test_h9_m21_3_lpi_motion_decomposition.py' -v

真实六材料只读诊断命令：
python -X int_max_str_digits=0 -u "$H9/source/h9_m21_3_lpi_motion_decomposition.py" --precision-ledger "$PRECISION_LEDGER" --artifact "$ARTIFACT" --stage17-native-dir "$STAGE17_NATIVE_DIR" --m19-run "$M19_RUN" --m21-source-run "$M21_SOURCE_RUN" --repo "$PWD" --output "$M21_3_OUT"

预期状态：SIX_PACKET_LPI_MOTION_DECOMPOSITION_COMPLETE_DIAGNOSTIC_ONLY。输出为 M21_3_OUT/lpi-decomposition.json。本脚本不执行 Cherchi Boolean 或 source 原生调用。

## 当前初始目标差距
- H9 sample 60 的有限点真实构造切换：核心调查已完成。
- 六份新 Cherchi 材料及独立十质量矩：已通过。
- M21.1 源运动重放和导数传播一致性：六点诊断已完成，但源速度连续真实性未证明。
- M21.2 LPI 入射角初筛：六点未显示角度代理塌缩，不能单独解释 LPI 残差。
- M21.3 交点分母/参数/速度分解：工具与测试已开发，六份真实材料运行待本地完成。
- 连续构造分支认证：未完成。
- Newton 准入、真实接受步、最终 Heart OBJ/物理指标：均未完成，当前继续拒绝 Newton。

## 下一步决策
先在本地运行六材料分解。若 |d'|/|d| 或 t' 的分母贡献在重复异常 LPI 上明显突出，再对该项做尺度/扰动敏感性分析；若分母项不突出，则转向平面点运动、法向量变化与源速度误差。看到真实分解报告后，才决定是否新增 source-only 采样；本阶段无需云端 GPU 或本地 GPU，也不需要重跑 Boolean。
