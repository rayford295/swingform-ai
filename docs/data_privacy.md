# Personal Data Program

## Purpose

SwingForm AI should become a long-term personal practice record, not a one-off demo. The project can learn from repeated golf and basketball sessions while publishing examples that are explicitly cleared for open-source release.

## Operating Principle

The public repository stores methods and cleared examples. The local workspace stores drafts, experiments, and files not yet ready to publish.

```text
public git repo: code, docs, tests, cleared videos, pose exports, metrics, reports
local machine: drafts, uncategorized captures, temporary model files, private notes
```

This gives the project room to grow while making the open examples genuinely inspectable.

## Local Session Lifecycle

1. Record a practice video.
2. Register it with a local-only manifest.
3. Extract pose landmarks into `data/local/pose_exports/`.
4. Add manual phase labels for a few key frames.
5. Generate metrics and a markdown report.
6. Move the video and derived outputs into `examples/<demo-name>/` when the sample is cleared for release.

Register a session:

```bash
python scripts/register_local_session.py /path/to/golf.mp4 --sport golf
```

The command writes a manifest under `data/local/sessions/`, which is ignored by git until the session is promoted into an open example.

## Longitudinal Metrics

Track metrics that can improve through practice:

| Sport | Metric family | Why it matters |
| --- | --- | --- |
| Golf | Address posture | Establishes a repeatable starting shape |
| Golf | Shoulder-hip separation | Captures rotation pattern in the swing |
| Golf | Lead arm and trail elbow angle | Describes backswing structure and arm position |
| Golf | Head and balance proxy | Helps identify large body drift across the swing |
| Golf | Tempo between phases | Supports consistent rhythm across sessions |
| Basketball | Shooting elbow angle | Captures release shape and alignment |
| Basketball | Wrist and release-height proxy | Tracks release position over time |
| Basketball | Knee and hip extension | Captures lower-body contribution |
| Basketball | Landing balance | Checks whether the shot ends under control |

The first comparison should be against Yifan's own best sessions. Public pro templates can be useful later, but self-comparison is less noisy and more respectful of individual style.

## Annotation Strategy

Start small:

1. Label five to ten golf videos with address, top, impact, and finish.
2. Label five to ten basketball shots with set, dip, release, follow-through, and landing.
3. Use those labels to validate automatic phase detection.
4. Keep uncertain labels instead of forcing false precision.

## Open-Source Release Boundary

The repo can publish cleared examples:

1. Code.
2. Documentation.
3. Synthetic examples.
4. Raw practice videos that are intentionally released.
5. Pose exports, metric tables, reports, screenshots, and figures.

The repo should not publish:

1. Unreviewed captures.
2. Unapproved commercial app exports.
3. Credentials, cookies, keys, or model weights that should be downloaded upstream.
4. Medical or injury claims.

## Near-Term Plan

1. Register the first golf video as a local session.
2. Add MediaPipe pose extraction when the runtime supports it.
3. Generate the first golf swing pose JSON and metrics report.
4. Build a small personal session index.
5. Add basketball after the golf loop can run end to end.
