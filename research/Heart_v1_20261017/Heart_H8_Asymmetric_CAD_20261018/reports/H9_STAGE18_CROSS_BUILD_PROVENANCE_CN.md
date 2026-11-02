# W3 H9 第十八阶段：四份新原生材料的跨构建身份合同修复

## 真实材料与故障

用户在 Ubuntu 24.04 / 60GiB 系统上运行新 W3 Stage17 原生探针，真实记录：

- `H9_REAL_NATIVE_SIDE_PROBE 0 left-coarse 1`、`1 left-near 1`、`2 right-near -1`、`3 right-coarse -1`。
- 左右侧有限构造分别与历史 H8f sample59/sample60 符号身份匹配。
- 内层独立审计 `INDEPENDENT_AUDIT_FAILED_NO_ADMISSION`，报错 `UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE`。
- 四份 `side-XX` 新材料已由用户本机探针成功写出，但本报告没有接触到用户本机材料原始字节，不能宣称独立复核成功。

历史 H8f artifact `12135528290` ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`，CI 原状态 `failure`。本轮重新读取其 sample59 和历史二进制哈希：

- 历史 `_make_it_stand`：`ad0c4fe3527954c611743dbbccb384cc1521909e8a39d68c3b7554b3a3919d40`；用户新构建：`d66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd`。
- 历史 `_cherchi_core_boolean`：`3cc8bf789168752f8b921c160ca9937cdf0f61c845d3088760811b9e5a4596b7`；用户新构建：`9e04eb5b61767563c988a1e00a68f76b294c4c16ecc262c4220f8b49ae1c51b0`。
- `_cherchi_rational_moments` 新旧 SHA 相同：`ed05436e2796b190ddebb024f67318e2e88bdc46d96b01e9d7db71a6af080dca`。

生产端 `InProcessCherchiEvaluator.context_identity` 包含上述原生二进制 SHA，故跨构建比较时无条件要求 `evaluation_map_identity` 与历史 H8f digest 相同是不正确的。本阶段**不能仅凭失败码断定它是唯一差异**，因旧码把多个条件合并；验证本机真实材料需运行新的独立审计。

## 代码改动和保留的严格准入

`source/audit_h9_new_native_sides.py`：

1. 删除独立验收中“新 Map digest 必须等于历史 H8f”的无条件硬约束；保留历史记录但与新的 Map digest 分开报告。
2. 核对**本次** `_cherchi_core_boolean` 完整 SHA 对应的 `boolean_backend_identity`，不再只接受任意具有正确前缀的 backend。
3. 核对本次 GMP 算术模块 SHA、固定算法名、相同 Boolean 操作、有效导数及导数身份。
4. 核对四份新 side 必须拥有**同一份** `evaluation_map_identity`，并且该值是 64 字符小写 hex digest；中途更换求值器拒绝。
5. 新输出保留 `evaluation_map_identical_to_historical_h8f` 供追踪；新旧二进制哈希不同时 `cross_build_same_semantic_baseline_admitted` 按原逻辑仍为 False。无连续邻域与 Newton 准入。

`tests/test_h9_stage18_cross_build_provenance.py`：使用**真实 H8f sample59** 作为 fixture，在明确标记的测试对象上模拟新 Boolean SHA / 新 map SHA；不会冒充新真实原生结果。

## 真正完成的本地验证

- Stage18：12/12 PASS（历史 H8f ZIP SHA256 精确匹配）。
- Stage5 原有合同：9/9 PASS（真实 59/60 材料独立 Fraction 十矩复验，无跳过）。
- Stage6 原有合同：12/12 PASS（原始历史材料 Jacobian 与有限单侧检查，无跳过）。
- 合计 **33/33 PASS**。尚未运行用户本地实际四份材料的修复后独立审计，不能报告 4/4 合格。

## 不需要重复昂贵的四点原生求值

保留用户已有 `native-4side-s17/serial-native/native` 原始材料不动。只需升级 W3 到本提交，然后用修复后的审计器在**全新路径**重新独立验证：

```bash
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$H9/source/audit_h9_new_native_sides.py" \
  --artifact "$ARTIFACT" \
  --certificate "$CERT" \
  --native-dir "$W3_NATIVE_S17/serial-native/native" \
  --output "$RUNROOT/stage18-independent-audit.json"
```

该独立审计会大量使用 Fraction 十矩积分。若审计仍失败，检查新输出 `reason`，不要修改/覆盖原先失败日志，也不要伪造成功的旧 `launch_result.json`。若通过，仍然只算“后验四点有限材料验收”，不是新的同构建历史证据、连续性证明或 Newton 收敛。
