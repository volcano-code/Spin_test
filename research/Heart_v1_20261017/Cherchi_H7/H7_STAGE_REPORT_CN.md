# Heart H7 — Cherchi 精确面片分支诊断与性能剖析入口

更新：2026-10-18，隔离分支 `research/heart-p0-p3-20261017`。

## 本阶段已实做
- 新增 `source/h7_planar_patch.py`：基于精确有理支撑平面建立有向面链；用来源操作数的面集合与构造约束识别跨参数面片变化。比较时不直接匹配随 q 移动的绝对支撑平面。变化被分成构造点特征变化、支撑/边界变化、同支撑同边界但三角面重剖分候选、符号面片稳定四类。
- **保守认证规则**：上述任何一类都不授予布尔区域连续性、可微性或正式 Heart Jacobian 通过。尤其“共面重剖分候选”仅为候选，不能断言其实体等价。
- 新增 `source/triage_archived_h6.py`：严格检查 H6 两套保存报告的样本系数一致、25 点规模和历史代理身份，禁止替代原始 eval60。
- 新增 `source/profile_native_stages.py`：待在具有原生模块的研究主机上对同一输入逐阶段测量 wall time、CPU、source、Boolean、intersection_motion、derivative、integration、unattributed 和 peak RSS。可选 `--backend python|native|both`，严格比较两条算术路径的最终几何 SHA、质量矩及 Jacobian；阈值暂定为绝对 1e-8，最终性能发布仍须额外独立数值验收。
- 新增 8 项独立 Python 合成回归检查，并在 GitHub Actions 中运行。不依赖 CGAL、不执行动态布尔后备。
- 已从实际 H6 原始报告重新归类 24 个扰动点，保存于 `evidence/H7_SAVED_H6_TRIAGE.json`。

## 历史 H6 数据的准确解释
| 状态 | 数量 | 推断边界 |
|---|---:|---|
| 只有连接哈希变化，构造顶点哈希不变 | 18 | **不能凭哈希宣布共面重三角化** |
| 构造顶点来源哈希也变化 | 4 | 更强的构造分支警示；需原生 packet 重放 |
| 两种保存的哈希都不变 | 2 | 不等于连续邻域可微性认证 |
| 数值导数检查 | 9/9 | 最大相对误差 2.559927270162632e-11，但拓扑邻域认证未过 |

以上只代表历史 V4 Heart 代理数据，不是原始 Heart eval60，不能宣布 Heart/Newton 收敛。

## 重现
从仓库分支根目录运行：

```bash
python -m pytest -q research/Heart_v1_20261017/Cherchi_H7/tests
python research/Heart_v1_20261017/Cherchi_H7/source/triage_archived_h6.py \
  --output /tmp/heart-h7-triage.json
```

**需要原生环境的性能实验：**先从 H6 恢复 SHA 匹配的 `archived-heart-v4-request.json`，然后执行：

```bash
PYTHONPATH=python python research/Heart_v1_20261017/Cherchi_H7/source/profile_native_stages.py \
  --archived-v4 /tmp/archived-heart-v4-request.json \
  --backend both --repeats 3 \
  --output /tmp/heart-h7-stage-profile.json
```

主机须先构建、加载对应版本 `_make_it_stand`、`_cherchi_core_boolean` 及可选 `_cherchi_rational_moments`。原生 GMP 不可用时命令会失败，不允许静默回退；单纯脚本和 CI 成功不能当作原生计时结果。

## 尚未做到
1. 当前工具不能在本执行容器中运行真正 Cherchi（未安装原生模块），因此没有新的 H7 原生 wall time、25 点 packet 取证或材料等价认证。
2. H6 的 22 次变化仍只是哈希层面的未分类差异；H7 的分类器需要接入每个扰动点的**真实完整 Cherchi packet、源面及输入来源**，才能开始逐例分类。仅凭现有 H6 digest 无法升级认证。
3. 原始 eval60 的配置和事件文件仍缺；81 点完整认证、Newton 多种子、正式 Heart OBJ、MuJoCo 接触与制造均未验收。
4. 本轮没有修改 production solver，没有改变动态 Cherchi Boolean 后端，没有对原始 `Spin` 或 `Spin_test/main` 写入。

## 后续验收门
- H7b：原生重放并逐点记录构造特征、定向边界及准确精确几何；所有不唯一的支撑/来源严格标注未解析。
- H7c：隔离同一材料 q 的端到端性能热点，并分别验证 Python Fraction / Native GMP 的相同几何与 Jacobian；只有测试实际运行且证据可审计后才做加速声明。
- H8：正式 Heart 冻结输入恢复（或者明确新建重建域），81 点 10 列三尺度数值导数及真实邻域认证。
