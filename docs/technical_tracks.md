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

### Implementation Retrospective: What We Tried and Where It Breaks

We shipped an initial ball detection pipeline (`scripts/golf_render.py`) and tested it across four real practice videos. The honest assessment is that the results are visually unreliable. This section records what we learned so the next implementation does not repeat the same mistakes.

#### What we built

The pipeline uses three layers stacked on top of each other:

1. **Body exclusion mask.** Dilate all skeleton keypoints into a filled mask and subtract it from the search region. This removes most of the golfer's arms and torso from the candidate pool.
2. **Farneback optical flow + direction filter.** Compute per-pixel velocity vectors. After a few frames of observation, accumulate a dominant flow direction for the ball and discard blobs pointing more than 75 degrees away from it. The intention is to reject the club head, which follows a circular arc back toward the body after impact.
3. **RANSAC parabolic fit.** A ball in flight follows projectile physics: x is linear in time, y is quadratic. Run RANSAC to find the largest subset of detected points that fits a parabola and discard the rest.

#### Where it still fails

**The club head problem is not fully solved.** At 30 fps, the club head and the ball occupy nearly identical positions for the first 3–5 frames after impact. We skip those frames deliberately, but the club head is still bright, metallic, and moving fast in the frames that follow. The direction filter helps but does not eliminate the confusion because the club head's follow-through arc and the ball's early flight can point in similar directions for the first few observable frames.

**30 fps is the fundamental constraint.** At a moderate golf swing speed of 80 mph, the ball travels roughly 80–100 pixels between frames in a 320-pixel-wide video. In a 720-pixel-wide video it travels 180–220 pixels. The ball is visible in only 3–8 frames before it exits the frame entirely. With so few observations, any detector that relies on multi-frame consistency has almost no signal to work with.

**Brightness and size overlap.** A golf ball (white, ~4–8 pixels wide at typical recording distance) is visually similar to a club face reflection (metallic, similarly sized and bright at impact). Simple brightness thresholds cannot separate them without spatial or temporal context.

**Camera motion compounds everything.** Several of the test videos (especially `Yifan-golf-06.01.mp4`) show significant camera shake. Frame differencing and optical flow both interpret camera motion as scene motion, flooding the candidate pool with false positives across the entire frame.

#### What professional systems actually do

TopGolf, TrackMan, and Foresight Sports do not use standard video for ball tracking. Their hardware stack is fundamentally different:

| Capability | Professional system | What we have |
| --- | --- | --- |
| Capture rate | 200–2000 fps | 25–30 fps |
| Ball sensor | Doppler radar | None |
| Illumination | Controlled IR or strobe | Ambient light |
| Ball type | Standard or marked ball | Any ball |
| Compute | Dedicated DSP | CPU-bound OpenCV |

Radar systems (TrackMan) measure the Doppler shift of a radio wave reflected off the moving ball. They do not use video at all for trajectory. High-speed camera systems capture 200+ frames per second, giving 10–20 pixels of ball displacement per frame instead of 100+, which makes multi-frame tracking tractable with classical methods.

#### What would actually work for us

In priority order, from most to least practical for this project:

1. **Record in slow motion (120 fps).** Every modern iPhone supports 120 or 240 fps. At 120 fps and 80 mph ball speed, displacement drops from ~90 px/frame to ~22 px/frame. The ball becomes trackable with the same optical-flow approach, and direction filtering becomes far more discriminating because the club head and ball have time to separate visually.

2. **Manual labels for key demo clips.** Add a `ball_labels.csv` for the first 1–2 well-lit clips. Use those to build a correct visual story and calibrate what a good trajectory looks like before trying to detect it automatically.

3. **Fine-tune a small detector on golf-specific data.** TrackNet (designed for badminton) and its derivatives show that a small CNN trained on sport-specific frames can detect sub-pixel blurs of a fast ball. The training data requirement is significant, but a dataset of labeled golf ball positions from top-down range cameras would make this feasible.

4. **Radar or LiDAR as a future hardware path.** Out of scope for a phone-based app but worth noting as the technically correct long-term answer.

#### Current decision

The current overlay is honest about the limitation: `proxy` mode is displayed when no plausible trajectory is found. The ball trail renders as a best-effort visual. We do not claim it is a measured trajectory.

The next concrete step before claiming real ball tracking is to collect 120 fps clips from the same golfer and rerun the same pipeline. If the detection quality improves significantly, 120 fps capture becomes the documented requirement for this feature. If it does not, the correct path is a dedicated detector trained on labeled data.

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

1. Long-video highlight reel: count swings, rank them, and export the best clips.
2. Ball trajectory V0-V1.
3. Pseudo-3D skeleton V0-V1.
4. Club tracking.
5. 3D trajectory and mesh recovery.
6. Polished interactive viewer.

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
