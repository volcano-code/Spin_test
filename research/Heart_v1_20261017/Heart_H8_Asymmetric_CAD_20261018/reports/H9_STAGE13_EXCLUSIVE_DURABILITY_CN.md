# W3 Heart H9｜Stage 13：取证材料排他发布、崩溃持久性及并发保护

**唯一写入分支：** `research/neuralmoments-w3-heart-h9-20261019`。原分支第十二阶段 HEAD `d69a9c91bf3a9359cf2a480fc22fec8bc8393ca3`；冻结 H8f 源提交 `0bcc187b3005478baa586a6d6f450e73811ca342`。不得修改 main、W0/W1/W2/W4/W5/W6、原始 CAD、公共 core 或历史工作流。

## 当前研究状态（不放大）

原始 [H8f Actions #39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402) 仍为 **failure**；[artifact #12135528290](https://github.com/volcano-code/Spin_test/actions/runs/39123384402/artifacts/12135528290) SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`。历史 81 点已求值与 30 项数值差分通过不能转为 H9 真实平滑邻域、最终 Heart 结果或训练标签。W3 当前执行环境 **没有原生扩展**，cgroup RAM 上限 `4294967296` 字节、非完整 W3 checkout，原生 build/run 均在预检阶段以 `exit 2` 阻断，**本轮新 Cherchi Boolean 调用 0、四点材料 0、Newton 准入 False、最终 Heart OBJ 无**。

## 发现并修复的实际错误风险

第十二阶段 `h9_same_call_capture.py` 在生成 `unverified-*` gzip 与 JSON 元数据时，虽先检查目标不存在，随后却使用 `os.replace` 发布：如果不同进程在检查和提交之间同时占据同名路径，后者会覆盖前者。且原始 gzip 的新目录项尚无 fsync 持久化保障。该问题会破坏原生高成本材料的取证独占性，是**文件系统语义修复**而非 Cherchi 几何结果。

新版本使用同目录 `tempfile` + 可靠文件数据 `fsync` + `os.link(temp, dest)` 的排他新建名称（已有文件包括断链 symlink 均不覆盖），再 `fsync` 输出目录：

- 未认证材料/元数据发布均不会覆盖已有文件；写入冲突后保留竞争者内容和现场。
- 在“gzip 已链接、JSON manifest 未创建”时发生崩溃，只保留 **UNVERIFIED** 残留，不计入成功样本，也不静默重跑覆盖。
- `promote_after_full_audit` 拒绝待升级 symlink 或非普通文件，独立重验正式 gzip 字节 SHA 后才提交元数据；源材料被篡改则拒绝。
- 元数据发生竞争写入时，回滚只能删除本进程实际拥有的名称，不能删除竞争者的记录；发布后目录同步失败同样保持故障关闭。
- 在正式 gzip + 元数据持久化完成后，清理旧取证链接的**可选**目录同步失败只标记 `forensic_cleanup_incomplete`，不能否认已持久化的正式文件对（仍需要独立原生材料验收）。

## 真实运行与覆盖范围

源码 `source/h9_same_call_capture.py` Git blob SHA `8f597a2380a5fd8298e240ac09e11e61ff88268c`；新增测试 `tests/test_h9_stage13_exclusive_capture.py` Git blob SHA `ac62df904f01be10ebe897972fa3d443ae86d09e`。

使用同一个原始真实 H8f 81 点 ZIP、设置 `H9_EVIDENCE_ZIP` 的已完成测试：

| 测试组 | 实际通过 |
|---|---:|
| `test_h9_stage11_early_material_capture.py` | 8/8 |
| `test_h9_stage12_forensic_commit.py` | 7/7 |
| `test_h9_stage13_exclusive_capture.py` | 10/10 |
| **总计** | **25/25，0 failed、0 skipped** |

新增测试的真实操作包括：两个独立 Python 进程同时争用同一取证名称（恰一个成功）；真实子进程在 gzip 发布后强制退出；文件写入竞争、断链 symlink、归档字节突变、元数据提交冲突；以及在非原生环境复用历史 **sample 59 的真实 Cherchi 材料**，验证 gzip JSON 往返与 SHA。其他小型材料是明确标记的**文件系统测试夹具**，没有新原生 Cherchi 样本，也未伪造正式材料的真实执行。

### 复现命令

```bash
export H9_EVIDENCE_ZIP=/path/to/original-12135528290.zip
H9=research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018
for t in test_h9_stage11_early_material_capture.py test_h9_stage12_forensic_commit.py test_h9_stage13_exclusive_capture.py; do
    python -m unittest discover -s "$H9/tests" -p "$t" -v
done
python -m py_compile "$H9/source/h9_same_call_capture.py" "$H9/tests/test_h9_stage13_exclusive_capture.py"
```

本地运行日志 `reports/H9_STAGE13_LOCAL_TESTS.log` SHA256 `487c273dc9e570c70147dd71f5f6ccc8db8ad9343db635701ce24a4981cbb6d0`；另有独立原生预检日志和 JSON。没有启动新的 GitHub Actions（W3 独占文件规则禁止修改 `.github/workflows`）。

## 下一真正科学门槛

在 ≥24 GiB 内存、swap0、完整 W3 checkout、固定 CGAL/Cherchi/GMP 原生模块均存在且已通过源码/二进制 SHA 门槛时，使用现有 `prepare_h9_pinned_native.py --phase build` 和 `--phase run` 串行取得四份真实新材料；随后运行独立十质量矩积分、LPI/TPI 分支比较和左右 Jacobian 检查。仅得到有限点通过仍不得自动批准 Newton。须后续具备连续准入证明、实际接受步与独立终态复核才可能启动/验收 Heart Newton。
