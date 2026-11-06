# W3 H9 M21.3　六点 LPI 运动离线核验

从 W3 仓库根目录运行。五个路径使用 M21 原有运行目录；SOURCE_RUN 指包含 layered-report.json 和 worker 子目录的 source 阶段输出。OUTPUT 指向一个尚不存在的 JSON 文件，父目录须已存在。

```bash
W3=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
python "$W3/source/h9_m21_3_lpi.py" \
  --precision-ledger "$M20_LEDGER" --artifact "$H8_ARTIFACT" \
  --stage17-native-dir "$STAGE17_NATIVE_DIR" --m19-run "$M19_RUN" \
  --source-run "$SOURCE_RUN" --output "$PWD/m21-3-lpi.json"
```

读取六份已固定 SHA 的材料及六份 M21 source-motion 附件。M21 监督器的报告给出 worker 报告摘要；worker 报告绑定各附件摘要；每个附件必须引用相同材料和同一核心二进制。材料、冻结请求、M20 ledger 与 M19 运行产物沿用 M21 的 SHA 核验。worker 报告的来源为操作者保存的历史运行，报告输出包含其 SHA 供外部核对。整个命令仅用 Python 标准库。

每份材料中按源身份寻找三个指定 LPI。设计边与源平面顶点均按编号升序。逐项核对 operand 坐标、已有求交构造的 Fraction 位置和速度、保存的物理交点与目标坐标。缺少任一构造或输入时程序报错退出。成功后输出 6 组样本 × 3 个诊断记录。

对于直线 X=A+t(B−A) 和过 C 的源平面，设 u=B−A，w=C−A，n 为按固定顺序构造的法向量。d=n·u，N=n·w，t=N/d。每行同时报告：

- 原始 d、d′、N、N′、t、t′、|d′/d|、|t′|、物理交点和速度。
- 商法则分解 t′=N′/d−t d′/d，其中两项分别对应该行 t_prime_numerator 和 t_prime_denominator。
- 同一 t′ 的隐式约束分解，分别为法向变化 n′·(C−X)/d、平面锚点 n·C′/d，以及直线运动 −n·(A′+t u′)/d。两套分解是对同一个数的两种分组，分别求和。各项精确相等通过后才记入报告。
- incidence_squared 及 speed_squared 为准确有理数；incidence_approx 与 speed_approx 是便于阅读的平方根近似。尺度无关入射指标只反映几何角度。

本轮新增 9 项合成测试全部通过。另有 24 项既有合成回归用例通过；既有真实证据测试类缺少冻结 H8f ZIP，未能运行。用户的六包及对应源速度附件待原机回放，当前新增真实记录为 0/18。该诊断比较六个离散样本上给定源速度的传播；源速度本身、连续邻域、Newton 准入仍待单独验证。

```bash
python -m unittest discover -s "$W3/tests" -p 'test_h9_m21_3_lpi.py' -v
```

## M21.3.1 补充：同侧区间逐特征割线残差

在六份材料逐点 LPI 分解之外，输出增加左右全区间、前半区间、后半区间的三个候选构造逐特征残差。位置和速度使用物理坐标系中的 Fraction 字符串，保留有符号残差；同时提供范数近似与非零端点平均速度下的相对残差近似。该结果用于检查各 LPI 的残差是否与组内最大值一致，仍然只是六个离散样本的诊断。

新增两项合成测试：线性位置映射的六个区间残差必须精确为零；三次位置映射用于验证全区间与两个半区间的有符号残差和顺序。新增测试不调用 Cherchi，也不替代六份真实材料的本地运行。
