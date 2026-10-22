# W3 H9｜第十六阶段：Ubuntu Boost 静态链接路径兼容修复

## 本地用户真实阻断

在固定 Cherchi `7bd6c2697695f555f9a15d7e154e084d841316f0`、CGAL `f7c3c8212b56c0d6dae63787efc99093f4383415`、GMP 6.3.0、MPFR 4.2.1 获取/检查通过后，主机核心 CMake 配置已返回零；生成的 `build/h9-w3-core/build.ninja` 被 `boost_shared_rewrite` 拒绝，错误 `STATIC_BOOST_REFERENCES_REMAIN`。原修复函数仅替换 `/usr/lib/x86_64-linux-gnu/libboost_{thread,system}.a`，对于 Ubuntu usrmerge 的 `/lib/x86_64-linux-gnu/` 前缀无法识别。

**注意：本聊天无法读取用户主机真实 `build.ninja` 中残留的具体路径。当前修复经模拟路径测试通过，不代表已解决主机实际路径；若仍拒绝，会在错误信息中附加前 8 个原始静态引用以便诊断。**

## 实际修改

- `source/prepare_h9_pinned_native.py`：兼容 `/lib/x86_64-linux-gnu/` 和 `/usr/lib/x86_64-linux-gnu/` 的 Boost `thread/system` 静态库引用；仅在同一目录共享 `.so` 存在时替换生成的 W3 `build.ninja`；未知 / Conda 路径、丢失 `.so` 时拒绝且不写入部分更改。
- `tests/test_h9_stage16_boost_shared_paths.py`：9 个模拟构建文件测试，覆盖 2 种系统路径、混合引用、无引用、未知路径、缺失共享库、后缀、嵌套路径以及裸静态库名。
- 不修改历史 H8f、`main`、其他窗口、系统 Boost 档案和冻结 CMake 源码。

## 已执行与尚未执行

- 隔离 Python 函数等价实现的 **9/9 测试 PASS**。这不是用户本地主机对完整 W3 构建的验证，也不是 GitHub Actions CI。
- 当前新的真实 Cherchi 原生调用：**0/4**；Newton 不准入；Heart OBJ、真实收敛残差仍无。

## 本地主机只读诊断

```bash
cd /data/xvxinyao1/Spin_test-W3
grep -nE 'libboost_(thread|system)\\.a' build/h9-w3-core/build.ninja | head -n 20
ls -l /lib/x86_64-linux-gnu/libboost_{thread,system}.so /usr/lib/x86_64-linux-gnu/libboost_{thread,system}.so
```

## 应用修复

在 W3 仓库工作区跟踪文件干净时 `git pull --ff-only origin research/neuralmoments-w3-heart-h9-20261019`，激活原 `spin-w3-313` Python 环境，生成**新的**构建证据输出目录后重新执行 `--phase build`；保持 `build/h9-w3-core` CMake 编译缓存和外部 pinned Git checkout 不变。如果再次失败，查看新的 `build.log` 和新增的残留路径诊断，绝不删除系统 Boost `.a`。
