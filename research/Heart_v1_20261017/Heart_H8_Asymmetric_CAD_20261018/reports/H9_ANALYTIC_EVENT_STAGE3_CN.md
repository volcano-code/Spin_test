# Heart H9｜第三里程碑：有理区间的逆 Gauss 边—边事件证据（2026-10-19）

**执行窗口：** W3，仅 `research/neuralmoments-w3-heart-h9-20261019` 分支；冻结母证据 `0bcc187b3005478baa586a6d6f450e73811ca342`。本次 **没有改变** run [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 的 `failure` 结论，不更改历史 CAD。原始 [artifact 12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290) SHA256：`99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`；冻结 request SHA256：`1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`。

## 实际核验的新成果

基于 **九个真实归档同调用 Cherchi 材料**（index `0,57,58,59,60,61,62,63,64`），以冻结的二次曲面 `q=(c,b,A)`、`q[7]` 唯一扰动维度、`target_axes=I` 和归档原生 source 顶点（24、89、90、151）构造一个条件性连续源运动模型。其固定法向逆 Gauss 表达式：

\[
C(t)=-\tfrac12 A(t)^{-1}b,\quad K(t)=-c+\tfrac14 b^T A(t)^{-1}b,\quad
X(t,n)=C(t)+A(t)^{-1}n\sqrt{\frac{K(t)}{n^T A(t)^{-1}n}},
\]

其中 `t=q[7]`，`A(t)` 在对角项固定的条件下只有 `A[1,2]=A[2,1]=t`。法向 `n` 从归档 binary64 顶点与基点 `C(0)` 反推，且不需要单位化。验证该模型在九个样本中四个重点顶点的 108 个坐标分量，与真实归档 source 坐标**最大偏差 `9.830390539378602e-16` 模型单位**。

取真实设计域边端点 `d5517,d5518`，研究

\[
D(t)=\det\bigl(X(t,n_{24}),X(t,n_{90}),d_{5517},d_{5518}\bigr).
\]

验证器 `source/certify_h9_analytic_edge_event.py` 用 **10^38 固定分母的整数区间端点，全部四则运算向外舍入，整数 `isqrt` 包围根号值**，并通过自动微分区间 `Jet` 包围 `D'(t)`。对整个区间 `[1.5e-6,3e-6]`：

- `D(1.5e-6)>0`、`D(3e-6)<0`；
- **`D'(t) ∈ [-0.020033154531313845, -0.020015040217368812]`（区间端点仅供展示）**，严格负数；
- 因而在上述**固定法向解析代理模型**中，该区间有唯一 `D(t)=0`，并通过 44 次有理二分包围其根：`2.28058622834439e-6` 至 `2.2805862283444754e-6`，宽 `8.526512829121202e-20`；
- 用真实归档其他点 `57,59,60,62` 独立重建源法向，解析代理根的估计跨度 `8.688525159755711e-17`（与模型根包围宽度不同，前者体现二进制原生档案种子误差）。

该新解析根与原阶段二有限样本割线估计 `2.2805875399117463e-6` 略有差别，进一步缩窄待调查范围。

## 严格认证边界（不予夸大）

**已认证的是“从冻结 native binary64 顶点取种子的连续逆 Gauss 代理模型”**；数值匹配不等于原生代码在整段区间持续使用相同 fixed-normal、相同源三角面链，也没有为 native binary64 舍入及连续 provenance 变化给出严格整体误差界。所以绝不能说“Cherchi 真实 Boolean 的跳变时刻已严格确定”或“有真实可微邻域”。

真实 H8f 81 点数值 FD 30/30 虽通过，但 exact branch 分类仍有 sample 60 异常，H8f CI 整体是 `failure`。没有新原生求值、没有可接受的真实 Newton 步、没有 Heart 最终 OBJ、终态收敛残差或独立积分物理指标。

## 实际执行与阻碍

- 真实下载保留的 81 点 ZIP，校验 SHA / report / 9 个材料 archive，并实际运行如下命令生成 [H9_ANALYTIC_EVENT_CERTIFICATE.json](H9_ANALYTIC_EVENT_CERTIFICATE.json)。
- 新增的区间算术与真实 ZIP 复核单元测试在当前 Python 3.13 环境 **5/5 PASS**，包括双边舍入及有理除法、严格开平方包围、自动微分、篡改 ZIP 拒绝、9 个真实材料点、导数负性、根唯一、标记 Newton 未准入。
- 环境检查：Python 3.13.5，约 5.8 GiB 内存 / 0 swap；`_make_it_stand`、`_cherchi_core_boolean`、`_cherchi_rational_moments`、CGAL / Eigen 本地原生依赖不存在。访问 `github.com` 的网络 DNS 失败，所以不能安全完成原生编译，也没有新的真正 Cherchi 微区间求值。GitHub 连接器现有权限支持**源码读写**，但未提供启动 workflow_dispatch 的操作；原有 workflows 只自动监听别的 Heart 专属分支，而独占范围禁止修改 `.github/workflows`。

```bash
export H9_EVIDENCE_ZIP=/path/to/heart-h8f-artifact.zip
python research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/certify_h9_analytic_edge_event.py \
  --artifact "$H9_EVIDENCE_ZIP" --output /tmp/h9-analytic-root-proof.json
python -m unittest discover -v \
  -s research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/tests \
  -p 'test_h9_analytic_event.py'
```

## 下一关键验收

在满足 24 GiB/swap0、编译并发最多 4、原生串行 ≤60 分钟的环境中，执行第二里程碑已有的 `source/probe_h9_transition_live.py` 四个真实样本，重点将新解析事件根两侧再加紧邻真实采样；必须逐点存原生 source/Boolean 构造记录、边界完整性、有理材料独立十质量矩、Jacobian、accept/reject，以及原始哈希。确认二侧 LPI 及支撑面身份是否发生相应转变，比较左右极限后才能决定 Newton 是否允许启动。仍坚持 **NEWTON_DENIED**。
