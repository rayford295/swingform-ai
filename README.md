# SwingForm AI

<p align="center">
  <img src="docs/assets/readme/hero.png" alt="SwingForm AI golf swing analysis hero" width="980">
</p>

<p align="center">
  <a href="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/rayford295/swingform-ai/actions/workflows/test.yml/badge.svg"></a>
  <a href="./LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-2f6f4e"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2458a6">
  <img alt="Sports" src="https://img.shields.io/badge/sports-golf%20%2B%20basketball-c46a2c">
</p>

SwingForm AI is an open-source sports-AI toolkit for turning real practice video into pose landmarks, swing phases, and explainable posture metrics. Golf is the first profile. Basketball shot form is built into the architecture as the next sport profile.

This is not a paper repository. It is meant to be beautiful, inspectable, practical, and fun to improve.

```text
practice video -> pose landmarks -> movement phase -> biomechanical metrics -> feedback
```

The next concrete workflow is:

```text
long practice video -> swing count -> best swings -> short highlight reel -> ball-trail overlay
```

## Open Demo

The first golf sample is committed as a full open example. The repo includes the source clip, pose export, metrics, report summary, and visual indexes.

| Signal | Value |
| --- | ---: |
| Video length | 14.44s |
| Resolution | 320x568 |
| Pose coverage | 361 / 361 frames |
| Detected swing cycles | 2 |
| Mean landmark visibility | 0.805 |

![Golf swing metric timeline](docs/assets/golf-swing-demo/metric_timeline.png)

![Golf swing skeleton keyposes](docs/assets/golf-swing-demo/skeleton_keyposes.png)

| File | Use |
| --- | --- |
| [examples/golf-swing-demo/golf.mp4](examples/golf-swing-demo/golf.mp4) | Source golf swing clip |
| [examples/golf-swing-demo/pose_sequence.json](examples/golf-swing-demo/pose_sequence.json) | MediaPipe pose landmarks for every frame |
| [examples/golf-swing-demo/metrics.csv](examples/golf-swing-demo/metrics.csv) | Per-frame kinematic metrics |
| [examples/golf-swing-demo/summary.json](examples/golf-swing-demo/summary.json) | Demo summary for reports |
| [examples/golf-swing-demo/contact_sheet.jpg](examples/golf-swing-demo/contact_sheet.jpg) | Full-video visual index |
| [examples/golf-swing-demo/swing_timeline.jpg](examples/golf-swing-demo/swing_timeline.jpg) | Human-check timeline for event labels |

Read the full demo report in [docs/examples/golf_swing_demo_2026-05-31.md](docs/examples/golf_swing_demo_2026-05-31.md).

## Quickstart

Install the package:

```bash
python -m pip install -e .
```

Run the tiny JSON metric demo:

```bash
python -m swingform_ai.analyze_pose_json examples/sample_pose_sequence.json --sport golf
python -m swingform_ai.analyze_pose_json examples/sample_pose_sequence.json --sport basketball
```

Analyze the open golf video:

```bash
python -m pip install -e ".[pose]"
python scripts/analyze_local_golf_video.py \
  examples/golf-swing-demo/golf.mp4 \
  --session-id golf-swing-demo \
  --handedness right \
  --events-json examples/golf_swing_demo_events.json
```

Build a highlight reel from a longer practice video:

```bash
python scripts/build_highlight_reel.py path/to/long_practice_video.mp4 \
  --session-id range-session-001 \
  --top-k 3 \
  --shot-direction right
```

Run tests:

```bash
python -m unittest discover -s tests
```

## What It Measures

SwingForm AI currently measures body kinematics from single-camera pose landmarks.

| Layer | Current capability |
| --- | --- |
| Video QA | Duration, frame rate, resolution, frame coverage |
| Pose estimation | MediaPipe Pose Landmarker body landmarks |
| Golf phases | Address, top, impact or low-point proxy, finish |
| Metrics | Elbow angle, knee angle, hand height, wrist speed, shoulder-hip proxy, head and hip drift |
| Reports | Markdown report, JSON summary, CSV metrics, skeleton keyposes, timeline chart |
| Highlight reel | Long-video swing count, transparent clip score, best-swing export, ball-trail overlay |

Current limits are explicit: it does not yet measure club-head speed, ball speed, spin, launch angle, or carry distance.

## Technical Focus

The next phase focuses on two visual intelligence tracks:

1. Ball trajectory: ball detection, trail rendering, trajectory smoothing, and later camera-aware 3D flight.
2. 3D-feeling motion review: pseudo-3D skeletons, motion trails, and later world-grounded human motion reconstruction.

See [docs/technical_tracks.md](docs/technical_tracks.md) for the implementation path and references.

## Project Map

| Path | Use |
| --- | --- |
| `examples/golf-swing-demo/` | Open source video, pose export, metrics, and report inputs |
| `docs/examples/` | Human-readable demo reports |
| `docs/assets/` | README and report visuals |
| `scripts/analyze_local_golf_video.py` | Golf video analyzer with open demo export |
| `scripts/build_highlight_reel.py` | Long-video highlight reel builder |
| `scripts/register_local_session.py` | Local session manifest tool |
| `src/swingform_ai/` | Pose schema, geometry, profiles, and CLI helpers |
| `tests/` | Geometry, profile, and local-session tests |
| `docs/requirements.md` | Product requirements and MVP scope |
| `docs/architecture.md` | Video, pose, phase, metric, and feedback architecture |
| `docs/roadmap.md` | Milestone plan |
| `docs/technical_tracks.md` | Ball trajectory and 3D motion review plan |
| `docs/highlight_reel_pipeline.md` | Long-video input to short-video output workflow |

## Design Principles

1. Beauty matters: the README, charts, and reports should be easy to scan.
2. Open examples matter: a visitor should see source input and derived output together.
3. Practical metrics matter: every score should point to a frame, phase, or measurable posture.
4. Sport profiles stay separate: golf and basketball share the pose core but keep their own phases and metrics.
5. Claims stay calibrated: single-camera pose is useful, but it is not a launch monitor or a certified coach.

Read the project taste and long-term direction in [docs/north_star.md](docs/north_star.md).

## Roadmap

Near-term:

1. Turn long practice videos into scored highlight reels.
2. Add ball trajectory tracking and a polished trail overlay.
3. Add pseudo-3D skeleton review.
4. Add club tracking and cleaner event detection.

Long-term:

1. Build camera-aware 3D ball flight and shot arc.
2. Compare new sessions against a personal best library.
3. Build a lightweight local web app for practice review.
4. Grow a clean open dataset of cleared sports practice examples.

## Contributing

Contributions should improve usefulness, beauty, reproducibility, or sport coverage. Start with [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- [中文说明](./README.zh-CN.md)
- [Technology and product scan](docs/research_scan_2026-05-31.md)
- [North Star](docs/north_star.md)
- [Technical tracks](docs/technical_tracks.md)
- [Highlight-reel pipeline](docs/highlight_reel_pipeline.md)
- [Open-source data boundary](docs/data_governance.md)
- [Personal data program](docs/personal_data_program.md)
