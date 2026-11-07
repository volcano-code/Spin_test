# W2 M23-P2 — 本地 /data 精确材料恢复扫描审计

**审计日期：** 2026-11-07  
**源文件：** 用户上传的 `W2_M23_RECOVERY_REPORT.txt`（928 bytes）  
**源文件 SHA-256：** `a250755ccbc428c6581fcd22fbc3d07ae491ef9a52462eb6844902dc1573a4a1`  
**目标分支：** `research/neuralmoments-w2-teacher-20261019`

## 结论

**目标 V7 六份历史精确有理 CSG 输出的原始字节依旧 0/6 恢复。** 本次 `/data` 扫描报告列出两份同名 `*-rational.json` 文件，但 SHA 与历史 V7 目标完全不匹配。不能将它们当作冻结 V7 的 Design 或 Fixed。其余四个目标文件未出现在本次限定名称扫描结果中；指定名称的 CGAL 可执行文件及限定文件名的压缩包也未报告命中。

## 本地报告中实际观察到的两个候选

两者均位于 `.../experiments/faster_core_repair_20261012/noodles-balanced-full-input-job-01/output/`。完整绝对路径仅保留在用户本地原始 TXT；此 GitHub 记录仅保存相关实验目录后缀。

| 文件 | 本地报告 SHA-256 | V7 冻结 SHA-256 | 分类 |
|---|---|---|---|
| `design-rational.json` | `d0aec854f2207f2b8abad99507e915fc86ce0b6055ef07a7a3b0a20c3a1eb7f7` | `48e8d3008bba746823eafd9c3704b52d597595b802066450a921ecc0dcb7f611` | **DIFFERENT_SHA** |
| `fixed-rational.json` | `a0e18f72355a0cd9b208c35bbb7aac195ce93401615125ef805a9935393a8953` | `71f9df91fca12fde4f4f2c80dc26e2d1229e8209e09db46e680d0de7baee264a` | **DIFFERENT_SHA** |

没有报告命中的目标：`envelope-rational.json`、`fixed-inside-envelope-rational.json`、`fixed-outside-envelope-rational.json`、`initial-rational.json`。

**证据层级：** 当前只有来自本地 `sha256sum` 的 TXT 记录。云端没有拿到这两份候选 JSON 的字节，因此未能独立复算它们的哈希，也没有审阅其几何内容。它们位于早期 Balanced Noodles 实验路径，但不能仅凭路径确定完整几何谱系。

## 扫描范围限制

上传 TXT 来自此前约定的 `find /data` 命令：只查指定六种 basename、完全等名 `noodles-exact-boolean` 后端、以及文件名中含 Noodles/V7 的少数压缩包模式。故本次“未找到”不是对其他文件名、其他压缩格式、其他数据盘、历史容器或无名备份的全盘不存在证明。

## 本轮代码与 CI

新增 `m23_p2_recovery_report_audit.py` 和 `test_m23_p2_recovery_report_audit.py`，读取用户本地扫描 TXT 时 fail-closed：

- 严格绑定 `FOUND: <path>` 与紧随的 SHA256 文件路径；
- 区分历史 SHA 相同、不同与完全未报告；
- 只有显式 `--verify-local-files` 在同一主机实际重新读取目标文件时，才标注 `LOCAL_BYTES_REHASHED`；
- 无论仅报告 SHA 如何，都不向训练集释放样本；
- 拒绝缺失 SHA、路径错配、截断报告。

GitHub Actions workflow: `.github/workflows/w2-m23-p2-recovery-report-audit.yml`。
- 首次 CI run `42382957999`：**5/6**，一项负向错误码文案不匹配，未通过；已按预期改为精确 `FOUND_PATH_MISSING_SHA`；
- 第二次 CI run `42383006185`：**6/6 PASS**，0 failures、0 skips。纯软件测试，不运行 CGAL 或 Cherchi。

## M23-P2 下一步

1. **避免误用早期 Balanced 文件：** 不将 `d0aec...`、`a0e18...` 写入 V7 六份冻结材料清单，也不以它们替换 `48e8...`、`71f9...`。
2. **本地进行归档拓展搜索：** 以 `/data` 为主，优先检查旧实验目录和 Spin_test-W2 等仓库外的归档，查找不同命名的 `.tar`、`.tgz`、`.tar.zst`、`.7z`、`.zip`、`.rar`，以及可执行文件的不同名字；将结果汇总成一个小 TXT 而非贴满终端。发现候选先按字节 SHA 核对。
3. **仍无法找回时：** 以新实验身份恢复完整冻结 V7 94 源部件并重新生成六份精确 CSG 输出。必须保留每一步原生执行记录、版本、哈希和输入输出。若结果 hash 与历史不同，记录为新的变体，不可冒称历史恢复。
4. **科学验收门保持不变：** 六份材料字节、独立实体嵌入/Boolean 关系、binary64 分区适配、W0/W3 导数邻域、Newton 验收；`J_D=null`、训练样本 0、`split=excluded`。

**云端判断：** 报告分析、SHA 验收程序、CI 和重建执行器的开发都可在现有云端完成。**本地判断：** 大型原始文件、精确 CSG 的全量执行与原生 Cherchi 教师需要 /data 本机和合格原生环境。此次没有进行任何新 CGAL/Cherchi 求值。
