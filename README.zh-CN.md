# SwingForm AI

<p align="center">
  <img src="docs/assets/readme/hero.png" alt="SwingForm AI golf swing analysis hero" width="980">
</p>

SwingForm AI 是一个纯开源 sports-AI 项目：把真实训练视频变成姿态关键点、动作阶段和可解释的姿势指标。第一阶段做 golf swing，架构上预留 basketball shooting form。

这不是论文仓库，而是一个要好看、好用、可复现、能长期成长的开源项目。

```text
训练视频 -> 姿态关键点 -> 动作阶段 -> 可解释指标 -> 反馈
```

现在最明确的产品闭环是：

```text
长训练视频 -> 统计挥杆次数 -> 挑出最好几次 -> 输出高质量短视频 -> 加球轨迹特效
```

## 开源示例

第一个 golf 视频已经作为完整示例提交。仓库包含原视频、姿态 JSON、指标 CSV、报告摘要和视觉索引。

| 指标 | 数值 |
| --- | ---: |
| 视频长度 | 14.44s |
| 分辨率 | 320x568 |
| 姿态覆盖 | 361 / 361 frames |
| 挥杆片段 | 2 |
| 平均 landmark visibility | 0.805 |

![Golf swing metric timeline](docs/assets/golf-swing-demo/metric_timeline.png)

![Golf swing skeleton keyposes](docs/assets/golf-swing-demo/skeleton_keyposes.png)

完整报告见 [docs/examples/golf_swing_demo_2026-05-31.md](docs/examples/golf_swing_demo_2026-05-31.md)。

## 快速开始

安装：

```bash
python -m pip install -e .
```

运行小型姿态 JSON demo：

```bash
python -m swingform_ai.analyze_pose_json examples/sample_pose_sequence.json --sport golf
python -m swingform_ai.analyze_pose_json examples/sample_pose_sequence.json --sport basketball
```

复现 golf 示例：

```bash
python -m pip install -e ".[pose]"
python scripts/analyze_local_golf_video.py \
  examples/golf-swing-demo/golf.mp4 \
  --session-id golf-swing-demo \
  --handedness right \
  --events-json examples/golf_swing_demo_events.json
```

从长视频生成 highlight reel：

```bash
python scripts/build_highlight_reel.py path/to/long_practice_video.mp4 \
  --session-id range-session-001 \
  --top-k 3 \
  --shot-direction right
```

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `examples/golf-swing-demo/` | 开源原视频、姿态导出、指标和报告输入 |
| `docs/examples/` | 可读的 demo 报告 |
| `docs/assets/` | README 和报告图片 |
| `scripts/analyze_local_golf_video.py` | golf 视频分析脚本 |
| `scripts/build_highlight_reel.py` | 长视频剪辑和球轨迹特效脚本 |
| `src/swingform_ai/` | 姿态 schema、几何计算、运动 profile 和 CLI |
| `tests/` | 单元测试 |

## 项目原则

1. 美观很重要：README、图表和报告都应该容易扫读。
2. 实用很重要：每个指标都要能回到具体帧、阶段或姿态。
3. 开源示例很重要：别人应该能看到输入和输出一起出现。
4. 运动 profile 要分开：golf 和 basketball 共享 pose core，但保留各自阶段和指标。
5. 结论要克制：单摄像头姿态估计有价值，但不是 launch monitor，也不是职业教练替代品。

项目气质和长期方向见 [docs/north_star.md](docs/north_star.md)。

## 技术主线

下一阶段聚焦两个方向：

1. 球的轨迹：球检测、轨迹渲染、平滑拟合，后面再做相机几何下的 3D flight。
2. 3D 视觉：pseudo-3D skeleton、motion trails，后面再接 world-grounded motion reconstruction。

具体技术路径见 [docs/technical_tracks.md](docs/technical_tracks.md)。

长视频到短视频的具体工作流见 [docs/highlight_reel_pipeline.md](docs/highlight_reel_pipeline.md)。

## 下一步

1. 先把长视频变成 scored highlight reel。
2. 先做 ball trajectory 和漂亮的 trail overlay。
3. 做 pseudo-3D skeleton review。
4. 再加 golf club tracking 和 basketball shooting profile。
