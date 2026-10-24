# W3 Heart H9｜第十七阶段：真实原生采样的十维系数容器一致性修复

## 故障定位（用户 Ubuntu 24.04、60 GB RAM）
用户已通过固定 Cherchi/CGAL 编译及三份原生模块 SHA 验证，在用系统 `libstdc++` 消除 Anaconda GLIBCXX 冲突后，新侧点 0 进入 `capture_same_call()`，失败：

```
failed_stage: PRESERVE_UNVERIFIED_TRUE_SAME_CALL_PACKET_0
CaptureRejected: NEW_NATIVE_CAPTURE_QUADRIC_IDENTITY_MISMATCH
```

W3 的生产端 `python/make_it_stand/verification/cherchi_inprocess.py`（Git blob `f9fa539f699df8baf8b8d30729048269a26ecb3c`）中 `InProcessCherchiEvaluator.material()` 明确将 `quadric_coefficients` 从 JSON list 转回 **tuple**。W3 探针传入 `q.tolist()`（**list**）；旧 `h9_same_call_capture.py` 使用 `tuple == list`，导致十个浮点值完全相同也被拒绝。此前的 0/4 表示未完成独立认证的新侧点，并非断言本次没有进入原生求值。

## 修复和严格性
`source/h9_same_call_capture.py` 新增 `same_binary64_coefficients`：请求向量必须是长度 10 的 list；保存材料的字段可为长度 10 的 list 或 tuple；逐项对 **IEEE 754 binary64 原始位模式** 严格比较，非有限值、布尔值、不同长度、一个 ULP 漂移、分量调换及正负零差异全部拒绝。**无 allclose、无误差容差、无重归一化、无修改原生材料和 q。**

保留原有 Cherchi backend/material_proof、原始 gzip+SHA、后续精确边界、十质量矩独立 Fraction 积分、LPI/TPI 身份和 Newton 准入拒绝门槛。通过该检查只允许创建未认证 `unverified-*` 取证快照，不等于四点求值完成。

## 本轮真实测试
- 新专项 10/10 PASS：tuple/list 生产路径、真实 H8f sample 59、一个 ULP、signed-zero、乱序、长度/类型/非有限值及跨 q 拒绝。
- 第 11–14+17 阶段相关 W3 离线回归 **42/42 PASS，6.174 秒**，无跳过；历史 ZIP 实际读取和 SHA256 验证：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- 修复后的 Python 源文件 blob SHA：`3a7586ee3ac1c98dd856931bcaff1ed08bcd08b5`；新测试 blob SHA：`6d6f7b2ee754744c525cbc2f7b8907669ecb4e41`；本地回归完整日志 SHA256：`9da4a8b38a4350eecd9c9c0c11934d63c3aceff6509f0dc31874563deff9887c`。
- 本轮**未在用户主机重新运行真正的原生四点实验，尚无 4 个成功新侧点、独立验收或 Newton 终态**；没有新远端 Actions CI。

## 用户本地后续验收
1. 检查 Git 工作区，`git pull --ff-only origin research/neuralmoments-w3-heart-h9-20261019`，不得修改 main 或历史 CAD。
2. **旧的 build_evidence.json 绑定旧 HEAD，不能直接重用**。使用此前清理 Anaconda 环境变量的构建命令，创建**全新构建证据输出目录**重跑 `--phase build`；增量构建可复用已有 CMake 缓存和 .so。
3. 使用新 build_evidence、已验证系统 libstdc++ 的 `LD_PRELOAD`、全新四点输出目录重新 `--phase run`，保留旧失败文件。
4. 检查 `launch_result.json`、`serial-native/run_status.json`、`probe.stderr.txt`、`native/failure.json`；若执行通过，继续检查独立 ten-moment/Jacobian 审计。不跳过身份检查，不声称 Newton 已准入。
