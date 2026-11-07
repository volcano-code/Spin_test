# W3 Heart H9 — M21.6A 全边界运动分层审计

## 目标

在已有六份 Cherchi 保存材料及六份 M21 source-only 速度附件上，把 M21.5B 的三个代表性 LPI 扩展到每样本 8,455 个保留构造顶点。按 EXPLICIT3D、LPI、TPI 和源映射顶点四类记录同侧六区间速度割线残差；检查全/半区间的精确残差分割恒等式。这是有限点诊断，不是连续光滑性证明、Newton 准入或最终 Heart 模型。

**唯一写入分支：** research/neuralmoments-w3-heart-h9-20261019。仅在 W3 独占目录内增补 source/tests/reports，不修改 main、其他研究窗口、历史 H8f CI 或原始 CAD。

## 实际提交文件

- source/h9_m21_6_full_boundary.py，23,638 bytes，SHA256 455a52b9bacd5ae2043f727b5713263b24cf46770bf63ef98e3ed3dc8720781b
- tests/test_h9_m21_6_full_boundary.py，10,375 bytes，SHA256 a0aabf931fe2e0cb6ae581ca7b6c6fed7d53aa2d7ab52433b52b53425c61ecf5
- reports/H9_M21_6A_REAL_DERIVED_LPI_SMOKE.json：18 条已上传真实派生 LPI 位置/速度和 18 条区间残差精确交叉验证的结果
- reports/H9_M21_6A_SYNTHETIC_8455_CAPACITY.json：8,455 顶点规模合成容量检查，非原始 Cherchi 数据
- 本报告

## 执行与科学边界

本轮云端 Python 3.13 环境实测：py_compile PASS，12/12 项单元测试 PASS，0 failure/skip。负例覆盖构造键更换、语义三角面片更换、源面片签名变化、速度附件哈希篡改、LPI 位置/速度和残差篡改、非正参数区间、重复 JSON 键、非有限值与不合法的满边界宣称。

从用户上传的 m21-3-lpi.json（SHA256 d353486cafb3b81a97c302c51d8a034eedee327fabe92f2497df2c48b49c522e）执行 18/18 精确 LPI 数据对照和六组分割恒等式通过。**这是派生报告的 3 个 LPI 子集验证，不是全部 8,455 顶点真实验收。**

另在相同核心代码上生成 8,452 个合成 EXPLICIT3D 构造，加 3 个上述 LPI，总计每包 8,455 顶点 × 6 包，源顶点额外 256/包：3.206 s、最大 RSS 145,548 KiB，17,422 个合成源/边界分割恒等式通过。**这不是原始材料的实际耗时或峰值内存。**

真实保存材料全边界分析尚未完成，因为此云端会话仅有 M20 precision-ledger 与 M21.5B 派生 LPI 输出，没有 M18/M19 的六份原始 json.gz 及 M21 的六份 source-motion 附件。

## 严格分析合同

1. 沿用 M21 的 load_ledger、frozen_request、load_six、source_rows、read_motion 与 material_state，依原始 SHA 核验六份同调用材料与全部源速度附件；不加载原生模块、不调用 Boolean。
2. 每组先校验相同的构造身份集合、来源面片与有向语义三角多重集，不使用数字槽位补救身份切换；变化时故障关闭。
3. 每个构造按精确 Fraction 计算 (Xb-Xa)/h - (Va+Vb)/2，记录最大、平均、RMS、相对残差及前五个带有理证据的构造。
4. 原生源顶点也以同一固定索引单独计算相同残差，帮助区分源运动和交点构造传播的误差层次。
5. 分别对两个三点序列在全区间及两个半区间，逐身份精确验证分割恒等式，输出同向/反向残差统计和端点速度的中点校正上界。
6. 严格绑定已上传 M21.5B 的十八条物理坐标/运动记录及 18 条区间残差，在目标坐标系作精确相等比较；只比较三个指定 LPI，不能据此宣布其余 LPI/TPI 已通过。
7. 新增 Boolean=0、新增 source evaluator=0、Newton 准入=false、连续邻域证明=false、根因最终认定=false、最终 Heart OBJ=false。

## 本地执行命令

本地工作站原有目录：/data/xvxinyao1/Spin_test-W3，Python：$HOME/.venvs/spin-w3-313/bin/python。先快进同步 W3 分支，然后运行：

- python -m unittest discover -s "$H9/tests" -p test_h9_m21_6_full_boundary.py -v
- python "$H9/source/h9_m21_6_full_boundary.py" --precision-ledger "$M20_LEDGER" --artifact "$H8_ARTIFACT" --stage17-native-dir "$STAGE17_NATIVE_DIR" --m19-run "$M19_RUN" --source-run "$SOURCE_RUN" --lpi-report "$LPI_REPORT" --output "$OUT/full-boundary.json"

参数应使用此前 M21.5B 的相同目录，其中 LPI_REPORT 必须与上面 d353... SHA 相同，不能用新的未认证文件。输出应放在全新目录，不覆盖旧证据；出现缺失输入、SHA 或构造身份不一致时保留错误并停止，不能调整门禁凑成功。

## 距离初始目标的差距、后续运行位置

- 当前 M21.6A 已云端实现、12/12 模拟验收、18 条真实派生 LPI 二次复核并推送 GitHub。
- 当前 8,455 顶点 × 6 包的**真实材料运行尚未完成**，需要在持有六份原始数据与速度附件的 Ubuntu 工作站执行。不是算法本身必须在本地：如把完整材料安全上传且环境资源足够，也可云端离线复核。
- 本阶段不需要重新编译 Cherchi、不需要 GPU、不需要新的 Boolean。
- M21.6B 将结合真实 M21.6A 分组结果与同调用十质量矩 Jacobian，按面片/构造类型分解积分导数误差，再研究连续构造分片认证和正式 Newton 准入。
