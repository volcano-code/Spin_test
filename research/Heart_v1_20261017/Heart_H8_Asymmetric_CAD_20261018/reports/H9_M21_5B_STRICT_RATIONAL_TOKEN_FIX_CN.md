# W3 Heart H9｜M21.5B 精确有理数字符串合同修复

## 实际触发

用户 Ubuntu 本地执行 `test_h9_m21_3_lpi.py`，11 个测试中 9 个通过、2 个抛出 `ValueError: BAD_EXACT_RATIONAL_TOKEN`。此前已修复 `NameError: F is not defined`，这次错误与 Python 环境和 Cherchi 编译无关。

经检查，`source/h9_m20_precision_replay.py` 的 `rational()` 仅接受有明确分母的 `n/d` 字符串（如 `0/1`、`2/1`，不接受 `0` 或 `2`）。原测试夹具把 `str(F(0))` 用作输入，得到 `'0'`。此外，生产 `source/h9_m21_3_lpi.py` 在输出交点位置/速度及 c7 时也使用 `str(Fraction)`，遇到整数可重复触发相同故障。

## 本轮实际修改

- `source/h9_m21_3_lpi.py`：新增 `exact_token()`，把 `Fraction` 输出格式固定为 `numerator/denominator`；用于 `decompose()` 的位置/速度输出和真实数据样本的 c7 参数。**不放松严格解析器；不修改精确几何、Jacobian 或 Cherchi 求值。**
- `tests/test_h9_m21_3_lpi.py`：把两项线性/三次函数测试夹具改为正规 `n/d` 字符串；新增 `test_decompose_output_round_trips_through_strict_rational_parser`，检查位置/速度的可解析性及整数/半整数值。
- 提交1：`b9e67deb14adf8c30d0673196e41bc241f9da127`。
- 提交2：`f2511a46d0523fba9fea01c9950c4b8f584b69c6`。

## 已执行验收与严格边界

- 当前执行容器无法通过 DNS 获取 GitHub 的完整 checkout，且没有 W3 本机历史材料及所有完整依赖，因此**未声称完成 W3 的 12/12 真实完整回归**。
- 已实际在当前 Python 3.13 容器运行与本次修复边界等价的三项针对性 smoke：严格 `n/d` 解析/往返、线性函数零割线残差、三次函数符号残差；**3/3 PASS**。注意这些 smoke 是自包含复现，**不是**直接运行 W3 完整模块的官方回归。
- 原用户日志：修复前 11 项中 9 PASS、2 ERROR。修复后预期新增 1 项，要求用户本地对完整 12 项重新运行。
- 未执行真实六份 LPI 输入复核；未执行新 Cherchi Boolean；无连续分支/正式 Newton 准入或最终 Heart OBJ。

## 本地复核（不退出交互终端）

在 W3 仓库执行：

```bash
cd /data/xvxinyao1/Spin_test-W3
BRANCH="research/neuralmoments-w3-heart-h9-20261019"
git pull --ff-only origin "$BRANCH"
H9="research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018"
W3_PY="$HOME/.venvs/spin-w3-313/bin/python"
"$W3_PY" -m unittest discover -s "$H9/tests" -p 'test_h9_m21_3_lpi.py' -v
echo "M21_5B_TEST_EXIT_CODE=$?"
git rev-parse HEAD
git status --short --branch
```

**完整回归标准：12/12 PASS、0 errors、0 failures**。如通过，继续沿用仓库 `reports/H9_M21_5B_LOCAL_LPI_REPLAY_HANDOFF_CN.md` 的六份保存材料只读分析入口；需核实六份 `source-motion` 附件是否存在。即使 12/12 通过，也不能记作 18/18 真实 LPI 数据诊断通过。

## 云端或本地

本次源码/测试修复和提交完全可云端完成，已推送 W3 独占分支。**完整模块集成测试和六包真实诊断**目前应在有完整 W3 checkout / 已保存附件的本地执行，不需重新编译 Cherchi、不需 GPU、不需新的 Boolean。
