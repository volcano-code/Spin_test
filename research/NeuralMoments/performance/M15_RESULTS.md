# W1 M15 — 实际编译的 C++/GMP 真实 Heart H8e 材料实验（2026-10-20）

**唯一写入分支** `research/neuralmoments-w1-native-20261019`；只修改 `research/NeuralMoments/performance/`。冻结祖先 `0bcc187b3005478baa586a6d6f450e73811ca342`。

## 实际执行，而非待执行方案

* 重新以 `g++ 14.2.0 -std=c++17 -O2` 构建两个已有的真实 C++/GMP 源文件：`real_h8_gmp_probe.cpp`（源自 W1 M3，精确表面积分及已解析原生材料持有对照）和 `m6_independent_tetra_gmp.cpp`（源自 W1 M6，独立精确四面体公式），通过 GMPXX+GMP 链接。实际可执行文件 SHA-256：表面 `48dad1839ba62912d94703f1ced394b70805b10df5e06a2bae02a62486e7b1e1`，独立四面体 `a19ae26404636910b0260a22d66e4e8a9a3d2e4e444a1918161ad52870d69b66`，与原研究中保存的 SHA 一致。没有使用 Python 的浮点三角网格积分来代替原生计算。
* 真实输入是 H8e 25-point GitHub Actions 原始 ZIP，SHA-256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`。每个包逐点检查压缩材料 SHA、q、构造身份、几何与拓扑哈希、原始原生精确边界证明、图形顶点/三角面计数和 Cherchi 后端身份。
* 每个真实材料点先后运行两个独立原生可执行文件，轮流切换先执行表面/四面体路径。表面可执行文件内部使用老/新/新/老交替计时（ABBA），每次做完整原生面邻接/定向/零面积检查和 GMP 精确十矩；四面体可执行文件自行做相同类型的原生边界检查并重新独立计算 GMP 十矩。
* 第一批执行到 **16/25** 点时遇到工具超时，该批次未产生完整 25 点成功报告，原始 `interrupted.json` 保留；第二批明确从 16 运行到 24（9 点）并正常完成。独立合并程序 `m15_consolidate.py` 确认点号 0..24 连续、来源 SHA、50 个 old + 50 个 prepared 的内部计时阶段可闭合、所有 250 个 GMP 精确分量相等、历史 8 个变更特征哈希保持，**不把两批运行伪装成一次完整的 25 点总耗时**。

## 真实指标

| 指标 | 真实数值 |
|---|---:|
| 归档 Cherchi 材料 | 25/25（每个 8455 顶点 / 16910 三角面） |
| 独立 GMP 表面/四面体精确十矩 | **250/250 个原分数完全一致** |
| 历史独立十矩浮点结果的最大缩放误差 | **0.0** |
| 老式十矩子流程中位耗时 | **371.100 ms**（50 次） |
| 准备好材料的十矩子流程中位耗时 | **359.721 ms**（50 次） |
| 子流程原生 GMP old/new 比值 | **1.031632×** |
| 125 次积分对应的原生进程 wall 合计（非求解器） | **47.698 s** |
| 历史 H8e 原始 8/24 构造哈希变化 | 保留，历史 CI 仍 **FAILED** |
| 真实新 Cherchi Boolean / Jacobian 再计算 / Newton | **0 / 0 / 0** |
| 完整 Faster 端到端加速 | **null，未验收** |

新的 old/prepared 中位比值只说明 C++/GMP 材料持有子流程的低个位数提升；绝不把它作为 Faster/Boolean/Newton 速度成绩或作者论文同条件跑分。两侧都执行了完整的**本实验**原生有向边界检查，但是 **没有**重新执行生产级的独立三角面自相交精确审计，也没有重新计算 Cherchi 构造运动/10×10 Jacobian。使用的是历史真实材料，不是一次新的 Cherchi Boolean。

## 本机完整原生求解器的实际阻塞

当前 cgroup 限制仅 4294967296 bytes (4 GiB)，swap=0，缺少完整的 Git W1 checkout、固定 Cherchi/CGAL 源码、MPFR 开发头及三个生产 Python 原生扩展。`git ls-remote` 不能解析 github.com；GitHub API 连接器可以拉取源文字及提交 W1，却不能代替完整、内存足够的 C++ 构建主机。本轮绝不把已有的独立 C++/GMP 探针等同于生产 `_cherchi_core_boolean`。

## 复现步骤

在 W1 checkout 下，首先确保拥有历史 ZIP SHA-256 如上；保留 24GiB 内存上限、零 swap，所有原生进程串行、每次不超过 3600s，编译 <=4 并发。

```bash
P=research/NeuralMoments/performance
mkdir -p /tmp/w1m15
c++ -std=c++17 -O2 -Wall -Wextra -pedantic "$P/real_h8_gmp_probe.cpp" -o /tmp/w1m15/surface -lgmpxx -lgmp
c++ -std=c++17 -O2 -Wall -Wextra -pedantic "$P/m6_independent_tetra_gmp.cpp" -o /tmp/w1m15/tetra -lgmpxx -lgmp
# On a host able to finish the full pass in one allowed execution:
python "$P/m15_real_native_surface_tetra.py" --archive /path/h8e-25point-39121571756.zip \
  --surface /tmp/w1m15/surface --tetra /tmp/w1m15/tetra \
  --output /tmp/w1m15/full-native --points 25
# This milestone was interrupted at 16, and actually resumed 16..24.
# m15_consolidate.py only merges that specific *observed* split when both
# original evidence batches and their binary SHA are present.
```

测试 `test_m15.py` 在真实归档、独立编译的两个 C++ 程序和 16+9 原始结果环境变量就绪时 **13/13 通过**，无跳过；`evidence/m15-tests.log` 保存完整实测。

## 后续决定性里程碑

有 24GiB 上限内足够实际内存的原生主机，应按 M13 构建真实模块，串行运行 M5 原生细粒度计时、M9 ABBA 和 M11/M12/M14 严格证据核验，最后进入完整 Newton、接受/拒绝历史、终态精确材料、十矩和完整 Jacobian 的新旧对照，并满足 W0/W2 准入。不得再将本实验的低个位数算术收益外推为完整 Faster 加速。
