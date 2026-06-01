# Architecture

## Design Principle

The project should separate sport-independent pose processing from sport-specific interpretation.

```text
Video or JSON
  -> frame sampler
  -> pose backend
  -> normalized landmark sequence
  -> sport profile
  -> phase timeline
  -> metric table
  -> report and visual overlay
```

The long-video product workflow adds a parallel highlight layer:

```text
Long video
  -> motion timeline
  -> swing candidates
  -> clip-selection score
  -> best clips
  -> ball trajectory overlay
  -> highlight reel
```

## Core Modules

| Module | Responsibility |
| --- | --- |
| `schema` | Shared landmark, frame, and sequence objects |
| `geometry` | Angles, distances, normalization, and stability helpers |
| `profiles.golf` | Golf events, lead/trail side logic, and swing metrics |
| `profiles.basketball` | Shot phases, shooting side logic, and shot-form metrics |
| `analyze_pose_json` | Tiny CLI for testing metrics before video backends are added |
| `highlight` | Long-video swing candidates, transparent scoring, and clip windows |

## Pose Backend Strategy

Start with JSON input and a MediaPipe backend. This keeps tests deterministic while allowing quick work on personal videos.

Later backends should follow the same contract:

```python
def infer_pose(video_path: str) -> PoseSequence:
    ...
```

Each backend must output the same landmark names where possible. Backend-specific confidence, visibility, and world-coordinate metadata should remain attached to landmarks.

## Sport Profile Contract

A sport profile should define:

1. Phase names.
2. Metric names.
3. Required landmarks.
4. Metric functions.
5. Optional feedback rules.

The profile should not know whether landmarks came from MediaPipe, YOLO, MMPose, or manual labels.

## Golf Pipeline

```text
video
  -> single-person pose
  -> swing event timeline
  -> address/top/impact/finish metrics
  -> tempo and stability summary
  -> feedback report
```

Golf-specific logic should remain in `profiles/golf.py`.

## Highlight-Reel Pipeline

```text
long practice video
  -> frame-difference motion stats
  -> swing-like segment detection
  -> transparent clip score
  -> top-k clip export
  -> label-based or proxy ball trail
  -> combined highlight reel
```

The current scorer is a clip-selection model. It ranks moments that are clear,
complete, stable, and worth saving from a long practice session. It should not
be described as a technical golf-quality score until ball, club, and pose-aware
event models are added.

## Basketball Pipeline

```text
video
  -> single-person pose
  -> shot phase timeline
  -> release and follow-through metrics
  -> own-best-shot comparison
  -> feedback report
```

Basketball-specific logic should remain in `profiles/basketball.py`.

## Future Model Layers

1. Phase classifier: classify frame sequences into golf swing events or basketball shot phases.
2. Metric scorer: learn which metric deviations matter for the user's own outcomes.
3. Retrieval layer: compare a new session against previous personal sessions.
4. Feedback layer: translate metrics into short coaching notes with citations to the measured frames.
