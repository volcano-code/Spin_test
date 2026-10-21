# P19：保留首轮 CI 失败，并补齐准确源码字节下的报告重播

## 当前应使用的证据

P19 的材料几何、真实构造与完整原轴保护结论保持不变。正式跨环境重播改用 [P19_CANONICAL_SOURCE_COMPLETE_REPORT.json](P19_CANONICAL_SOURCE_COMPLETE_REPORT.json)，SHA256 为 `f30fabc8ce348b9b8f42ff20649e683557349582ef31baf6c05d35e17b448601`。

这份报告直接保存了首次实际 GitHub CI 的 `fresh-complete-report.json` 原字节。它由固定仓库源码完整重算产生，几何状态为 `P19_EXACT_SAVED_SOLID_AND_COMPLETE_ORIGINAL_SHAFT_PASS_NOT_ADMITTED`；没有手动替换报告内的源码哈希。随后在恢复准确 Git 字节的本地环境中，用未修改的 `p19_material_candidate.py verify` 完整重算并验证通过，收据见 [P19_CANONICAL_SOURCE_LOCAL_REPORT_REPLAY.txt](P19_CANONICAL_SOURCE_LOCAL_REPORT_REPLAY.txt)。

原 [P19_COMPLETE_MATERIAL_REPORT.json](P19_COMPLETE_MATERIAL_REPORT.json) 及其 `62212e82…` SHA 原样保留。它如实记录此前本地恢复副本的字节身份，但不再作为准确 Git checkout 下的重播目标。

## 首次 CI 实际发生了什么

- 提交：[`c644a875c5e39818f99271f9bed311cee55320b5`](https://github.com/volcano-code/Spin_test/commit/c644a875c5e39818f99271f9bed311cee55320b5)。
- Run：[`39644621237`](https://github.com/volcano-code/Spin_test/actions/runs/39644621237)。
- P19 job：[`119376793003`](https://github.com/volcano-code/Spin_test/actions/runs/39644621237/job/119376793003)，最终 `failure`。
- 137 项测试全部通过，44.430 秒，无跳过；完整实际测试日志见 [P19_CANONICAL_SOURCE_FIRST_CI_TEST_RECEIPT.txt](P19_CANONICAL_SOURCE_FIRST_CI_TEST_RECEIPT.txt)。
- fresh 完整几何审计通过。
- 已提交旧报告的 replay 失败，异常为 `P19_FROZEN_REPORT_RECOMPUTATION_MISMATCH`。
- 后续构建、解析 native 与 Teapot native 步骤均跳过，因此此次失败 CI 的新原生调用数为 **0**。

首次 GitHub 工件 ID 为 `12366473184`，原始 ZIP SHA256 为 `9f5ba02f63118516a3a871ebdaec3dc3f90da7c847077ee47527d7e7827d8b93`。原 ZIP、完整实际 job 日志、字段差异、两种源码字节与原 workflow 均收录到 [P19_FIRST_CI_FAILURE_EVIDENCE.zip](P19_FIRST_CI_FAILURE_EVIDENCE.zip)。逐文件 SHA 见 [P19_CANONICAL_SOURCE_REPLAY_INDEX.json](P19_CANONICAL_SOURCE_REPLAY_INDEX.json)。ZIP 的统一 1980 年元数据只是确定性封装规则，不表示实验发生时间。

## 根因与逐字段检查

在本地恢复两个历史源码文件时，各多出一个末尾 LF。两个文件的全部既有字节与固定 Git blob 相同，但额外换行仍改变 SHA256，因此严格源码身份检查正确地拒绝了旧报告。

| 文件 | 准确 Git blob SHA1 | 准确 SHA256 |
|---|---|---|
| `p15_inherited_sliver_repair.py` | `397a6c49bcf5f1ec831fc3bc27e117fd58ab4276` | `f925f9fcc3690feb79d2474129c006c9ed5a482668f5c360879ee96e5897b6a3` |
| `p16_exact_binary64_chain.py` | `7f642c1b81d3f31b31bf3b865638b57867df24f7` | `d020cc3899707aeea1bb5641e09a0603f62868d0babdc260a2e038b67694191e` |

去除原已登记的计时字段后，两份报告共 10 项差异：两项上述源码哈希，以及材料表内重复显示的 8 项主惯量数值。8 项展示差异的最大相对值约 `4.34694e-15`，已经被原来的 `physical_reports_equal` 接受，远低于原登记 `1e-12`；未扩大该容差。其余几何证明、精确矩、完整惯量张量、材料字节及批准标志全部一致。

本次只将本地副本恢复为仓库原有字节，没有修改远端历史源码、P19 程序、测试、冻结网格、manifest 或任何已有报告。没有将末尾换行加入忽略规则，没有修改比较器。

## 追加的实际验收

新增独立 job 为 `p19-canonical-source-complete-material`，不依赖保留的首轮失败 job。原 workflow 的 56367 字节保持完整前缀。新 job 在测试前固定 canonical 报告 SHA、其全部 25 项源码／测试／清单身份，并独立验证两个历史 Git blob；随后执行原有全部验收：

1. 137 项完整测试，禁止跳过。
2. 冻结候选完整审计与 canonical 报告全量重播。
3. 固定原版 Cherchi 单 worker 真实编译。
4. 三次实际解析 Boolean，独立精确十矩共 30 项比较。
5. 三次新 Teapot 操作、精确顶点及有向面多重集比较、新输出的全实体与完整原轴证明。
6. 将两组实际调用的 binary SHA 绑定本次 build identity，保留真实输出和 receipt。

本文件登记的是验收要求；后续实际 run、job 及结果以提交后的 Actions 观察为准。本地累计 22 次真实原生调用没有增加，也不把首轮被跳过的步骤计入。

保存后几何通过仍不代表 W0 原生材料区域准入、教师 r/J、导数、训练或优化已经完成。下一研究门和输入继续见 [P19_W0_W2_HANDOFF.md](P19_W0_W2_HANDOFF.md)；构造与科学证明详见 [P19_COMPLETE_SHAFT_PROTECTION.md](P19_COMPLETE_SHAFT_PROTECTION.md)。
