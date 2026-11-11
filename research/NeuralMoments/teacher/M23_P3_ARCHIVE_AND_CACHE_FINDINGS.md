# W2 — 归档排查收口与新重建缓存验证

分支：`research/neuralmoments-w2-teacher-20261019`  
核对基线：`8834824d172cf310c6899d081f4f8e542bf73513`  
状态：**软件级探索完成；历史 common.py 未恢复；真实后端未接入。**

文件名沿用本次用户报告中的 M23-P3 标识。这不表示 teacher_manifest 中
M23-P2.3 原始依赖恢复已通过，也不升级正式教师准入。

## 1. 上传证据实际支持什么

用户上传的是三个 ZIP 的扫描终端文本，不是 ZIP 本体。
该文本 SHA-256：`5cae1bdd5ecab4806cbc38448404f1c13577893e9c6eb17269930f657abc1846`。

| 归档 | 报告 ZIP 校验 | 条目数 | 源码关键词匹配 | Python 清单 |
|---|---|---:|---:|---|
| Noodles_v7_optimized_and_extended_pivot_milestone_20261017.zip | PASS | 26 | 0 | 4 个脚本 |
| noodles_v6_source_parts.zip | PASS | 165 | 0 | 空 |
| noodles_v6_source_parts (1).zip | PASS | 165 | 0 | 空 |

V7 四个脚本是 pilot_v7_real_cherchi_newton.py、preliminary_ideal_pivot_spinning_top.py、
run_extended_ideal_pivot_grid.py、verify_v7_fresh_delivery.py。
V6 列表对应 79 个 tube 加 hub/outer-ellipsoid/pin，即 82 组 Model/SI OBJ 与 manifest，
不是冻结 V7 的 94 部件。两个 V6 ZIP 尚未比较原始哈希，不能宣称字节相同。
日志出现 SCAN FINISHED，没有展示 Traceback；回显乱码本身不能证明脚本执行失败。

限制：扫描器只检查指定扩展名，并静默跳过解码/读取失败；没有检查 JSON 内容和嵌套归档。
因此结论是“这三个归档的当前扫描未恢复构建器”，不是“整个磁盘或所有备份都不存在”。
停止重复扫描这三个文件，不以常见 export_obj 命中冒充目标实现。

## 2. 实际恢复并核对的源快照

本轮从用户 Library 取得 `Noodles_v7_GitHub_research_source_snapshot.json` 原始字节，
SHA-256 = `f7cf4c2efbd32b9c19d33359471f0671aa2efae104d3aa912500157052f39980`，
与 W2 清单冻结值一致。

其中 build_exact_v7.py 的 Git blob = `0c02cd8f4e7554ab6f3cbde497877253ce5bddec`，
与 GitHub 冻结提交 `8c949de977ef50be337da7aec6c852566e0da565` 的文件一致。
其中 V7 manifest SHA-256 = `67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a`。
源快照仍无 common.py 或 class ExactBuilder 定义。

## 3. 新发现：原构建脚本的缓存绑定不足

历史脚本的六个最终输出只要存在就跳过生成；没有逐项对照本次输入、后端和 receipt。
92 个 union 缓存核对来源名称及结果 SHA，但没有核对记录的 backend_sha，
也没有把两个操作数的内容 SHA 绑定到缓存键。
这不说明历史结果错误；它说明不能把旧脚本直接当作强身份绑定的安全续跑器。
外部 readiness 门可能额外拦截部分变化，本实验没有运行该门。

### 未改动历史脚本的控制流复现

`m23_p3_historical_cache_probe.py` 严格校验上述源快照、build 脚本和 manifest 身份，
然后用 **94 个合成输入、合成审核记录、明确标记的 common mock** 执行原脚本。
没有实际 Boolean 几何计算，没有调用任何 CGAL/Cherchi 原生程序。

| 用例 | 历史脚本行为 | 合成 Boolean 函数调用 |
|---|---|---:|
| 全新目录 | 完成 | 96（92 union 构建 + 4 最终运算） |
| 原样续跑 | 完成 | 0 |
| 六个最终输出全部改写坐标 | 仍完成并原样复用改写字节 | 0 |
| 当前 mock 后端身份改变 | 仍完成 | 0 |
| union receipt 的后端身份改变 | 仍完成 | 0 |
| 源输入改变且合成 manifest/audit 一致更新 | 仍完成、复用旧缓存 | 0 |
| 对照：union 结果 SHA 与 receipt 不符 | 正确拒绝 | 0 |

注意：96 是 mock 函数调用次数，绝不是新执行的 96 次原生 Boolean。
合成审计记录仅用于触发历史程序分支，不能作为真实源实体审核。

## 4. 已开发的新模块

`m23_p3_bound_cache.py` 是新代码，不是失踪 common.py 的历史恢复，也不是完整构建器。
它将结果绑定到实验 ID、节点、操作、有序操作数 SHA、manifest、source audit、
builder、adapter、backend、序列化和坐标策略。输出按原始 bytes 保存，不改有理数表示。

只有完整 receipt 最后提交才允许读取；缺失、改写、身份不符或半写入节点均拒绝。
禁止覆盖已有节点，禁止将目录存在当作成功，拒绝重复 JSON 键和不支持的准入声明。
每条记录保留 training_admitted=false、J_D=null、solid_certified=false。
这是意外污染/误复用防护，不是数字签名；调用方必须从实际当前输入独立计算期待上下文。
该模块尚未接入生产后端，不宣称原构建器已修复。

实际执行 `test_m23_p3_bound_cache.py`：22/22 PASS，0 fail，0 skip。
测试环境是本轮会话 Linux/Python 3.13.5 容器，**不是 GitHub Actions CI**。

## 5. 复现

从仓库根运行：

```bash
python3 -m unittest discover \
  -s research/NeuralMoments/teacher \
  -p 'test_m23_p3_bound_cache.py' -v

python3 research/NeuralMoments/teacher/m23_p3_historical_cache_probe.py \
  --snapshot /path/to/Noodles_v7_GitHub_research_source_snapshot.json \
  --output /new/path/W2_CACHE_CONTROL_FLOW_PROBE.json
```

第二条拒绝非冻结源快照与覆盖已存在输出。完整 stdout 在 probe JSON 内，
其开头明确说明原脚本打印的 native/EXACT 字样在本实验中不代表原生运算。

## 6. 剩余关键门与方向调整

原版 common.py 是历史同字节复现的依赖，但不应成为 W2 新教师研究的唯一入口。
下一步可在**新实验身份**下核对现有精确 Boolean 后端协议，建立自包含适配器，
先验证 union/intersection/difference 的小型闭合实体与独立精确十矩，再扩大到 V7。
必须明确 OBJ 小数/精确有理数/binary64 之间的转换，不能暗中更换语义。

原始 CGAL 脚本只用于离线输入构建，不意味着改掉 Cherchi 生产教师。
新构建若使用不同代码/后端/序列化，记录新的身份与独立证明，不伪装成六份历史字节恢复。

截至本轮：历史 common.py 未恢复；六份历史材料仍无新增恢复；
新 CGAL/Cherchi 调用 0；新训练样本 0；J_D 不释放。
冻结 Heart 的此前证据不因本次 Noodles 排查而被撤销，也不因这些软件测试而升级。
