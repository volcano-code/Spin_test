# W3 M21.6B｜5844 位精确有理数令牌解析/输出修复

## 用户本地真实失败

用户在 `--phase native-layers` 运行中已成功读取六份原始材料和 source-motion 附件，并进入 `compute()` 的 M20 精确十质量矩核对阶段。随后 Python 3.13 默认安全限制拒绝转换 5,844 位分母：

```
ValueError: Exceeds the limit (4300 digits) for integer string conversion:
value has 5844 digits; use sys.set_int_max_str_digits() to increase the limit
```

触发位置是 M21.6B `q()` 中的 `int(bits[1])`。这是 Python 全局 int 字符串转换保护与历史精确账本尺寸不兼容，不是数据 SHA 不匹配、不是内存不足，也不是 Cherchi/Boolean 问题。

## 修复

- 新增 `_parse_decimal_integer()`：对最多 100,000 字符的受限 ASCII 数字串按 1,000 位分块转换，再用整数乘加组合；不调用 `sys.set_int_max_str_digits(0)`，不修改解释器全局安全阈值。
- `q()` 对分子、分母均使用分块转换，仍严格要求 `n/d` 格式、ASCII 数字、分母正数；拒绝双负号、显式加号和负分母。
- 新增 `_format_decimal_integer()`：使用 base=10^1000 的 divmod 分块格式化任意精度整数；避免输入成功后 `token()` 在 f-string 转十进制时再次触发 4,300 位限制。
- `token()` 对分子和分母均使用该 formatter。
- 回归测试覆盖 5,844 位分子、5,844 位分母、负号、严格往返以及畸形符号拒绝。

## 实际测试

本轮在隔离 Python 3.13 环境运行了完整 M21.6B 测试集：

- **15/15 PASS**，0 failure、0 error。
- 5,844 位分子/分母解析及往返通过。
- 确认 `sys.get_int_max_str_digits()` 仍不低于 4,300，未全局关闭保护。
- 测试代码与本次 W3 分支所提交内容相同；该测试在云端隔离副本运行，尚未在用户本机运行最新版本。

## GitHub 修改

- 分析器 `source/h9_m21_6b_moment_layers.py`。
- 测试 `tests/test_h9_m21_6b_moment_layers.py`。
- 保留失败日志，不修改历史 ledger、原始材料、SHA 门禁、几何合同或 Newton 门槛。

## 下一步本地重跑

先同步最新 W3 分支，然后执行 15 项测试。成功后复用原来的 M20/ART/S17/M19/SOURCE/BOUNDARY 输入路径，**必须新建一个新的输出目录**。上一次失败的 `m21-6b-retry-20261108T062019Z-3084537` 保留不动。

本次失败发生在矩积分/比较之前；此前的六份材料读取与 source-motion 绑定已成功。因此修复后只需重跑 CPU 精确算术分层阶段，不需要新的 Cherchi Boolean、不需要 source-only 原生调用、不需要重新编译或 GPU。

## 科学状态

尚未得到成功的 `moment-layers.json`。因此 60 个真实矩/区间分解尚未验收，J7 根因未确定，连续构造邻域未认证，Newton 未准入，最终 Heart OBJ 未生成。
