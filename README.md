<p align="center">
  <img src="docs/assets/brand/swingform-icon.svg" alt="SwingForm AI icon" width="72">
</p>

<h1 align="center">SwingForm AI</h1>

<p align="center">
  <a href="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2f6f4e"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2458a6">
  <img alt="Sports" src="https://img.shields.io/badge/sports-golf%20%2B%20basketball-c46a2c">
  <a href="https://rayford295.github.io/swingform-ai/"><img alt="Website" src="https://img.shields.io/badge/website-live-1d6fa5"></a>
  <a href="https://rayford295.github.io/swingform-ai/viewer/pose3d.html"><img alt="3D Viewer" src="https://img.shields.io/badge/3D-pose%20viewer-7c3aed"></a>
</p>

![SwingForm AI hero](docs/assets/readme/hero.png)

Open-source sports posture intelligence for turning real practice video into pose landmarks, sport-specific phases, visual overlays, and explainable motion metrics. Golf and basketball live as separate profiles inside one shared posture-analysis core.

```
video -> pose landmarks -> swing phases -> metrics -> review-ready output
```

## Demo Surface

| Surface | What to Open |
| --- | --- |
| Website | [rayford295.github.io/swingform-ai](https://rayford295.github.io/swingform-ai/) |
| 3D pose viewer | [Interactive skeleton viewer](https://rayford295.github.io/swingform-ai/viewer/pose3d.html) |
| Golf effects video | [examples/yifan-golf-0520/golf_effects.mp4](examples/yifan-golf-0520/golf_effects.mp4) |
| Basketball overlay video | [examples/yifan-basketball-0601/basketball_overlay.mp4](examples/yifan-basketball-0601/basketball_overlay.mp4) |
| Golf report | [docs/examples/yifan-golf-0520.md](docs/examples/yifan-golf-0520.md) |
| Basketball report | [docs/examples/yifan-basketball-0601.md](docs/examples/yifan-basketball-0601.md) |

## What It Produces

| Layer | Output |
| --- | --- |
| Video QA | Duration, FPS, resolution, frame coverage |
| Pose | MediaPipe Pose Landmarker, 33 body landmarks |
| Golf phases | Address, top, impact proxy, finish |
| Basketball profile | Set, dip, lift, release proxy, follow-through, landing |
| Metrics | Elbow angle, knee angle, hand height, wrist speed, shoulder-hip separation, head and hip drift |
| Visuals | Skeleton overlay, ball-trail aid, keypose sheet, metric timeline, 3D viewer |

The ball trail is currently a visual review aid. It is not yet a measured ball-flight model, and the project does not estimate club-head speed, ball speed, spin, launch angle, or carry distance.

Basketball now supports a pose-based release-proxy demo. It does not yet estimate make/miss, shot arc, ball-rim contact, or measured release angle.

## Quickstart

```bash
# Install core package
python -m pip install -e .

# Install video and pose dependencies
python -m pip install -e ".[pose]"

# Render an effects video from a golf clip
python scripts/golf_render.py your_video.mp4 --output effects.mp4

# Export metrics, charts, summary JSON, and report assets
python scripts/analyze_local_golf_video.py your_video.mp4 \
  --session-id my-session \
  --handedness right

# Export basketball pose, metrics, charts, report assets, and overlay video
python scripts/analyze_local_basketball_video.py your_video.mp4 \
  --session-id my-basketball-session \
  --shooting-side right \
  --copy-video \
  --render-overlay
```

Run tests:

```bash
python -m unittest discover -s tests
```

## Open Examples

| Session | Source Clip | Frames | Events | Artifacts |
| --- | --- | --- | --- | --- |
| `yifan-golf-0520` | [golf.mp4](examples/yifan-golf-0520/golf.mp4) | 216 / 216 | 2 | [pose](examples/yifan-golf-0520/pose_sequence.json) · [metrics](examples/yifan-golf-0520/metrics.csv) · [report](docs/examples/yifan-golf-0520.md) |
| `yifan-basketball-0601` | [basketball.mp4](examples/yifan-basketball-0601/basketball.mp4) | 244 / 244 | 1 release-proxy event | [overlay](examples/yifan-basketball-0601/basketball_overlay.mp4) · [pose](examples/yifan-basketball-0601/pose_sequence.json) · [metrics](examples/yifan-basketball-0601/metrics.csv) · [report](docs/examples/yifan-basketball-0601.md) |
| `golf-swing-demo` | [golf.mp4](examples/golf-swing-demo/golf.mp4) | 361 / 361 | 2 | [pose](examples/golf-swing-demo/pose_sequence.json) · [metrics](examples/golf-swing-demo/metrics.csv) · [report](docs/examples/golf_swing_demo_2026-05-31.md) |

## Project Map

```text
scripts/
  golf_render.py              one-command video -> effects video pipeline
  analyze_local_golf_video.py analysis export for pose, metrics, charts, reports
  analyze_local_basketball_video.py basketball export for pose, metrics, charts, overlay
  build_highlight_reel.py     long-video swing scoring and clip export

src/swingform_ai/
  schema.py                   pose dataclasses
  geometry.py                 angle, distance, and line helpers
  profiles/golf.py            golf posture metrics
  profiles/basketball.py      basketball shot-form metrics

docs/
  index.html                  GitHub Pages website
  viewer/pose3d.html          interactive 3D skeleton viewer
  technical_tracks.md         ball trajectory and 3D roadmap
  architecture.md             pipeline architecture
```

## Direction

SwingForm AI should look useful early while staying honest about what it measures. The near-term focus is polished multi-sport examples, clean visual review, and reproducible artifacts. The next technical steps are a labeled golf ball-tracking benchmark and a basketball multi-person shooter-selection loop before claiming measured ball flight or shot outcome.

---

[Website](https://rayford295.github.io/swingform-ai/) · [3D Viewer](https://rayford295.github.io/swingform-ai/viewer/pose3d.html) · [中文说明](README.zh-CN.md) · [Contributing](CONTRIBUTING.md) · MIT License
