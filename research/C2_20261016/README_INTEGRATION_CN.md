# C2 审阅包：离线恢复与源码接入说明

**本包包含可审核的修复候选及真实测试证据，不是已验收的完整 Newton 或旋转模型，也不能直接取代最新 `Spin` 仓库。**

## 内容目录

- `code/exact_retriangulate.py`：只对两个精确支撑平面上均位于直线段内部的冗余三角化顶点做精确重三角化；要求每个补片的 10 个原始质量矩严格相同。
- `code/cherchi_input_precision_guard.py`：拒绝 distinct rational vertex alias / binary64 零面积面。
- `code/export_cherchi_ready_input.py`：需核对精确链证明、原生 float64 网格审计、改造后来源记录后，输出 `float64` 顶点与 `int32` 面索引的 `.npz`。
- `code/emit_face_provenance.py`：输出局部新增面到旧源面集合的映射；**不伪造单一来源**。
- `models/`：静态实体的有理精确重三角化候选（design/fixed/initial）、经摘要固定的 Cherchi 静态输入 `.npz`，及其 JSON manifest。
- `proofs/`：溯源、三份全局精确面链、原生 float64 合法性、两次真实 Cherchi/CGAL 交叉验证、另含独立舍入引起的非零静态材料残差。
- `native_outputs/`：实际 Cherchi 交集/差集返回的精确坐标压缩文件，及 CGAL 对照材料；不等于优化终态。
- `logs/`：脚本执行日志、测试和失败证据。

## 从前一阶段的 P1a 精确资产重做

C2 修复脚本的 `--source` 应指向上一阶段 P1a 的 `design-rational.json`、`fixed-rational.json` 或 `initial-rational.json`；不依赖本包之外的隐藏数据，但要使用匹配的源 SHA。当前安装路径的绝对值仅是在线报告取证位置，**本包没有修改你本机原始源码**。

示例：

```bash
python code/exact_retriangulate.py \
  --source /path/to/P1a/design-rational.json \
  --analysis proofs/design-alias-analysis.json \
  --output /path/to/new_C2_experiment
```

脚本对原始 SHA 有硬门；首次运行时 `cherchi_input_precision_guard.py` 需与修复脚本位于同一目录。成功返回时必须看到 `ready_for_cherchi_float_input=true`，**这仅是入参可表达性检查**。

若需在原样恢复的源码环境重新跑 `test_exact_retriangulation.py`，设置环境变量 `NOODLES_V6_P1A_ROOT=/path/to/P1a`；该测试还需已提供的 proof 文件位于自身所在目录，或复制到对应工作根目录。测试不能替代真正的 C++ 几何检查。

后续整合时不要复用旧 `birth_faces` 作为新增面的唯一来源。`design-retessellated-static-face-provenance.json` 对新增面给出源面集合，动态导数必须再单独验收。

## 已知局限

真实 Cherchi 大网格交集与差集已经通过同 binary64 输入的独立 CGAL 精确对照，但 `F_double + D_double - A_double` **并非精确零面链**。新旧原有理区域边界严格一致与各自舍入后仍精确一致是不同命题。C3 必须显式处理这一数值契约。不能改论文容差、假装已经完成 Newton 或宣称切片/打印通过。

## 审批

向原正式 `Spin` 的写入需要用户另行批准。当前交付为待审阅候选，未经批准不推送 GitHub。