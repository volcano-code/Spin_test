# W2-M18｜Noodles V7 94/94 冻结源部件原始字节恢复；F/D/A 布尔与 Frozen Heart 原生教师仍需验收

**执行日期**：2026-10-21。**唯一写入分支**：`research/neuralmoments-w2-teacher-20261019`；唯一修改目录 `research/NeuralMoments/teacher/`。未修改 main、W0、W1、W3、W4、共享原生模块、历史原生失败 CI。

## 1. 本阶段真实突破：从 M17 的 3/94 到 94/94

原始来源：[Spin_test/main Noodles V7 frozen parts manifest](https://github.com/volcano-code/Spin_test/blob/main/research/Noodles_v7_20261017/frozen-parts-v7c/manifest.json)，Git blob `f476a8c3e87bd30ef186b24442f641c2602c32ec`，SHA256 `67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a`。

本轮实际完成：
- 补齐 **79 根 rounded tubes**、**11 根横向 ribs**、**1 根轴向 rib**，加 M17 已恢复的外椭球、hub、pin，总计 **94 个**原始几何部件、**93 个 fixed 来源部件**；
- 为每个部件重新写出原始 model 坐标和 SI 坐标 OBJ，共 **188 份**；
- 对每个部件独立检查闭合、朝向一致、单个连通分量、正有向体积。注意这不证明独立无自相交、更不证明合并的 F/D/A 有效；
- `m18_noodles_full_source.py` 独立实现并实际运行原始生成算法，核对 10 个事先独立声明的个体 model/SI SHA，并计算整个 94-name / 188-SHA / 94-vertex-count / 94-face-count 的固定编码 SHA256 `6b2da86949e4426986e2460167f1255f0c44d6e708be87bfec17fb78ce4a69c6`；
- **独立连接 GitHub** 重新读取原始 manifest，重新计算该全部字段摘要，同为 `6b2da86949e4426986e2460167f1255f0c44d6e708be87bfec17fb78ce4a69c6`；并非只检验几个示例。

### 原始源码再运行的第二套独立复验

从已保存的 Noodles V7 研究源码快照恢复原始四个生成器文件和原始 manifest，核对 Git blob：
- v7 生成器 `73f78e76100139184318131eb7cff9816384bc7c`；
- v5 父生成器 `a1d18dfd010f415cadc98990060796bc2d15d0c8`；
- v3 父生成器 `3231deef019d676cb86bdcce7f54de90dd6d7256`；
- 管体成网辅助 `afc9a90bf5263a868038ea5ae66581941c6dfd3b`。

**真正执行**原版 `noodles_paper_geometry_v7.py --output <new-dir>`，退出码 **0**，输出的 **`manifest.json` 与历史冻结原文件逐字节一致**（SHA256 `67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a`）。原版的 188 份 OBJ SHA 与历史 manifest 完全一致。这是单独运行原版源码，不是根据 W2 独立恢复器的成功标记猜测结果。

## 2. 精确布尔 F/D/A 仍未完成：已做真实失败判定

历史 [CGAL 构造收据](https://github.com/volcano-code/Spin_test/blob/main/research/Noodles_v7_20261017/frozen-inputs/author-rational/construction.json) Git blob `1e824c72d5ee13cc484bbf60a0be9b79be86d787`，其 `manifest_sha` 与本轮字节恢复的真正源清单 SHA 一致，记录 **96 次历史 CGAL 精确布尔**（本轮 0 次）。但六个历史真正的 `*-rational.json`（`design`, `envelope`, `fixed`, `fixed-inside-envelope`, `fixed-outside-envelope`, `initial`）在本轮可用的 Git / 原始源码快照中**都缺实际数据**。

本轮使用旧 W2 M17 严格 `inspect_csg` 读**真实字节锁定**的构造收据，得到：`matched_historical_packets=[]`、`missing_packets=6`、`all_historical_CSG_packets_present=false`。原始生产用的 `noodles-exact-boolean` 可执行文件也不在本容器；当前内存只 4 GiB，禁止在此冒险重启 96 次高成本 Boolean。不把 94 部件合并成浮点几何代替原有精确 CSG，不把旧最终优化 OBJ 当作新的 F/D/A 原生教师输入。

本轮 F/D/A 仍需要：在合格研究主机上以冻结同一 backend/hash 获得六份原始有理 CSG 包，并比较六个已归档 SHA；如重新构建结果与历史不同，必须声明新证据身份，再做闭合/有向/精确体积/集合分区独立验证。之后锁定外壳/固定域/设计域及 native c，才能准入真正新 Noodles 教师尝试。原版历史收据的 `independent_partition_verified=false` 不得改写为成功。

## 3. Frozen Heart：重新尝试并保留失败

实际执行原 W2 M16 `--execute-native`，输入真正的 H8f 81 点冻结 ZIP (SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`)，本轮预检退出码 **2**，状态 `BLOCKED_BEFORE_NATIVE_CALL`，失败证据本地 SHA256 `8f9727be1a0a88edac09eae2286efbf6c1b33f50ede4f47b7ac96ca8b7588a46`。容器有效内存上限 `4294967296` bytes (4 GiB)，团队序列任务至少要求 24 GiB；完整 W2 研究检出、三个外部 SHA 锁定原生模块及单独预声明十矩误差预算仍未满足。**不发生新的 Cherchi 求值，也没有真实新 Jacobian 或单次性能指标**。原 H8f workflow 39123384402 **failure** 保留。

## 4. 实际运行的 GitHub 同版代码与测试

W2 本次新增：
- `m18_noodles_full_source.py`：生成全部 94 部件和 188 OBJ；严格检查整个 frozen corpus SHA，不接受“只差一点”的浮点几何。
- `test_m18_full_source.py`：真实重生全部部件、哈希/拓扑、阻止结果覆盖、篡改与伪 CSG 的 **16/16 PASS**，执行 1.505s；日志 SHA256 `5ba855c33e39e2310bc0aa08e08ac5aff3fc1262b5cdf32acc96c4f41db9a22c`。
- `test_m18_original_generator.py`：在提供 SHA 锁定的原版源码快照时，真实启动原版生成器并核验同一 manifest 字节及 188 原始 SHA；**3/3 PASS**，3.199s；日志 SHA256 `8d7117fbd8fa1805931cce187738806f4ee0a27f7698325d93ceba86cddb3a38`。
- `M18_FROZEN_NOODLES_94_SOURCE_IDENTITY.json`：94 组逐点模型 SHA、SI SHA、面/点数，源代码版本锁定，以及 CSG 缺失与 Heart 预检失败信息。
- 本报告。

已使用 GitHub 工具独立重读源代码及测试的 Git blob，与本轮本地真正运行的相应 blob 完全一致；这是**本地 Python 的原始生成器与测试执行结果**，不是新远端 GitHub Actions CI，也不是原生 Cherchi 测试通过。

### 复现

```bash
# 在 W2 repo checkout; Python 3.13、NumPy、trimesh
python -m unittest discover -s research/NeuralMoments/teacher -p 'test_m18_full_source.py' -v

python research/NeuralMoments/teacher/m18_noodles_full_source.py \
  --out /new/empty/location/rebuilt_parts \
  --manifest /path/to/Spin_test-main/research/Noodles_v7_20261017/frozen-parts-v7c/manifest.json

# 可选：真实原版源码快照，四个 generator 文件的 Git blob 必须与本报告一致
W2_M18_PINNED_SOURCE_SNAPSHOT=/path/to/Original-V7-Snapshot \
 python -m unittest discover -s research/NeuralMoments/teacher \
 -p 'test_m18_original_generator.py' -v

# Frozen Heart: 仅在 ≥24 GiB、swap=0、完整 W2 checkout、
# 三个原生二进制 SHA 锁定及十项独立参考预算满足后尝试
python research/NeuralMoments/teacher/m16_native_acceptance.py \
 --heart-archive /path/to/real-h8f-81.zip --output-dir /new/empty/dir \
 --checkout /path/to/actual/W2-checkout \
 --native-manifest /path/to/externally-verified-ELF-manifest.json \
 --reference-budgets-json /path/to/independent-ten-moment-budgets.json \
 --execute-native
```

## 5. 科学结论及下一阶段

**94/94 原始 V7 几何部件已完成字节级重建，且原版生成器也独立重现；这是本阶段已达成的真实成果。** 完整 `F/D/A` 有理布尔/独立分区、最新编译原生 Cherchi 教师运行和 W0/W3 导数授权仍未达成。所有样本保持 `excluded`，本轮新 native Cherchi 0，新增可训练 `J_D` 0。下一步应在合格原生主机上优先对真正的 Frozen Heart 执行一次封闭单次教师，然后复原 V7 CGAL 六份有理实体和完整原生 F/D 请求。
