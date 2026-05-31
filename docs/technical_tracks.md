# Technical Tracks

SwingForm AI now has two primary technical tracks:

1. Ball trajectory.
2. 3D-feeling motion review.

These tracks matter because they make the project visually compelling while staying tied to measurable data.

## Track 1: Ball Trajectory

### Why It Matters

Ball trajectory is the fastest way to make a sports-AI demo feel alive. For golf, it means ball launch, flight trace, carry proxy, and visual shot line. For basketball, it means shot arc, release point, entry angle proxy, and make or miss context.

### Technical Path

| Stage | Goal | Method |
| --- | --- | --- |
| V0 | Draw a clean 2D trail | Manual or semi-automatic labels on demo clips |
| V1 | Track the ball in video | YOLO-style detector plus ByteTrack or BoT-SORT |
| V2 | Smooth and predict | Kalman filtering, polynomial or projectile fitting, outlier removal |
| V3 | Estimate camera-aware trajectory | Camera calibration, court or range geometry, 2D-to-3D trajectory estimation |
| V4 | Make it beautiful | Glow trail, speed-coded path, impact/release marker, report-ready overlay |

### Open References

- TrackNet shows the classic sports-ball route: heatmap-based tracking for tiny, fast, blurry balls across consecutive frames. It is not golf-specific, but the problem shape is close enough to learn from.
- Ultralytics YOLO tracking supports video object tracking through configurable trackers such as ByteTrack and BoT-SORT, which is a practical first implementation path.
- Where Is The Ball estimates 3D ball trajectory from 2D monocular tracking. This is the right long-term direction once our 2D tracking is stable.

### First SwingForm Implementation

Start with something visually useful:

1. Add `examples/golf-swing-demo/ball_labels.csv` for a handful of manually checked ball positions.
2. Render a bright ball path overlay on the source clip.
3. Fit a smooth curve through visible ball positions.
4. Save `ball_trajectory.json`, `ball_trail_overlay.mp4`, and a report image.
5. Only after the visual story works, train or fine-tune a detector.

This keeps the project moving fast and makes the demo immediately stronger.

## Track 2: 3D-Feeling Motion Review

### Why It Matters

Flat 2D pose plots are useful, but 3D-feeling review is what makes the project feel premium. The goal is not to claim lab-grade biomechanics. The goal is to create a clean motion review that helps people see body shape, rotation, timing, and progress.

### Technical Path

| Stage | Goal | Method |
| --- | --- | --- |
| V0 | Better visual skeleton | Smooth 2D pose, keypose cards, motion trails |
| V1 | Pseudo-3D skeleton | Use MediaPipe world landmarks or lift 2D pose into 3D coordinates |
| V2 | Temporal 3D pose | VideoPose3D-style lifting from 2D keypoint trajectories |
| V3 | 3D human mesh | WHAM or HMR-style mesh recovery for body shape and motion |
| V4 | Cinematic review | Three.js scene, camera orbit, ghosted previous swing, side-by-side sessions |

### Open References

- VideoPose3D is a mature reference for lifting 2D keypoint trajectories into 3D pose.
- WHAM is a stronger world-grounded human motion direction for video, but it brings model downloads, SMPL registration, and heavier runtime assumptions.
- Mesh-based approaches look better, but the first open demo should use a lightweight 3D skeleton before adding full mesh recovery.

### First SwingForm Implementation

Start with a polished 3D skeleton viewer:

1. Export `pose_sequence_3d.json` with normalized 3D landmarks.
2. Add a `docs/assets/golf-swing-demo/pose_3d_preview.png`.
3. Add a small Three.js viewer under `viewer/` or `docs/viewer/`.
4. Show address, top, impact proxy, and finish as a 3D orbitable skeleton.
5. Later add body mesh recovery as an optional offline pipeline.

## OpenAI Angle

OpenAI has useful generative-media references, but we should not make OpenAI the core 3D analysis dependency.

- Point-E is an OpenAI research system for generating 3D point clouds from prompts. It is useful inspiration for 3D asset generation, not sports biomechanics.
- Shap-E is OpenAI research code for generating 3D objects from text or images. It can inspire object or scene assets, not direct swing reconstruction.
- Sora is video generation, not a 3D reconstruction engine. The official OpenAI docs describe Sora as understanding 3D space, motion, and scene continuity, but also note that Sora 2 video API models are deprecated and scheduled to shut down on September 24, 2026.

Use OpenAI-style generation for presentation polish, concept videos, or future visual storytelling. Use pose, tracking, physics, and 3D reconstruction libraries for the actual measurements.

## Priority Decision

Focus order:

1. Ball trajectory V0-V1.
2. Pseudo-3D skeleton V0-V1.
3. Club tracking.
4. 3D trajectory and mesh recovery.
5. Polished interactive viewer.

The project should look impressive early, but every impressive visual should map back to an input video, a detection, a pose landmark, or a fitted trajectory.

## Sources

- OpenAI Point-E: https://openai.com/index/point-e/
- OpenAI Shap-E: https://github.com/openai/shap-e
- OpenAI Sora video generation docs: https://developers.openai.com/api/docs/guides/video-generation
- TrackNet paper: https://arxiv.org/abs/1907.03698
- Where Is The Ball paper: https://arxiv.org/abs/2506.05763
- Ultralytics YOLO tracking docs: https://docs.ultralytics.com/modes/track/
- WHAM: https://github.com/yohanshin/WHAM
- VideoPose3D: https://github.com/facebookresearch/VideoPose3D
