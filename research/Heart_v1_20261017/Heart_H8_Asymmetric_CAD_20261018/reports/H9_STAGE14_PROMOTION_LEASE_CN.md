# Heart H9 W3｜第十四阶段：真正复现并修复的跨进程材料升级竞争

日期：2026-10-20。**唯一允许写入分支**：`research/neuralmoments-w3-heart-h9-20261019`；上阶段 HEAD：`0366dd65bfe373aa3657c3fc03463d4cd59d0760`。W3 文件独占范围之外没有修改。冻结 H8f 祖先：`0bcc187b3005478baa586a6d6f450e73811ca342`。

## 1. 原来确实存在的错误（真实双进程复现，而非推测）

第十三阶段 `h9_same_call_capture.py` Git blob `8f597a2380a5fd8298e240ac09e11e61ff88268c` 的 `promote_after_full_audit` 对 `side-XX.json.gz` 的孤儿链接进行安全 inode 比对，但**没有跨进程互斥**。

真实执行两次独立 CPython 进程 A/B，使用明确标注的**存储测试夹具**（不是新原生 Cherchi 材料）：

1. A 为 `unverified-00-left-coarse.json.gz` 建立 `side-00-left-coarse.json.gz` 硬链接，尚未提交正式 `side-00-left-coarse.json`；
2. B 将 A 正在使用的同 inode 链接错误识别为“崩溃残留”，删除并重新建链接，完成正式 JSON 与 gzip，并报告 `success`；
3. A 继续写元数据发现名字被占用，进入失败清理流程，**又删掉了 B 创建的正式 gzip**；
4. 最终状态：`formal_json_exists=true`，`formal_gzip_exists=false`，虽然 B 声称升级成功。

可复现的原始输出保存在 `H9_STAGE14_RACE_BEFORE.json`。这会使已有真实原生 Boolean 结果在多进程误启动时丢失正式材料，属于**执行可靠性真实缺陷**。

## 2. 修复

在 `source/h9_same_call_capture.py` 中新增 `_exclusive_promotion_lease`：

- 每个 side 独立稳定的 `.h9-promotion-XX-<side>.lock`；Linux `fcntl.flock(LOCK_EX)`，从**读取/恢复已有正式文件**之前一直持有到元数据、材料及可选清理全部完成；
- 采用 `O_NOFOLLOW`、`lstat/fstat` inode 与同 UID 检查，拒绝符号链接或替换掉的锁路径；
- **永不删除锁文件**，避免进程仍锁住被 unlink 的旧 inode、另一进程却锁住新 inode；进程正常退出或 `os._exit` 崩溃后内核自动释放文件锁；
- 延用第十二、十三阶段的 fsync、排他链接、SHA256 重新核验、合法 inode 孤儿恢复，不改变用于新原生材料判定的科学门槛。

相同双进程故障注入重放：A `success`；B 返回 `VALIDATED_NATIVE_PACKET_ALREADY_PRESENT`；**正式 gzip 和 JSON 均存在且 gzip SHA 与捕获报告一致**。证据在 `H9_STAGE14_RACE_AFTER.json`，本次测试没有新增原生 Cherchi 调用。

## 3. 本地实际测试

- 第十四阶段新增 `tests/test_h9_stage14_promotion_lease.py`：**7/7 PASS**，包括真实 OS 双进程竞争、崩溃自动解锁、持久锁 inode、不可信锁文件拒绝、四个 side 独立锁、原始 H8f sample59 实际 JSON 材料往返（历史样本不计新教师样本）。
- 第十一～十三阶段 8+7+10 = **25/25 PASS**；合计 **32/32 PASS**。详见 `H9_STAGE14_32_TESTS.log`。
- `py_compile` 两个脚本及新增单测通过。
- 原始 [H8f run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 仍为 `failure`；原始 artifact 12135528290 的 ZIP SHA256 仍是 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。
- 本地实际执行 `prepare_h9_pinned_native.py --phase plan`：**exit 0**；`--phase build`：**exit 2**；`--phase run`：**exit 2**；内层 `run_h9_native_serial.py`：**exit 2**。本次环境的 cgroup 有效内存 **4294967296 bytes (4 GiB)**，不是完整 W3 checkout，缺三个原生模块，禁止违反冻结的 ≥24 GiB/swap0 原生作业协议。详细机器预检记录保存在 `H9_STAGE14_NATIVE_PREFLIGHT.json`。

## 4. 复现实验

完整 W3 checkout 下（`H9` 为以下目录）：

```bash
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
export H9_EVIDENCE_ZIP=/path/to/original-actions-artifact-12135528290.zip
python -m unittest discover -v -s "$H9/tests" -p test_h9_stage14_promotion_lease.py

# 复现第十三阶段原版竞争：先恢复上一提交的该文件，不修改当前源码。
mkdir -p /tmp/h9-original-stage13/source
git show 0366dd65bfe373aa3657c3fc03463d4cd59d0760:"$H9/source/h9_same_call_capture.py" \
  > /tmp/h9-original-stage13/source/h9_same_call_capture.py
python "$H9/tests/reproduce_h9_stage14_race.py" \
  --source /tmp/h9-original-stage13/source --mode original --output /tmp/h9-race-before.json

# 新版在同样双进程竞争下不丢正式材料。
python "$H9/tests/reproduce_h9_stage14_race.py" \
  --source "$H9/source" --mode fixed --output /tmp/h9-race-after.json
```

## 5. 未完成与准入

本阶段**没有**新的四个 Cherchi Boolean 侧点材料、没有生产连续可微邻域证明、没有真实接受的 Newton 步、没有最终 Heart OBJ 或独立终态物理量。`newton_admitted=false` 保持不变。新代码只增强高成本原生取证可靠性，不改变 sample60 的 5 个槽位、2+2 个 LPI 构造身份、17+17 个语义三角形变化的原历史事实。

**下一科学里程碑仍是：** 在满足内存与源版本约束的 W3 原生机器上执行四点真实 Cherchi，留存每个 `side-*` gzip/JSON、二进制哈希和独立十质量矩积分/左右 Jacobian，对连续源构造做进一步检验，之后才能讨论 Newton 准入。
