# Golf Swing Demo, 2026-05-31

This demo analyzes an open driving-range example video.
The source clip, pose export, metrics, report summary, and visual indexes are committed so the example is inspectable.

![Metric timeline](../assets/golf-swing-demo/metric_timeline.png)

![Skeleton keyposes](../assets/golf-swing-demo/skeleton_keyposes.png)

## Open Example Files

| File | Use |
| --- | --- |
| `examples/golf-swing-demo/golf.mp4` | Source golf swing clip |
| `examples/golf-swing-demo/pose_sequence.json` | MediaPipe pose landmarks for every frame |
| `examples/golf-swing-demo/metrics.csv` | Per-frame kinematic metrics |
| `examples/golf-swing-demo/summary.json` | Demo summary for reports |
| `examples/golf-swing-demo/contact_sheet.jpg` | Full-video visual index |
| `examples/golf-swing-demo/swing_timeline.jpg` | Human-check timeline for event labels |

## Video and Detection

- Duration: 7.19s
- Resolution: 320x568
- FPS: 30.05
- Pose coverage: 216 of 216 frames (100.0%)
- Mean landmark visibility: 0.814

## Detected Swing Events

Event labels are human-checked for this first example. `Impact` is treated as an impact or low-point proxy because the pipeline does not yet track the ball or club head.

| Swing | Label | Address | Top | Impact proxy | Finish | Backswing | Downswing | Tempo ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 |  | 0.77s | 2.70s | 3.93s | 4.83s | 1.93s | 1.23s | 1.57 |
| 2 |  | 4.03s | 5.66s | 6.96s | 7.16s | 1.63s | 1.30s | 1.26 |

## Main Read

- The clip contains two detectable swing cycles plus reset time.
- Pose coverage is strong enough for a first body-kinematics pass.
- The first motion is a slower practice motion; the second motion is the fuller shot-like swing.
- The current analysis measures body posture and timing. It does not yet measure club speed, ball speed, spin, carry distance, or launch angle.
- The next technical step is to use these labels to validate the automatic event detector, then add club and ball tracking.

## Technology Layers Used

1. Video QA: resolution, duration, frame rate, and pose coverage.
2. MediaPipe Pose Landmarker: frame-level body landmarks.
3. Kinematic geometry: elbows, knees, shoulder-hip separation, hand height, and drift proxies.
4. Temporal analysis: address, top, impact proxy, finish, backswing time, downswing time, and tempo ratio.
5. Open example publication: source clip, pose export, metrics, and report assets.

## Per-Swing Metrics

| Swing | Top lead arm | Top trail elbow | Top shoulder-hip separation | Impact head drift | Finish hip drift |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 166.5 deg | 155.3 deg | 5.1 deg | 0.027 | 0.008 |
| 2 | 146.0 deg | 176.4 deg | 5.9 deg | 0.560 | 0.042 |

## Interpretation

These numbers are best used as a personal baseline, not as universal coaching truth. The strongest immediate value is repeatability: new sessions can be compared against this first local baseline.

## First Coaching Read

- Camera and lighting were good enough for full-frame pose coverage, but the side/back angle limits true 3D rotation analysis.
- Both motions reached the checked top position about 1.20s after address, while the fuller second swing moved from top to impact proxy faster.
- Head and hip drift are now measurable baselines. Future sessions should compare against these values rather than against a generic pro template first.
- Shoulder-hip separation from a single vertical phone video is only a weak image-plane proxy. Treat it as a trend metric until 3D or multi-view capture is added.
