# SwingForm AI

SwingForm AI 是一个把人工智能、golf swing 分析和未来 basketball shooting form 姿势控制放在同一套架构里的科研风格 GitHub 项目。

第一阶段先做 golf，因为高尔夫挥杆有明确的动作阶段，也容易用手机视频持续采集。篮球先作为第二个 sport profile 预留接口，以后可以做投篮姿势、出手点、手肘角度、膝盖发力和 follow-through 分析。

## 这个项目先做什么

```text
手机视频 -> 姿态关键点 -> 动作阶段 -> 可解释指标 -> 反馈建议
```

第一版不是直接做完整 App，而是先搭一个可以复现、可以写论文/项目说明、也可以继续产品化的研究仓库。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `docs/research_scan_2026-05-31.md` | 当前 golf 和 basketball AI 姿势分析调研 |
| `docs/requirements.md` | 需求、MVP、指标和后续路线 |
| `docs/architecture.md` | 视频、姿态估计、动作分段、指标和反馈的架构 |
| `docs/data_governance.md` | 私人视频和公开数据的边界 |
| `src/swingform_ai/` | Python 姿态分析核心代码 |
| `examples/` | 可以安全提交的合成样例 |
| `tests/` | 几何和运动指标的单元测试 |

## 第一阶段目标

1. 输入单人 golf swing 视频或姿态 JSON。
2. 接入 MediaPipe、YOLO pose 或 MMPose 这类姿态估计后端。
3. 把挥杆分成 address、top、impact、finish 等阶段。
4. 计算手肘、膝盖、肩髋分离、节奏、平衡等可解释指标。
5. 输出带时间戳、关键帧和训练建议的反馈报告。

## 篮球扩展目标

篮球不另开一套系统，而是在同一个 pose-control core 上加 profile：

1. 分出 set、dip、lift、release、follow-through、landing。
2. 跟踪投篮侧手肘、手腕、髋、膝、脚踝、平衡和出手高度。
3. 优先和自己的最佳动作比较，再考虑和职业球员模板比较。

## 隐私边界

你的个人训练视频默认只留在本地，不进 git。仓库只提交代码、文档、合成样例、去标识化指标和明确可以公开的材料。

