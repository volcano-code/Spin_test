# W4 P3 — Cherchi 正式路线 + MuJoCo 仿真入口

**状态：Cherchi Teapot 原生结果尚未生成；MuJoCo MJCF 已生成，但物理仿真尚未运行。**

## 为什么 P2 不是 Cherchi

P2 8fc1dd3 使用的是 OpenSCAD/CGAL Nef 布尔并集，只作为几何对照。仓库 bindings/cherchi/InProcessBoolean.cpp 的 Python 接口只支持 intersection/difference；native 内部虽然已有 UNION 分支，但并未对 Python 暴露。所需 external/.../InteractiveAndRobustMeshBooleans 固定源码在仓库中缺失。W2 teacher_manifest 目前也是 ADAPTER_SMOKE_ONLY、零真实教师样本。

w4_cherchi_union.py 要求已编译、SHA 锁定的真实 Cherchi 模块，两次 union 必须真实执行，检查 native backend、exact_vertices、construction_records、独立拓扑和浮点自交；失败直接退出，没有 CGAL 替代。W4_CHERCHI_UNION_HANDOFF.patch 是供公共绑定维护者审查的补丁，W4 未修改公共源文件。

## MuJoCo 接口

p3_mujoco_teapot.py prepare 从经过几何检验的网格和明确输入的 SI 尺度/质量产生 MJCF，包含惯性张量主轴、freejoint、重力、地面、虚拟轴尖、简化球碰撞体及摩擦。run 调用官方 MuJoCo 的 MjModel、MjData、mj_forward、mj_step，设计测试 0/30/60 rad/s 与 5 度初始倾斜，输出接触、质心、高度、倾角和角速度 CSV。没有其他物理求解器的隐式回退。

本次生成的 diagnostic-cgal 代理网格仅供场景测试，并非 Cherchi 或 W0 批准的真实 CAD / 轴尖 / 固定 F / 可删 D。示例尺寸 0.15 m、质量 0.25 kg、虚拟轴尖半径 0.002 m、摩擦 0.9 均为显式的诊断假设。cherchi-certified 模式要求独立认证文件及 W0 的 Teapot 物理案例合同，否则拒绝。

## 从仓库根目录使用

```bash
python -m pip install numpy scipy trimesh mujoco==3.3.7
P1=research/SpinIt2014_Teapot_20261018/P1
python "$P1/p2_cgal_union.py" --source research/SpinIt2014_Teapot_20261018/input/teapot-public-original.obj --candidate "$P1/teapot-topology-candidate-p1.obj" --output "$P1/p2-output"
python "$P1/p3_mujoco_teapot.py" prepare --mesh "$P1/p2-output/p2-teapot-cgal-union-z-up.obj" --source-kind diagnostic-cgal --height-m 0.15 --mass-kg 0.25 --output "$P1/p3-mujoco-diagnostic"
python "$P1/p3_mujoco_teapot.py" run --xml "$P1/p3-mujoco-diagnostic/teapot_spinning.xml" --output "$P1/p3-mujoco-diagnostic/actual-run" --duration 2 --tilt-deg 5 --spin-rates 0 30 60
python -m unittest discover -v -s "$P1" -p 'test_p3_mujoco_teapot.py'
```

示例 viewer（有桌面图形环境时）: python -m mujoco.viewer --mjcf=<MJCF_XML_PATH> 。真正的稳定性结论必须有 MuJoCo 轨迹和轴尖/接触独立审计。

## 当前实际结果

本地回归共 11 项：10 通过，1 项真实 MuJoCo 动力学集成测试由于未安装运行时而跳过。调用 run 实际返回退出码 2、错误 MUJOCO_RUNTIME_UNAVAILABLE；尝试 pip 安装时容器 DNS 失败。没有生成任何真实 MuJoCo 轨迹或稳定性数据。

根据 P2 代理网格的积分惯性，0.15m/0.25kg 案例 COM_Z=0.05961113826578046m，主惯量约为 0.00070173346、0.00079569730、0.00099778189 kg*m^2，回构误差 4.34e-19。仅为诊断参数。

下一步：W0 明确尺度、密度、轴/尖和 F/D；共享核心负责人接入真正的 Cherchi UNION 并通过精确数值认证；在安装 MuJoCo 的环境里真实运行接触/旋转扫描，对比 Cherchi 优化前后。不能将 CGAL 或静态 MJCF 代替这些验收。
