# Heart H8b：非对称 CAD → Faster 冻结请求与云端构建推进

## 已完成且通过
- 使用 H8 默认版实物 OBJ（initial_top 31,288 面；design 26,244 面），建立以 25 mm/model unit 为单位的 `prepared-request.json`，冻结了完整三维坐标、面片、原点、旋转轴和 10 项固定材料矩。原点声明为杆尖处的最低 z 值（离散几何尖端，**不代表物理点接触已验证**）。
- 计算统一的无量纲密度 1 质量矩，并记录 density=1187 kg/m³ 对应的质量单位 0.018546875 kg；相同几何的外壳、F 和 D 满足归一化十矩分区一致性，最大误差 4.7982e-14（独立于 Newton）。
- 本会话在实际 H8 默认 CAD 文件上运行了 **5 个**本地回归用例：真实输入、固定/设计质量矩相加、错误单位拒绝、已有输出拒绝、篡改网格 SHA 拒绝，**5/5 PASS**。完整可执行版本封存于会话 `Heart_H8_Stage2_Prepared_Request.zip`。
- 在 GitHub 的 Heart 独立研究分支提交同一接口用途的轻量版 `source/prepare_h8_solver_request.py`、对应几何矩约定/负例测试，以及 Python CI workflow。大型二进制/多兆字节的冻结请求未写入 GitHub 主仓库；会话 ZIP 中包含精确请求 JSON、清单及程序。
- 修正 H7 云端临时 runner 的 Boost 链接阻塞策略：静态 `libboost_thread.a` 被非 PIC 链接，单纯 Boost_USE_STATIC_LIBS=OFF 未起作用。现在仅在**云端临时 runner**隐藏非 PIC thread/system .a，保留共享 .so 供 CMake 使用；修改启动新 CI 构建。不能把 CI 排队或重新构建当作原生通过。

## 未完成 / 无法宣称
- H8 是基于解析 SDF 及 marching cubes 的 **reconstructed CAD**，不是作者原 CAD；浮点网格与边界尚未通过 native exact-rational/CGAL 全部认证，0.375 mm 的保守下界并非 2.4 mm 标称壁厚的实际独立证明。
- 这份请求尚未经过 `SpinItFasterRequest` 的原生实例化和正式 same-call `InProcessCherchiEvaluator` 25 点/81 点协议；没有更新 q、没有 Cherchi 终态、没有收敛。
- 输入 `evidence=RECONSTRUCTED_ASSET`；密度在算法坐标下是相对密度 1，现实质量由所登记的 SI 单位转换，不可用 1187 直接替代。
- 真实 H8 正式 Newton/OBJ/接触动力学均是 **NOT VERIFIED**，性能数字仍需原生测量。

## 后续
- 在云端成功得到 `_make_it_stand`、`_cherchi_core_boolean` 后，对 H8 的新冻结请求执行独立 native exact boundary、正交轴、设计域包含关系和同次材料矩检查。
- 若有阻塞，记录具体失败源面/布尔见证；不能通过降低精度、改变设计输入或退回 CGAL Boolean 来伪造成功。
- 完成完整 H8 十维导数认证之后，方可进行 Cherchi + Faster Newton 多种子并报告收敛与耗时。
