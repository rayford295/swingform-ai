# SwingForm AI

<p align="center">
  <a href="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2f6f4e"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2458a6">
  <img alt="Sports" src="https://img.shields.io/badge/sports-golf%20%2B%20basketball-c46a2c">
  <a href="https://rayford295.github.io/swingform-ai/"><img alt="Website" src="https://img.shields.io/badge/website-live-1d6fa5"></a>
  <a href="https://rayford295.github.io/swingform-ai/viewer/pose3d.html"><img alt="3D Viewer" src="https://img.shields.io/badge/3D-pose%20viewer-7c3aed"></a>
</p>

开源运动 AI 工具包：把真实训练视频变成姿态关键点、动作阶段和可解释的运动指标。第一个运动 profile 是高尔夫挥杆，篮球投篮已在架构中预留接口。

```
视频 → 姿态关键点 → 动作阶段 → 运动指标 → 分析反馈
```

## Demo

[![点击查看骨架 + 球轨迹特效演示](docs/assets/yifan-golf-0520/skeleton_keyposes.png)](https://rayford295.github.io/swingform-ai/)

*点击图片打开项目网站 — 包含骨架叠加特效视频和可交互 3D 骨架查看器*

![指标时间线](docs/assets/yifan-golf-0520/metric_timeline.png)

*逐帧运动指标：手部高度 · 前臂角度 · 肩髋分离角 · 手腕速度*

## 快速开始

```bash
# 安装核心包（无重型依赖）
pip install -e .

# 安装视频分析扩展
pip install -e ".[pose]"

# 一条命令完成完整流水线：姿态提取 + 挥杆检测 + 球轨迹 + 特效视频
python scripts/golf_render.py your_video.mp4 --output effects.mp4

# 完整分析：逐帧指标 CSV、摘要 JSON、骨架图、时间线图
python scripts/analyze_local_golf_video.py your_video.mp4 \
  --session-id my-session --handedness right
```

运行测试：

```bash
python -m unittest discover -s tests
```

## 能力范围

| 层次 | 当前能力 |
| --- | --- |
| 视频 QA | 时长、帧率、分辨率、帧覆盖率检测 |
| 姿态估计 | MediaPipe Pose Landmarker — 33 个关键点，图像坐标 + 世界坐标（3D 米制） |
| 高尔夫阶段 | 站位、顶部、击球代理帧、收杆 — 由手腕轨迹自动检测 |
| 运动指标 | 肘关节角、膝关节角、手部高度、手腕速度、肩髋分离角、头部和髋部偏移 |
| 球轨迹追踪 | 光流 + 身体遮罩排除 + RANSAC 抛物线拟合 |
| 输出 | 特效视频、指标 CSV、摘要 JSON、3D 查看器、Markdown 报告 |

当前限制：不测量杆头速度、球速、旋转、发射角或飞行距离。球轨迹和 3D 动作回顾的技术路线见 [docs/technical_tracks.md](docs/technical_tracks.md)。

## 开源示例

两个完整会话已提交至仓库，包含原始视频、姿态导出、逐帧指标和可视化输出。

| 会话 | 视频信息 | 帧数 | 挥杆次数 | 报告 |
| --- | --- | --- | --- | --- |
| [golf-swing-demo](examples/golf-swing-demo/) | 14.4s · 320×568 | 361 / 361 | 2 | [报告](docs/examples/golf_swing_demo_2026-05-31.md) |
| [yifan-golf-0520](examples/yifan-golf-0520/) | 7.2s · 320×568 | 216 / 216 | 2 | [报告](docs/examples/yifan-golf-0520.md) |

## 仓库结构

```
scripts/
  golf_render.py              ← 完整流水线：视频 → 特效视频
  analyze_local_golf_video.py ← 含图表和报告的完整分析
  build_highlight_reel.py     ← 长视频挑选最佳挥杆片段

src/swingform_ai/
  schema.py                   ← Landmark、FramePose、PoseSequence 数据模型
  geometry.py                 ← 角度、距离、中点计算工具
  profiles/golf.py            ← 高尔夫挥杆指标与阶段检测
  profiles/basketball.py      ← 篮球投篮指标

docs/
  index.html                  ← 项目网站（GitHub Pages）
  viewer/pose3d.html          ← 可交互 3D 骨架查看器
  technical_tracks.md         ← 球轨迹与 3D 动作回顾技术路线
  architecture.md             ← 流水线架构设计

examples/
  golf-swing-demo/            ← 原始开源演示会话
  yifan-golf-0520/            ← 个人会话（含特效视频）
```

## 参与贡献

欢迎提升可用性、可复现性或运动覆盖范围的贡献。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

[项目网站](https://rayford295.github.io/swingform-ai/) · [3D 查看器](https://rayford295.github.io/swingform-ai/viewer/pose3d.html) · [English](README.md) · MIT License
