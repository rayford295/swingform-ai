# Personal Data Program

## Purpose

SwingForm AI should become a long-term personal practice record, not a one-off demo. The project can learn from repeated golf and basketball sessions while keeping raw personal data private.

## Operating Principle

The public repository stores methods. The local workspace stores personal practice data.

```text
public git repo: code, docs, tests, synthetic examples, approved aggregate outputs
local machine: raw videos, pose exports, private reports, manual labels, session notes
```

This gives the project room to grow without forcing every practice video into a public artifact.

## Local Session Lifecycle

1. Record a practice video.
2. Register it with a local-only manifest.
3. Extract pose landmarks into `data/local/pose_exports/`.
4. Add manual phase labels for a few key frames.
5. Generate metrics and a markdown report.
6. Decide whether any aggregate result is safe to publish.

Register a session:

```bash
python scripts/register_local_session.py /path/to/golf.mp4 --sport golf
```

The command writes a manifest under `data/local/sessions/`, which is ignored by git.

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

## Privacy Boundary

Raw videos stay local. The repo can publish:

1. Code.
2. Documentation.
3. Synthetic examples.
4. De-identified aggregate metrics.
5. Approved screenshots or figures.

The repo should not publish:

1. Raw personal videos.
2. Faces or private practice locations.
3. Exact filming timestamps from private sessions.
4. Unapproved commercial app exports.
5. Medical or injury claims.

## Near-Term Plan

1. Register the first golf video as a private local session.
2. Add MediaPipe pose extraction when the runtime supports it.
3. Generate the first golf swing pose JSON and metrics report.
4. Build a small personal session index.
5. Add basketball after the golf loop can run end to end.

