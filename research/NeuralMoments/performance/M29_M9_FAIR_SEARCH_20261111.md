# W1 M29：M9 基准定位的搜索覆盖修复（2026-11-11）

## 本地日志支持的结论

用户报告 `directories_scanned=20000`、`limit_reached=true`、`depth_cutoffs=3013`、`symlink_directories_not_followed=1231`，只检查了三个报告，均因 `WRONG_SCHEMA` 被拒绝。`roots` 仅包含 `/data/xvxinyao1/Spin_test-W1` 与 `/home/lin`；第三个请求根 `/data/xvxinyao1` 未开始。没有命中不等于文件已删除，空的压缩包候选列表也不代表全盘没有备份。

在基线提交 `e05e1e9cfdebae3b735f6d2ea95f1edd184261d5` 的定位器中，所有根共用开始时间和目录计数；达到任一上限后退出外层根循环。按目录名排序的深度优先遍历，还可能在扫描浅层实验目录前消耗大量预算。本次不修改历史代码及证据，新增一个公平分配搜索预算的工具。

## 本轮实现

`m29_locate_m9_baseline_fair.py`：

- 每个可用的独立根目录分别分配目录数和时间上限，前一根触及限制不会阻止下一根。
- 优先浅层，再深入；同一深度优先原运行名及 W1/M9/实验/备份相关名字。
- 复用原有 `validate_report()`，不放宽格式、二进制或材料身份条件。
- 将原路径状态、每根目录扫描量、未扫描队列、深度限制、目录条目限制、跳过项和读取错误写入结果。
- 相关软链接只列出路径及链接目标，不自动递归跟随。用户显式给出的根目录可解析为链接目标。
- 相关压缩包只列文件名线索；不解包、不认定其中存在合格报告。
- 不调用原生扩展，不重跑 M5/M9/有限差分，不生成替代基准，不移动或删除原文件。

这是仍然有边界的文件定位，不是全盘法证恢复。报告必须是已保存的文件；原报告的独立文件 SHA 未提供，匹配已知字段也不等于完整证据认证。每个结果列表最多记录 200 项，多余数量在 `truncated_lists` 中明示。时间上限是协作式检查，不能中断卡住的文件系统调用。

## 实际测试

在工作容器 Python 3.13.5 中实际执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v \
  test_m29_locate_m9_baseline.py test_m29_locate_m9_baseline_fair.py
```

结果：28 项测试全部通过，其中旧定位器 11 项、新增 17 项。日志保存在 `m29-fair-baseline-recovery-tests.log`。新增回归用例在合成文件树上直接复现旧工具耗尽第一个根配额、漏掉第二个根内报告的行为；相同输入下新版找到该合成报告。其他用例覆盖浅层优先、原运行名优先、时间预算重置、软链接环、断链、缺失根、重复根、深度和条目上限、FIFO 不读取、归档不解包、只读性、以及错误 schema 仍被拒绝。

这些测试不是本地 M9 材料已找回的证据，也没有新的科学实验结果。

已测试新版源码 SHA-256：`c5f259d7925eff2bfc9dbeba961e296854355d4ff9dfb04b8650f1c633c0d07d`。
已测试新增测试源码 SHA-256：`c7b24f90539e6247573828006bcb65f2ba0432f55520c720b6dec3ced8750484`。
实际测试日志 SHA-256：`07b0a1764de4e236cf0069310e52260da8a80b13bbd9cd3dd00b784abbd55880`。

## 本地使用

```bash
PERF=/data/xvxinyao1/Spin_test-W1/Spin_test-w1/research/NeuralMoments/performance
PYTHONDONTWRITEBYTECODE=1 python3 "$PERF/m29_locate_m9_baseline_fair.py" \
  --known-run "$HOME/w1-m29-m9-fixed-20261108-181458" \
  --root /data/xvxinyao1/Spin_test-W1/experiments \
  --root "$HOME" \
  --root /data/xvxinyao1 \
  --root "$HOME/Research" \
  --root "$HOME/.local/share/Trash/files" \
  --max-depth 8 --directories-per-root 12000 --seconds-per-root 20
```

`Research` 和回收站路径仅是显式检查的位置，不是已确认的新存储位置。不存在的根会登记并继续。输出 JSON 应写到 `/data/xvxinyao1/Spin_test-W1/experiments/recovery/` 下的新文件，不覆盖前次搜索结果；前次资源快照中 `/home` 只有 3.8 GB 可用。

退出 0：存在已知字段匹配候选。退出 2：限定范围未找到。两者都不会触发原生计算。优先检查 `matches`，其次 `symlink_leads`、`archive_candidates_not_opened`、`run_directory_leads`、`root_summaries`。

## W1 状态边界

本轮只修复证据定位过程；M9 原报告当前实际位置仍未确认。原有六个方向的局部有限差分记录不因搜索限额而失效，但完整九维导数、光滑邻域、Newton 和完整求解器加速仍未验收。所有修改仅进入 W1 分支的 performance 子目录。源代码与测试可在云端完成；用户机器上的文件定位和后续原生诊断需本地执行。
