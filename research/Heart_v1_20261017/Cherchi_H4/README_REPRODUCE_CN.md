# Cherchi Heart H4 — 准确、可复验的 V4 代理网格修复

这是一套通用的“保持有理几何的局部共面凸四边形换边 + 全局有向面链证明 + 原生两种边界验收”程序，但**已认证成功的具体输入仅是 H1 历史 V4 代理 Heart**。程序**不会**执行新的 Cherchi 动态布尔，也不会使用 CGAL 代替 Cherchi 正式优化，更不会宣称是论文作者 CAD 或完整 Newton 结果。

依赖：Python 3.13、NumPy、pytest；以及与项目源码/运行时一致的 `_make_it_stand` 原生几何审计模块（需支持 `audit_exact_triangle_boundary` 和 `audit_exact_rational_triangle_boundary`）。在原 `Spin_test` 独立 Heart 分支中，H1 的权威输入位于同级 `../Cherchi_H1/`，本目录包含完整输出和测试证据。

```bash
# 工作目录为 research/Heart_v1_20261017/Cherchi_H4
python source/certify_h4_retriangulation.py \
  --material ../Cherchi_H1/output_proxy_v1/cherchi-authoritative-exact.json \
  --binary-audit ../Cherchi_H1/evidence/proxy-cherchi-full-audit.json \
  --rational-audit ../Cherchi_H1/evidence/rational-output-audit.json \
  --output /tmp/heart_h4_replay_01

python source/verify_independent_global_moments.py \
  ../Cherchi_H1/output_proxy_v1/cherchi-authoritative-exact.json \
  /tmp/heart_h4_replay_01/faces.json \
  /tmp/heart_h4_moments.json

python source/classify_binary64_plane_sign_changes.py \
  --material ../Cherchi_H1/output_proxy_v1/cherchi-authoritative-exact.json \
  --binary-audit ../Cherchi_H1/evidence/proxy-cherchi-full-audit.json \
  --rational-audit ../Cherchi_H1/evidence/rational-output-audit.json \
  --output /tmp/heart_h4_side_events.json

python -m pytest -q tests
sha256sum /tmp/heart_h4_replay_01/v4-proxy-cherchi-retained-material-retriangulated.obj
```

要求摘要：
- 真正 H1 输入文件 SHA-256 经脚本固定匹配，否则拒绝运行。
- 所有新增或改变的三角面必须来自合法的 **精确凸共面二面换边**；局部有向边界、十项有理矩完全一致。
- 全球有理支撑面有向边界链零差异；本地原生 exact rational 及 roundtrip binary64 审核同时通过。
- 原历史浮点自相交数 78，修复后为 0；新增 38 次换边，最终仅 64 个原面记录发生变化，顶点不变。
- OBJ SHA-256 `09d98c0ec66f79aa4a927281da204f94cbf4d66d53fb79a97fade7295d9dd5cd`。

历史失败日志/非通过试验保留在相关来源中；本目录仅包含**成功复现**的最终 H4 数据以及必要的测试运行日志。`final_certified/` 仅合格于这份 V4 代理材料，不得贴上论文 Heart 实际优化完成或可打印的标签。
