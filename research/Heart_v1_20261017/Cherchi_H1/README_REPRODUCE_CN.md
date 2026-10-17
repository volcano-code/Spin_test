# Heart Cherchi H1 可复现实验

该压缩包提供 2026-10-17 **历史 V4 代理输入**上的 Cherchi 动态 Boolean 研究，不是 2014/2024 作者 Heart CAD，不是完整原生 Heart Newton 优化。

## 文件与快速验收

- `H1_STAGE_REPORT_CN.md`：中文结论与限制。
- `H1_STAGE_STATUS.json`：机器可读判定。
- `input/heart_v4_proxy_fixture.json`：代理设计域及保留的 eval60 二次曲面系数。
- `source/cherchi_heart_guard.py`：Cherchi 真后端、材料有理数、精确与浮点导出资格门。
- `source/run_heart_h1.py`：源面 → Cherchi → 独立几何审核 → 有理数证据封存。
- `source/run_authoritative_eval60_cherchi.py`：需要真实历史配置和事件日志，SHA 不匹配明确拒绝。
- `source/compare_independent_exact_set.py`：**独立只读**实体比较，不替代 Cherchi 生产 Boolean。
- `output_proxy_v1/cherchi-authoritative-exact.json`：真实 Cherchi 精确输出，有理数坐标与构造来源（非可打印 OBJ）。
- `evidence/independent-exact-set-comparison.json`：与同操作数参考实体双向包含，对称差体积 0/1。
- `evidence/rational-output-audit.json`、`evidence/proxy-cherchi-full-audit.json`：精确有理数与 binary64 两份审核；**后者 78 对自交而失败**。
- `evidence/pytest-all.log`：16 项本地测试通过。

### 无原生依赖的测试

```bash
python -m pytest -q tests
```

### 使用自己编译的 CPython 3.13 Cherchi/Core 原生模块进行独立重放

```bash
export PYTHONPATH="<path-to-core-native-module>:<path-to-cherchi-native-module>:$PYTHONPATH"
export LD_LIBRARY_PATH="<path-to-required-cherchi-runtime-libs>:$LD_LIBRARY_PATH"
python source/run_heart_h1.py \
  --fixture input/heart_v4_proxy_fixture.json \
  --output /tmp/heart-h1-new-run
```

脚本必定要求 `_cherchi_core_boolean`，不会回退到 CGAL。请校验新编译模块的 SHA、比较科学结果和历史证据，不得直接将不同编译版本的耗时或结果标记为一致。浮点导出不合法时，只保存有理数材料 JSON，不生成成功 OBJ。

### 原始 eval60 认证重放（真实历史输入目前缺失）

```bash
python source/run_authoritative_eval60_cherchi.py \
  --registration <historical-registration.json> \
  --configuration <original-configuration.json> \
  --events <original-events.jsonl> \
  --out /tmp/heart-eval60-replay
```

登记中规定配置 SHA 为 `071c799c92b522fb3d4de4b9aacf9a9ae8bcae102a49940f33f4037f28a74141`，事件 SHA 为 `2333a9e3c87d9e6b7d3a73676fe9bd940f6e500c9c20b7ce34867d2475269b70`。没有这两份原始文件时必须拒绝，不能用 V4 代理数据代替。

**归档不打包原生二进制**，不提供作者原始 CAD，也不以原生通过作为最新源码重编译通过。正式 Cherchi/Faster 的完整 Heart、源动导数 81 点门、材料 Jacobian、终态修复和物理仿真仍需后续验收。
