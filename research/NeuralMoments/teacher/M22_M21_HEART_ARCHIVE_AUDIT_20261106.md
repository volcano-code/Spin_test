# W2 M22-P1：Frozen Heart M21 原始运行归档审计

**审计日期：** 2026-11-06
**分支：** research/neuralmoments-w2-teacher-20261019
**目标运行 ID：** heart-pilot9-flex-20261105T083338329274558-3159689
**审计对象：** 用户上传的 M21_HEART_NATIVE_EVIDENCE_20261105.tar.gz
**原始归档 SHA-256：** 259b9f288b629415bafa42e4e09d6503e4f474e0e2253e6cc9eb1cd775a64dfd
**归档大小：** 1,423,726 bytes

## 1. 三项目标原始材料均已找回

| 目标 | 状态 | 审计结果 |
|---|---|---|
| heart-pilot9-flex-20261105T083338329274558-3159689/ | FOUND | 完整目录在归档内 |
| m21-flex-20261105T083338329274558-3159689.log | FOUND | 5,783 bytes |
| m21-m22fix-20261105T083338Z-2114359.log | FOUND | 5,783 bytes |

两个外层日志 SHA-256 均为 ebcb505b1c070a86c5750b8c7dfb3eabb3abb938ac81b8076547d993436e4dbe，字节完全相同。它们是同一执行输出的重复捕获，不是两次独立实验日志。

## 2. 运行目录内文件清单

| 文件 | 大小 | SHA-256 / 状态 |
|---|---:|---|
| M21_PILOT_RESULT.json | 4,396 B | f84b38c326bc4fd79068d5a89f94500bb60306c5a77289a550a278355dd89dc3 |
| M21_PILOT_LABEL.json | 103,718 B | 747101c819d95959020a39ea54eec5af280fd465b786c3f94312bb7447136729 |
| M21_PILOT_SPEC.json | 6,309,429 B | 4d3cb03ee3a1190142638a99cd90e6aaf0a3e7030b956ef813ebabeb0c6898d0 |
| M21_PILOT_PREPARATION.json | 1,886 B | 已纳入 SHA256SUMS |
| frozen_heart_preparation.json | 6,309,213 B | 已纳入 SHA256SUMS |
| frozen_normalized_outer.obj | 1,510,016 B | cde5dbdf894c181c27abf22abe8bce8b82a2a3a68b141cfb24749ef07e864062 |
| M21_NATIVE_STDOUT.log | 365 B | 已纳入 SHA256SUMS |
| M21_NATIVE_STDERR.log | 0 B | 文件存在，内容为空 |

另有根目录的 FILE_INDEX.txt、MISSING_FILES.txt、SHA256SUMS.txt 和两份外层日志。

## 3. SHA 与跨文件身份校验

原始 SHA256SUMS.txt 中的 12 项全部重新计算并通过。另完成以下校验：

- M21_PILOT_SPEC.json 的实际 SHA 与 M21_PILOT_PREPARATION.json.spec_sha256 一致。
- M21_PILOT_RESULT.json.label_sha256 与实际 Label 文件 SHA 一致。
- Label 内 canonical payload SHA 与 payload_sha256 一致。
- Spec 的模型 SHA 与归档中的 frozen_normalized_outer.obj 实际 SHA 一致。
- Label 的 native_c、模型 SHA、原生模块 SHA 与 Spec 对应字段一致。
- Label 的 q identity 和 geometry identity 摘要均通过重新计算。
- frozen_heart_preparation.json 的 H8f 原始归档 SHA 为 99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9。
- Frozen preparation 中的 request/evaluator settings 与 Pilot Spec 对应对象一致。
- Spec、Result cgroup scope、Native stdout 和两份外层日志中的运行目录/时间戳/PID 对应同一目标运行。

## 4. 原始运行报告中记录的结果

- status=PILOT_EXACT_TEN_MOMENTS_PASSED_DIAGNOSTIC_ONLY
- native_cherchi=true
- same_call_attachment_present=true
- 十个预声明绝对误差预算均为 1e-10
- 十个绝对误差均为 0.0，within_tolerance=true
- topology_status=OBSERVED_DISCRETE_MAP
- derivative_status=UNKNOWN
- J_D=null
- split=excluded
- training_admitted=false
- 原生子进程退出码为 2，原因是明确的 W0_VERIFIER_AND_INDEPENDENT_SOLID_PROOF_NOT_VERIFIED 排除状态；外层 Pilot 将其标记为数值诊断通过。
- 外层 wall time：8.551563279 s；报告内存峰值：657,793,024 bytes；OOM/OOM-kill 事件均为 0。
- source_and_module_postflight_verified=true，postflight_errors=[]。

这确认归档中的记录与之前粘贴的终端摘要一致；本审计没有重新运行 Cherchi。

## 5. Same-call material attachment 的边界

Label 内存在 same_call_attachment 描述对象，包含 schema w2-same-call-material-binding-v1、serialized_material_sha256 b136cbcc09740915cd70615d73fab3ab2aa0b680cdb823cfed12375bed6c20e8、native-c SHA、系数顺序和 producer validator 来源。

但归档中没有单独的 serialized material payload 文件，也没有找到与上述 SHA 对应的原始材料字节。Label 另存了十项 exact-rational reference moments、边界 SHA 48aae36777ed15e705f1ab919edac07756d3a7444100c060ee5baabd310afe20、8455 顶点和 16910 面的计数；这些不能替代完整输出边界顶点/三角面数据。

因此：同次附件的描述及生产端校验结果记录存在；完整同次材料几何的字节级重放仍缺材料 payload。

## 6. 缺件与注意事项

1. 原 MISSING_FILES.txt 将 M21_NATIVE_STDERR.log 列为缺件，是因为打包脚本用 test -s 要求文件非空。该路径实际存在，大小为 0，SHA 是空文件标准 SHA；这是缺件清单的误报。
2. 两份外层日志完全相同，不是两份独立日志。
3. 三个已记录的原生模块 SHA 在 preparation JSON 中，但三个编译 .so 文件本身没有打包；外部 native_modules_exact_20261104T054311Z-2114359.json 也未包含。
4. 外部 heart_pilot_budgets.json 未包含；Preparation 记录其 SHA-256 为 36020dd4871eac10948a3c322ccc212666b42ebf60e40db2bc15611ba0f7c87d，但十个 1e-10 容差也已经写入 Pilot Spec。
5. Frozen preparation 明确记录 model_is_original_CAD=false；本次使用冻结 H8f 重建模型，不能据此声称它是作者原始 CAD。
6. 原始 H8f workflow 的历史 failure 状态仍保留；本次单点物理矩诊断通过不等于 H8f 81 点工作流整体成功。

## 7. 审计结论

**M22-P1 原始归档完整性：通过。** 目标运行目录、两份日志、Result、Label、Spec、冻结准备文件、模型 OBJ、stdout/stderr 均已找回；归档内 SHA256SUMS 和关键跨文件身份关系全部通过。

**M22 完整独立回放：部分受阻。** 缺少实际 same-call serialized material payload、编译模块二进制及外部模块清单。可以对已存 JSON/Spec/OBJ/精确矩证据进行进一步独立核验，但不能仅凭当前归档重新执行完全相同的 Cherchi 原生调用。

保持 J_D=null、split=excluded、训练样本 0，直到 solid embedding 与 W0/W3 导数准入完成。