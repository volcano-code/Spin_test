# P21：同次 M6 证据捕获、离线复算与合格主机执行入口

## 本关结论

P21 补齐正式 M6 的可复算证据链。新增程序利用原 `InProcessCherchiEvaluator.stage_observer`，保存一次实际执行产生的 source、两次原始 Cherchi Boolean packet、同次精确 material、积分值及 10×10 Jacobian。每个 operation 只执行一次，原结果对象原样返回；没有 subclass、monkeypatch、第二次源生成或为归档补做第三次 Boolean。

**本关没有实际执行正式 M6。** 正式入口继续要求物理与有效内存均至少 20 GiB、swap0。本机执行的详细资源观察、运行锁、路径和日志归档等待单独的公开授权；本次公开提交包含实现、控制测试和基于既有公开冻结输入的算术结果。

本地 72 项新测试全部通过，0 skip、0 expected failure；其中正向切割／J replay 使用明确标记的解析 box fixtures，不能当作 Teapot 原生执行。另对真实冻结 M/F/D OBJ 独立重算了 30 个精确矩，全部匹配 P20 冻结值，10 个 M−F−D 残差为零，耗时约 2.614 秒。这个纯算术结果不重新证明集合相等。

本说明及证据索引在本轮 Git 提交和新 CI 执行之前冻结。远端实际作业状态应查看对应提交的 Actions；本文没有预先宣称 CI 成功。

## 为什么需要 P21

固定 W0 的 M4/M5/M6 在运行时已经验证同次 material、J、同源互反 Boolean 和三组原生集合分区。但原返回 JSON 主要保留结论、摘要、计数与误差，没有保存全部实际 source、Boolean packet 和 J 数组。原生进程结束后，仅靠这些摘要无法重新计算切割结果的十矩或核对 100 个 J 元素。

P21 使用已有阶段接口捕获真实输出，并保持 W0、P20、P19 几何和历史证据原样。新的 factory 仍返回精确类型为 `InProcessCherchiEvaluator` 的真实对象；未改变注册的 c、目标轴、尺度、F/D、源三角化、Cherchi 版本或积分算法。

## 新增实现

| 文件 | 职责 |
|---|---|
| `p21_same_call_capture.py` | 单进程、单线程阶段观察器；exclusive 文件、fsync 事件流、每阶段序号和失败记录 |
| `p21_native_factory.py` | 复用 P20 实际准备，核对真实 fresh evaluator 后附加观察器 |
| `p21_m6_replay.py` | `preflight`、`register`、`execute`；预登记字节锁、调用冻结 P20、保留成功和失败归档 |
| `p21_replay_verify.py` | 标准库离线核验与精确有理数重算，不导入 native、不调用 factory 或 Boolean |
| `test_p21_*.py` | 72 项控制、序列化和解析算术回归；fixtures 明确为 TEST_ONLY |

### 捕获的内容

- source 原生返回值，以及实际保存 material 中的 physical source 顶点、面和 source digest。
- 两次 Boolean 原始 packet，保留 exact vertices、construction records、原始索引和后续局部 winding 信息。
- intersection motion、各积分输出。
- 导数的完整 **100 个 binary64 元素，800 个 little-endian 字节**；负零位保留。
- 原 `material_attachment_serialization` 返回的 JSON 字符串原始 UTF-8 字节，不添加换行、不重新编码该字符串。
- 准备和执行阶段的 begin/completed/failed 事件。attempt 计数与已完成计数区分；operation 失败和保存失败区分。
- 真实 c、frame、request、fixed、problem identity、六项 pins、生产代码／二进制身份以及资源观察。

`PreparedBoundary` 等不透明对象只保存具体类型，避免通过 repr 或额外调用改变行为。观察器的写盘时间计入运行耗时；本关不把该耗时称为无观测开销的性能基准。

### 离线核验的范围

完整正式产物可核验：外部 manifest SHA、所有文件字节、P20 父子 envelope、worker nonce 与 stdout marker、六项 pins、同次 100 个 J 的字节身份、精确边界和 frame、R/C/D 及 M/F 的完整十矩，以及全部十个 D−R−C、M−F−R−C 残差。原生三分区收据与 M4/M5 身份也被相互绑定。

离线程序不重新执行原生集合谓词。十矩相等不等于集合相等；保存的 J 字节相等不证明 J 的数学正确性或导数邻域。原始 complement packet 本身不含 operand/operation 参数，互反操作的执行关联依靠固定 W0 M6 收据和阶段顺序，不能仅由这个 packet 独立证明原生来源。

即使完整 replay 通过，以下仍为 false：独立原生运行认证、原生集合谓词重新执行、J 正确性证明、导数邻域认证、W0 owner／物理案例准入、W2 teacher/training 准入、优化执行、优化前后 MuJoCo 对照及物理验证。

## 公开验收文件

| 文件 | 内容 |
|---|---|
| `P21_TEST_INVENTORY.json` | 全部 72 个必须运行的 test ID |
| `P21_LOCAL_TEST_RECEIPT.txt`、`P21_LOCAL_TEST_RESULT.json` | 实际 72/72、零跳过结果和受测代码摘要 |
| `P21_FROZEN_MFD_ARITHMETIC.json` | 已公开冻结 M/F/D 输入的 30 个精确矩与十个零残差 |
| `P21_IMPLEMENTATION_INDEX.json` | 本次公开的实现和验收文件摘要 |

本机正式入口执行的 ZIP、详细执行摘要和离线报告暂不在本次公开提交中。自动审批要求对包含本地路径、运行锁和资源快照的具体归档另行取得公开授权。没有把这些详细内容移入其他格式发布。公开 CI 会从本次提交自行生成其控制测试、资源预检和公开冻结输入算术证据。

换机器或重新构建时，需要在新机器重新准备并登记；历史 lock 绑定原机器的实际路径和构建，不能作为新机器的可移植凭据。

## 合格主机如何执行

### 1. 先运行纯资源检查

在独立 W4 checkout 中运行。`P21_W4` 必须指向真实 W4 checkout，不能把 W2 项目父目录假定为 W4 根目录。

```bash
P21_W4="$(git rev-parse --show-toplevel)"
P21_P1="$P21_W4/research/SpinIt2014_Teapot_20261018/P1"
P21_RUN="$(mktemp -d /tmp/w4-p21-run-XXXXXXXX)"
python "$P21_P1/p21_m6_replay.py" preflight \
  --output "$P21_RUN/resource-preflight.json"
```

退出 0 仅代表这次实际资源观察满足原资源策略。退出 3 表示资源拒绝；报告保留物理、cgroup、RLIMIT_AS 和 swap 信息。正式准备按既有名义 24 GiB/swap0 协议，物理与有效内存均至少 20 GiB。P20 worker 自己还会复查，最长原生运行 3600 秒，保持原串行锁。

### 2. 使用实际构建和实际 preparation 的 pins

需要三个真实路径：固定 W0 checkout、完整 `_make_it_stand` 所在目录、两个 Cherchi 扩展所在目录。W0 checkout 的全部受检查源码必须实体化且符合固定 Git blob。

| 部件 | 固定版本 |
|---|---|
| W0 | `51cbfd33d08063404d7e0c40e4256dd0e38efa1a` |
| Native core 构建源 | `58fd12c1306c1c01679a19172e276eef0cb30542` |
| 原始 Cherchi | `7bd6c2697695f555f9a15d7e154e084d841316f0` |
| P20 request | SHA `74d9cfa64417dd2c82d196ab27094651976954742a4c692667a1b19b1032de62` |

重新构建继续使用未改动的 `p20_build_native_ci.py`。`--source-checkout`、`--build-root`、`--evidence` 必须是互不嵌套的独立目录，输出目录必须全新。已实际通过的环境配方见工作流 `p20-swap0-owned-material-replay`：Ubuntu 24.04、Python 3.12、numpy 2.3.5、scipy 1.17.0、trimesh 4.12.2、networkx 3.7、CMake 3.31.6、Ninja 1.11.1.4、pybind11 3.0.1、GMP 6.3.0、MPFR 4.2.1。Ubuntu 22.04 的系统包不能直接假定满足这些严格检查。

构建示例（路径由实际工作目录填写）：

```bash
: "${P21_CORE_CHECKOUT:?fixed core source checkout}"
: "${P21_BUILD_ROOT:?new non-nested build directory}"
: "${P21_BUILD_EVIDENCE:?new non-nested build evidence directory}"
python "$P21_P1/p20_build_native_ci.py" \
  --source-checkout "$P21_CORE_CHECKOUT" \
  --build-root "$P21_BUILD_ROOT" \
  --evidence "$P21_BUILD_EVIDENCE" \
  --timeout-seconds 2400
```

先按 P20 原生准备入口取得**该构建自己的**新 pins，使用完整实际动态库环境。P21 不把历史 CI ELF 摘要替换进本机 pins；不自动安装依赖、切换仓库分支或修改全局 swap。

### 3. 单独登记本机执行输入

```bash
: "${P21_W0_CHECKOUT:?W0 checkout at the fixed commit}"
: "${P21_CORE_PYTHON:?directory containing the actual core ELF}"
: "${P21_CHERCHI_PYTHON:?directory containing both actual Cherchi ELFs}"
: "${P21_PINS_FILE:?six-pin JSON from actual preparation of this build}"

python "$P21_P1/p21_m6_replay.py" register \
  --w0-checkout "$P21_W0_CHECKOUT" \
  --pins "$P21_PINS_FILE" \
  --python-path "$P21_CORE_PYTHON" \
  --python-path "$P21_CHERCHI_PYTHON" \
  --output "$P21_RUN/prerun-lock.json"
```

这一步只读取和核对实际字节，不导入 factory、不执行 native。输出明确包含 `lock_sha256`。将该摘要作为执行前已登记值保存；它是字节绑定，不能自行解释为外部 owner 批准或独立运行认证。源码、二进制、Python 或动态库环境改变后，应重新登记到新的 lock。

### 4. 使用已登记摘要执行并离线核验

```bash
: "${P21_LOCK_SHA256:?digest recorded from the preceding registration}"
python "$P21_P1/p21_m6_replay.py" execute \
  --lock "$P21_RUN/prerun-lock.json" \
  --lock-sha256 "$P21_LOCK_SHA256" \
  --output-directory "$P21_RUN/formal-bundle"
```

执行结果会打印 `manifest_sha256`。即使正式入口资源拒绝，bundle 也保留真实报告和日志。对于启动失败或不完整输出，未知执行状态保持 null；不补写零计数或成功标志。运行后资源读取／报告解析失败会归档为 collection error，并以退出 4 表示失败。

```bash
: "${P21_BUNDLE_SHA256:?digest recorded from the actual execution output}"
python "$P21_P1/p21_replay_verify.py" \
  --bundle "$P21_RUN/formal-bundle" \
  --manifest-sha256 "$P21_BUNDLE_SHA256" \
  --output "$P21_RUN/offline-review.json"
```

| 退出码／状态 | 含义 |
|---|---|
| execute 0 | 原 P20 正式入口实际返回完整原生 M6 几何验证结果；仍需核验归档 |
| execute 3 | 实际资源或串行条件拒绝；不能认为 M6 通过 |
| execute 4 / 5 | 输入、执行、采集失败 / 原入口超时；保留原始失败 |
| verify 0 | `ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT`，完整收据与保存算术一致 |
| verify 3 | 资源拒绝或证据不完整；不会声明正式切割/J 通过 |
| verify 4 | 输入、哈希、身份、算术或收据冲突 |

## 本关 CI 与后续研究

新增 `p21-replay-evidence-contract` 仅执行 72 项控制／捕获／解析算术测试、真实资源观察和真实冻结 M/F/D 精确矩重算，不执行 native build、factory、Boolean 或正式 M6。新 artifact 名明确为 `W4-P21-replay-evidence-control-only-formal-M6-NOT-executed`。原工作流 11 个作业和 85,436-byte 前缀逐字节保留；历史失败不会因本关测试通过而消失。

下一项实算仍是在资源合格的主机执行正式 M6，取得真实一次 source、两次同源 Cherchi Boolean、D=R+C、M=F+R+C 与同次 J 证据。此后仍须分别通过 W0/W2 的外部准入，完成 Figure 9 三目标消融、相同初态的真实优化前后 MuJoCo 对照，以及物理验证。P21 完成的是证据保存与复算实现，没有替代这些研究结果。
