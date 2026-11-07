# W3 Heart H9｜M21.5B 精确分数平均权重修复

## 问题证据

用户 Ubuntu W3 工作站最新运行回归：12 tests, 10 PASS, 2 ERROR。
异常出现在 `source/h9_m21_3_lpi.py` 的 `same_side_interval_residuals`：
```
TypeError: frac() takes 1 positional argument but 2 were given
average = mul(frac(1, 2), add(va, vb))
```

`source/h9_m21_motion_math.py` 的 `frac(x)` 只接收一个参数，
内部调用 `h9_m20_precision_replay.rational(token)` 解析 `n/d` 格式。
`frac(1,2)` 是误把函数当作 Python `Fraction(1,2)` 使用；这不是新的 Boolean/几何/导数科学发现。

## 修改

把上述错误行最小替换为：

```python
average = mul(frac('1/2'), add(va, vb))
```

它使用与严格解析器一致的精确有理数 1/2，不调用浮点 `0.5`，不改变任何物理公式、历史材料、原始容差或 Newton 门禁。

修改文件仅为：
`research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/h9_m21_3_lpi.py`。

提交：`df2621d8ca9074d92c3dd780055378a1e2eea0b0`。

## 实际测试边界

当前云端模型容器无法 DNS 获取完整 GitHub checkout，也未连接 W3 的本地原始材料。
已使用与生产修复路径相同的 `Fraction` 严格 token `1/2` 和分段函数复现
运行 **2/2 isolated smoke PASS**：

1. 线性位置/速度：左右六个区间残差均 0。
2. 三次位置/速度：左右区间残差均为 `-2, -1/2, -1/2`。

**该结果不等于** W3 完整 `test_h9_m21_3_lpi.py` 的 12/12 回归已运行。
用户上传的修复前实际日志为 12 tests、2 errors；修复后完整回归还需在 Ubuntu 运行。

## 下一步：本地无需重新编译

```bash
cd /data/xvxinyao1/Spin_test-W3
BRANCH="research/neuralmoments-w3-heart-h9-20261019"
git pull --ff-only origin "$BRANCH"
H9="research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018"
W3_PY="$HOME/.venvs/spin-w3-313/bin/python"
"$W3_PY" -m unittest discover -s "$H9/tests" -p test_h9_m21_3_lpi.py -v
RC=$?
printf 'M21_3_TEST_EXIT_CODE=%s\n' "$RC"
git rev-parse HEAD
git status --short --branch
```

期望：12 tests、0 errors、0 failures、退出码 0。命令不含主动退出 shell 的 `exit`。
通过后仍需在本地运行既有的六份原生保存材料 × 3 个 LPI 构造的只读诊断，
其输入和步骤见 `reports/H9_M21_5B_LOCAL_LPI_REPLAY_HANDOFF_CN.md`。

## 科学结论与资源要求

- 新的六份原始材料诊断：本轮 0/18。
- 新的 Cherchi Boolean / build：0 次；不需要重新编译或 GPU。
- 连续构造分支认证：未完成。
- Newton 准入：false；最终 Heart OBJ：未产生。
- 修改、提交和隔离测试能在云端完成；真实材料只在本地保存时，必须本地执行读取。
