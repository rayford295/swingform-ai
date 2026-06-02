# SwingForm AI

<p align="center">
  <a href="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml"><img src="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <img src="https://img.shields.io/badge/python-3.10%2B-2458a6" alt="Python">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-2f6f4e" alt="MIT"></a>
  <a href="https://rayford295.github.io/swingform-ai/"><img src="https://img.shields.io/badge/website-live-1d6fa5" alt="Website"></a>
  <a href="https://rayford295.github.io/swingform-ai/viewer/pose3d.html"><img src="https://img.shields.io/badge/3D%20viewer-open-7c3aed" alt="3D Viewer"></a>
</p>

<p align="center">
  <b>Open-source sports posture intelligence.</b><br>
  Turn a phone video into pose landmarks, swing phases, biomechanical metrics, and a skeleton overlay — in one command.
</p>

---

[![Demo — click to open the live site](docs/assets/yifan-golf-0520/skeleton_keyposes.png)](https://rayford295.github.io/swingform-ai/)

<p align="center"><sub>Golf · 2 swing cycles detected · click to see the full effects video and 3D skeleton viewer</sub></p>

---

## Install

```bash
pip install -e ".[pose]"
```

## Usage

```bash
# Skeleton + ball-trail effects video (full pipeline, one command)
python scripts/golf_render.py your_video.mp4 --output effects.mp4

# Detailed analysis — CSV metrics, JSON summary, keypose chart, timeline
python scripts/analyze_local_golf_video.py your_video.mp4 --session-id s1 --handedness right
python scripts/analyze_local_basketball_video.py your_video.mp4 --session-id s1 --shooting-side right

# Tests
python -m unittest discover -s tests
```

## What It Measures

| | Golf | Basketball |
|---|---|---|
| **Phases** | Address · Top · Impact · Finish | Set · Dip · Lift · Release · Follow-through |
| **Angles** | Lead arm · Trail elbow · Knee flex | Shooting elbow · Knee |
| **Spatial** | Hand height · Stance width · Shoulder-hip separation | Wrist height · Guide-hand distance |
| **Temporal** | Backswing / downswing time · Tempo ratio | — |
| **Drift** | Head drift · Hip drift from address | — |

Ball tracking uses optical flow + body-exclusion mask + RANSAC parabolic fit. It is a **visual aid**, not a measured flight model — no club speed, ball speed, spin, or launch angle.

## Open Examples

| Session | Sport | Clip | Frames | Events |
|---|---|---|---|---|
| [yifan-golf-0520](examples/yifan-golf-0520/) | ⛳ Golf | 7.2 s · 320×568 | 216 / 216 | 2 swings |
| [yifan-basketball-0601](examples/yifan-basketball-0601/) | 🏀 Basketball | 8.1 s · 720×1280 | 244 / 244 | 1 release |
| [golf-swing-demo](examples/golf-swing-demo/) | ⛳ Golf | 14.4 s · 320×568 | 361 / 361 | 2 swings |

Each session includes source video · pose JSON · metrics CSV · visual charts · Markdown report.

## Project Layout

```
src/swingform_ai/       core library (schema, geometry, profiles, ball tracking)
scripts/                runnable pipelines (golf_render, analyze, highlight_reel)
examples/               open sessions with source clips and all derived artifacts
docs/                   website, 3D viewer, architecture, roadmap
tests/                  unit tests (geometry, profiles, ball tracking)
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Contributions that improve reproducibility, add sport coverage, or make the outputs more beautiful are especially welcome.

---

<p align="center">
  <a href="https://rayford295.github.io/swingform-ai/">Website</a> ·
  <a href="https://rayford295.github.io/swingform-ai/viewer/pose3d.html">3D Viewer</a> ·
  <a href="README.zh-CN.md">中文</a> ·
  <a href="docs/technical_tracks.md">Roadmap</a> ·
  MIT License
</p>
