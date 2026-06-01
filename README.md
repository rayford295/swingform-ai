# SwingForm AI

<p align="center">
  <a href="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2f6f4e"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2458a6">
  <img alt="Sports" src="https://img.shields.io/badge/sports-golf%20%2B%20basketball-c46a2c">
  <a href="https://rayford295.github.io/swingform-ai/"><img alt="Website" src="https://img.shields.io/badge/website-live-1d6fa5"></a>
  <a href="https://rayford295.github.io/swingform-ai/viewer/pose3d.html"><img alt="3D Viewer" src="https://img.shields.io/badge/3D-pose%20viewer-7c3aed"></a>
</p>

Open-source sports-AI toolkit for turning real practice video into pose landmarks, swing phases, and explainable posture metrics. Golf is the first profile; basketball is built into the architecture as the next.

```
video → pose landmarks → swing phases → biomechanical metrics → feedback
```

## Demo

<table>
<tr>
<td width="50%">

**Skeleton + ball-trail overlay**

<video src="https://raw.githubusercontent.com/rayford295/swingform-ai/main/examples/yifan-golf-0520/golf_effects.mp4" controls width="100%"></video>

Depth-aware skeleton coloring · tee-anchored ball trail with detector confidence gates

</td>
<td width="50%">

**Skeleton keyposes — 2 swing cycles**

![Skeleton keyposes](docs/assets/yifan-golf-0520/skeleton_keyposes.png)

Address → Top → Impact proxy → Finish, auto-detected from wrist trajectory

</td>
</tr>
</table>

![Metric timeline](docs/assets/yifan-golf-0520/metric_timeline.png)

## Quickstart

```bash
# Install (core only — no heavy dependencies)
pip install -e .

# Full pipeline: pose + swing detection + ball trail + effects video
pip install -e ".[pose]"
python scripts/golf_render.py your_video.mp4 --output effects.mp4

# Detailed analysis: metrics CSV, summary JSON, charts
python scripts/analyze_local_golf_video.py your_video.mp4 \
  --session-id my-session --handedness right
```

Run tests:

```bash
python -m unittest discover -s tests
```

## What It Measures

| Layer | Capability |
| --- | --- |
| Video QA | Duration, FPS, resolution, frame coverage |
| Pose | MediaPipe Pose Landmarker — 33 landmarks, image + world (3D metric) coords |
| Golf phases | Address, top, impact proxy, finish — auto-detected from wrist path |
| Metrics | Elbow angle, knee angle, hand height, wrist speed, shoulder-hip separation, head and hip drift |
| Ball tracking | Tee/ball anchor estimation, conservative detector checks, and low-confidence proxy fallback |
| Output | CSV metrics, JSON summary, skeleton video, 3D viewer, Markdown report |

Current limits: the ball trail is a visual review aid, not a measured flight model. The pipeline does not yet estimate club-head speed, ball speed, spin, launch angle, or carry distance. See [docs/technical_tracks.md](docs/technical_tracks.md) for the roadmap on ball trajectory and 3D motion review.

## Open Examples

Two sessions are fully committed — source clip, pose export, per-frame metrics, and visual output.

| Session | Video | Frames | Swings | Report |
| --- | --- | --- | --- | --- |
| [golf-swing-demo](examples/golf-swing-demo/) | 14.4s · 320×568 | 361 / 361 | 2 | [report](docs/examples/golf_swing_demo_2026-05-31.md) |
| [yifan-golf-0520](examples/yifan-golf-0520/) | 7.2s · 320×568 | 216 / 216 | 2 | [report](docs/examples/yifan-golf-0520.md) |

## Project Map

```
scripts/
  golf_render.py              ← one-command pipeline: video → effects video
  analyze_local_golf_video.py ← full analysis with charts and reports
  build_highlight_reel.py     ← score and clip best swings from long videos

src/swingform_ai/
  schema.py                   ← Landmark, FramePose, PoseSequence dataclasses
  geometry.py                 ← angle, distance, midpoint helpers
  profiles/golf.py            ← golf swing metrics
  profiles/basketball.py      ← basketball shot metrics

docs/
  index.html                  ← project website (GitHub Pages)
  viewer/pose3d.html          ← interactive 3D skeleton viewer
  technical_tracks.md         ← ball trajectory and 3D motion roadmap
  architecture.md             ← pipeline architecture

examples/
  golf-swing-demo/            ← original open demo session
  yifan-golf-0520/            ← personal session with effects video
```

## Contributing

Contributions should improve usefulness, reproducibility, or sport coverage. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

[Website](https://rayford295.github.io/swingform-ai/) · [3D Viewer](https://rayford295.github.io/swingform-ai/viewer/pose3d.html) · [中文说明](README.zh-CN.md) · MIT License
