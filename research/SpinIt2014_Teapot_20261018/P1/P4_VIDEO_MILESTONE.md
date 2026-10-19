# W4 P4｜Teapot 旋转对照：真实计算、视频导出与未完成的 MuJoCo

**本轮可复现里程碑是 SciPy 固定轴尖刚体对照，不是 MuJoCo 成功。**

P2 的公开 Utah Teapot CGAL 诊断代理网格经真实体积矩积分得到质心与中心惯性张量。 P4 使用平行轴定理构造轴尖惯性，采用 DOP853 求解重力矩下刚体 Euler 方程与四元数姿态。 质量 0.25 kg、高度 0.15 m、初始倾角 5°、g=9.81 m/s²。没有接触、摩擦、真实杆尖或材料裁剪。

### 真实结果（2.8 s）

| 初始自转 | 最大倾角 | 末尾倾角 | 达到 60° 的时间 |
|---|---:|---:|---:|
| 0 rad/s | 177.1276° | 31.5235° | 0.34s |
| 30 rad/s | 34.6659° | 4.2262° | 未到达 |
| 60 rad/s | 9.7222° | 5.1341° | 未到达 |

423 行计算轨迹；能量守恒最大相对漂移 1.38e-11，竖直角动量最大绝对漂移 2.13e-12。 该数值模型固定枢轴，允许刚体穿过画面参考平面，因**没有地面碰撞**不能作为稳定站立证据。

### 视频及复现

H.264 MP4 1440x810、30 FPS、169 帧、5.633s 慢放；完整解码检查通过。 MP4 SHA256: `280216a3cb50904fda6fc1012b7b622dcaf7fd5b250e0a1515a80c66e2669ef6`。 轨迹 CSV SHA256: `7642661476b9cb9acbf5b16a6bccbb7b3c61831f4b8259586d48d695b97a319c`。

本分支 P1/ 下提交：`w4_fixed_pivot_reference.py`, `render_fixed_pivot_video.py`, `p4_mujoco_video_capture.py`, 本说明与 `P4_VIDEO_EVIDENCE.json`。视频/CSV/输入网格/运行包在本轮对话的 ZIP 附件中，不在 GitHub 的 commit 内。

ZIP 解压后在打包根目录运行：

```bash
python w4_fixed_pivot_reference.py --asset p3-mujoco-diagnostic/assets/teapot_visual_z_up.obj --manifest p3-mujoco-diagnostic/simulation-manifest.json --out reference_results
python render_fixed_pivot_video.py --asset p3-mujoco-diagnostic/assets/teapot_visual_z_up.obj --manifest p3-mujoco-diagnostic/simulation-manifest.json --csv reference_results/reference_trajectories.csv --summary reference_results/reference_summary.json --out reference_results/w4_teapot_fixed_pivot_comparison.mp4 --poster reference_results/w4_teapot_fixed_pivot_poster.png
```

### MuJoCo 运行门禁

新脚本 `p4_mujoco_video_capture.py` 仅使用真正的 `mujoco.MjModel/MjData/mj_step/Renderer`；本地运行已尝试但 MuJoCo 缺失，返回退出码 2， 不能生成真实 MuJoCo 轨迹或视频。在联网 Ubuntu 安装 MuJoCo + OpenGL/EGL 后运行：

```bash
export MUJOCO_GL=egl
python p4_mujoco_video_capture.py --xml p3-mujoco-diagnostic/teapot_spinning.xml --out mujoco_actual --duration 2 --fps 24
```

当前 MJCF 仍是 CGAL 诊断代理网格及近似碰撞球，未来还需真正 Cherchi 结果、W0 物理尺寸和 F/D 合同、独立接触认证与 W2 真实教师， 才能将 MuJoCo 试验作为论文的正式验收。
