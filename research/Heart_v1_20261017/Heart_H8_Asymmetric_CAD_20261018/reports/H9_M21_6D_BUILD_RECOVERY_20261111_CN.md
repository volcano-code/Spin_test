# W3 M21.6D：构建证据恢复，不启动 Boolean

复核日期：2026-11-11。用户提供的是本地终端输出；本报告不将它冒充本轮云端原生执行。

## 用户最新现场

- 用户本地 HEAD：e793e3fc83e4cda7d0310bd1c801151d3a0c7107。
- 原构建器 --phase plan：ready=true，blocked_reasons=[]；tracked_source_clean=true；untracked_importable_source_absent=true。
- build/ 占用 184 MB；三份 .so 已存在，字节数为 11098512、1006552、342824。存在和大小不能替代 SHA/加载核验。
- /home 空闲约 19 GiB；/data 空闲约 49 GiB，均显示使用率 99%。不能只凭百分比认定增量构建不可执行，也不能保证未来峰值空间足够。
- effective_memory_bytes=64890523648，约 60.43 GiB；mem_available_bytes=19377733632，约 18.05 GiB；swap=0。
- ready=true 是原脚本的预检结论，不代表它预留了 24 GiB 空闲内存。
- 上次 FileExistsError 来自错误的交接命令 mkdir -p "$QPT_BUILD"；build() 用 exist_ok=False，故尚未进入 CMake/Ninja。后续命令必须让构建器自己创建新的输出叶目录。

## 更正此前说明

调用 CMake/Ninja 不等于必然全量重编。现有脚本使用原有 build/h9-w3-core 和 build/h9-w3-cherchi，无 clean-first；构建系统可以复用未失效的产物，但配置/依赖/命令变化仍可触发重编。不能预报一定无编译工作。输出 --output 目录保存报告/日志，并不迁移实际 CMake 构建树。

参考官方说明：
- https://cmake.org/cmake/help/latest/manual/cmake.1.html
- https://ninja-build.org/manual.html

## 本轮实际修复

### 1. Quarterpoint 入口的 BINARY_SHA 缺失

现有 h9_m21_6d_quarterpoints.py 从 h9_m21_layered_replay 导入 BINARY_SHA，但该模块此前未导出这个符号。现在在 shared replay 模块增加兼容导出，其值与 M21.6B/C 既有冻结 core pin 完全相同：

d66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd

没有修改任何几何算法、历史材料、SHA 准入值或 Newton 门槛。旧 replay 文件的 Git blob 在本轮工作容器重建后核对为 cc3eca3c4f5a60a8bd3306ff8529754bf061be89；仅增加四行兼容导出，新 blob 为 2e35321d20d41f2dfe9971ce291939d47212fdf8。

### 2. 新增 h9_m21_6d_safe_build.py

入口不依赖旧 shell 的 PY/H9/PLAN/QPT_BUILD 等变量：

- 用当前执行 Python 与固定本地默认路径；检查 W3 分支及 tracked 文件状态。
- 核对 quarterpoint-plan.json 的已报告 SHA dbed9b42b77a8d7df942613d7b9f111386ff7b00dcadde60f0b5a0912373965b。
- 在任何构建前核对三份现有 .so 的 SHA 与计划完全一致。
- 输出根默认 /data/xvxinyao1/W3_H9_Results。只创建唯一记录目录和 tmp 子目录；传给原构建器的 build-output 子目录必须尚不存在。
- 清理 Conda 搜索变量，设置系统 libstdc++，设置 PYTHONINTMAXSTRDIGITS=100000，保存完整日志。
- 在构建前执行现有 P0 与 P1 的 quarterpoint 测试（按当前源码应为 11+15=26 项）；测试错误就停止，不进入编译。
- 默认只检查。显式 --build 才调用既有 pinned build 流程。
- --build 额外要求 MemAvailable >=24 GiB、swap=0、构建和记录文件系统各至少 4 GiB 可用。这是本轮保守运维阈值，不是测得的编译峰值需求，也不替代原始 check_runtime。
- 对旧 HEAD、失败状态、二进制 SHA 变化拒绝放行；调用原 verify_build_evidence 再验证。
- 任何阶段均不启动 Boolean、source-motion 或 Newton。
- build-evidence 成功后保持 HEAD 不变；不要立即再次 pull 使证据绑定过期。

## 实际已运行的验证

当前工作容器 Python 3.13.5：

python -m unittest discover -s tests -p test_h9_m21_6d_safe_build.py -v

结果：18 tests，0.736 s，OK，无失败/跳过。包括真实子进程退出码传播和超时清理测试；文件/库样本明确为合成 fixture，不冒充 .so 构建或 Cherchi 材料。BINARY_SHA 回归是实际源码 AST 常量检查，而非完整原生模块导入。

还执行了新增入口和 replay 文件的 py_compile。源代码 SHA256：

- h9_m21_layered_replay.py：46d950e668f21b568e421989a5e294a54f81b5f1ecef6072e1dd0757662ecc69
- h9_m21_6d_safe_build.py：6c9a382b76a76d17d463f9ae7e22a2ad0de44bfbc805171127ba03b88820db6c
- test_h9_m21_6d_safe_build.py：bd3c3fcfb263b7f9131ae4217bffbe2ed8c7f2ce6ee643eb4a761eb52f0c52d1

未在本轮云端执行原有完整 P0/P1 的 26 项测试、真实 CMake/Ninja 构建、原生模块加载或 quarterpoint 求值。完整 checkout/本地 .so 位于用户工作站；新入口会先在该机器执行测试。禁止将上述 18 项恢复入口测试写成四点真实采样验收。

## 本地命令

在交互终端复制整个 if/heredoc 块。set -e 只用于子 shell，失败不会主动退出交互终端；也不依赖之前 export 的变量。保留 external/、build/ 和所有旧实验目录。

```bash
if bash <<'W3_BUILD'
set -eu
REPO=/data/xvxinyao1/Spin_test-W3
BRANCH=research/neuralmoments-w3-heart-h9-20261019
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
cd "$REPO"
test "$(git branch --show-current)" = "$BRANCH"
git pull --ff-only origin "$BRANCH"
"$HOME/.venvs/spin-w3-313/bin/python" \
  "$H9/source/h9_m21_6d_safe_build.py" \
  --repo "$REPO" --output-root /data/xvxinyao1/W3_H9_Results --build
W3_BUILD
then
  echo '构建证据恢复成功；尚未启动 Boolean。'
else
  echo '已停止；查看报错及 RECOVERY_RESULT 指向的日志，不要重复启动 Boolean。'
fi
```

当前约 18.05 GiB MemAvailable 低于新增 24 GiB 运维阈值。应暂停能够确认身份的其他高内存任务后再尝试构建；不要自动杀进程、清理历史实验或启用 swap。即使资源阻断，已创建记录目录时仍保存 recovery-result.json。成功的状态必须为 BUILD_EVIDENCE_VERIFIED_NO_BOOLEAN，并输出新 build_evidence.json 绝对路径。

## 原始目标差距与执行位置

已知本地历史 M21.6C 18/18 和 M21.6D-P0 11/11 的用户日志不变。本轮推进的是入口/构建可靠性，不是新的研究采样结论。四个 quarterpoint 尚无本轮合格结果；连续邻域、渐近阶数、Newton 接受步和最终 Heart OBJ 均未完成。

代码/恢复测试/提交在云端完成。当前 HEAD 的构建证据和固定二进制核对需在拥有这些产物的本地工作区进行；不需要 GPU 或额外云服务器。只有构建证据通过且采样入口完整验收后，才单独安排 index 0。
