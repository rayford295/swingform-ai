# Requirements

## Project Purpose

SwingForm AI should turn personal sports practice video into interpretable posture feedback. The project begins with golf swing analysis and keeps the core general enough for basketball shooting form.

## Intended Users

1. Yifan as a golfer and basketball player who wants self-review from practice videos.
2. Research collaborators who want a clear computer-vision and sports-analytics prototype.
3. Future open-source users who want to inspect methods rather than use a closed coaching app.

## Non-Goals

1. Do not replace a certified coach.
2. Do not claim professional biomechanical accuracy without validation.
3. Do not infer private health or injury conditions.
4. Do not commit raw personal videos, faces, or commercial app exports.

## MVP Scope

| Capability | MVP behavior | Later behavior |
| --- | --- | --- |
| Video input | Local video path or exported pose JSON | Mobile capture, webcam, cloud batch processing |
| Pose backend | MediaPipe first, JSON fallback always available | YOLO pose, MMPose, RTMPose, 3D reconstruction |
| Sport profile | Golf first | Basketball shot profile, later tennis or baseball |
| Phase detection | Rule-based or manually annotated phase placeholders | Learned phase model trained on public or self-labeled data |
| Metrics | Joint angles, torso proxy, balance proxy, tempo | 3D kinematics, ball flight, club trajectory |
| Feedback | Short deterministic rule report | LLM-assisted plain-language coaching notes |
| Output | JSON, markdown report, annotated frames | Dashboard, web app, mobile app |

## Golf Requirements

The first golf profile should track:

1. Address posture.
2. Backswing progression.
3. Top position.
4. Downswing transition.
5. Impact posture.
6. Follow-through and finish.

The first metrics should include:

1. Lead arm angle.
2. Trail elbow angle.
3. Lead knee flexion.
4. Trail knee flexion.
5. Shoulder-hip separation proxy.
6. Head stability proxy.
7. Tempo proxy between key events.
8. Balance proxy from ankle and hip alignment.

## Basketball Requirements

The basketball profile should track:

1. Set.
2. Dip.
3. Lift.
4. Release.
5. Follow-through.
6. Landing.

The first metrics should include:

1. Shooting elbow angle.
2. Shooting wrist extension proxy.
3. Knee bend.
4. Hip extension.
5. Release height proxy.
6. Shoulder alignment.
7. Landing balance.
8. Own-best-shot distance.

## Evaluation Requirements

For the first research milestone:

1. Run on at least five personal or public golf videos stored outside git.
2. Save only de-identified metric CSVs or synthetic examples in git.
3. Compare automatically detected phases against manual labels.
4. Report failure modes, especially camera angle, occlusion, lighting, and loose clothing.
5. Keep all commands reproducible from the README.

## Repository Requirements

1. Keep docs, code, examples, and tests separate.
2. Use small committed examples only.
3. Add tests for geometry, metric calculation, and JSON parsing.
4. Treat model weights and raw videos as local artifacts.
5. Keep public README factual and modest.

