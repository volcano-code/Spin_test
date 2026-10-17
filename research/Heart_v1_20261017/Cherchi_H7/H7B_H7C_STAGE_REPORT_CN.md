# Heart H7b/H7c 阶段报告：25 点真实 Cherchi 重放协议与计时入口（2026-10-18）

## 已提交实现
- `source/replay_25_cherchi.py`: 严格恢复 H6 的历史 V4 输入，逐点执行真正 `_make_it_stand` 源面与 `_cherchi_core_boolean`，验证原生库 SHA-256、H6 注册的全部源面指纹与输出 Cherchi 构造指纹；每个输出使用原生 **有理数** 合法边界/自相交审核。归档 25 份完整 packet、源操作数及 SHA-256。
- `source/verify_replayed_packets.py`: 读取归档 packet，校验所有 25 份 SHA-256、Cherchi 后端、H6 构造摘要及每点面片标签，并重新分类 24 个扰动。**不重新运行原生几何合法性检查**，保存的审核证明只是由归档记录，不能把离线复核当作独立原生审计。
- `source/summarize_stage_profile.py`: 对现有 `source/profile_native_stages.py`（前一阶段）输出进行真实墙钟/CPU/各阶段中位耗时统计；仅两后端材料指纹与 Jacobian 差异准入后才公布 A/B 速度比。统计中位速度比属于硬件及输入绑定的描述性指标，并非论文求解器加速比。
- `tests/test_h7bc_contracts.py`: 纯 Python 正例与篡改拒绝回归，GitHub Actions H7 workflow 自动收集测试结果。

## 当前保守结论
* 目前本执行环境**没有历史原生动态库**，所以本次未执行 25 个点真实 Cherchi 重放、未产生新的原生计时。上述原生数据只能在具有与 H6 匹配二进制的主机实际运行后产生。
* H6 22 处特征哈希变化仍**没有**得到几何等价或分支连续证明；历史 25 点数值误差不能自动变成正式 Jacobian 认证。
* 原始 Heart `eval60` 所要求的 `configuration.json` 和 `events.jsonl` 仍未恢复；H7b 是历史 V4 **代理**重放，不是正式 Heart 程序复现。
* 二进制要求固定为 H6 旧检查点；“最新 Spin 源码重新编译”的成果需另开基线，不能与历史 H6 字节级重放混为一谈。
* CGAL 仍不是动态 Boolean 求值的替代品。所有原生审计是独立检查，并非替代求解。
* 所有新增内容只写入 `Spin_test` 的 Heart 隔离分支，未写入原 `Spin` 或 `Spin_test/main`。

## 原生主机运行方法

首先按 H6 `README_REPRODUCE_CN.md` 恢复并 SHA 校验 V4 历史源文件。将对应 native 动态库和 Spin_test 仓库 python 包加入 `PYTHONPATH` 后执行：

```bash
python research/Heart_v1_20261017/Cherchi_H7/source/replay_25_cherchi.py \
  --archived-v4 /tmp/archived-heart-v4-request.json \
  --output /tmp/heart-h7b-native-25
python research/Heart_v1_20261017/Cherchi_H7/source/verify_replayed_packets.py \
  --report /tmp/heart-h7b-native-25/report.json \
  --output /tmp/heart-h7b-offline-audit.json

python research/Heart_v1_20261017/Cherchi_H7/source/profile_native_stages.py \
  --archived-v4 /tmp/archived-heart-v4-request.json \
  --backend both --repeats 3 \
  --output /tmp/heart-h7c-profile.json
python research/Heart_v1_20261017/Cherchi_H7/source/summarize_stage_profile.py \
  --report /tmp/heart-h7c-profile.json \
  --output /tmp/heart-h7c-summary.json
```

**接下来：** 在研究主机执行、保留真实 packet 和分阶段耗时；处理无法匹配的 Cherchi 面片支撑（不能使用错误的平面归属），然后才能确定应优先优化 GMP 积分、导数、重复验证，还是布尔几何。之后推进 H8 原始或新冻结 Heart 上的 81 点质量矩/导数验收。
