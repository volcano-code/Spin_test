# Noodles v6 在线精确构造与求解接入：实际执行报告

## 结论

本轮继续了去除永久椭球外壳后的真实精确构造、独立分区检查、原生导数检查和有条件求解。所有结果以下表的实际终态记录为准；没有把输入几何、函数可调用或局部测试当作完整目标达成。

**尚未达到花盘案例的完整优化—材料—动力学交付标准。没有推送 GitHub。**

## 实际阶段

| 阶段 | 退出码 | 秒数 |
|---|---:|---:|
| 08-foreground-build | 1 | 0.016 |
| 09-native-proof-regressions | 127 | 0.008 |
| 10-exact-input-proof | 127 | 0.008 |
| 11-native-reynolds-derivatives | 127 | 0.008 |
| 12-native-noodles-seed0 | 未取得记录 | — |
| 13-exact-terminal-closure | 未取得记录 | — |

退出码0仅证明该脚本阶段成功退出；完整优化还需要原生 CONVERGED、实际同次返回的终态材料及独立分区结果。124为资源时间中断，不代表不可行。未运行的步骤不能计为通过。

## 修复范围

1. 使用既有82个v6源部件，固定材料仅为79根管、连接与转轴的81部件并集；外椭球仅定义设计空间。
2. 显式构造 F=S、D=E\S、A=E∪S，并构造K=E∩F、R=F\E，供独立分区验证。没有继承旧v5质量、惯量或优化系数。
3. 为暴露设计域新增专用输入检查，不再要求新移除材料永远与初始外表面保持正间距。旧的空腔模型检查保持原状。
4. 检查有向有限表面链 F+D−A、K+D−E、K+R−F；在每个输入均为有界0/1实体的前提下，用完整表面链消去而非仅体积近似确认分区。
5. 新增CGAL精确布尔与离散表面Reynolds导数适配候选。源三角形由原生二次曲面映射产生；切割面运动通过实际出生源面和精确重心坐标关联，使用原GMP积分模块。候选并非已批准的生产后端。
6. 在前置检查通过时，使用原生质量矩Newton入口及原v6登记参数启动求解；不存在预设最终双曲面、删壳后沿用旧解或使用体素回退。
7. 新增同次终态材料的独立闭合脚本：只能处理实际CONVERGED和同次保存的源/材料，不会为未完成的运行造出complete.obj。

## 状态文件与证据解释

- 精确构造：没有对应完成文件。
- 完整新输入分区：没有对应完成文件。
- 原生小型回归：没有对应完成文件。
- 小型状态导数检查：没有对应完成文件。
- 原生优化终态：没有对应完成文件。
- 终态材料独立交付：没有对应完成文件。
## 实际失败或中断（完整日志在证据包）

### 08-foreground-build

```text
ninja: error: loading 'build.ninja': No such file or directory

```

### 09-native-proof-regressions

```text
/mnt/data/noodles_v6_work/env.sh: line 8: /mnt/data/noodles_v6_work/bootstrap/sysroot/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2: No such file or directory

```

### 10-exact-input-proof

```text
/mnt/data/noodles_v6_work/env.sh: line 8: /mnt/data/noodles_v6_work/bootstrap/sysroot/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2: No such file or directory

```

### 11-native-reynolds-derivatives

```text
/mnt/data/noodles_v6_work/env.sh: line 8: /mnt/data/noodles_v6_work/bootstrap/sysroot/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2: No such file or directory

```

## 构建与版本边界

- 当前主原生运行检查点来自已上传 b0a13e3，不是 a17ff49 全量重新编译。
- 独立新增 CGAL 求值适配为实验候选；没有覆盖项目现有正式求解路线。
- 小型状态导数测试不等于完整面条所有迭代状态导数通过。
- 输入整体仍填满设计椭球；固定材料没有永久椭球壳。输入 OBJ 不是最终优化结果。
- 未执行新的面条动力学或实际 Bambu Studio 切片验证。

没有运行新面条动力学，因此不会借用花盘轴承结果或旧v5仿真赋予v6旋转通过。没有实际打印/切片证据，因此所有输入及候选网格均不带制造认证。

## 文件使用

精确输入包里的 fixed-input-mm.obj、design-input-mm.obj、initial-input-mm.obj 是不同角色的输入视图；不能将 fixed 预览误称最终优化体，也不能将初始椭球外观解释为壳约束未移除。正式几何为有理坐标JSON，OBJ是浮点视图。

源码包为独立实验增量，不整体替换原项目，不包含旧统一入口的强制配置改动，也不改变花盘、心形或旧面条记录。