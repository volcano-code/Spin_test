# W2-M13｜精确不可约正向射线、真实 point60 绑定与 W0 正式交接（2026-10-20）

**仅写入** `research/neuralmoments-w2-teacher-20261019` 分支的 `research/NeuralMoments/teacher/`。未修改 W0、W3、main、共享 C++/Python core、原始 CAD 或 Actions 失败工作流。

## 与最初 W2 目标的关系

原先 W2 要提供真实 Cherchi 的单次 `r_D,J_D`、严格的 F/D 身份、合法拓扑、阶段计时与完整失败记录，并在已验证解析体及合法 Frozen Heart/Noodles 上验收。到 M12 已真实离线重积分历史 H8f 81/81 十矩、确立固定矩分离及候选数据只读拒绝，但**W2 新在线原生 Cherchi 验收=0、合法 Noodles V7 教师验收尚未完成、W0 导数合同正式准入=0**。不要把 W3 的完整 Heart Newton 求解、打印或动力学终态错误算成 W2 独占必做项。

## 本轮科学与代码贡献

M12 的 exact positive pivot ratios 可以判定 raw binary64 的正比例射线身份，但不是 W0 能直接用来核对原始分量的简单整数证书。M13 [`w2_projective_handoff_m13.py`](./w2_projective_handoff_m13.py) 将每个保存的原始 c 逐项精确解码为 Fraction，求各分母 LCM，再对扩展整数取正 GCD，形成：

`original_native_c[i] == (g/L) * primitive_signed_integer_c[i]`，
`g/L > 0`，整数十元组的绝对值 GCD 为 1，不抹掉整体负号。

它精确检查 10 个 native 到 monomial 系数映射 `q=Bc`（仅交叉项乘 2），并在 7 个有理数探针位置核验 `P(raw_c,x) = (g/L)P(primitive_integer_c,x)` 的精确值与符号。**没有调用 Cherchi、新生成任何 c 或把单位显示替换历史同次 c**。严格原始 c 和 material SHA 仍然是源计算身份。

### 实际真实材料与测试

- GitHub 原始 H8f [Actions 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 严格保留 **failure**，源提交 `0bcc187b3005478baa586a6d6f450e73811ca342`，原生 artifact `12135528290`，ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- M9 原始 81 点候选 SHA256 `fcfccf626af7166c577ba15cc95c5ae0b345cd58a15000d708d5e68e9b85019a`、M12 exact ray Git blob `2d4cf4aae1368e22e760803d9bfe49479125ac4b`，均保持不变。
- **81/81** signed primitive integer rays 精确正比例重构、**81** 条唯一 ray；H8f **17** 个原始单位范数兼容、**64** 个非单位，全部保持原始 c 与 SHA。
- 本轮再次读取真实原始 ZIP、检验全 ZIP SHA 和真实 point60 单份 material gzip SHA、原始系数、几何/拓扑及 Jacobian 摘要、`r_D+r_F`。**实际本轮原始材料重读为 1 份**，先前 81 份全量真实材料重绑定沿用已保存的 M10/M12 证据，不宣称本轮重新解压了 81 份。
- 原始 point60 `c[7]=3e-6`、`q[7]=6e-6`、5 个变化位置、2+2 LPI 特征和 17+17 个有向三角面特征变化保持。拒绝声明光滑区间、左右侧导数或 Newton 已成立。
- 本地 Python 3.13 + NumPy，先实际执行 CLI 成功生成完整 81 条数学证书与聚焦点原始材料证据（`M13_H8F_81_PROJECTIVE_HANDOFF.json`，**381548 字节，SHA256 `2de535d1243802eba1826870001e7d7dc8c34ba8f6d911e933bc201da14ee8fc`**）；又在**不使用缓存报告**时执行专项回归 **25/25 PASS、0 FAIL、约 5.734 秒**，日志 SHA256 `871feaa4ebcc6c768dd4d9bf011a82f08fe3e08b9f3ca5f7ac0c3b9b39fb6b15`。
- 本地测试使用从 GitHub M9 锁定内容重建、明确标记的 **semantic manifest fixture**。W2 仓库真实 `teacher_manifest.json` 已由 GitHub 连接器读取并更新，但本地测试未冒充对远端完整 manifest 逐字节运行。历史 ZIP 是原始字节内容，SHA 独立验证。
- 测试覆盖有理正比例、负号禁并、float 缩放舍入、不合法分数/零向量、真实 81 点证书、point60 来源、M10/M12 污染反例、训练导出拒绝、覆盖证据拒绝与假冒 W0/W3 证明拒绝。

## GitHub 输出与复现

新提交：

- [M13 代码](./w2_projective_handoff_m13.py)：Git blob SHA1 `cc31a440f62af8a1d214bfd7fcc156ae31213808`
- [M13 25 项测试](./test_w2_projective_handoff_m13.py)：Git blob SHA1 `011a5dd71c9927824918b50789c7b3193d29867d`
- [81 点精确整数射线紧凑索引](./M13_H8F_81_PROJECTIVE_HANDOFF_INDEX.json)：Git blob SHA1 `fe6fbae5bf3e6f139bfef5dd66620208429483ee`，用原 M12 Git SHA 锁定的 81 条原始 c 独立核验精确分量与正有理缩放。
- [W0 正式交接提案](./M13_W0_PROJECTIVE_HANDOFF_REQUEST.md)：只读依赖/合同提案，不修改 W0。

完整包含 7 个探针逐点有理数值的 381548 字节本地报告只作为本会话可下载研究附件，**本阶段 GitHub 提交的是可再生的紧凑 81 条数学索引而非这份完整报告**。原始 H8f ZIP（约 64 MB）继续保存在原始 Actions artifact，未复制进 Git 源码树。

在 W2 完整 checkout：

```bash
export W2_H8F_ARCHIVE=/absolute/path/original-h8f-81.zip
python -m unittest discover -s research/NeuralMoments/teacher \
    -p 'test_w2_projective_handoff_m13.py' -v

python research/NeuralMoments/teacher/w2_projective_handoff_m13.py \
    --candidate research/NeuralMoments/teacher/M9_H8F_81_EXCLUDED_CANDIDATES.json \
    --manifest research/NeuralMoments/teacher/teacher_manifest.json \
    --archive "$W2_H8F_ARCHIVE" --index 60 \
    --output /new/nonexistent/path/M13_H8F_81_PROJECTIVE_HANDOFF.json
```

输出采用 M10 已有的 exclusive atomic evidence write，任何已有文件/新训练准入尝试都必须拒绝。

## W0/W3 仍待独立验收

- W0 现行 `MomentContractV1` 保存 c 单位范数合同与 W2 v2/projective 正式交接尚未更改；W2 当前只构建**代数正比例证明**，不得宣称 W0 接受或 native 演算身份等价。已向 W0 提交 W2 分支中的协议建议链接，供 W0 在自己的独占范围独立决定。
- W3 最新 Stage11 [独立证据](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w3-heart-h9-20261019/research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_STAGE11_EXECUTION_EVIDENCE.json) 仍为新增原生 Cherchi 四点 **0**、Newton **0**；不能用其条件性解析穿越替代原生侧点。
- W2 自身的 Frozen Noodles V7 独立老师样本及新在线 Cherchi 性能计时仍缺。研究主机的 24GiB/swap0、≤60分钟串行原生任务协议继续有效。
- **新原生评估=0，正式 Jacobian 教师=0、训练准入=0。**

GitHub CI 对本 M13 SHA 尚需独立查询；不能用本地 25/25 代称远端 CI 通过。
