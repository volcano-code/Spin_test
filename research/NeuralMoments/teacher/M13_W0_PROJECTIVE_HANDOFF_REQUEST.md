# W2 M13 → W0：精确正比例 projective 身份的只读交接提案

**仓库：** `volcano-code/Spin_test`  
**W2 唯一写入分支：** `research/neuralmoments-w2-teacher-20261019`  
**本文件不是 W0 合同的正式变更，也不是训练准入签发。**

## 需要 W0 决定的问题

W0 已冻结的 `MomentContractV1` 要求保存系数满足 `abs(||c||₂-1)<=1e-12`，但真实 H8f 的 81 个历史 native `c` 中仅 **17** 个满足该保存门槛，剩下 **64** 个属于真实有限扰动时保存的未归一化 native `c`。对应原始 81 点 GitHub Actions [39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 是 **failure**；不能通过重写原始样本、归一化后沿用同次 SHA 或修改 CI 状态来使其“通过”。

**数学建议（待 W0 独立评审）：**在不改变 W0 现行 `MomentContractV1` 已发布 schema 的情况下，研究可扩展的 `SavedNativeCProjectiveIdentity`：

```text
original_native_c        : 10 recorded binary64 numeric tokens
original_native_c_sha256 : sha256(canonical(original_native_c))
signed_primitive_integer_c : 10 exact integer strings, gcd(abs(...)) = 1
positive_rational_scale    : numerator/denominator, >0
algebraic_binding          : for every i, Fraction(original_native_c[i]) ==
                             positive_rational_scale * signed_primitive_integer_c[i]
native_order               : CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY
polynomial_mapping         : q=Bc, B=diag(1,1,1,1,1,1,1,2,2,2)
negative_ray_unchanged     : c and -c MUST NOT match this positive-ray identity
exact_ray_digest           : sha256(canonical(order, signed integer ray, positive only))
raw_material_attachment    : separately pinned original same-call gzip SHA
release_status             : PENDING_INDEPENDENT_W0_AND_W3_ADMISSION
```

所有比例计算基于**保存的 binary64 值作为精确有理数**，不是重新数值拟合原始网格。正有理因子允许代数重标度，而有符号整数向量保留负号及 Boolean retained-side 语义。

### 已独立完成的 W2 证据

- [M13 源码](./w2_projective_handoff_m13.py) 与 [M13 测试](./test_w2_projective_handoff_m13.py)。
- [81 条紧凑精确射线索引](./M13_H8F_81_PROJECTIVE_HANDOFF_INDEX.json)，源于原始 [M12 81 点射线](./M12_H8F_81_PROJECTIVE_RAYS.json)。
- 81/81 原始 `c=a n` 有理恒等式通过，81 个 signed primitive ray 唯一；17/64 的 W0 范数分类未改变。
- 7 个有理数坐标探针和全部 10 个 `q=Bc` 系数满足精确的 `P(c,x)=a P(n,x)`。
- 原始 ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`；本轮重新核验了所选真实 point60 的材料 gzip SHA、完整 native c、geometry/topology hash、r_D、10×10 Jacobian 摘要；M10 历史 81 包重绑定记录保留，**本轮没有声称再次逐包解压 81 份**。
- 原始 `c[7]=3e-6` / W0 多项式 `q[7]=6e-6` 不变；point60 构造变化拒绝。
- M13 本地使用真实原始 ZIP 的非缓存专项测试 **25/25 PASS**，GitHub 上的完整 W2 manifest 与本地单元测试使用的 M9 语义 fixture 必须区分。

### 绝不能根据本提案推出的结论

1. 任意对原始 `c` 的新 binary64 单位化显示向量不是已运行的新 Cherchi 样本；64 个非单位样本的显示向量不具原始 binary64 精确有理射线身份。
2. 即使零集在精确多项式意义上满足正比例等价，也不保证浮点 Cherchi 构造、离散面片分支、精确同次材料或 Jacobian 完全相同。
3. 有限点数值差分与 81/81 物理十矩重积分均不能证明整个连续邻域可微，更不能授予 Newton 收敛。
4. W0 当前只读 `w2_teacher_gate.py` Git blob `b42ec6d9b389675123250d79f9cc9efb1b658c07` 只接受 W2 **v1**。M13 不更改它，也未调用一个 W0 独立批准的 v2/projective verifier。
5. W3 Stage11 [执行证据](https://github.com/volcano-code/Spin_test/blob/research/neuralmoments-w3-heart-h9-20261019/research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/reports/H9_STAGE11_EXECUTION_EVIDENCE.json) 尚为零新增原生侧点，point60 是真实构造变化见证，不存在 W3 正式连续性放行。

**期望 W0 输出（必须由 W0 在其独占分支实际开发与测试）：**带独立版本号、正负比例/原始 SHA/跨系数 B 映射的验证器，以及明确“保存 raw c、诊断显示、native 材料结果、Jacobian 导数合同”四者不能互相冒充的验收测试。再由 W3 的新原生点决定是否存在可授权的光滑分支；W2 自身的 `export_training` 在此之前保持无条件拒绝。
