# W2 M22-P2 · Frozen Heart 的独立边界重积分

对 11 月 5 日同一个 M21 诊断，分别从原包和审计包运行 M22 数值回放。两个包共有的 13 份原始文件逐字节一致；原包 12 项校验和及审计包新清单 14 项全部通过。审计包只增加说明和校验清单。两份外层日志是同一次输出的副本；stderr 路径存在，大小为 0。完整哈希和分层结果保存在 [机器可读记录](M22_P2_HEART_BOUNDARY_REPLAY_20261106.json)。

## 两次独立检查

1. 重新读取冻结 spec、原始 label 与 result。将十个归档有理参考逐项舍入到 binary64，与此次诊断的十个原生测量值比较，十项差均为零。直接将每个原生 binary64 值视为精确分数与参考分数相减时，最大绝对差约为 2.4071727477604756e-17（质量分量）；各项都在预登记的 1e-10 容差内。
2. 从 [历史 H8f 工作流](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 取回 artifact 12135528290 并核对整个 ZIP 的固定 SHA。从中读取唯一的 point-000-material.json.gz，核对 M9 登记的成员 SHA、输入系数、几何与拓扑，以及矩数据。在 M21 密度与目标坐标系下，以 8,455 个有理数顶点、16,910 个定向三角面重新计算十个带密度的体积矩。规范化目标边界摘要与 M21 记录逐字节吻合；新积分结果与 M21 留存的十个精确有理数逐项严格相等。

## 来源与准入

历史对象的完整规范材料 SHA 为 6be4faf58ef2fc31b6a1e6d67e601417150d0b43dbd37104b61565a2ca6708c1，本次 M21 标签期望 b136cbcc09740915cd70615d73fab3ab2aa0b680cdb823cfed12375bed6c20e8。两者的 evaluation-map identity 也不同。目标边界一致支持数值重积分，未恢复 M21 原调用的完整序列化对象或编译模块。此次复核没有新运行 Cherchi。冻结输入是 H8f 重建模型。保留原 H8f 工作流结论，当前标签 split=excluded、J_D=null、训练样本增量为零；材料布尔语义及连续导数仍须独立审查。

## 重放

在 W2 teacher 目录运行。以下命令使用原包解压后的 M21 运行目录，以及完整 H8f ZIP 或字节匹配的历史点 0 原始 gzip 成员。

```bash
python3 m22_recover_h8f_point0.py --pilot-dir "$RUN_DIR" --historical "$H8F_ZIP"
```

本例预期返回 JSON 状态 BOUNDARY_ONLY（退出码 3）。0 表示完整规范材料与边界均匹配；2 表示证据冲突或输入无效。后续独立产出新的同次材料时，应把它与对应标签和新运行 ID 绑定。

## 对同一目标边界的几何检查

另用 [W1 已冻结的 M26 检查器](https://github.com/volcano-code/Spin_test/blob/249db334303b31b8b8c2cfcb415b21a7cc2c9464/research/NeuralMoments/performance/m26_exact_intersection.cpp) 核对这张边界。14 项检查器回归通过。将历史点 0 的 variable_rational_vertices 逐坐标约为分子/分母规范文本，与 variable_faces 一起封存。边界哈希与 P2 一致，传给原版 M26 的输入流 SHA 及二进制和源码身份见[几何检查原始输出](M22_P2_HEART_BOUNDARY_SELF_INTERSECTION_20261106.json)。

有理数检查处理全部 161,702 对候选面，其中相邻 111,975 对，非相邻 49,727 对。没有检出非法相交。边界闭合、定向一致，每条边由两个相反方向的面使用，每顶点只有一片连通面扇。独立计得 1 个连通分量、8,455 个顶点、25,365 条边、16,910 个面。这个结果描述给定网格的嵌入性质；应保留的布尔区域是否完整、源几何归属、完整同次材料对象和导数邻域仍分别待证。P2 标签继续排除在训练之外。

复现几何检查时，先按上节验证点 0、M21 标签与固定边界哈希，再将匹配的点 0 gzip 转为 M26 输入格式。M26 路径、编译方式和依赖沿用 W1 该固定版本。

```bash
python3 - "$POINT000_GZ" <<'PY' | "$M26_CHECKER" --max-seconds 300
import gzip, json, sys
from fractions import Fraction
from hashlib import sha256
with gzip.open(sys.argv[1], 'rt') as inp:
    material = json.load(inp)
vertices = [[f'{q.numerator}/{q.denominator}' for q in map(Fraction, row)]
            for row in material['variable_rational_vertices']]
faces = material['variable_faces']
raw = json.dumps({'vertices': vertices, 'faces': faces}, sort_keys=True, separators=(',', ':')).encode()
if sha256(raw).hexdigest() != '48aae36777ed15e705f1ab919edac07756d3a7444100c060ee5baabd310afe20':
    sys.exit('wrong target boundary')
print(len(vertices), len(faces))
for row in vertices:
    print(*row)
for row in faces:
    print(*row)
PY
```
