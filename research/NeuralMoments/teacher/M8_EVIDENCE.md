# W2-M8｜真实 H8e Cherchi 历史归档的独立十矩复验

**执行日期：** 2026-10-19  
**唯一写入：** `research/neuralmoments-w2-teacher-20261019` / `research/NeuralMoments/teacher/`  
**冻结上游：** `0bcc187b3005478baa586a6d6f450e73811ca342`

## 已实际完成

本里程碑没有再次调用原生 Cherchi，而是通过 GitHub 连接器下载了 **真实已运行过的** H8e 25 点 Cherchi 材料归档及对应独立构造分类归档。它们来自原先的 Heart H8e 非对称**重建** CAD，不是论文作者原 CAD。

| 证据 | GitHub Actions run | 状态 | Artifact ID | ZIP SHA256 |
|---|---|---|---|---|
| 25 点原生 Cherchi 运行材料 | [39121571756](https://github.com/volcano-code/Spin_test/actions/runs/39121571756) | **failure，必须保留** | `12134772056` | `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38` |
| 离线精确构造分类 | [39122997405](https://github.com/volcano-code/Spin_test/actions/runs/39122997405) | success | `12134499573` | `e17d90a8195637358d19e61fda3d8e1946cb33540f26190cead6723e7a36ef16` |

上述状态均通过 GitHub Actions API 重新核查，不能把原始 failure 改报为 success。25 点原生运行于 **2026-10-18** 发生。本轮新增的是**独立离线复验和代码**，并非 25 次新原生调用。

## 验收数据

- 真正重读 **25/25** 份 `point-XXX-material.json.gz`，逐文件验证压缩包内材料 SHA-256；请求 JSON SHA 与原始 report 对齐。
- 对各份材料验证 native c 系数、Cherchi 后端及 GMP 模块身份、source geometry hash、physical material geometry hash、离散拓扑 hash、10×10 Jacobian 的存在和形状、变量/总十矩与点报告一致。
- 从 **8455 个精确有理坐标顶点和 16910 个定向三角面**（每点）直接用独立 Python `Fraction` + 有向四面体积分重算原始十个质量矩；逐点检查有向闭合边及正质量。
- **25/25 数值匹配**。重算的精确 Fraction 转成 binary64 后，与生产端和历史独立十矩的 **最大绝对误差 = 0.0，最大 ULP 差 = 0.0**。这个“0”指最后的浮点转换值相同，**不是**声称 native 原始十矩等于十个 Fraction 对象、无测量不确定性或几何证明已经完成。
- 依据冻结 Faster 请求的目标坐标系，将固定矩 `r_F` 独立变换后核验全部 `r_total = r_F + r_D`；没有重复计数。
- **25 个不同的原生系数向量**；观察到 **3 个原始构造哈希**。与基点比较的漂移索引为 **17–24**，计 **8** 个，保留原始 `all_tested_stencils_same_feature_hash=false`。
- 独立分类 artifact 对 24 个有限扰动点给出 `SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED`，且明确 `certified_smooth_neighborhood=false` 和 `certified_newton_direction=false`。这个结果不能把 8 个原始哈希变化抹去，更不能证明连续邻域已光滑。
- 原始 25 点 Native+审核总 wall：`379.493727883s`。本轮**最终 SHA 固定后的** Python 离线重算 wall：`79.53340224199997s`；这两个数据是不同范围，不能用于声称 Cherchi 速度提升。
- 归档原始数值求值总数 **25**；本轮新启动原生 Cherchi 数 **0**；正式 W0 导数训练准入数 **0**。

## 提交代码

- `audit_archived_h8e.py`：独立读取真实 ZIP、限制并固定两个 artifact SHA、逐点验证密封材料 SHA、原生 c/来源及几何哈希、独立 Fraction 十矩、`r_F+r_D`、分类状态，输出逐点证据 JSON；失败即拒绝。
- `test_archived_h8e.py`：解析四面体精确十矩、边界/朝向拒绝、坏分数及形状拒绝、真实材料 gzip SHA 篡改、原生交叉系数交换、几何 hash 篡改、完整真实基点复验。未提供真实 ZIP 时真实档案用例显式 skip，不会虚报通过。
- `teacher_manifest.json`：严格分开原历史 native=25、新本地 native=0、已独立复验 archived=25、训练 admitted=0。

Git blob SHA 与本地执行源码逐字节相同：

- `audit_archived_h8e.py`：`cafa555297c36492f81ecfce66fac4066861276f`
- `test_archived_h8e.py`：`2fb9b3cb8d0989b42c8e3424245b77478251e496`

**真实执行命令：**

```bash
# ZIP 应为原先 Actions 中下载的字节完全一致的档案
sha256sum h8e_25point_real.zip h8e_25point_classifier.zip

python research/NeuralMoments/teacher/audit_archived_h8e.py \
  --archive h8e_25point_real.zip \
  --classifier h8e_25point_classifier.zip \
  --output M8_ARCHIVE_AUDIT.json

W2_H8E_ARCHIVE_ZIP=h8e_25point_real.zip \
  python -m unittest discover \
    -s research/NeuralMoments/teacher -p 'test_archived_h8e.py' -v
```

实际记录：全 25 点审计退出码 `0`，`verified_points=25`、`max_exact_raw_ten_moment_absolute_error=0`、`training_samples_admitted=0`；新增专项测试 **11/11 PASS**（约 3.7 秒）。

最终完整逐点证据 JSON SHA256（在本会话容器内生成，尚未当作训练集发布）：

`29977a068888c0891c12614a74513ca885f5246fd78ebf2b8fbaeea999661cd1`

25 份 `index:compressed_snapshot_sha256\n` 的串联清单 SHA256：

`e792c0032359ed2ae69119f4a0fb11f14314868c87be1d37d2a21b35c9e8eba2`

## 严格界限 / M9 依赖

1. 原生库在当前 Python 环境中仍缺失，因此没有新 Cherchi 求值，也没有独立重跑原生精确自交、Boolean 或连续导数。离线审核使用已保存的真实 exact material。
2. Jacobian 虽然存在于归档，但**仅检查形状与绑定**，不做光滑导数准入。W0 `MomentContractV1` 可信邻域验证器未接入，`J_D` 训练标签保持 `UNKNOWN/excluded`。
3. 25 点覆盖 q/c 的 `[0,4,8]` 三列，**不是** 10 列 81 点。**H8 point60** 未验证，不可作为平滑导数真值；开边界 Teapot 不可作为体积教师。
4. 目前尚未验证整体 Newton/KKT、完整材料打印或物理接触稳定性。不得以本报告宣称 H8 目标模型已优化成功。
5. 下一阶段继续寻找/生成有正式签名的 81 点及 W0 合同证据；若需重新运行原生 Cherchi，必须在拥有编译扩展的研究主机上执行，并保持串行、24GiB/swap0、每次不超过 60 分钟。
