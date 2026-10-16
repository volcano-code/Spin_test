# 备份完整性与待迁移成果（2026-10-16）

## 已经写入 GitHub、且已核对
1. `upstream-spin-it-strict-computational-v2` 分支的 HEAD = `a17ff49cd8a1e6e8b388bc591410bda56d67c28a`，Git tree = `0000e2f24a7622a9f500322351998d321f51252e`。与 `volcano-code/Spin` 原分支完全相同。包含该分支可达的历史与 Git 跟踪的源码/模型；不会包括原仓库中未提交、本机忽略或未同步的文件。
2. `main` 分支内 `research/CONTINUE_RESEARCH_HERE.md` 与 `research/plans`、`research/reports`、`research/status` 和 `research/source/noodles_paper_domain_v6.py` 记载新一轮成果、限制和待执行关卡。
3. 源分支原历史镜像的 GitHub Actions 工作流成功结束： https://github.com/volcano-code/Spin_test/actions/runs/38915441596 。

## 仍未在 GitHub 存储的会话专有二进制包
**以下文件没有得到远端 blob/SHA 的核验，不能称已经上传。** 已计算的本地 SHA-256 用于未来上传后比对：

| 名称 | 大小（字节） | SHA-256 |
|---|---:|---|
| Noodles_v6_P0_native_build_and_tests_review.zip | 786880 | ec8cf1ec7c88e35b8814727ea569d0ee48d265d230c82706dc2f58c2e40ead97 |
| Noodles_v6_P1a_exact_input_models_review.zip | 29902182 | 83224c5095280490314e716b14ec72005408b64f3cf7a0897e3780f917b51212 |
| Noodles_v6_P1b_three_exact_chain_checks_review.zip | 13994 | 3cb8bf65faa53dcecc2437ff9c71d4ddc172b15644c8eaec3c53e922045c1ca6 |
| Noodles_v6_exact_domain_review.zip | 36530 | 9fa6bdc98330a709b610313f23a087246a4b271b5d1b167930651250e5f878e5 |
| noodles_v6_source_parts.zip | 3051047 | e2f0b96006735686187e3741f9742f8dc55a6624fb678f0258772977936f199c |
| Spin_native_round2_evidence.zip | 15332781 | e8ec8003ad9ca7c5d500768d8d857390e126c54031de4a97a5882c0bf1ac30d9 |
| Spin_native_round2_runtime_checkpoint.zip | 20031204 | 8a5aed055b89aab88e19a79263991bebb41ac5932d657124345835e5c786a42d |
| Spin_compact_001.zip | 36318342 | 8157bc618ff85af611a6c21ec51fb8553690b4d85a9ff47d0497fc2184890e51 |
| Spin_compact_002.zip | 48227830 | 75f5185e6d057d4ff29298e04625841144b62ef9665de9cdce10eb138519291b |
| Spin_compact_003.zip | 57012923 | 97cf462acd2e2cbac3dd49c0f0f3e2f922acf16830d4d888769383a8fa833355 |
| Spin_compact_004.zip | 65774567 | 00748761bdbd596499d1cccc5c5bdb373bcfe1c34ef0c4a3d03165dbcbae9387 |
| Spin_compact_005.zip | 114850845 | 26e262ab7a8c26b5a8f64bc269312743e342804ec9e7359d73b90dcc396689fd |

GitHub 单文件大小限制以及接口传输方式意味着**不能把这批 ZIP 的文件名写进 README 就视作完成备份**。优先补上 P0、P1a、P1b 原始审阅包；较大的离线构建包优先使用 Git LFS 或 GitHub Releases，避免污染源码 Git 历史。

## 新对话的恢复用法
告诉助手：**“从 https://github.com/volcano-code/Spin_test 的 research/CONTINUE_RESEARCH_HERE.md 接续，代码参考 upstream-spin-it-strict-computational-v2 分支；继续 Noodles v6 Cherchi C0/C1，未经批准不写入正式 Spin 仓库。”**

不要将旧的 CGAL 候选当作正式 Cherchi 优化完成，不要将原输出 OBJ 当成新版面条求解终态。
