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

<p align="center">
  <img src="docs/assets/readme/hero.png" alt="SwingForm AI — Golf swing analysis for real practice" width="860">
</p>

---

<table>
<tr>
<td width="50%">

![Golf swing skeleton overlay](docs/assets/yifan-golf-0601/demo.gif)

<p align="center"><sub>⛳ <b>Golf · TopGolf</b> · skeleton overlay · ball trail · <a href="https://github.com/rayford295/swingform-ai/blob/main/examples/yifan-golf-0601/golf.mp4">source video ↗</a></sub></p>

</td>
<td width="50%">

![Basketball skeleton overlay](docs/assets/yifan-basketball-0710/demo.gif)

<p align="center"><sub>🏀 <b>Basketball · 1v1 gameplay</b> · skeleton overlay · release detected under contest · <a href="https://github.com/rayford295/swingform-ai/blob/main/examples/yifan-basketball-0710/basketball_overlay.mp4">full video ↗</a> · <a href="https://www.youtube.com/shorts/9nPEMg---YA">YouTube Short ↗</a></sub></p>

</td>
</tr>
</table>

<p align="center"><sub><a href="https://rayford295.github.io/swingform-ai/">Open the live site</a> for the full effects video and interactive 3D skeleton viewer</sub></p>

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

# Compare two analyzed sessions of the same sport
python scripts/compare_sessions.py examples/yifan-golf-0520 examples/yifan-golf-0601

# Regenerate the README example tables from committed summaries
python scripts/generate_examples_table.py

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

<!-- examples-table:start -->
| Session | Sport | Clip | Frames | Events |
|---|---|---|---|---|
| [yifan-basketball-0710](examples/yifan-basketball-0710/) | 🏀 Basketball · 1v1 | 57.1 s · 480×854 | 1621 / 1712 | 2 releases |
| [yifan-golf-0601](examples/yifan-golf-0601/) | ⛳ Golf | 27.0 s · 720×1280 | 802 / 809 | 3 swings |
| [yifan-golf-0520](examples/yifan-golf-0520/) | ⛳ Golf | 7.2 s · 320×568 | 216 / 216 | 2 swings |
| [golf-swing-demo](examples/golf-swing-demo/) | ⛳ Golf | 14.4 s · 320×568 | 361 / 361 | 2 swings |
<!-- examples-table:end -->

Each session includes source video · pose JSON · metrics CSV · visual charts · Markdown report.
Cross-session comparison: [yifan-golf-0520 vs yifan-golf-0601](docs/examples/compare-yifan-golf-0520-vs-yifan-golf-0601.md) — generate your own with `python scripts/compare_sessions.py examples/<a> examples/<b>`.

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
